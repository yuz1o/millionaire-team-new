import os
import io
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pypdf import PdfReader
from google import genai

app = Flask(__name__)
CORS(app)

# 保存先フォルダの指定
STORAGE_DIR = "subjects_data"
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file):
    try:
        pdf_stream = io.BytesIO(file.read())
        reader = PdfReader(pdf_stream)
        text = "".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        return ""

# 教科一覧を取得
@app.route('/get-subjects', methods=['GET'])
def get_subjects():
    subjects = [d for d in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, d))]
    return jsonify(subjects)

# 特定の教科の履歴を取得
@app.route('/get-history/<subject>', methods=['GET'])
def get_history(subject):
    path = os.path.join(STORAGE_DIR, subject, "history.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    file = request.files.get('file')
    subject = request.form.get('subject', '一般')
    q_type = request.form.get('type', '一問一答')
    q_count = request.form.get('count', '5')
    
    pdf_text = extract_text_from_pdf(file) if file else "資料なし"

    prompt = f"""
    あなたは教育のスペシャリストです。教科「{subject}」の問題を作成してください。
    【重要：数式の書き方】
    数学的な記号や式が登場する場合は、必ずLaTeX形式を使用してください。
    JSON形式で出力するため、LaTeXのバックスラッシュは必ず二重（例：\\\\frac）にしてください。
    文中は '$...$'、独立行は '$$...$$' で囲んでください。

    必ず以下のJSON配列フォーマットのみで出力してください。
    [ {{ "id": 1, "question": "問題文", "answer": "解答", "explanation": "解説" }} ]

    【講義資料】
    {pdf_text[:12000]}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        new_questions = json.loads(response.text)

        # --- 履歴の保存処理 ---
        sub_path = os.path.join(STORAGE_DIR, subject)
        if not os.path.exists(sub_path):
            os.makedirs(sub_path)
        
        history_file = os.path.join(sub_path, "history.json")
        history = []
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        
        # 新しい問題を履歴の先頭に追加
        history = new_questions + history 
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return jsonify(new_questions)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
