"""
日志模块 - 记录RAG系统的关键中间过程
包括: 文档处理、向量检索结果、LLM调用、API请求等
"""
import logging
import os
import sys
from datetime import datetime

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"rag_{datetime.now().strftime('%Y%m%d')}.log")

logger = logging.getLogger("RAG_System")
logger.setLevel(logging.DEBUG)

# 控制台handler - INFO级别
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_fmt = logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(console_fmt)

# 文件handler - DEBUG级别(记录所有细节)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_fmt = logging.Formatter(
    '[%(asctime)s] %(levelname)s [%(funcName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_fmt)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def log_retrieval(query, collection_name, n_results, results):
    """记录检索过程"""
    docs = results.get('documents', [[]])[0]
    distances = results.get('distances', [[]])[0]
    logger.info(f"[检索] 查询: '{query}' | 集合: {collection_name} | 返回 {len(docs)} 条结果")
    for i, (doc, dist) in enumerate(zip(docs, distances)):
        logger.debug(f"[检索] Top{i+1} (距离={dist:.4f}): {doc[:100]}...")


def log_llm_call(prompt, response, model="qwen-turbo-latest"):
    """记录LLM调用"""
    prompt_preview = prompt[:200].replace('\n', ' ')
    response_preview = response[:200].replace('\n', ' ')
    logger.info(f"[LLM] 模型: {model} | Prompt长度: {len(prompt)} | 回复长度: {len(response)}")
    logger.debug(f"[LLM] Prompt: {prompt_preview}...")
    logger.debug(f"[LLM] Response: {response_preview}...")


def log_document_process(filepath, chunk_count, collection_name):
    """记录文档处理"""
    logger.info(f"[文档处理] 文件: {filepath} | 分块数: {chunk_count} | 集合: {collection_name}")


def log_api_request(endpoint, method, params=None):
    """记录API请求"""
    logger.info(f"[API] {method} {endpoint}" + (f" | 参数: {params}" if params else ""))


def log_error(module, error_msg, detail=None):
    """记录错误"""
    logger.error(f"[错误] {module}: {error_msg}")
    if detail:
        logger.debug(f"[错误详情] {detail}")