import os
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from pypdf import PdfReader # PyPDF2からpypdfに変更
from google import genai

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = "AIzaSyDUstPG-1SpKksGhwxwscaT25Dj6hbmgkA"
client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file):
    """PDFからテキストを抽出（強化版）"""
    try:
        # ファイルを読み込んでバイナリストリームに変換
        pdf_stream = io.BytesIO(file.read())
        reader = PdfReader(pdf_stream)
        
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        # 抽出されたテキストの余白を削除
        final_text = text.strip()
        
        # デバッグ用：読み取った文字数をターミナルに表示
        print(f"--- PDF解析完了 ---")
        print(f"総ページ数: {len(reader.pages)}")
        print(f"抽出文字数: {len(final_text)} 文字")
        
        return final_text
    except Exception as e:
        print(f"PDF解析中にエラーが発生しました: {e}")
        return ""

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    if 'file' not in request.files:
        return jsonify({"error": "ファイルが見つかりません"}), 400
    
    file = request.files['file']
    subject = request.form.get('subject', '一般')
    q_type = request.form.get('type', '一問一答')
    q_count = request.form.get('count', '5')
    
    pdf_text = extract_text_from_pdf(file)
    
    # 読み取り失敗時の詳細チェック
    if not pdf_text:
        return jsonify({
            "error": "PDFからテキストを抽出できませんでした。このPDFは『文字が選択できない画像形式（スキャンされたもの）』である可能性があります。"
        }), 400

    prompt = f"""
    講義資料（教科: {subject}）に基づいて、学習用の問題を作成してください。
    
    【条件】
    - 形式: {q_type} / 問題数: {q_count}問
    
    【出力形式】必ずJSON配列のみで出力
    [
      {{ "id": 1, "question": "...", "answer": "...", "explanation": "..." }}
    ]

    【講義資料】
    {pdf_text[:15000]}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return response.text 
    except Exception as e:
        return jsonify({"error": f"Gemini APIエラー: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)