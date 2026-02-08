import os
import asyncio
import cv2
import numpy as np
from aiohttp import web
import logging




# Configuración de Logs para ver TODO en Azure
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BadApple")



# --- CONFIGURACIÓN ---
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "bad_apple.mp4")

ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
WIDTH = 80 

class VideoEngine:
    def __init__(self):
        self.frames = []
        self.is_ready = False
        self.error = None

    async def preload_async(self):
        logger.info(f"Buscando video en: {VIDEO_PATH}")
        if not os.path.exists(VIDEO_PATH):
            self.error = "ERROR: No existe assets/bad_apple.mp4"
            logger.error(self.error)
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret or count >= 2100: break # ~1 min para no saturar memoria
                
                # Procesamiento optimizado
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape
                new_height = int(WIDTH / (w / h) * 0.5)
                resized = cv2.resize(gray, (WIDTH, new_height))
                
                # Conversión rápida a ASCII
                ascii_frame = ""
                for row in resized:
                    ascii_frame += "".join([ASCII_CHARS[pixel // 25] for pixel in row]) + "\n"
                
                self.frames.append(ascii_frame)
                count += 1
                if count % 100 == 0:
                    await asyncio.sleep(0.01) # Deja respirar a la CPU
            
            self.is_ready = True
            logger.info(f"VIDEO CARGADO: {len(self.frames)} cuadros listos.")
        except Exception as e:
            logger.error(f"Error procesando video: {e}")
        finally:
            cap.release()

engine = VideoEngine()

# --- INTERFAZ WEB INTEGRADA ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BAD APPLE AZURE MASTER</title>
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; 
               display: flex; flex-direction: column; align-items: center; justify-content: center; 
               height: 100vh; margin: 0; overflow: hidden; }
        #screen { font-size: 9px; line-height: 7px; white-space: pre; border: 1px solid #050; padding: 10px; }
        #status { font-size: 1.2rem; margin-bottom: 10px; font-weight: bold; }
        .live { color: #0f0; text-shadow: 0 0 10px #0f0; }
        .error { color: #f00; }
    </style>
</head>
<body>
    <div id="status">CONECTANDO AL SERVIDOR...</div>
    <div id="screen"></div>
    <script>
        const screen = document.getElementById('screen');
        const status = document.getElementById('status');
        
        function start() {
            const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const ws = new WebSocket(proto + window.location.host + '/ws');
            
            ws.onopen = () => {
                status.innerText = "● EN VIVO - REPRODUCIENDO";
                status.className = "live";
            };
            
            ws.onmessage = (e) => { screen.innerText = e.data; };
            
            ws.onclose = () => {
                status.innerText = "○ CONEXIÓN PERDIDA - REINTENTANDO...";
                status.className = "error";
                setTimeout(start, 2000);
            };
            
            ws.onerror = (e) => console.error("Error WS:", e);
        }
        start();
    </script>
</body>
</html>
"""

async def index_handler(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def ws_handler(request):
    ws = web.WebSocketResponse(autoping=True, heartbeat=10.0)
    await ws.prepare(request)
    
    logger.info("Cliente conectado al WebSocket")

    if not engine.is_ready:
        await ws.send_str("ESPERA: Cargando video en memoria del servidor...")
        while not engine.is_ready:
            await asyncio.sleep(1)

    try:
        idx = 0
        while not ws.closed:
            await ws.send_str(engine.frames[idx])
            idx = (idx + 1) % len(engine.frames)
            await asyncio.sleep(0.04) # 25 FPS
    except Exception as e:
        logger.info(f"Cliente desconectado: {e}")
    return ws

async def init():
    app = web.Application()
    # Esto soluciona problemas de CORS internamente
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    
    # Iniciar carga de video en segundo plano
    asyncio.create_task(engine.preload_async())
    return app

if __name__ == '__main__':
    web.run_app(init(), host='0.0.0.0', port=PORT)
