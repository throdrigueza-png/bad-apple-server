import os
import asyncio
import cv2
import numpy as np
from aiohttp import web

# --- CONFIGURACIÓN ---
# Azure asigna el puerto dinámicamente o usa el 8000 por defecto
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "bad_apple.mp4")

# Caracteres para el arte ASCII (de oscuro a claro)
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
WIDTH = 80 # Ancho de la "pantalla" en caracteres

# --- HTML DEL CLIENTE ---
# Este HTML incluye reconexión automática si se cae
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Bad Apple Azure</title>
    <style>
        body { background: #000; color: #fff; display: flex; flex-direction: column; 
               align-items: center; justify-content: center; height: 100vh; margin: 0; 
               font-family: 'Courier New', monospace; overflow: hidden; }
        #screen { font-size: 8px; line-height: 8px; white-space: pre; }
        #status { font-size: 14px; color: #555; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div id="status">Conectando...</div>
    <div id="screen"></div>
    <script>
        const screen = document.getElementById('screen');
        const status = document.getElementById('status');
        
        function connect() {
            // Detectar si es http o https para usar ws o wss
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const ws = new WebSocket(protocol + window.location.host + '/ws');

            ws.onopen = () => { status.innerText = "EN VIVO"; status.style.color = "#0f0"; };
            
            ws.onmessage = (event) => { 
                screen.innerText = event.data; 
            };
            
            ws.onclose = () => { 
                status.innerText = "Reconectando..."; 
                status.style.color = "red";
                setTimeout(connect, 1000); // Reintentar en 1 segundo
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

    def preload(self):
        print(f"Cargando video desde: {VIDEO_PATH}")
        if not os.path.exists(VIDEO_PATH):
            self.error = f"ERROR CRITICO: No encuentro el video en {VIDEO_PATH}"
            print(self.error)
            return

        cap = cv2.VideoCapture(VIDEO_PATH)
        if not cap.isOpened():
            self.error = "ERROR CRITICO: OpenCV no pudo abrir el archivo de video."
            print(self.error)
            return

        # Pre-procesamos todo el video a RAM para que sea fluido
        try:
            while True:
                ret, frame = cap.read()
                if not ret: break
                
                # Convertir a escala de grises
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Redimensionar manteniendo relación de aspecto de fuente
                h, w = gray.shape
                aspect_ratio = w / h
                new_height = int(WIDTH / aspect_ratio * 0.55)
                resized = cv2.resize(gray, (WIDTH, new_height))
                
                # Mapear pixeles a caracteres
                # Usamos division entera // 25 para mapear 0-255 a 0-10 indices
                ascii_frame = ""
                for pixel_row in resized:
                    line = "".join([ASCII_CHARS[pixel // 28] for pixel in pixel_row])
                    ascii_frame += line + "\n"
                
                self.frames.append(ascii_frame)
                
                # Limite de seguridad por si el video es eterno (max 3000 frames)
                if len(self.frames) > 3000: break
                
            self.is_ready = True
            print(f"Video cargado exitosamente: {len(self.frames)} frames.")
            
        except Exception as e:
            self.error = f"Error procesando video: {str(e)}"
            print(self.error)
        finally:
            cap.release()

# Instancia global del motor
engine = VideoEngine()

# --- RUTAS WEB ---

async def index(request):
    """Sirve la página HTML"""
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def websocket_handler(request):
    """Maneja la conexión en vivo"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Si hubo error al cargar, enviarlo al cliente
    if engine.error:
        await ws.send_str(engine.error)
        await ws.close()
        return ws

    # Si aun carga, esperar
    if not engine.is_ready:
        await ws.send_str("Servidor iniciando... Procesando video...")
        while not engine.is_ready:
            await asyncio.sleep(1)

    # Bucle de reproducción
    frame_idx = 0
    total_frames = len(engine.frames)
    
    try:
        while not ws.closed:
            if total_frames > 0:
                # Enviar frame actual
                await ws.send_str(engine.frames[frame_idx])
                
                # Avanzar frame (loop)
                frame_idx = (frame_idx + 1) % total_frames
                
                # Controlar velocidad (30 FPS aprox = 0.033s)
                await asyncio.sleep(0.04) 
            else:
                await ws.send_str("Video vacio.")
                await asyncio.sleep(1)
    except Exception as e:
        print(f"Cliente desconectado: {e}")
    finally:
        print("Cerrando socket")

    return ws

# --- INICIO DE LA APP ---

async def init_app():
    # Cargar video en segundo plano al arrancar
    engine.preload()
    
    app = web.Application()
    app.add_routes([
        web.get('/', index),
        web.get('/ws', websocket_handler)
    ])
    return app

if __name__ == '__main__':
    # Azure requiere que escuchemos en 0.0.0.0 y el puerto correcto
    print(f"Iniciando servidor en puerto {PORT}...")
    web.run_app(init_app(), host='0.0.0.0', port=PORT)
