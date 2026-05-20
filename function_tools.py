import uuid
import json

import chromadb
from chromadb.config import Settings
from models import *
from functools import wraps
from pypinyin import pinyin, Style
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from logger_config import logger, log_retrieval, log_llm_call, log_document_process, log_api_request, log_error

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("[依赖] PyPDF2 未安装，PDF 文件支持不可用。请运行: pip install PyPDF2")


# ChromaDB 向量数据库类
class MyVectorDBConnector:

    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./chroma")
        self.client = get_normal_client()

    def get_embeddings(self, texts, model=ALI_TONGYI_EMBEDDING_V4):
        data = self.client.embeddings.create(input=texts, model=model).data
        return [x.embedding for x in data]

    def get_embeddings_batch(self, texts, model=ALI_TONGYI_EMBEDDING_V4, batch_size=10):
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_text = texts[i:i + batch_size]
            data = self.client.embeddings.create(input=batch_text, model=model).data
            all_embeddings.extend([x.embedding for x in data])
        return all_embeddings

    def add_documents(self, documents, collection_name='demo', source_file=''):
        """向 collection 中添加文档与向量，包含 metadata"""
        logger.info(f"[向量DB] 添加文档到集合: {collection_name}, 文档块数: {len(documents)}, 来源: {source_file}")
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i: i + batch_size]
            # 为每个文档块构建 metadata：来源文件名、块索引、块大小
            metadatas = [
                {
                    "source": source_file,
                    "chunk_index": i + j,
                    "chunk_size": len(doc),
                }
                for j, doc in enumerate(batch_docs)
            ]
            collection.add(
                embeddings=self.get_embeddings(batch_docs),
                documents=batch_docs,
                ids=[str(uuid.uuid4()) for _ in batch_docs],
                metadatas=metadatas,
            )
        log_document_process(source_file, len(documents), collection_name)

    def search(self, query, collection_name='demo', n_results=5):
        """检索向量数据库，返回文档+metadata+距离"""
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

        results = collection.query(
            query_embeddings=self.get_embeddings([query]),
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        log_retrieval(query, collection_name, n_results, results)
        return results


# 读取Word文档
def extract_text_from_docx(filename):
    """从 DOCX 文件中提取文字并分块"""
    logger.info(f"[文档处理] 正在读取 DOCX: {filename}")
    full_text = ''
    doc = Document(filename)
    for para in doc.paragraphs:
        if para.text.strip():
            full_text += para.text + '\n'

    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    documents = splitter.split_text(full_text)

    logger.info(f"[文档处理] DOCX 分块完成: {len(documents)} 个块")
    return documents


# 读取PDF文档
def extract_text_from_pdf(filename):
    """从 PDF 文件中提取文字并分块"""
    if not PDF_SUPPORT:
        log_error("PDF处理", "PyPDF2 未安装，无法处理 PDF 文件")
        return []

    logger.info(f"[文档处理] 正在读取 PDF: {filename}")
    full_text = ''
    try:
        reader = PdfReader(filename)
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text and page_text.strip():
                full_text += f"[第{page_num + 1}页] {page_text}\n"
    except Exception as e:
        log_error("PDF处理", f"读取 PDF 失败: {str(e)}", detail=filename)
        return []

    if not full_text.strip():
        logger.warning(f"[文档处理] PDF 内容为空: {filename}")
        return []

    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    documents = splitter.split_text(full_text)
    logger.info(f"[文档处理] PDF 分块完成: {len(documents)} 个块")
    return documents


# 访问大模型
def get_completion(prompt, model=ALI_TONGYI_TURBO_MODEL):
    """封装 openai 接口"""
    client = get_normal_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    result = response.choices[0].message.content
    log_llm_call(prompt, result, model)
    return result


# 生成结构化摘要
def generate_summary(collection_name='demo', n_results=10, model=ALI_TONGYI_TURBO_MODEL):
    """从向量库检索文档内容，生成结构化摘要"""
    vector_db = MyVectorDBConnector()
    # 检索足够多的文档块来生成全面摘要
    search_results = vector_db.search("文档摘要 概述 主要内容", collection_name=collection_name, n_results=n_results)

    docs = search_results['documents'][0]
    content = '\n'.join(docs)

    prompt = f"""
    你是一个文档摘要专家。请根据下述文档内容生成一份结构化摘要，包含以下三个部分：

    1. **文档概述**：一句话概括文档的核心主题和用途。
    2. **关键要点**：提取3-5个最重要的要点或规定，每个要点用编号列出。
    3. **详细摘要**：200字左右的详细内容摘要。

    请严格按照上述格式输出，使用中文。

    文档内容:
    {content}
    """

    response = get_completion(prompt, model=model)
    log_llm_call(prompt, response, model)
    return response


# 装饰器：中文->英文
def to_pinyin(fn):
    @wraps(fn)
    def chinese_to_pinyin(*args, **kwargs):
        chinese_name = kwargs['collection_name']
        chinese_name = chinese_name.replace('.', '')
        pinyin_list = pinyin(chinese_name, style=Style.NORMAL, heteronym=False)
        pinyin_str = ''.join([word[0].lower() for word in pinyin_list])
        kwargs['collection_name'] = pinyin_str
        return fn(*args, **kwargs)
    return chinese_to_pinyin