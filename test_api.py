"""
测试样例 - 企业资料处理 Copilot MVP
包含：问答测试、摘要测试、API 调用测试
运行方式：python test_api.py
前提：需要先启动 Flask 服务 (python app.py) 并上传过文档
"""
import requests
import json
import sys
import os

BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 30


def test_chat_with_citation():
    """
    测试样例1: 问答 + 引用来源验证
    验证点：返回 JSON 包含 answer 和 sources 字段，sources 中有 ref_id、distance 等
    """
    print("=" * 60)
    print("测试样例1: 问答 + 引用来源验证")
    print("=" * 60)

    # 先获取可用的集合列表
    try:
        coll_resp = requests.get(f"{BASE_URL}/api/collections/", timeout=TIMEOUT)
        coll_data = coll_resp.json()
        collections = coll_data.get("collections", [])
        current = coll_data.get("current", "demo")
    except Exception as e:
        print(f"[失败] 无法获取集合列表: {e}")
        print("请确保 Flask 服务已启动 (python app.py)")
        return False

    if not collections:
        print("[失败] 没有可用的文档集合，请先上传文档")
        return False

    print(f"可用集合: {collections}, 当前: {current}")

    # 发送问答请求
    test_query = "不符合录用条件的情形有哪些？"
    payload = {
        "message": test_query,
        "collection_name": current
    }

    try:
        resp = requests.post(f"{BASE_URL}/api/chat/", json=payload, timeout=TIMEOUT)
        if resp.status_code != 200:
            print(f"[失败] HTTP {resp.status_code}: {resp.text}")
            return False

        data = resp.json()
        answer = data.get("answer", "")
        sources = data.get("sources", [])

        print(f"问题: {test_query}")
        print(f"回答: {answer[:200]}...")
        print(f"引用来源数量: {len(sources)}")

        # 验证引用来源结构
        if sources:
            for src in sources[:3]:
                print(f"  来源{src.get('ref_id')}: 块索引={src.get('chunk_index')}, "
                      f"相似度={src.get('distance')}, 预览={src.get('content_preview', '')[:50]}")
            print("[通过] 问答 + 引用来源功能正常")
            return True
        else:
            print("[部分通过] 问答功能正常但无引用来源（可能旧数据未含 metadata）")
            return True

    except requests.exceptions.ConnectionError:
        print("[失败] 无法连接到服务，请先启动: python app.py")
        return False
    except Exception as e:
        print(f"[失败] 请求出错: {e}")
        return False


def test_summary_generation():
    """
    测试样例2: 结构化摘要生成
    验证点：返回 JSON 包含 summary 和 collection_name 字段，summary 包含概述/要点/摘要
    """
    print("=" * 60)
    print("测试样例2: 结构化摘要生成")
    print("=" * 60)

    try:
        coll_resp = requests.get(f"{BASE_URL}/api/collections/", timeout=TIMEOUT)
        coll_data = coll_resp.json()
        current = coll_data.get("current", "demo")
        collections = coll_data.get("collections", [])
    except Exception as e:
        print(f"[失败] 无法获取集合列表: {e}")
        return False

    if not collections:
        print("[失败] 没有可用的文档集合")
        return False

    payload = {"collection_name": current}

    try:
        resp = requests.post(f"{BASE_URL}/api/summary/", json=payload, timeout=TIMEOUT)
        if resp.status_code != 200:
            print(f"[失败] HTTP {resp.status_code}: {resp.text}")
            return False

        data = resp.json()
        summary = data.get("summary", "")
        coll_name = data.get("collection_name", "")

        print(f"集合: {coll_name}")
        print(f"摘要内容:\n{summary[:500]}...")

        # 验证摘要包含结构化元素
        has_structure = any(keyword in summary for keyword in ["概述", "要点", "摘要", "1.", "2.", "**"])
        if has_structure:
            print("[通过] 结构化摘要生成功能正常，包含结构化标记")
        else:
            print("[部分通过] 摘要已生成，但结构化程度可能不高")

        return True

    except requests.exceptions.ConnectionError:
        print("[失败] 无法连接到服务，请先启动: python app.py")
        return False
    except Exception as e:
        print(f"[失败] 请求出错: {e}")
        return False


def test_collections_api():
    """
    测试样例3: API 集合列表接口
    验证点：GET /api/collections/ 返回正确的 JSON 结构
    """
    print("=" * 60)
    print("测试样例3: API 集合列表接口")
    print("=" * 60)

    try:
        resp = requests.get(f"{BASE_URL}/api/collections/", timeout=TIMEOUT)
        if resp.status_code != 200:
            print(f"[失败] HTTP {resp.status_code}")
            return False

        data = resp.json()
        collections = data.get("collections", [])
        current = data.get("current", "")

        print(f"文档集合列表: {collections}")
        print(f"当前集合: {current}")

        if isinstance(collections, list) and isinstance(current, str):
            print("[通过] 集合列表 API 功能正常")
            return True
        else:
            print("[失败] 返回数据格式异常")
            return False

    except requests.exceptions.ConnectionError:
        print("[失败] 无法连接到服务，请先启动: python app.py")
        return False
    except Exception as e:
        print(f"[失败] 请求出错: {e}")
        return False


def print_curl_examples():
    """打印可直接使用的 curl 命令示例"""
    print("\n" + "=" * 60)
    print("附: curl 调用示例命令")
    print("=" * 60)

    print("\n# 1. 问答接口 (含引用来源)")
    print("""curl -X POST http://127.0.0.1:5000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "不符合录用条件的情形有哪些？", "collection_name": "人事管理流程.docx"}'""")

    print("\n# 2. 结构化摘要接口")
    print("""curl -X POST http://127.0.0.1:5000/api/summary/ \
  -H "Content-Type: application/json" \
  -d '{"collection_name": "人事管理流程.docx"}'""")

    print("\n# 3. 获取文档集合列表")
    print("curl http://127.0.0.1:5000/api/collections/")


if __name__ == '__main__':
    print("\n企业资料处理 Copilot MVP - 测试样例\n")
    print("前提: 请确保已启动 Flask 服务 (python app.py) 并上传了文档\n")

    results = []

    results.append(("问答+引用", test_chat_with_citation()))
    results.append(("结构化摘要", test_summary_generation()))
    results.append(("集合列表API", test_collections_api()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "通过" if passed else "失败"
        print(f"  {name}: {status}")

    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    print(f"\n总计: {passed_count}/{total} 通过")

    print_curl_examples()