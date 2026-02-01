import asyncio
import cv2
import os
import math
from aiohttp import web

# --- CONFIGURACIÓN ---
# Azure usa 'PORT' o 'WEBSITES_PORT'. Si no, usamos 8000.
PORT = int(os.environ.get("PORT", os.environ.get("WEBSITES_PORT", 8000)))
VIDEO_PATH = "assets/bad_apple.mp4" 
WIDTH = 80 
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

HTML_CONTENT = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>BAD APPLE</title>
<style>body{background:#000;color:#0f0;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;margin:0;font-family:monospace;}
#c{font-size:10px;line-height:8px;white-space:pre;font-weight:bold;}</style></head>
<body><h1 id="s">CONECTANDO...</h1><div id="c"></div><script>
const c=document.getElementById('c'),s=document.getElementById('s');
const ws=new WebSocket((window.location.protocol==='https:'?'wss://':'ws://')+window.location.host+'/ws');
ws.onopen=()=>{s.innerText="ONLINE";};
ws.onmessage=(e)=>{c.innerText=e.data;};
ws.onclose=()=>setTimeout(()=>window.location.reload(),2000);
</script></body></html>
"""

class VideoEngine:
    def __init__(self):
        self.frames = []
    def load(self):
        if os.path.exists(VIDEO_PATH):
            cap = cv2.VideoCapture(VIDEO_PATH)
            while len(self.frames) < 600:
                ret, frame = cap.read()
                if not ret: break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (WIDTH, int(WIDTH * 0.5)))
                ascii_f = "".join([ASCII_CHARS[p // 25] for p in resized.flatten()])
                self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
            cap.release()
    def get_frame(self, t):
        if self.frames: return self.frames[t % len(self.frames)]
        return "Cargando video o archivo no encontrado..."

engine = VideoEngine()

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    t = 0
    try:
        while not ws.closed:
            await ws.send_str(engine.get_frame(t))
            t += 1
            await asyncio.sleep(0.04)
    except: pass
    return ws

async def index(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def create_app():
    engine.load()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', ws_handler)])
    return app

if __name__ == '__main__':
    print(f"🚀 ARRANCANDO EN PUERTO: {PORT}")
    web.run_app(create_app(), port=PORT)
