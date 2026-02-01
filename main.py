import asyncio
import cv2
import os
import math
import numpy as np
from aiohttp import web

# --- CONFIGURACIÓN ---
PORT = int(os.environ.get("PORT", 8000))
VIDEO_PATH = "assets/bad_apple.mp4" 
WIDTH = 80 
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

# --- HTML INTEGRADO ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><title>BAD APPLE SERVER</title>
    <style>
        body { background: #000; color: #0f0; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: monospace; overflow: hidden; }
        #canvas { font-size: 10px; line-height: 8px; white-space: pre; font-weight: bold; }
    </style>
</head>
<body>
    <h1 id="status">CONECTANDO AL NÚCLEO...</h1>
    <div id="canvas"></div>
    <script>
        const canvas = document.getElementById('canvas');
        const status = document.getElementById('status');
        const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws';
        let socket;
        function connect() {
            socket = new WebSocket(wsUrl);
            socket.onopen = () => { status.innerText = "SISTEMA ONLINE"; status.style.color = "#fff"; };
            socket.onmessage = (e) => { canvas.innerText = e.data; };
            socket.onclose = () => { status.innerText = "RECONECTANDO..."; setTimeout(connect, 1000); };
        }
        connect();
    </script>
</body>
</html>
"""

class BadAppleEngine:
    def __init__(self):
        self.frames = []
        self.use_math = True
        
    def load(self):
        print(f"🔍 Buscando video en: {os.path.abspath(VIDEO_PATH)}")
        if os.path.exists(VIDEO_PATH):
            cap = cv2.VideoCapture(VIDEO_PATH)
            if cap.isOpened():
                print("✅ Video abierto. Procesando frames...")
                while len(self.frames) < 500: # Limitamos a 500 frames para no explotar la RAM de Azure
                    ret, frame = cap.read()
                    if not ret: break
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    resized = cv2.resize(gray, (WIDTH, int(WIDTH * 0.5)))
                    ascii_f = "".join([ASCII_CHARS[p // 25] for p in resized.flatten()])
                    self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
                cap.release()
                if self.frames:
                    self.use_math = False
                    print(f"🎬 {len(self.frames)} frames cargados.")
                    return
        print("⚠️ Falla de video. Activando generador matemático.")

    def get_frame(self, t):
        if not self.use_math:
            return self.frames[t % len(self.frames)]
        # Generador de emergencia (Metaballs ASCII)
        out = ""
        for y in range(30):
            for x in range(WIDTH):
                d = math.sqrt((x-WIDTH/2 + math.sin(t/10)*20)**2 + (y-15 + math.cos(t/10)*10)**2)
                out += ASCII_CHARS[min(int(100/max(d,1)), 10)]
            out += "\\n"
        return out

engine = BadAppleEngine()

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    t = 0
    try:
        while not ws.closed:
            await ws.send_str(engine.get_frame(t))
            t += 1
            await asyncio.sleep(0.04)
    finally:
        return ws

async def index(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

app = web.Application()
app.add_routes([web.get('/', index), web.get('/ws', websocket_handler)])

if __name__ == '__main__':
    engine.load()
    web.run_app(app, port=PORT)
