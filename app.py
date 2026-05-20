from flask import Flask, render_template, request, flash, redirect, jsonify
import os
import re
import json

from main import *
from logger_config import logger, log_api_request, log_error

# 创建app对象
app = Flask(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'docx', 'doc', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 集合名称
collection_name = 'demo'
name_list = os.listdir(UPLOAD_FOLDER)
if name_list:
    collection_name = name_list[0]


# ------------------------------------------------------------------------- #
# -----------------------------   1. 上传文档  ----------------------------- #
# ------------------------------------------------------------------------- #
@app.route('/document_upload/', methods=['GET', 'POST'])
def document_upload():
    if request.method == 'GET':
        log_api_request('/document_upload/', 'GET')
        return render_template('document_upload.html')
    elif request.method == 'POST':
        log_api_request('/document_upload/', 'POST')
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            global collection_name
            collection_name = re.split(r'[/\\]', filename)[-1]
            result = save_to_db(file_path, collection_name=collection_name)
            logger.info(f"[上传] 文件上传完成: {filename}, 结果: {result}")

        return redirect(request.url)


# ------------------------------------------------------------------------- #
# ------------------------------   2. 聊天    ------------------------------ #
# ------------------------------------------------------------------------- #
@app.route('/')
@app.route('/chat/', methods=['GET', 'POST'])
def chat():
    if request.method == 'GET':
        log_api_request('/chat/', 'GET')
        return render_template('chat.html')
    elif request.method == 'POST':
        message = request.json.get('message')
        log_api_request('/chat/', 'POST', params={"message": message})

        if message:
            try:
                response_json = rag_chat(message, collection_name=collection_name, n_results=10)
                return response_json
            except Exception as e:
                log_error("聊天", str(e), detail=f"查询: {message}, 集合: {collection_name}")
                return jsonify({"answer": "抱歉，系统出现错误，请稍后再试。", "sources": []})
        else:
            return jsonify({"answer": "不知道", "sources": []})


# ------------------------------------------------------------------------- #
# -----------------------------   3. 文档摘要   ----------------------------- #
# ------------------------------------------------------------------------- #
@app.route('/summary/', methods=['GET', 'POST'])
def summary():
    if request.method == 'GET':
        log_api_request('/summary/', 'GET')
        return render_template('chat.html', mode='summary')
    elif request.method == 'POST':
        log_api_request('/summary/', 'POST', params={"collection": collection_name})
        try:
            summary_json = rag_summary(collection_name=collection_name)
            return summary_json
        except Exception as e:
            log_error("摘要", str(e), detail=f"集合: {collection_name}")
            return jsonify({"summary": "摘要生成失败，请稍后再试。", "collection_name": collection_name})


# ------------------------------------------------------------------------- #
# ---------------------------   4. 文档名称切换  --------------------------- #
# ------------------------------------------------------------------------- #
@app.route('/collection/', methods=['GET', 'POST'])
def collection():
    global collection_name

    if request.method == 'GET':
        log_api_request('/collection/', 'GET')
        name_list = os.listdir(UPLOAD_FOLDER)
        if name_list:
            return jsonify({'name_list': name_list, 'collection_name': collection_name})
        return jsonify({'name_list': [], 'collection_name': collection_name})

    elif request.method == 'POST':
        collection_name = request.json.get('collection_name')
        log_api_request('/collection/', 'POST', params={"collection_name": collection_name})
        return redirect('/chat/')


# ------------------------------------------------------------------------- #
# ---------------------------   5. REST API 路径  --------------------------- #
# ------------------------------------------------------------------------- #
@app.route('/api/chat/', methods=['POST'])
def api_chat():
    """REST API: 问答接口，返回 JSON"""
    data = request.json
    message = data.get('message', '')
    coll = data.get('collection_name', collection_name)

    log_api_request('/api/chat/', 'POST', params={"message": message, "collection": coll})

    if not message:
        return jsonify({"error": "message 参数必填", "answer": "", "sources": []}), 400

    try:
        response_json = rag_chat(message, collection_name=coll, n_results=5)
        return response_json
    except Exception as e:
        log_error("API聊天", str(e))
        return jsonify({"error": str(e), "answer": "", "sources": []}), 500


@app.route('/api/summary/', methods=['POST'])
def api_summary():
    """REST API: 摘要接口，返回 JSON"""
    data = request.json or {}
    coll = data.get('collection_name', collection_name)

    log_api_request('/api/summary/', 'POST', params={"collection": coll})

    try:
        summary_json = rag_summary(collection_name=coll)
        return summary_json
    except Exception as e:
        log_error("API摘要", str(e))
        return jsonify({"error": str(e), "summary": "", "collection_name": coll}), 500


@app.route('/api/collections/', methods=['GET'])
def api_collections():
    """REST API: 获取所有文档集合列表"""
    name_list = os.listdir(UPLOAD_FOLDER)
    log_api_request('/api/collections/', 'GET')
    return jsonify({"collections": name_list, "current": collection_name})


if __name__ == '__main__':
    logger.info("[启动] Flask 应用启动, 访问: http://127.0.0.1:5000")
    app.run(debug=True)