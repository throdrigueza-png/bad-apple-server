import asyncio
import cv2
import os
from aiohttp import web

# --- CONFIGURACIÓN A PRUEBA DE FALLOS ---
# 1. Detectar puerto de Azure
PORT = int(os.environ.get("WEBSITES_PORT", 8000))

# 2. Detectar ruta REAL del archivo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "bad_apple.mp4")

# 3. Caracteres ASCII
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
WIDTH = 80

# --- HTML CLIENTE ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BAD APPLE DIAGNOSTIC</title>
    <style>
        body { background: #000; color: #0f0; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: monospace; }
        #c { font-size: 8px; line-height: 8px; white-space: pre; border: 1px solid #333; padding: 10px; }
        h1 { color: #fff; }
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
        
        ws.onopen = () => { s.innerText = "CONECTADO"; };
        ws.onmessage = (e) => { c.innerText = e.data; };
        ws.onclose = () => { s.innerText = "DESCONECTADO"; s.style.color = "red"; };
    </script>
</body>
</html>
"""

class Engine:
    def __init__(self): 
        self.frames = []
        self.error_msg = None

    def load(self):
        # MODO DIAGNÓSTICO: Si no está el video, avisa qué archivos hay
        if not os.path.exists(VIDEO_PATH):
            files_root = str(os.listdir(BASE_DIR))
            try:
                files_assets = str(os.listdir(os.path.join(BASE_DIR, "assets")))
            except:
                files_assets = "CARPETA ASSETS NO EXISTE"
                
            self.error_msg = f"ERROR: NO VEO EL VIDEO\\nBuscando en: {VIDEO_PATH}\\n\\nArchivos aqui: {files_root}\\n\\nDentro de assets: {files_assets}"
            print(self.error_msg)
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        while len(self.frames) < 1000:
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            res = cv2.resize(gray, (WIDTH, int(WIDTH * 0.55)))
            ascii_f = "".join([ASCII_CHARS[p // 25] for p in res.flatten()])
            self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
        cap.release()

engine = Engine()

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    t = 0
    while not ws.closed:
        # Si hay error (no video), mostramos el diagnóstico en pantalla
        if engine.error_msg:
            await ws.send_str(engine.error_msg)
            await asyncio.sleep(1)
        # Si hay video, lo reproducimos
        elif engine.frames:
            await ws.send_str(engine.frames[t % len(engine.frames)])
            t += 1
            await asyncio.sleep(0.04)
        else:
            await ws.send_str("Cargando...")
            await asyncio.sleep(0.1)
    return ws

async def index(request): return web.Response(text=HTML, content_type='text/html')

async def init():
    engine.load()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', ws_handler)])
    return app

if __name__ == '__main__':
    web.run_app(init(), host='0.0.0.0', port=PORT)
