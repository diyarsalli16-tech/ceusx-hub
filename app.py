from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import requests
import os

app = Flask(__name__)
app.secret_key = 'yeralti_kral_ceusx_gizli_anahtar'
DB_NAME = 'ceusx_v4.db' # ⚠️ İSMİ DEĞİŞTİRDİK, RENDER SIFIR TERTEMİZ DB KURACAK
ADMIN_KEY = 'ceusx2026'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (user TEXT, text TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        game TEXT, 
        title TEXT, 
        verified BOOLEAN, 
        keyless BOOLEAN, 
        code TEXT,
        approved BOOLEAN DEFAULT 0,
        uploader TEXT
    )''')
    conn.commit()
    conn.close()

# --- YENİ EKLENEN KISIM: ONAYLI SCRİPTLERİ OTOMATİK YÜKLE ---
def seed_approved_scripts():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Eklenecek Scriptler Listesi
    default_scripts = [
        ("Brookhaven RP", "Rael Hub", 1, 0, 'loadstring(game:HttpGet("https://rawscripts.net/raw/Brookhaven-RP-Rael-Hub-58126"))()', "CeusX (RESMİ)"),
        ("Murder Mystery 2", "MM2 Script (Güvenli)", 1, 1, 'loadstring(game:HttpGet("https://pastebin.com/raw/F5SuruDs"))()', "CeusX (RESMİ)"),
        ("Brookhaven RP", "Nova Hub (Key Korumalı)", 1, 0, 'loadstring(game:HttpGet("https://pastebin.com/raw/HcFi4rrZ"))()', "CeusX (RESMİ)"),
        ("Brookhaven RP", "Sander X", 1, 1, 'loadstring(game:HttpGet("https://rawscripts.net/raw/Brookhaven-RP-Sander-XY-35845"))()', "CeusX (RESMİ)")
    ]

    for game, title, verified, keyless, code, uploader in default_scripts:
        # Aynı script var mı kontrol et (Tekrarlanmayı önlemek için)
        c.execute("SELECT id FROM scripts WHERE title = ?", (title,))
        if not c.fetchone():
            c.execute("""INSERT INTO scripts (game, title, verified, keyless, code, approved, uploader) 
                         VALUES (?, ?, ?, ?, ?, 1, ?)""", 
                      (game, title, verified, keyless, code, uploader))
    
    conn.commit()
    conn.close()

# Başlangıçta fonksiyonları çağır
init_db()
seed_approved_scripts()

# --- ROUTELER VE DİĞER FONKSİYONLAR AYNEN KALIYOR ---

@app.route('/')
def index():
    return render_template('index.html', logged_in=('user' in session), user=session.get('user'))

# --- 📡 SCRIPTBLOX CANLI BAĞLANTI ---
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    page = request.args.get('page', '1')
    url = "https://scriptblox.com/api/script/search"
    params = {"q": query, "max": 12, "page": page, "mode": "free"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        return jsonify(response.json())
    except:
        return jsonify({"success": False, "error": "Bağlantı Sorunu"})

# --- 🔍 YEREL ARAMA (SADECE ONAYLI) ---
@app.route('/api/local_search')
def local_search():
    query = request.args.get('q', '').lower()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if query:
        c.execute("SELECT id, game, title, verified, keyless, code, uploader FROM scripts WHERE approved=1 AND (LOWER(game) LIKE ? OR LOWER(title) LIKE ?) ORDER BY id DESC", (f"%{query}%", f"%{query}%"))
    else:
        c.execute("SELECT id, game, title, verified, keyless, code, uploader FROM scripts WHERE approved=1 ORDER BY id DESC LIMIT 20")
        
    scripts = [{"id": r[0], "game": r[1], "title": r[2], "verified": bool(r[3]), "keyless": bool(r[4]), "script": r[5], "uploader": r[6]} for r in c.fetchall()]
    conn.close()
    return jsonify({"scripts": scripts})

# --- 📤 YÜKLEME ---
@app.route('/api/upload_script', methods=['POST'])
def upload_script():
    data = request.json
    uploader = session.get('user', 'Gizli')
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("INSERT INTO scripts (game, title, verified, keyless, code, approved, uploader) VALUES (?, ?, 0, ?, ?, 0, ?)",
              (data['game'], data['title'], data['keyless'], data['code'], uploader))
    conn.commit(); conn.close()
    return jsonify({"success": True})

# --- 👑 ADMİN PANELI ---
@app.route('/api/admin/get_all', methods=['POST'])
def admin_get_all():
    if request.json.get('key') != ADMIN_KEY: return jsonify({"success": False})
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    
    c.execute("SELECT id, game, title, keyless, code, uploader FROM scripts WHERE approved=0 ORDER BY id DESC")
    pending = [{"id": r[0], "game": r[1], "title": r[2], "keyless": r[3], "script": r[4], "uploader": r[5]} for r in c.fetchall()]
    
    c.execute("SELECT id, game, title, keyless, code, uploader FROM scripts WHERE approved=1 ORDER BY id DESC")
    approved_list = [{"id": r[0], "game": r[1], "title": r[2], "keyless": r[3], "script": r[4], "uploader": r[5]} for r in c.fetchall()]
    
    conn.close()
    return jsonify({"success": True, "pending": pending, "approved_list": approved_list})

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

# --- AUTH & CHAT ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?,?)", (data['username'], data['password']))
        conn.commit(); return jsonify({"success": True})
    except: return jsonify({"success": False})
    finally: conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get('password') == 'google_oauth_bypass': session['user'] = data['username']; return jsonify({"success": True})
    conn = sqlite3.connect(DB_NAME); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (data['username'], data['password']))
    if c.fetchone(): session['user'] = data['username']; conn.close(); return jsonify({"success": True})
    conn.close(); return jsonify({"success": False})

@app.route('/logout')
def logout(): session.pop('user', None); return redirect('/')

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
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
