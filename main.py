import os
import asyncio
import cv2
import logging
from aiohttp import web

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BadApple")

# --- CONFIGURACIÓN DE ENTORNO ---
# Azure siempre pasa el puerto en la variable de entorno PORT
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
        """Carga el video en memoria COMPLETO en segundo plano"""
        logger.info(f"--> Buscando video en: {VIDEO_PATH}")
        
        if not os.path.exists(VIDEO_PATH):
            self.error = "ERROR CRÍTICO: No existe assets/bad_apple.mp4"
            logger.error(self.error)
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret: 
                    break 
                
                # 1. Escala de grises
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 2. Redimensionar
                h, w = gray.shape
                aspect_ratio = w / h
                new_height = int(WIDTH / aspect_ratio * 0.55)
                resized = cv2.resize(gray, (WIDTH, new_height))
                
                # 3. ASCII
                ascii_frame = ""
                for row in resized:
                    ascii_frame += "".join([ASCII_CHARS[pixel // 25] for pixel in row]) + "\n"
                
                self.frames.append(ascii_frame)
                count += 1
                
                # Dejamos respirar al servidor cada 50 cuadros para no bloquear el inicio
                if count % 50 == 0:
                    await asyncio.sleep(0.01) 
            
            self.is_ready = True
            logger.info(f"--> VIDEO COMPLETADO: {len(self.frames)} cuadros cargados en RAM.")
            
        except Exception as e:
            logger.error(f"Error procesando video: {e}")
        finally:
            cap.release()

engine = VideoEngine()

# --- FRONTEND (HTML) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BAD APPLE FULL</title>
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; 
               display: flex; flex-direction: column; align-items: center; justify-content: center; 
               height: 100vh; margin: 0; overflow: hidden; }
        #screen { font-size: 10px; line-height: 8px; white-space: pre; border: 1px solid #050; padding: 20px; }
        #status { font-size: 1.2rem; margin-bottom: 10px; font-weight: bold; }
        .live { color: #0f0; text-shadow: 0 0 10px #0f0; }
        .error { color: #f00; }
        .loading { color: #ff0; }
    </style>
</head>
<body>
    <div id="status" class="loading">CONECTANDO...</div>
    <div id="screen"></div>
    <script>
        const screen = document.getElementById('screen');
        const status = document.getElementById('status');
        let socket;

        function connect() {
            const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const wsUrl = proto + window.location.host + '/ws';
            console.log("Conectando a: " + wsUrl);
            
            socket = new WebSocket(wsUrl);
            
            socket.onopen = () => {
                status.innerText = "● BAD APPLE - ONLINE";
                status.className = "live";
            };
            
            socket.onmessage = (e) => { 
                screen.innerText = e.data; 
            };
            
            socket.onclose = () => {
                status.innerText = "○ RECONECTANDO...";
                status.className = "error";
                setTimeout(connect, 2000);
            };
            
            socket.onerror = (e) => console.error("WS Error:", e);
        }
        connect();
    </script>
</body>
</html>
"""

async def index_handler(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def ws_handler(request):
    ws = web.WebSocketResponse(autoping=True, heartbeat=10.0)
    await ws.prepare(request)
    
    # Esperar a que el video cargue si el usuario entra muy rápido
    if not engine.is_ready:
        await ws.send_str("CARGANDO VIDEO EN EL SERVIDOR...\nESPERA UN MOMENTO...")
        while not engine.is_ready:
            await asyncio.sleep(1)

    try:
        i = 0
        total_frames = len(engine.frames)
        if total_frames == 0:
             await ws.send_str("ERROR: VIDEO NO ENCONTRADO O VACÍO")
             return ws

        # Bucle de streaming
        while not ws.closed:
            await ws.send_str(engine.frames[i])
            i = (i + 1) % total_frames
            await asyncio.sleep(0.033) # ~30 FPS
    except Exception as e:
        logger.error(f"Error en socket: {e}")
    finally:
        pass
        
    return ws

async def start_background_tasks(app):
    """Inicia la carga del video sin bloquear el servidor"""
    app['video_loader'] = asyncio.create_task(engine.preload_async())

# --- INICIO DE LA APP ---
def init_app():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    app.on_startup.append(start_background_tasks)
    return app

if __name__ == '__main__':
    # Ejecución directa para Azure
    app = init_app()
    web.run_app(app, host='0.0.0.0', port=PORT)
