import os
import asyncio
import cv2
import numpy as np
from aiohttp import web

# --- CONFIGURACIÓN ---
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "bad_apple.mp4")

# Caracteres para el arte ASCII
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
WIDTH = 80 

# --- HTML DEL CLIENTE ---
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Bad Apple Azure - Live</title>
    <style>
        body { background: #000; color: #fff; display: flex; flex-direction: column; 
               align-items: center; justify-content: center; height: 100vh; margin: 0; 
               font-family: 'Courier New', monospace; overflow: hidden; }
        #screen { font-size: 10px; line-height: 8px; white-space: pre; color: #0f0; 
                  text-shadow: 0 0 5px #0f0; }
        #status { font-size: 14px; color: #555; margin-bottom: 10px; text-transform: uppercase; }
    </style>
</head>
<body>
    <div id="status">Iniciando...</div>
    <div id="screen"></div>
    <script>
        const screen = document.getElementById('screen');
        const status = document.getElementById('status');
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const ws = new WebSocket(protocol + window.location.host + '/ws');

            ws.onopen = () => { 
                status.innerText = "● EN VIVO"; 
                status.style.color = "#0f0"; 
            };
            
            ws.onmessage = (event) => { screen.innerText = event.data; };
            
            ws.onclose = () => { 
                status.innerText = "○ RECONECTANDO..."; 
                status.style.color = "red";
                setTimeout(connect, 2000);
            };
        }
        connect();
    </script>
</body>
</html>
"""

# --- MOTOR DE VIDEO ---
class VideoEngine:
    def __init__(self):
        self.frames = []
        self.is_ready = False
        self.error = None

    async def preload_async(self):
        """Carga el video sin bloquear el inicio del servidor"""
        print(f"DEBUG: Iniciando carga de video en: {VIDEO_PATH}")
        
        if not os.path.exists(VIDEO_PATH):
            self.error = "ERROR: Video no encontrado en /assets/"
            print(self.error)
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        try:
            count = 0
            while True:
                ret, frame = cap.read()
                if not ret or count >= 2000: # Límite de 2000 frames para estabilidad
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape
                aspect_ratio = w / h
                new_height = int(WIDTH / aspect_ratio * 0.5)
                resized = cv2.resize(gray, (WIDTH, new_height))
                
                ascii_frame = ""
                for pixel_row in resized:
                    line = "".join([ASCII_CHARS[pixel // 25] for pixel in pixel_row])
                    ascii_frame += line + "\n"
                
                self.frames.append(ascii_frame)
                count += 1
                
                # Soltar el control cada 50 frames para que el servidor responda
                if count % 50 == 0:
                    await asyncio.sleep(0.01)

            self.is_ready = True
            print(f"DEBUG: Video cargado con éxito ({len(self.frames)} frames)")
            
        except Exception as e:
            self.error = f"Error en motor: {str(e)}"
            print(self.error)
        finally:
            cap.release()

engine = VideoEngine()

# --- RUTAS ---
async def index(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    if not engine.is_ready:
        await ws.send_str("CARGANDO VIDEO EN SERVIDOR... ESPERE...")
        while not engine.is_ready:
            await asyncio.sleep(1)

    frame_idx = 0
    try:
        while not ws.closed:
            await ws.send_str(engine.frames[frame_idx])
            frame_idx = (frame_idx + 1) % len(engine.frames)
            await asyncio.sleep(0.04) # ~25 FPS
    except Exception:
        pass
    return ws

# --- ARRANQUE OPTIMIZADO PARA AZURE ---
async def on_startup(app):
    # Esto inicia la carga del video sin detener el arranque del servidor
    asyncio.create_task(engine.preload_async())

async def init_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.add_routes([
        web.get('/', index),
        web.get('/ws', websocket_handler)
    ])
    return app

if __name__ == '__main__':
    print(f"Servidor Bad Apple iniciando en puerto {PORT}...")
    web.run_app(init_app(), host='0.0.0.0', port=PORT)
