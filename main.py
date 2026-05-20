# main.py
from function_tools import *
import json

# --------------   1. 上传文档  -------------- #
vector_db = MyVectorDBConnector()

@to_pinyin
def save_to_db(filepath, collection_name='demo'):
    logger.info(f"[上传] 正在存入文档: filepath={filepath}, collection={collection_name}")
    documents = []

    if filepath.endswith('.docx') or filepath.endswith('.doc'):
        documents = extract_text_from_docx(filepath)
    elif filepath.endswith('.pdf'):
        documents = extract_text_from_pdf(filepath)

    if not documents:
        logger.warning(f"[上传] 文件内容为空: {filepath}")
        return '读取文件内容为空'

    # 存入向量数据库，带上来源文件名
    vector_db.add_documents(documents, collection_name=collection_name, source_file=collection_name)
    return '文档已成功存入'


# --------------  2. 聊天    -------------- #
@to_pinyin
def rag_chat(user_query, collection_name='demo', n_results=5):
    """检索知识库 => top5相关文档 => LLM => 答案(含引用来源)"""
    logger.info(f"[问答] 查询: '{user_query}', 集合: {collection_name}")

    # 1. 检索知识库
    search_results = vector_db.search(user_query, collection_name=collection_name, n_results=n_results)

    # 2. 构建带引用标注的 Prompt
    docs = search_results['documents'][0]
    metadatas = search_results.get('metadatas', [[]])[0]
    distances = search_results.get('distances', [[]])[0]

    # 为每个检索到的块标注来源编号
    context_with_refs = []
    sources_info = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances)):
        ref_label = f"[来源{i+1}]"
        context_with_refs.append(f"{ref_label} {doc}")
        sources_info.append({
            "ref_id": i + 1,
            "chunk_index": meta.get("chunk_index", "N/A") if meta else "N/A",
            "source": meta.get("source", "未知") if meta else "未知",
            "chunk_size": meta.get("chunk_size", len(doc)) if meta else len(doc),
            "distance": round(dist, 4) if dist else 0,
            "content_preview": doc[:80] + "..." if len(doc) > 80 else doc,
        })

    context_text = '\n'.join(context_with_refs)

    prompt = f"""
    你是一个问答机器人。
    你的任务是根据下述给定的已知信息回答用户问题。

    重要规则：
    1. 确保你的回复完全依据下述已知信息，不要编造答案。
    2. 如果已知信息不足以回答用户的问题，请直接回复"我无法回答您的问题"。
    3. 在回答时，请在相关陈述后标注来源编号，格式为[来源X]，其中X对应已知信息中的编号。
    4. 请用中文回答。

    已知信息:
    {context_text}

    用户问：
    {user_query}
    """

    # 3. 调用 LLM 生成答案
    response = get_completion(prompt)

    # 4. 返回结构化数据
    result = {
        "answer": response,
        "sources": sources_info,
    }
    log_llm_call(prompt, response)
    return json.dumps(result, ensure_ascii=False)


# --------------  3. 摘要    -------------- #
@to_pinyin
def rag_summary(collection_name='demo', n_results=10):
    """生成文档结构化摘要"""
    logger.info(f"[摘要] 请求生成摘要, 集合: {collection_name}")
    summary = generate_summary(collection_name=collection_name, n_results=n_results)
    result = {
        "summary": summary,
        "collection_name": collection_name,
    }
    return json.dumps(result, ensure_ascii=False)


# 测试代码
if __name__ == '__main__':
    # 测试1：上传文档并问答
    save_to_db(filepath='uploads/人事管理流程.docx', collection_name='人事管理流程.docx')

    user_query = "视为不符合录用条件的情形有哪些?"
    response = rag_chat(user_query, collection_name='人事管理流程.docx', n_results=5)
    print("问答结果:", response)

    # 测试2：生成摘要
    summary = rag_summary(collection_name='人事管理流程.docx')
    print("摘要结果:", summary)