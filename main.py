import asyncio
import cv2
import websockets
import os
import signal

# --- CONFIGURACIÓN ---
# Detecta el puerto que nos da Azure o usa el 8081 por defecto
PORT = int(os.environ.get("PORT", 8081))
VIDEO_PATH = "assets/bad_apple.mp4" 
WIDTH = 100 
ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]

# --- VARIABLES GLOBALES ---
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
    global ASCII_CACHE, TOTAL_FRAMES
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ ERROR CRITICO: No encuentro {VIDEO_PATH}")
        return

    print("⏳ CARGANDO VIDEO EN MEMORIA RAM...")
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
    global CURRENT_FRAME_INDEX
    print("⏰ RELOJ GLOBAL INICIADO")
    while True:
        if TOTAL_FRAMES > 0:
            CURRENT_FRAME_INDEX = (CURRENT_FRAME_INDEX + 1) % TOTAL_FRAMES
        await asyncio.sleep(0.033) # 30 FPS

async def handler(websocket):
    print(f"🔥 CLIENTE CONECTADO desde {websocket.remote_address}")
    try:
        while True:
            if TOTAL_FRAMES > 0:
                await websocket.send(ASCII_CACHE[CURRENT_FRAME_INDEX])
            await asyncio.sleep(0.033)
            
    except websockets.exceptions.ConnectionClosed:
        print("⚠️ Cliente desconectado")
    except Exception as e:
        print(f"❌ Error en socket: {e}")

async def main():
    print("--- INICIANDO SERVIDOR BAD APPLE ---")
    load_video_to_memory()
    
    if TOTAL_FRAMES == 0:
        print("❌ DETENIENDO: El video está vacío o no se cargó.")
        return

    asyncio.create_task(global_video_clock())

    # AQUÍ ESTÁ LA CLAVE: 0.0.0.0 permite que Azure entre
    print(f"🚀 SERVIDOR ESCUCHANDO EN 0.0.0.0:{PORT}")
    async with websockets.serve(handler, "0.0.0.0", PORT, ping_interval=None):
        # Mantenemos el proceso vivo para siempre
        stop = asyncio.Future()
        await stop

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido manualmente.")