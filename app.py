from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

app = Flask(__name__)
# 允許前端來源
CORS(app, origins=["https://reader-frontend-e3f.pages.dev", "http://localhost:5173"])

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/list-epubs')
def list_epubs():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.epub')]
    return jsonify(files)

@app.route('/api/read-epub', methods=['POST'])
def read_epub():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"error": f"File not found: {filename}"}), 404

    try:
        book = epub.read_epub(path)
        chapters = []
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                chapters.append(soup.get_text())
        return jsonify(chapters)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith('.epub'):
        return jsonify({"error": "Only .epub allowed"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    return jsonify({"message": "Upload successful", "filename": file.filename})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))