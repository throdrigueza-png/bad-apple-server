import asyncio
import cv2
import os
from aiohttp import web

# Usamos el puerto 8000 que configuraste en tus variables de Azure
PORT = int(os.environ.get("WEBSITES_PORT", 8000))
VIDEO_PATH = "assets/bad_apple.mp4"
WIDTH = 80
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

# HTML que el navegador va a mostrar
HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>BAD APPLE</title>
<style>body{background:#000;color:#0f0;display:flex;flex-direction:column;align-items:center;font-family:monospace;}
#c{font-size:10px;line-height:8px;white-space:pre;}</style></head>
<body><h1 id="s">CONECTANDO...</h1><div id="c"></div><script>
const c=document.getElementById('c'), s=document.getElementById('s');
const ws=new WebSocket((window.location.protocol==='https:'?'wss://':'ws://')+window.location.host+'/ws');
ws.onopen=()=>{s.innerText="BAD APPLE ONLINE";};
ws.onmessage=(e)=>{c.innerText=e.data;};
</script></body></html>
"""

class BadAppleEngine:
    def __init__(self): self.frames = []
    def load(self):
        cap = cv2.VideoCapture(VIDEO_PATH)
        while len(self.frames) < 1000:
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            res = cv2.resize(gray, (WIDTH, int(WIDTH * 0.5)))
            ascii_f = "".join([ASCII_CHARS[p // 25] for p in res.flatten()])
            self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
        cap.release()

engine = BadAppleEngine()

async def ws_handler(request):
    ws = web.WebSocketResponse(); await ws.prepare(request)
    t = 0
    while not ws.closed:
        await ws.send_str(engine.frames[t % len(engine.frames)] if engine.frames else "Cargando...")
        t += 1; await asyncio.sleep(0.04)
    return ws

async def index(request): return web.Response(text=HTML, content_type='text/html')

app = web.Application()
app.add_routes([web.get('/', index), web.get('/ws', ws_handler)])

if __name__ == '__main__':
    engine.load()
    web.run_app(app, host='0.0.0.0', port=PORT)
