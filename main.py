import asyncio
import cv2
import websockets
import os
import time

# --- CONFIGURACIÓN ---
PORT = int(os.environ.get("PORT", 8081))
VIDEO_PATH = "assets/bad_apple.mp4" 
WIDTH = 100 
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

# --- VARIABLES GLOBALES ---
# Aquí guardaremos TODO el video convertido a texto para máxima velocidad
ASCII_CACHE = [] 
CURRENT_FRAME_INDEX = 0
TOTAL_FRAMES = 0

def resize_image(image, new_width=100):
    (h, w) = image.shape
    aspect_ratio = h / w
    new_height = int(aspect_ratio * new_width * 0.55)
    resized_image = cv2.resize(image, (new_width, new_height))
    return resized_image

def pixel_to_ascii(image):
    pixels = image.flatten()
    ascii_str = "".join([ASCII_CHARS[pixel // 25] for pixel in pixels])
    return ascii_str

def load_video_to_memory():
    """
    LEE EL VIDEO UNA SOLA VEZ Y LO GUARDA EN RAM.
    Esto evita que el disco duro o el procesamiento en tiempo real causen lag.
    """
    global ASCII_CACHE, TOTAL_FRAMES
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ ERROR: No encuentro {VIDEO_PATH}")
        return

    print("⏳ CARGANDO VIDEO EN MEMORIA RAM (Esto puede tardar unos segundos)...")
    cap = cv2.VideoCapture(VIDEO_PATH)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized_frame = resize_image(gray_frame, WIDTH)
        ascii_str = pixel_to_ascii(resized_frame)
        img_width = resized_frame.shape[1]
        ascii_img = "\n".join([ascii_str[i:(i+img_width)] for i in range(0, len(ascii_str), img_width)])
        
        ASCII_CACHE.append(ascii_img)

    cap.release()
    TOTAL_FRAMES = len(ASCII_CACHE)
    print(f"✅ VIDEO CARGADO: {TOTAL_FRAMES} frames listos en RAM.")

async def global_video_clock():
    """
    ESTO ES EL CORAZÓN.
    Avanza el video en segundo plano SIEMPRE, haya clientes o no.
    Garantiza que el video nunca se detenga por culpa del scroll del usuario.
    """
    global CURRENT_FRAME_INDEX
    while True:
        if TOTAL_FRAMES > 0:
            CURRENT_FRAME_INDEX = (CURRENT_FRAME_INDEX + 1) % TOTAL_FRAMES
        # 30 FPS constantes (0.033s)
        await asyncio.sleep(0.033)

async def handler(websocket):
    print(f"🔥 CLIENTE CONECTADO: {websocket.remote_address}")
    try:
        # El cliente simplemente recibe cual sea el frame actual del "reloj global"
        while True:
            if TOTAL_FRAMES > 0:
                # Enviamos el frame que toca AHORA MISMO
                await websocket.send(ASCII_CACHE[CURRENT_FRAME_INDEX])
            
            # Pequeña pausa para no saturar la red, pero el ritmo lo marca el global_clock
            await asyncio.sleep(0.033)
            
    except websockets.exceptions.ConnectionClosed:
        print("⚠️ Cliente desconectado (El video sigue corriendo en el servidor)")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    # 1. Cargar video en RAM antes de abrir el servidor
    load_video_to_memory()
    
    if TOTAL_FRAMES == 0:
        print("❌ NO SE PUDO CARGAR EL VIDEO. REVISA LA RUTA.")
        return

    # 2. Iniciar el reloj del video en segundo plano
    asyncio.create_task(global_video_clock())

    # 3. Abrir el servidor
    print(f"🚀 SERVIDOR GOD MODE LISTO EN PUERTO {PORT}")
    async with websockets.serve(handler, "0.0.0.0", PORT, ping_interval=None):
        await asyncio.Future()  # Correr para siempre

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido.")