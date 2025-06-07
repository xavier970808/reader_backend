# backend/app.py
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE
from bs4 import BeautifulSoup
import html
import base64


app = Flask(__name__)
CORS(app, origins=[
  "https://reader-frontend-e3f.pages.dev",
  "http://localhost:5173"
])

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/list-epubs')
def list_epubs():
    epub_paths = []
    for root, _, filenames in os.walk(UPLOAD_FOLDER):
        for fname in filenames:
            if fname.lower().endswith('.epub'):
                # 生成相对于 UPLOAD_FOLDER 的路径
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, UPLOAD_FOLDER)
                # 使用 POSIX 风格分隔符，前端 encodeURIComponent('%2F') 后可正确解码
                epub_paths.append(rel_path.replace(os.sep, '/'))
    return jsonify(epub_paths)


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
        images = {}
        for image in book.get_items_of_type(ITEM_IMAGE):
            image_content = image.get_content()
            image_name = image.get_name()
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            _, file_extension = os.path.splitext(image_name)
            if file_extension:
                file_extension = file_extension[1:]  # 去掉前面的點
            else:
                file_extension = 'png'
            data_uri = f'data:image/{file_extension};base64,{image_base64}'
            images[image_name] = data_uri
        chapters = []
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                img_tags = soup.find_all('img')
                for img in img_tags:
                    src = img.get('src')
                    while src.startswith('../'):
                        src = src[3:]
                    if src in images:
                        img['src'] = images[src]
                    img['width'] = "100%"
                    img['height'] = "auto"
                content = soup.body.decode_contents()
                
                chapters.append(content)
        #print("chapters :",chapters)
        return jsonify(chapters)
    except Exception as e:
        print(f"[ERROR] 讀取 epub 檔案失敗：{e}")
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
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src:
                        asset_path = os.path.join(os.path.dirname(filename), src).replace('\\', '/')
                        img['src'] = f"/api/book-assets/{asset_path}"
                chapter_texts.append(str(soup))  # 保留 HTML 結構

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

@app.route('/api/upload', methods=['POST'])
def upload_file():
    # 檢查是否有檔案欄位
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    # 只允許 epub
    if not file.filename.lower().endswith('.epub'):
        return jsonify({"error": "Only .epub allowed"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    return jsonify({"message": "Upload successful", "filename": file.filename})

@app.route('/api/list-books')
def list_books():
    books = [name for name in os.listdir(UPLOAD_FOLDER)
             if os.path.isdir(os.path.join(UPLOAD_FOLDER, name))]
    return jsonify(books)

from flask import send_from_directory

@app.route('/api/book-assets/<path:filename>')
def serve_epub_assets(filename):
    full_path = os.path.join(UPLOAD_FOLDER, filename)
    directory = os.path.dirname(full_path)
    file = os.path.basename(full_path)
    return send_from_directory(directory, file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
