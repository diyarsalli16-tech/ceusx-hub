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

# 1. SCRIPTBLOX ARAMASI
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

# 🌟 2. YENİ URL YAPISIYLA ÖZEL ARAMA MOTORU 🌟
@app.route('/api/hasanefenc')
def search_hasanefenc():
    query = request.args.get('q', '').strip()
    if not query: return jsonify({"success": False, "scripts": []})
    
    try:
        # Senin uyardığın o yeni URL yapısı! Boşlukları %20 yapar.
        safe_query = urllib.parse.quote(query.lower())
        search_url = f"https://www.hasanefenc.com/home/search/{safe_query}"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # HasanEfeNC'nin sonuç kartlarını (article, div.post vb.) buluyoruz
        # Çoğu WordPress/Özel tema aramalarında sonuçlar genelde article veya a etiketleriyle listelenir
        articles = soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in x or 'item' in x))
        if not articles:
            # Eğer class bulamazsa sayfadaki tüm büyük linkleri tara
            articles = soup.find_all('a', href=True)
            
        count = 0
        for article in articles:
            if count >= 6: break # En fazla 6 sonuç getir
            
            # Başlık ve link bulma mantığı
            if article.name == 'a':
                post_link = article['href']
                title = article.text.strip()
            else:
                link_tag = article.find('a', href=True)
                if not link_tag: continue
                post_link = link_tag['href']
                title = link_tag.text.strip() or "VIP Script"
            
            # Alakasız linkleri atla (menü linkleri vb.)
            if len(title) < 5 or "http" not in post_link: continue
            
            script_code = f"Script detayları ve güncellemeler için kaynak linki: {post_link}"
            
            # Linkin içine girip kod (loadstring) ara
            try:
                post_resp = requests.get(post_link, headers=headers, timeout=3)
                post_soup = BeautifulSoup(post_resp.text, 'html.parser')
                code_blocks = post_soup.find_all(['code', 'pre', 'textarea'])
                for block in code_blocks:
                    if 'loadstring' in block.text:
                        script_code = block.text.strip()
                        break
            except:
                pass
            
            results.append({
                "title": title,
                "game": query.capitalize(),
                "script": script_code
            })
            count += 1
            
        if not results:
            return jsonify({"success": False, "message": "Bu oyuna ait VIP script bulunamadı!"})
            
        return jsonify({"success": True, "scripts": results})
        
    except Exception as e:
        return jsonify({"success": False, "message": "Arama motoru şu an meşgul, tekrar dene!"})

# SOHBET MESAJLARI
@app.route('/send_message', methods=['POST'])
def send_message():
    if "user" not in session: return jsonify({"success": False})
    data = request.json
    messages = load_data(MESSAGES_DATA)
    messages.append({"user": session["user"], "text": data.get("text", ""), "is_audio": data.get("is_audio", False), "time": datetime.now().strftime("%H:%M")})
    save_data(MESSAGES_DATA, messages[-200:])
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
