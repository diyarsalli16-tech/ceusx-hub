from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = 'yeralti_kral_ceusx_gizli_anahtar'
DB_NAME = 'ceusx_database.db'
ADMIN_KEY = 'ceusx2026' # 👑 SENİN GİZLİ ADMİN ŞİFREN

# --- 💾 YEREL VERİTABANI KURULUMU (GELİŞMİŞ) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (user TEXT, text TEXT)''')
    
    # YENİ SCRIPT TABLOSU: Onay (approved) ve Yükleyen (uploader) eklendi
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
    
    # Eğer eski tablo varsa ve yeni sütunlar yoksa diye güncelleme (Render çökmesin diye)
    try:
        c.execute("ALTER TABLE scripts ADD COLUMN approved BOOLEAN DEFAULT 1")
        c.execute("ALTER TABLE scripts ADD COLUMN uploader TEXT DEFAULT 'CeusX (RESMİ)'")
    except:
        pass # Zaten varsa hata verme, devam et

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', logged_in=True, user=session['user'])
    return render_template('index.html', logged_in=False)

# --- 📤 KULLANICI SCRIPT YÜKLEME API'si ---
@app.route('/api/upload_script', methods=['POST'])
def upload_script():
    data = request.get_json()
    uploader = session.get('user', 'Gizli Kullanıcı') # Yükleyenin adını al
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Scripti veritabanına yaz ama approved=0 (Onaysız) olarak!
    c.execute("INSERT INTO scripts (game, title, verified, keyless, code, approved, uploader) VALUES (?, ?, 0, ?, ?, 0, ?)",
              (data['game'], data['title'], data['keyless'], data['code'], uploader))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- 🔍 YEREL ARAMA MOTORU (SADECE ONAYLANANLAR) ---
@app.route('/api/local_search')
def local_search():
    query = request.args.get('q', '').lower()
    keyless = request.args.get('keyless', 'false') == 'true'
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # SADECE ADMİNİN ONAYLADIĞI (approved=1) SCRİPTLERİ GETİRİR
    sql = "SELECT id, game, title, verified, keyless, code, uploader FROM scripts WHERE approved=1 AND (LOWER(game) LIKE ? OR LOWER(title) LIKE ?)"
    params = [f"%{query}%", f"%{query}%"]
    if keyless:
        sql += " AND keyless=1"
        
    sql += " ORDER BY id DESC"
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    
    scripts = [{"id": r[0], "game": r[1], "title": r[2], "verified": bool(r[3]), "keyless": bool(r[4]), "script": r[5], "uploader": r[6]} for r in rows]
    return jsonify({"success": True, "scripts": scripts})

# --- 👑 ADMİN PANELİ API'LERİ (CEUSX RESMİ) ---
@app.route('/api/admin/get_scripts', methods=['POST'])
def admin_get_scripts():
    if request.json.get('key') != ADMIN_KEY:
        return jsonify({"success": False, "message": "Yetkisiz Erişim!"})
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Onay bekleyenler
    c.execute("SELECT id, game, title, keyless, code, uploader FROM scripts WHERE approved=0 ORDER BY id DESC")
    pending = [{"id": r[0], "game": r[1], "title": r[2], "keyless": bool(r[3]), "script": r[4], "uploader": r[5]} for r in c.fetchall()]
    
    # Onaylanmış aktif scriptler
    c.execute("SELECT id, game, title, keyless, code, uploader FROM scripts WHERE approved=1 ORDER BY id DESC")
    active = [{"id": r[0], "game": r[1], "title": r[2], "keyless": bool(r[3]), "script": r[4], "uploader": r[5]} for r in c.fetchall()]
    conn.close()
    
    return jsonify({"success": True, "pending": pending, "active": active})

@app.route('/api/admin/action', methods=['POST'])
def admin_action():
    data = request.get_json()
    if data.get('key') != ADMIN_KEY:
        return jsonify({"success": False})
        
    action = data.get('action')
    script_id = data.get('id')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if action == 'approve':
        c.execute("UPDATE scripts SET approved=1, verified=1, uploader='CeusX (RESMİ)' WHERE id=?", (script_id,))
    elif action == 'delete':
        c.execute("DELETE FROM scripts WHERE id=?", (script_id,))
        
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- 📡 SCRIPTBLOX CANLI ARAMA ---
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1)
    url = f"https://scriptblox.com/api/script/search?q={query}&max=12&page={page}&mode=free"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({"success": False, "error": f"ScriptBlox Engelledi: {response.status_code}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- DİĞER STANDART İŞLEMLER ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    u, p = data.get('username'), data.get('password')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
        conn.commit()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Bu isim alınmış!"})
    finally: conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    u, p = data.get('username'), data.get('password')
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
    return jsonify({"success": False, "message": "Yanlış şifre!"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

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
