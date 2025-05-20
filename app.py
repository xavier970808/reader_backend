# backend/app.py
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app, origins=["https://reader-frontend-e3f.pages.dev"])

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/list-epubs')
def list_epubs():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.epub')]
    return jsonify(files)

@app.route('/api/read-epub', methods=['POST'])
def read_epub():
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(path):
        print(f"[ERROR] 檔案找不到：{path}")
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
        print(f"[ERROR] 無法讀取 EPUB：{e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/read-epub-chapter', methods=['POST'])
def read_epub_chapter():
    data = request.get_json()
    filename = data.get('filename')
    chapter_index = data.get('chapterIndex', 0)

    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"error": f"File not found: {filename}"}), 404

    try:
        book = epub.read_epub(path)
        chapter_texts = []

        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                chapter_texts.append(soup.get_text())

        if chapter_index < 0 or chapter_index >= len(chapter_texts):
            return jsonify({"error": "Invalid chapter index"}), 400

        return jsonify({
            "chapter": chapter_texts[chapter_index],
            "totalChapters": len(chapter_texts),
            "chapterIndex": chapter_index
        })

    except Exception as e:
        print(f"[ERROR] 讀取章節失敗：{e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
