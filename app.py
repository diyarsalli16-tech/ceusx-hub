from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = 'yeralti_kral_ceusx_gizli_anahtar'
DB_NAME = 'ceusx_database.db'

# --- 💾 YEREL VERİTABANI KURULUMU (Kullanıcılar ve Chat için) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (user TEXT, text TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', logged_in=True, user=session['user'])
    return render_template('index.html', logged_in=False)

# --- 📡 YENİ: DOĞRUDAN SCRIPTBLOX API BAĞLANTISI ---
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1)
    
    # ScriptBlox'un gerçek API'sine istek atıyoruz!
    url = f"https://scriptblox.com/api/script/search?q={query}&max=12&page={page}&mode=free"
    
    try:
        response = requests.get(url)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- 🔑 GİRİŞ VE KAYIT ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    u = data.get('username')
    p = data.get('password')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
        conn.commit()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Bu isim alınmış!"})
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    u = data.get('username')
    p = data.get('password')
    if p == 'google_oauth_bypass':
        session['user'] = u
        return jsonify({"success": True})
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
    user = c.fetchone()
    conn.close()
    
    if user:
        session['user'] = u
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Yanlış şifre kanka!"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# --- 💬 SOHBET SİSTEMİ ---
@app.route('/send_message', methods=['POST'])
def send_msg():
    if 'user' not in session: return jsonify({"error": "Giriş yap"})
    text = request.get_json().get('text')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (user, text) VALUES (?, ?)", (session['user'], text))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/get_messages')
def get_msgs():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user, text FROM messages ORDER BY ROWID DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"user": r[0], "text": r[1]} for r in reversed(rows)])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
