from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse

app = Flask(__name__)
app.secret_key = "ceusx_mega_secret"

USER_DATA = "users.json"
MESSAGES_DATA = "messages.json"

def load_data(file):
    if not os.path.exists(file): return [] if "messages" in file else {}
    try:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else ([] if "messages" in file else {})
    except:
        return [] if "messages" in file else {}

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def home():
    return render_template("index.html", logged_in="user" in session, user=session.get("user"))

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    users = load_data(USER_DATA)
    user, password = data.get("username", "").strip(), data.get("password", "").strip()
    if not user or not password: return jsonify({"success": False, "message": "Boş bırakma!"})
    if user in users: return jsonify({"success": False, "message": "İsim alınmış!"})
    users[user] = password
    save_data(USER_DATA, users)
    return jsonify({"success": True})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    users = load_data(USER_DATA)
    user, password = data.get("username", "").strip(), data.get("password", "").strip()
    if users.get(user) == password:
        session["user"] = user
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Hatalı giriş!"})

# --- 1. SCRIPTBLOX ARAMASI ---
@app.route('/api/search')
def search_scriptblox():
    query = request.args.get('q', '')
    if not query: return jsonify({"success": False, "scripts": []})
    try:
        url = f"https://scriptblox.com/api/script/search?q={query}&max=20"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        results = []
        if "result" in data and "scripts" in data["result"]:
            for s in data["result"]["scripts"]:
                if s.get("verified", False):
                    results.append({
                        "title": s.get("title", "İsimsiz"),
                        "game": s.get("game", {}).get("name", "Bilinmeyen"),
                        "script": s.get("script", ""),
                        "has_key": s.get("key", False)
                    })
        return jsonify({"success": True, "scripts": results})
    except Exception as e:
        return jsonify({"success": False, "message": "Bağlantı koptu!"})

# --- 2. HASANEFENC BOTU (HATA KORUMALI) ---
@app.route('/api/hasanefenc')
def search_hasanefenc():
    query = request.args.get('q', '').strip()
    if not query: return jsonify({"success": False, "scripts": [], "target_url": ""})
    
    # Senin bulduğun URL yapısı
    safe_query = urllib.parse.quote(query.lower())
    target_url = f"https://www.hasanefenc.com/home/search/{safe_query}"
    
    try:
        # Gerçek bir insan gibi görünmek için detaylı header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        response = requests.get(target_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # Wix sitelerinde sonuçlar genelde link olarak listelenir.
        links = soup.find_all('a', href=True)
        
        for a in links:
            href = a['href']
            text = a.text.strip()
            # Linkin içinde oyun adı geçiyorsa ve yeterince uzunsa al
            if query.lower() in text.lower() and len(text) > 5 and "http" in href:
                results.append({
                    "title": text,
                    "game": query.capitalize(),
                    "url": href # Direkt o postun linkini veriyoruz
                })
                
        # Eğer sonuç bulduysak gönder
        if results:
            return jsonify({"success": True, "scripts": results[:5], "target_url": target_url})
        else:
            # JavaScript duvarına takıldıysak veya sonuç yoksa (HATA VERMEDEN) ana linki döndür
            return jsonify({"success": False, "message": "Bot engellendi", "target_url": target_url})
            
    except Exception as e:
        # Eğer sunucu çökerse bile "Veritabanı hatası" vermemek için güvenli dönüş
        return jsonify({"success": False, "message": "Sunucu hatası", "target_url": target_url})

# --- SOHBET SİSTEMİ ---
@app.route('/send_message', methods=['POST'])
def send_message():
    if "user" not in session: return jsonify({"success": False})
    data = request.json
    messages = load_data(MESSAGES_DATA)
    messages.append({"user": session["user"], "text": data.get("text", ""), "time": datetime.now().strftime("%H:%M")})
    save_data(MESSAGES_DATA, messages[-100:])
    return jsonify({"success": True})

@app.route('/get_messages')
def get_messages():
    return jsonify(load_data(MESSAGES_DATA)[-50:])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
