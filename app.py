from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import requests
from datetime import datetime

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
    if not user or not password: return jsonify({"success": False, "message": "Boş bırakma kanka!"})
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

@app.route('/api/search')
def search_scriptblox():
    query = request.args.get('q', '')
    keyless_only = request.args.get('keyless', 'false').lower() == 'true'
    if not query: return jsonify({"success": False, "scripts": []})
    try:
        url = f"https://scriptblox.com/api/script/search?q={query}&max=40"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        results = []
        if "result" in data and "scripts" in data["result"]:
            for s in data["result"]["scripts"]:
                is_verified = s.get("verified", False)
                has_key = s.get("key", False)
                if is_verified:
                    if keyless_only and has_key: continue
                    results.append({
                        "title": s.get("title", "İsimsiz"),
                        "game": s.get("game", {}).get("name", "Bilinmeyen Oyun"),
                        "features": s.get("features", "Özellik belirtilmemiş."),
                        "script": s.get("script", ""),
                        "has_key": has_key
                    })
        return jsonify({"success": True, "scripts": results})
    except Exception as e:
        return jsonify({"success": False, "message": "Bağlantı hatası!"})

# 🌟 ODA SİSTEMİ EKLENDİ 🌟
@app.route('/send_message', methods=['POST'])
def send_message():
    if "user" not in session: return jsonify({"success": False})
    data = request.json
    messages = load_data(MESSAGES_DATA)
    
    room_name = data.get("room", "Global") # Varsayılan oda Global
    
    messages.append({
        "user": session["user"], 
        "text": data.get("text", ""), 
        "is_audio": data.get("is_audio", False),
        "room": room_name, # Mesajın hangi odaya ait olduğunu kaydediyoruz
        "time": datetime.now().strftime("%H:%M")
    })
    
    save_data(MESSAGES_DATA, messages[-200:]) # Daha fazla mesaj tutalım
    return jsonify({"success": True})

@app.route('/get_messages')
def get_messages():
    room_name = request.args.get("room", "Global") # İstenen odayı al
    messages = load_data(MESSAGES_DATA)
    
    # Sadece seçili odadaki mesajları filtrele ve gönder
    room_messages = [m for m in messages if m.get("room", "Global") == room_name]
    return jsonify(room_messages[-50:]) # Odadaki son 50 mesaj

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)