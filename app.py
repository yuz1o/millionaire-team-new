import os
import io
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pypdf import PdfReader
from google import genai

app = Flask(__name__)
CORS(app)

# Renderの環境変数から取得
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file):
    try:
        pdf_stream = io.BytesIO(file.read())
        reader = PdfReader(pdf_stream)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF解析エラー: {e}")
        return ""

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    if 'file' not in request.files:
        return jsonify({"error": "ファイルが見つかりません"}), 400
    
    file = request.files['file']
    subject = request.form.get('subject', '一般')
    q_type = request.form.get('type', '一問一答')
    q_count = request.form.get('count', '5')
    
    pdf_text = extract_text_from_pdf(file)
    if not pdf_text:
        return jsonify({"error": "PDFから文字を読み取れませんでした"}), 400

    prompt = f"""
    あなたは教育工学の専門家です。提供された資料（教科: {subject}）を詳細に分析し、
    学習効果が高いとされる「{q_type}」形式の問題を{q_count}問作成してください。
    
    【出力形式】必ず以下のJSON配列のみで回答してください。
    [
      {{ "id": 1, "question": "問題文", "answer": "解答", "explanation": "詳しい解説" }}
    ]
    
    【講義資料】
    {pdf_text[:12000]}
    """
    
    try:
        # 最新の Gemini 3 モデルを使用
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return response.text 
    except Exception as e:
        print(f"APIエラー: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
