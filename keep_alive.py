from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy! ✅"

def run():
    port = int(os.getenv("PORT", 8080))   # ← Render tự cấp biến PORT
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
