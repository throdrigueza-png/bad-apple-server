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

# Caracteres para el arte ASCII
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
WIDTH = 80 

class VideoEngine:
    def __init__(self):
        self.frames = []
        self.is_ready = False
        self.error = None

    async def preload_async(self):
        """Carga el video en memoria sin bloquear el servidor"""
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
                # Limite de seguridad (aprox 1.5 min de video para no explotar la RAM)
                if not ret or count >= 2500: 
                    break 
                
                # 1. Escala de grises
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 2. Redimensionar manteniendo ratio
                h, w = gray.shape
                aspect_ratio = w / h
                new_height = int(WIDTH / aspect_ratio * 0.55) # 0.55 corrige la altura de la fuente
                resized = cv2.resize(gray, (WIDTH, new_height))
                
                # 3. Convertir a ASCII
                ascii_frame = ""
                for row in resized:
                    ascii_frame += "".join([ASCII_CHARS[pixel // 25] for pixel in row]) + "\n"
                
                self.frames.append(ascii_frame)
                count += 1
                
                # IMPORTANTE: Cede el control cada 50 frames para que el servidor arranque
                if count % 50 == 0:
                    await asyncio.sleep(0.01) 
            
            self.is_ready = True
            logger.info(f"--> VIDEO CARGADO EXITOSAMENTE: {len(self.frames)} cuadros en memoria.")
            
        except Exception as e:
            logger.error(f"Error procesando video: {e}")
        finally:
            cap.release()

# Instancia global del motor
engine = VideoEngine()

# --- HTML / FRONTEND ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BAD APPLE AZURE</title>
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
            socket = new WebSocket(proto + window.location.host + '/ws');
            
            socket.onopen = () => {
                status.innerText = "● EN VIVO";
                status.className = "live";
            };
            
            socket.onmessage = (e) => { 
                screen.innerText = e.data; 
            };
            
            socket.onclose = () => {
                status.innerText = "○ RECONECTANDO...";
                status.className = "error";
                setTimeout(connect, 1000);
            };
            
            socket.onerror = (e) => console.error("WS Error:", e);
        }
        connect();
    </script>
</body>
</html>
"""

# --- HANDLERS (RUTAS) ---

async def index_handler(request):
    """Sirve la página HTML"""
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def ws_handler(request):
    """Maneja la conexión WebSocket con Heartbeat"""
    
    # AQUÍ ESTÁ LA MAGIA: heartbeat=10.0 evita que Azure corte la conexión
    ws = web.WebSocketResponse(autoping=True, heartbeat=10.0)
    await ws.prepare(request)
    
    logger.info("NUEVO CLIENTE CONECTADO")

    # Si el video aun no carga, esperamos sin bloquear
    if not engine.is_ready:
        await ws.send_str("CARGANDO VIDEO EN EL SERVIDOR...\nESPERA UN MOMENTO...")
        while not engine.is_ready:
            await asyncio.sleep(1)

    try:
        # Bucle de reproducción
        i = 0
        total_frames = len(engine.frames)
        
        while not ws.closed:
            # Enviamos el cuadro actual
            await ws.send_str(engine.frames[i])
            
            # Avanzamos al siguiente cuadro (bucle infinito con módulo %)
            i = (i + 1) % total_frames
            
            # CONTROL DE VELOCIDAD (FPS)
            # 0.033 = ~30 FPS
            # IMPORTANTE: Usar await asyncio.sleep, NUNCA time.sleep
            await asyncio.sleep(0.033)

    except Exception as e:
        logger.info(f"Cliente desconectado o error: {e}")
    finally:
        logger.info("Conexión cerrada.")
    
    return ws

# --- INICIO DE LA APP ---

async def start_background_tasks(app):
    """Inicia la carga del video cuando la app arranca"""
    app['video_loader'] = asyncio.create_task(engine.preload_async())

async def init_app():
    """Factoría de la aplicación"""
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    
    # Registramos la tarea de carga al inicio
    app.on_startup.append(start_background_tasks)
    return app

if __name__ == '__main__':
    # Ejecución directa
    web.run_app(init_app(), host='0.0.0.0', port=PORT)
