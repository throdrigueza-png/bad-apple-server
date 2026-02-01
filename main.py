import asyncio
import cv2
import os
from aiohttp import web

# Lee el puerto de las variables que ya configuraste (8000)
PORT = int(os.environ.get("WEBSITES_PORT", 8000))
VIDEO_PATH = "assets/bad_apple.mp4"
WIDTH = 80
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>BAD APPLE</title>
<style>body{background:#000;color:#0f0;display:flex;flex-direction:column;align-items:center;font-family:monospace;justify-content:center;height:100vh;margin:0;}
#c{font-size:10px;line-height:8px;white-space:pre;}</style></head>
<body><h1 id="s">CONECTANDO...</h1><div id="c"></div><script>
const c=document.getElementById('c'), s=document.getElementById('s');
const ws=new WebSocket((window.location.protocol==='https:'?'wss://':'ws://')+window.location.host+'/ws');
ws.onopen=()=>{s.innerText="ONLINE";};
ws.onmessage=(e)=>{c.innerText=e.data;};
</script></body></html>
"""

class Engine:
    def __init__(self): self.frames = []
    def load(self):
        if not os.path.exists(VIDEO_PATH): return
        cap = cv2.VideoCapture(VIDEO_PATH)
        while len(self.frames) < 1000:
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            res = cv2.resize(gray, (WIDTH, int(WIDTH * 0.5)))
            ascii_f = "".join([ASCII_CHARS[p // 25] for p in res.flatten()])
            self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
        cap.release()

engine = Engine()

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    t = 0
    while not ws.closed:
        await ws.send_str(engine.frames[t % len(engine.frames)] if engine.frames else "No video found in assets/")
        t += 1
        await asyncio.sleep(0.04)
    return ws

async def index(request): return web.Response(text=HTML, content_type='text/html')

async def init():
    engine.load()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', ws_handler)])
    return app

if __name__ == '__main__':
    web.run_app(init(), host='0.0.0.0', port=PORT)
