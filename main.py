import os
import asyncio
import cv2
import logging
from aiohttp import web

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BadApple")

# --- CONFIGURACIÓN DE ENTORNO ---
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "bad_apple.mp4")

ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
# Reducimos un poco el ancho para que Azure no se ahogue
WIDTH = 60 

class VideoEngine:
    def __init__(self):
        self.frames = []
        self.is_ready = False
        self.total_frames_loaded = 0

    async def preload_async(self):
        """Carga el video cediendo el control en CADA cuadro para no bloquear"""
        logger.info(f"--> Iniciando carga suave de: {VIDEO_PATH}")
        
        if not os.path.exists(VIDEO_PATH):
            logger.error("ERROR CRÍTICO: No existe el video")
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret: 
                    break 
                
                # Procesamiento rápido
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape
                aspect_ratio = w / h
                new_height = int(WIDTH / aspect_ratio * 0.55)
                resized = cv2.resize(gray, (WIDTH, new_height))
                
                ascii_frame = ""
                for row in resized:
                    ascii_frame += "".join([ASCII_CHARS[pixel // 25] for pixel in row]) + "\n"
                
                self.frames.append(ascii_frame)
                self.total_frames_loaded += 1
                
                # --- EL CAMBIO MÁGICO ---
                # Dormir 0 segundos fuerza a Python a soltar la CPU y 
                # atender el WebSocket. Vital para que no se corte.
                await asyncio.sleep(0) 
            
            self.is_ready = True
            logger.info(f"--> CARGA COMPLETA: {len(self.frames)} cuadros.")
            
        except Exception as e:
            logger.error(f"Error cargando video: {e}")
        finally:
            cap.release()

engine = VideoEngine()

# --- FRONTEND ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAD APPLE</title>
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; 
               display: flex; flex-direction: column; align-items: center; justify-content: center; 
               height: 100vh; margin: 0; overflow: hidden; }
        #screen { font-size: 8px; line-height: 8px; white-space: pre; border: 1px solid #050; padding: 10px; }
        #status { font-size: 1rem; margin-bottom: 10px; font-weight: bold; text-align: center; }
        .live { color: #0f0; text-shadow: 0 0 5px #0f0; }
        .error { color: #f00; }
    </style>
</head>
<body>
    <div id="status">CONECTANDO...</div>
    <div id="screen"></div>
    <script>
        const screen = document.getElementById('screen');
        const status = document.getElementById('status');
        let socket;

        function connect() {
            const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            // Añadimos timestamp para evitar caché agresivo
            const wsUrl = proto + window.location.host + '/ws?t=' + Date.now();
            
            socket = new WebSocket(wsUrl);
            
            socket.onopen = () => {
                status.innerText = "● LIVE";
                status.className = "live";
            };
            
            socket.onmessage = (e) => { 
                screen.innerText = e.data; 
            };
            
            socket.onclose = (e) => {
                console.log("Cerrado: ", e);
                status.innerText = "RECONECTANDO...";
                status.className = "error";
                // Reconexión agresiva rápida
                setTimeout(connect, 500);
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
    # Heartbeat a 30s para ser más tolerantes con lags de red
    ws = web.WebSocketResponse(autoping=True, heartbeat=30.0)
    await ws.prepare(request)
    
    # Si el motor apenas está arrancando, esperamos un poco
    while len(engine.frames) < 100 and not engine.is_ready:
        await ws.send_str(f"BUFFERING... {len(engine.frames)} FRAMES")
        await asyncio.sleep(0.5)

    try:
        i = 0
        total_frames = len(engine.frames)
        
        # Bucle de streaming
        while not ws.closed:
            # Si alcanzamos el final de lo que hay cargado, esperamos
            if i >= len(engine.frames):
                if engine.is_ready:
                    i = 0 # Reiniciar video si ya terminó de cargar todo
                else:
                    await asyncio.sleep(0.1) # Esperar a que cargue más
                    continue
            
            # Enviar cuadro
            await ws.send_str(engine.frames[i])
            i += 1
            
            # Control de FPS (30 FPS = ~0.033s)
            await asyncio.sleep(0.033)
            
    except Exception as e:
        logger.error(f"Cliente desconectado: {e}")
    finally:
        pass
        
    return ws

async def start_background_tasks(app):
    app['video_loader'] = asyncio.create_task(engine.preload_async())

def init_app():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    app.on_startup.append(start_background_tasks)
    return app

if __name__ == '__main__':
    app = init_app()
    web.run_app(app, host='0.0.0.0', port=PORT)
