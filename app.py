from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

@app.route('/send_message', methods=['POST'])
def send_message():
    if "user" not in session: return jsonify({"success": False})
    data = request.json
    messages = load_data(MESSAGES_DATA)
    messages.append({"user": session["user"], "text": data.get("text", ""), "time": datetime.now().strftime("%H:%M")})
    save_data(MESSAGES_DATA, messages[-200:])
    return jsonify({"success": True})

@app.route('/get_messages')
def get_messages():
    return jsonify(load_data(MESSAGES_DATA)[-50:])

# 🌟 MAİL MOTORU 🌟
@app.route('/api/contact', methods=['POST'])
def send_contact_mail():
    data = request.json
    user = data.get("username", "Bilinmeyen")
    msg_text = data.get("message", "")
    
    if not msg_text: return jsonify({"success": False, "message": "Mesaj boş olamaz!"})

    GMAIL_ADRESI = "balliyok232@gmail.com"
    GMAIL_UYGULAMA_SIFRESI = "BURAYA_16_HANELI_SIFREYI_YAZ" 
    
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESI
        msg['To'] = GMAIL_ADRESI 
        msg['Subject'] = f"CeusX İletişim | Gönderen: {user}"
        msg.attach(MIMEText(msg_text, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(GMAIL_ADRESI, GMAIL_UYGULAMA_SIFRESI)
        server.send_message(msg)
        server.quit()
        return jsonify({"success": True})
        
    except smtplib.SMTPAuthenticationError:
        print("!!! GMAIL HATASI: Uygulama Şifresi yanlış veya eksik girildi !!!")
        return jsonify({"success": False, "message": "Adminin mail şifresi yanlış!"})
    except Exception as e:
        print("!!! BEKLENMEYEN MAİL HATASI:", e)
        return jsonify({"success": False, "message": f"Sistem hatası: {str(e)}"})

# 👑 GİZLİ ADMİN PANELİ (ŞİFRE: 2023) 👑
@app.route('/api/admin/users', methods=['POST'])
def admin_get_users():
    key = request.json.get("key", "")
    if key != "2023": return jsonify({"success": False, "message": "Geçersiz Admin Şifresi!"})
    
    users = load_data(USER_DATA)
    user_list = [{"username": k, "password": v} for k, v in users.items()]
    return jsonify({"success": True, "users": user_list})

@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    data = request.json
    key = data.get("key", "")
    username_to_delete = data.get("username", "")
    
    if key != "2023": return jsonify({"success": False})
    
    users = load_data(USER_DATA)
    if username_to_delete in users:
        del users[username_to_delete]
        save_data(USER_DATA, users)
        return jsonify({"success": True})
        
    return jsonify({"success": False, "message": "Kullanıcı bulunamadı!"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
