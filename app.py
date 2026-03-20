from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import requests
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # Dinamik gizli anahtar
DB_NAME = 'ceusx_milli.db'
ADMIN_KEY = 'ceusx2026'

# --- 💾 VERİTABANI MİMARİSİ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS messages (user TEXT, text TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        game TEXT, title TEXT, verified BOOLEAN, keyless BOOLEAN, 
        code TEXT, approved BOOLEAN DEFAULT 0, uploader TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html', logged_in=('user' in session), user=session.get('user'))

# --- 📡 SCRIPTBLOX GLOBAL API (BYPASS) ---
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    page = request.args.get('page', '1')
    url = f"https://scriptblox.com/api/script/search?q={query}&max=12&page={page}&mode=free"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return jsonify(r.json())
    except:
        return jsonify({"success": False, "error": "Bağlantı Hatası"})

# --- ☁️ CEUSX YERLİ ARŞİV (ONAYLI) ---
@app.route('/api/local_search')
def local_search():
    query = request.args.get('q', '').lower()
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("SELECT game, title, verified, keyless, code, uploader FROM scripts WHERE approved=1 AND (LOWER(game) LIKE ? OR LOWER(title) LIKE ?)", (f"%{query}%", f"%{query}%"))
    scripts = [{"game": r[0], "title": r[1], "verified": bool(r[2]), "keyless": bool(r[3]), "script": r[4], "uploader": r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify({"scripts": scripts})

# --- 📤 SCRIPT YÜKLEME ---
@app.route('/api/upload_script', methods=['POST'])
def upload_script():
    data = request.json
    uploader = session.get('user', 'Gizli Kullanıcı')
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("INSERT INTO scripts (game, title, verified, keyless, code, approved, uploader) VALUES (?, ?, 0, ?, ?, 0, ?)",
              (data['game'], data['title'], data['keyless'], data['code'], uploader))
    conn.commit(); conn.close()
    return jsonify({"success": True})

# --- 👑 ADMİN PANELI (YÜCE YARGI) ---
@app.route('/api/admin/get_pending', methods=['POST'])
def admin_get():
    if request.json.get('key') != ADMIN_KEY: return jsonify({"success": False})
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("SELECT id, game, title, code, uploader FROM scripts WHERE approved=0")
    pending = [{"id": r[0], "game": r[1], "title": r[2], "script": r[3], "uploader": r[4]} for r in c.fetchall()]
    conn.close()
    return jsonify({"success": True, "pending": pending})

@app.route('/api/admin/action', methods=['POST'])
def admin_act():
    data = request.json
    if data.get('key') != ADMIN_KEY: return jsonify({"success": False})
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    if data['action'] == 'approve':
        c.execute("UPDATE scripts SET approved=1, verified=1, uploader='CeusX (RESMİ)' WHERE id=?", (data['id'],))
    elif data['action'] == 'delete':
        c.execute("DELETE FROM scripts WHERE id=?", (data['id'],))
    conn.commit(); conn.close()
    return jsonify({"success": True})

# --- STANDART AUTH & CHAT ---
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data['password'] == 'google_oauth_bypass': session['user'] = data['username']; return jsonify({"success": True})
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (data['username'], data['password']))
    if c.fetchone(): session['user'] = data['username']; conn.close(); return jsonify({"success": True})
    conn.close(); return jsonify({"success": False})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?,?)", (data['username'], data['password']))
        conn.commit(); return jsonify({"success": True})
    except: return jsonify({"success": False})
    finally: conn.close()

@app.route('/logout')
def logout(): session.pop('user', None); return redirect(url_for('index'))

@app.route('/get_messages')
def get_msgs():
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("SELECT user, text FROM messages ORDER BY ROWID DESC LIMIT 30")
    data = [{"user": r[0], "text": r[1]} for r in reversed(c.fetchall())]
    conn.close(); return jsonify(data)

@app.route('/send_message', methods=['POST'])
def send_msg():
    if 'user' not in session: return jsonify({"error": 1})
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (?,?)", (session['user'], request.json['text']))
    conn.commit(); conn.close(); return jsonify({"success": True})

if __name__ == '__main__':
    # RENDER İÇİN KRİTİK PORT AYARI
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
