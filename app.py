import os
import io
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pypdf import PdfReader
from google import genai

app = Flask(__name__)
CORS(app)

# Renderの環境変数からAPIキーを取得
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file):
    """PDFからテキストを抽出（強化版）"""
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

# --- 追加: メインページ（index.html）を表示する設定 ---
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
        return jsonify({"error": "PDFから文字を読み取れませんでした（画像形式の可能性があります）"}), 400

    prompt = f"""
    あなたは優秀な大学教授です。以下の講義資料（教科: {subject}）に基づいて、学習用の問題を作成してください。
    【条件】
    - 形式: {q_type} / 問題数: {q_count}問
    【出力形式】必ずJSON配列のみで出力
    [
      {{ "id": 1, "question": "...", "answer": "...", "explanation": "..." }}
    ]
    【講義資料】
    {pdf_text[:10000]}
    """
    
    # サーバー負荷対策のリトライ処理
    max_retries = 3
    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash-8b", # 503エラー対策で軽量版を使用
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return response.text 
        except Exception as e:
            if "503" in str(e) and i < max_retries - 1:
                time.sleep(3) # 混雑時は3秒待ってリトライ
                continue
            return jsonify({"error": f"APIエラー: {str(e)}"}), 500

if __name__ == '__main__':
    # 開発環境（自分のPC）では 5000ポートで動かす
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
