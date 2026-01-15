import os
import io
import time
import json
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

    # 【重要】バックスラッシュを二重にするよう指示を追加
    prompt = f"""
    あなたは教育のスペシャリストです。
    提供された【講義資料】に基づいて、学習効果の高い「{q_type}」を{q_count}問作成してください。
    
    【重要：数式の書き方】
    数学的な記号や式が登場する場合は、必ずLaTeX形式を使用してください。
    JSON形式で出力するため、LaTeXのバックスラッシュは必ず二重（例：\\\\frac , \\\\sqrt , \\\\theta）にして出力してください。
    - 文中の数式は '$...$' で囲んでください（例: $E=mc^2$）
    - 独立した行の数式は '$$...$$' で囲んでください。

    必ず以下のJSON配列フォーマットのみで出力してください。
    [
      {{ "id": 1, "question": "問題文", "answer": "解答", "explanation": "解説" }}
    ]

    【講義資料】
    {pdf_text[:12000]}
    """
    
    try:
        # Gemini 3 Flash モデルを使用
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        
        # もしGeminiがバックスラッシュをエスケープし忘れた場合でもエラーにならないように
        # strict=False を付けるか、事前に置換を検討しますが、まずは指示を優先します
        result_json = json.loads(response.text)
        return jsonify(result_json)

    except Exception as e:
        print(f"APIエラー: {e}")
        # デバッグ用に生のテキストをログに出す
        print(f"RAW RESPONSE: {response.text}")
        return jsonify({"error": f"AI生成エラー: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
