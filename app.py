import os
import sqlite3
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'static/uploads'
PDF_FOLDER = 'static/pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER
app.secret_key = 'super_secret_key'

# ✅✅✅ ADD YOUR REAL GEMINI API KEY HERE
GENAI_API_KEY = os.getenv("AIzaSyC7VTFChnTWIhvZrC3POEcGTrTtbLFRBPE")
# GENAI_API_KEY = "AIzaSyC7VTFChnTWIhvZrC3POEcGTrTtbLFRBPE"
genai.configure(api_key=GENAI_API_KEY)

# ✅✅✅ LOAD MODEL ONCE (IMPORTANT)
model = genai.GenerativeModel("gemini-1.5-flash")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect('manuscripts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS manuscripts 
                 (id INTEGER PRIMARY KEY, title TEXT, era TEXT, genre TEXT, 
                  description TEXT, cover_image TEXT, pdf_file TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- HOME PAGE ---
@app.route('/')
def index():
    conn = sqlite3.connect('manuscripts.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM manuscripts")
    manuscripts = c.fetchall()
    conn.close()
    return render_template('index.html', manuscripts=manuscripts)

# ✅✅✅ NEW AI PAGE ROUTE
@app.route('/ai')
def ai_page():
    return render_template('ai.html')

# --- ADMIN PANEL ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect('manuscripts.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':

        # ADD MANUSCRIPT
        if 'add_manuscript' in request.form:
            title = request.form['title']
            era = request.form['era']
            genre = request.form['genre']
            desc = request.form['description']
            cover = request.files['cover']
            pdf = request.files['pdf']

            if cover and pdf:
                cover_filename = secure_filename(cover.filename)
                pdf_filename = secure_filename(pdf.filename)

                cover.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))
                pdf.save(os.path.join(app.config['PDF_FOLDER'], pdf_filename))

                c.execute(
                    "INSERT INTO manuscripts (title, era, genre, description, cover_image, pdf_file) VALUES (?,?,?,?,?,?)",
                    (title, era, genre, desc, cover_filename, pdf_filename)
                )
                conn.commit()

        # EDIT MANUSCRIPT
        elif 'edit_manuscript' in request.form:
            m_id = request.form['id']
            title = request.form['title']
            era = request.form['era']
            genre = request.form['genre']
            desc = request.form['description']

            c.execute("SELECT * FROM manuscripts WHERE id=?", (m_id,))
            current_data = c.fetchone()

            cover_filename = current_data['cover_image']
            pdf_filename = current_data['pdf_file']

            if 'cover' in request.files and request.files['cover'].filename != '':
                cover = request.files['cover']
                cover_filename = secure_filename(cover.filename)
                cover.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))

            if 'pdf' in request.files and request.files['pdf'].filename != '':
                pdf = request.files['pdf']
                pdf_filename = secure_filename(pdf.filename)
                pdf.save(os.path.join(app.config['PDF_FOLDER'], pdf_filename))

            c.execute(
                "UPDATE manuscripts SET title=?, era=?, genre=?, description=?, cover_image=?, pdf_file=? WHERE id=?",
                (title, era, genre, desc, cover_filename, pdf_filename, m_id)
            )
            conn.commit()

        # DELETE MANUSCRIPT
        elif 'delete_manuscript' in request.form:
            m_id = request.form['id']
            c.execute("DELETE FROM manuscripts WHERE id=?", (m_id,))
            conn.commit()

    c.execute("SELECT * FROM manuscripts")
    manuscripts = c.fetchall()
    conn.close()
    return render_template('admin.html', manuscripts=manuscripts)

# --- READER PAGE ---
@app.route('/reader/<int:id>')
def reader(id):
    conn = sqlite3.connect('manuscripts.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM manuscripts WHERE id=?", (id,))
    manuscript = c.fetchone()
    conn.close()
    return render_template('reader.html', manuscript=manuscript)

# ✅✅✅ ✅✅✅ ✅✅✅ ✅✅✅
# ✅✅✅ FINAL WORKING GEMINI CHAT API
# ✅✅✅ ✅✅✅ ✅✅✅ ✅✅✅
@app.route('/chat_api', methods=['POST'])
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return jsonify({'response': "Empty message received."})

        prompt = f"""
You are a helpful assistant for the Manuscript Explorer app.
You are an expert in Indian manuscripts, ancient history, Ayurveda, Vedas, and Sanskrit texts.
Answer clearly and briefly.

User Question: {user_message}
"""

        response = model.generate_content(prompt)
        return jsonify({'response': response.text})

    except Exception as e:
        print("GEMINI ERROR:", str(e))
        return jsonify({'response': "AI system is currently unavailable. Please try again later."})

# --- RUN SERVER ---
if __name__ == '__main__':
    app.run(debug=True)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
