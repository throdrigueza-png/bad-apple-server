import asyncio
import cv2
import os
import math
from aiohttp import web

# Azure configurado: Usará el puerto 8000 que definiste en tus variables
PORT = int(os.environ.get("WEBSITES_PORT", 8000))
VIDEO_PATH = "assets/bad_apple.mp4"
WIDTH = 80
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>BAD APPLE ASCII</title>
<style>body{background:#000;color:#0f0;display:flex;flex-direction:column;align-items:center;font-family:monospace;justify-content:center;height:100vh;margin:0;}
#c{font-size:10px;line-height:8px;white-space:pre;background:#000;padding:20px;border:1px solid #333;}</style></head>
<body><h1 id="s">CONECTANDO AL NÚCLEO...</h1><div id="c"></div><script>
const c=document.getElementById('c'), s=document.getElementById('s');
const ws=new WebSocket((window.location.protocol==='https:'?'wss://':'ws://')+window.location.host+'/ws');
ws.onopen=()=>{s.innerText="BAD APPLE ONLINE";s.style.color="#fff";};
ws.onmessage=(e)=>{c.innerText=e.data;};
ws.onclose=()=>s.innerText="DESCONECTADO - REINTENTANDO...";
</script></body></html>
"""

class BadAppleEngine:
    def __init__(self): self.frames = []
    def load(self):
        if not os.path.exists(VIDEO_PATH): return
        cap = cv2.VideoCapture(VIDEO_PATH)
        while len(self.frames) < 1200: # Carga unos 40 segundos para no saturar la RAM
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            res = cv2.resize(gray, (WIDTH, int(WIDTH * 0.5)))
            ascii_f = "".join([ASCII_CHARS[p // 25] for p in res.flatten()])
            self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
        cap.release()
    def get(self, t):
        if self.frames: return self.frames[t % len(self.frames)]
        return "ERROR: No se encontró assets/bad_apple.mp4"

engine = BadAppleEngine()

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    t = 0
    try:
        while not ws.closed:
            await ws.send_str(engine.get(t))
            t += 1
            await asyncio.sleep(0.04) # 25 FPS aprox
    except: pass
    return ws

async def index(request): return web.Response(text=HTML, content_type='text/html')

async def init_app():
    engine.load()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', ws_handler)])
    return app

if __name__ == '__main__':
    web.run_app(init_app(), host='0.0.0.0', port=PORT)
