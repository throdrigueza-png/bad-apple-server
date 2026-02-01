import asyncio
import cv2
import os
import math
from aiohttp import web

# --- CONFIGURACIÓN AZURE ---
PORT = int(os.environ.get("PORT", 8000))
VIDEO_PATH = "assets/bad_apple.mp4" 
WIDTH = 80 
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

# --- CLIENTE HTML INTEGRADO ---
HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>BAD APPLE ASCII</title>
<style>body{background:#000;color:#0f0;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;margin:0;font-family:monospace;}
#c{font-size:10px;line-height:8px;white-space:pre;font-weight:bold;transform:scale(1.2);}</style></head>
<body><h1 id="s">CONECTANDO...</h1><div id="c"></div><script>
const c=document.getElementById('c'),s=document.getElementById('s');
const ws=new WebSocket((window.location.protocol==='https:'?'wss://':'ws://')+window.location.host+'/ws');
ws.onopen=()=>{s.innerText="ONLINE";s.style.color="#fff";};
ws.onmessage=(e)=>{c.innerText=e.data;};
ws.onclose=()=>s.innerText="DISCONNECTED";
</script></body></html>
"""

class AppleEngine:
    def __init__(self):
        self.frames = []
        self.ready = False
    
    def load_video(self):
        if os.path.exists(VIDEO_PATH):
            cap = cv2.VideoCapture(VIDEO_PATH)
            while cap.isOpened() and len(self.frames) < 1000:
                ret, frame = cap.read()
                if not ret: break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (WIDTH, int(WIDTH * 0.5)))
                ascii_f = "".join([ASCII_CHARS[p // 25] for p in resized.flatten()])
                self.frames.append("\\n".join([ascii_f[i:i+WIDTH] for i in range(0, len(ascii_f), WIDTH)]))
            cap.release()
            if self.frames: self.ready = True

    def get_frame(self, t):
        if self.ready: return self.frames[t % len(self.frames)]
        # Failsafe: Animación matemática si el video falla
        out = ""
        for y in range(30):
            for x in range(WIDTH):
                d = math.sqrt((x-WIDTH/2+math.sin(t/10)*20)**2 + (y-15+math.cos(t/10)*10)**2)
                out += ASCII_CHARS[min(int(100/max(d,1)), 10)]
            out += "\\n"
        return out

engine = AppleEngine()

async def wsh(r):
    ws = web.WebSocketResponse()
    await ws.prepare(r)
    t = 0
    try:
        while not ws.closed:
            await ws.send_str(engine.get_frame(t))
            t += 1
            await asyncio.sleep(0.04)
    finally: return ws

async def index(r): return web.Response(text=HTML, content_type='text/html')

async def init():
    engine.load_video()
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/ws', wsh)])
    return app

if __name__ == '__main__':
    web.run_app(init(), port=PORT)
