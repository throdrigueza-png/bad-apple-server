import cv2
import websocket
import time
import numpy as np
import threading

# Configuración
JAVA_SERVER_URL = "ws://localhost:8080/ws-binary-stream"
VIDEO_PATH = "bad_apple.mp4" 
WIDTH = 100 

def on_open(ws):
    print(">>> CONEXIÓN ABIERTA CON JAVA. INICIANDO STREAM...")
    def run(*args):
        cap = cv2.VideoCapture(VIDEO_PATH)
        if not cap.isOpened():
            print(f"❌ ERROR: No encuentro el video en {VIDEO_PATH}")
            ws.close()
            return

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Procesamiento Matrix
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            height, _ = gray.shape
            aspect_ratio = gray.shape[1] / height
            new_height = int(WIDTH / aspect_ratio * 0.55)
            resized = cv2.resize(gray, (WIDTH, new_height))
            
            # Binarizar (0 y 1)
            binary_frame = np.where(resized > 128, "1", "0")
            frame_text = "\n".join(["".join(row) for row in binary_frame])
            
            # Enviar a Java
            ws.send(frame_text)
            time.sleep(0.033) # ~30 FPS

        cap.release()
        ws.close()
        print(">>> STREAM FINALIZADO")
    
    threading.Thread(target=run).start()

def on_error(ws, error):
    print(f"❌ Error WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    print(">>> Conexión cerrada")

if __name__ == "__main__":
    # Mantener intento de conexión hasta que Java despierte
    while True:
        try:
            ws = websocket.WebSocketApp(JAVA_SERVER_URL,
                                      on_open=on_open,
                                      on_error=on_error,
                                      on_close=on_close)
            ws.run_forever()
        except:
            print("⏳ Esperando a Java Server...")
            time.sleep(2)
