import asyncio
import cv2
import os
import sys
from aiohttp import web

# --- 1. CONFIGURACIÓN ROBUSTA DE RUTAS ---
# Esto encuentra la carpeta donde está este main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Esto construye la ruta completa al video
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "bad_apple.mp4")
PORT = int(os.environ.get("WEBSITES_PORT", 8000))
WIDTH = 80
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

print(f"📂 DIRECTORIO BASE: {BASE_DIR}")
print(f"🔍 BUSCANDO VIDEO EN: {VIDEO_PATH}")

if os.path.exists(VIDEO_PATH):
    print("✅ EL ARCHIVO DE VIDEO EXISTE.")
else:
    print("❌ ERROR FATAL: EL ARCHIVO NO ESTÁ AHÍ.")
    print("📂 ARCHIVOS EN CARPETA ACTUAL:", os.listdir(BASE_DIR))
    if os.path.exists(os.path.join(BASE_DIR, "assets")):
        print("📂 ARCHIVOS EN ASSETS:", os.listdir(os.path.join(BASE_DIR, "assets")))

# --- 2. HTML CLIENTE ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BAD APPLE FINAL</title>
    <style>
        body { background: #000; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: monospace; }
        #c { font-size: 8px; line-height: 8px; white-space: pre; }
        h1 { font-size: 20px; color: #0f0; }
    </style>
</head>
<body>
    <h1 id="s">CONECTANDO...</h1>
    <div id="c"></div>
    <script>
        const c = document.getElementById('c');
        const s = document.getElementById('s');
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const ws = new WebSocket(protocol + window.location.host + '/ws');
        
        ws.onopen = () => { s.innerText = "ONLINE"; s.style.color = "#0f0"; };
        ws.onmessage = (e) => { c.innerText = e.data; };
        ws.onclose = () => { s.innerText = "DESCONECTADO"; s.style.color = "red"; };
    </script>
</body>
</html>
"""

class VideoServer:
    def __init__(self): self.frames = []
    
    def load_video(self):
        if not os.path.exists(VIDEO_PATH):
            print("⚠️ USANDO MODO EMERGENCIA (VIDEO NO ENCONTRADO)")
            # Generar frames falsos si no hay video para que veas que funciona
            for t in range(100):
                self.frames.append(f"ERROR: VIDEO NO ENCONTRADO\\nRuta: {VIDEO_PATH}")
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        while len(self.frames) < 1500:
            ret, frame = cap.read()
            if not ret: break
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                res = cv2.resize(gray, (WIDTH, int(WIDTH * 0.55)))
                ascii_f = "".join([ASCII_CHARS[p // 25] for p in res.flatten()])
                self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
            except Exception as e:
                print(f"Error procesando frame: {e}")
        cap.release()
        print(f"✅ VIDEO CARGADO: {len(self.frames)} frames en memoria.")

engine = VideoServer()

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    frame_idx = 0
    while not ws.closed:
        if engine.frames:
            await ws.send_str(engine.frames[frame_idx % len(engine.frames)])
            frame_idx += 1
        else:
            await ws.send_str("CARGANDO O ERROR...")
        await asyncio.sleep(0.04)
    return ws

async def index(request):
    return web.Response(text=HTML, content_type='text/html')

async def init_app():
    engine.load_video()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', websocket_handler)])
    return app

if __name__ == '__main__':
    web.run_app(init_app(), host='0.0.0.0', port=PORT)
