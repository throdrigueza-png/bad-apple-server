import asyncio
import cv2
import os
from aiohttp import web

# Usamos el puerto que Azure nos da
PORT = int(os.environ.get("WEBSITES_PORT", 8000))
VIDEO_PATH = "assets/bad_apple.mp4"
WIDTH = 80
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

# --- PÁGINA WEB INTEGRADA ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BAD APPLE AZURE</title>
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
        // Conexión automática (detecta si es seguro wss o normal ws)
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const ws = new WebSocket(protocol + window.location.host + '/ws');
        
        ws.onopen = () => { s.innerText = "ONLINE - DISFRUTA"; s.style.color = "#0f0"; };
        ws.onmessage = (e) => { c.innerText = e.data; };
        ws.onclose = () => { s.innerText = "DESCONECTADO"; s.style.color = "red"; };
    </script>
</body>
</html>
"""

class VideoServer:
    def __init__(self): self.frames = []
    
    def load_video(self):
        if not os.path.exists(VIDEO_PATH): return
        cap = cv2.VideoCapture(VIDEO_PATH)
        while len(self.frames) < 1500: # Cargar ~50 segundos
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            res = cv2.resize(gray, (WIDTH, int(WIDTH * 0.55)))
            # Convertir a ASCII
            ascii_f = "".join([ASCII_CHARS[p // 25] for p in res.flatten()])
            # Formatear con saltos de línea
            self.frames.append("\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
        cap.release()

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
            await ws.send_str("Cargando video o error en assets/...")
        await asyncio.sleep(0.04) # ~25 FPS
    return ws

async def index(request):
    return web.Response(text=HTML, content_type='text/html')

async def init_app():
    engine.load_video()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', websocket_handler)])
    return app

if __name__ == '__main__':
    # Azure espera que escuchemos en 0.0.0.0
    web.run_app(init_app(), host='0.0.0.0', port=PORT)
