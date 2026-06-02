import cv2
import threading
import time
import numpy as np
from app.core.detector import PersonDetector
from app.core.counter import MalocaCounter

class MonitorSystem:
    def __init__(self, source, capacity, line_ratio, rotate=False):
        self.detector = PersonDetector()
        self.counter = MalocaCounter(capacity, line_ratio)
        self.source = source
        self.rotate = rotate
        self.cap = cv2.VideoCapture(source)
        
        # Buffer de frames
        self.raw_frame = None
        self.encoded_frame = None
        self.running = True
        
        # Thread de Captura (Lectura constante para evitar lag)
        threading.Thread(target=self._capture, daemon=True).start()
        # Thread de Procesamiento (IA + UI)
        threading.Thread(target=self._run, daemon=True).start()

    def _capture(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.source)
                continue
            self.raw_frame = frame
            time.sleep(0.01)

    def _run(self):
        frame_count = 0
        while self.running:
            if self.raw_frame is None:
                time.sleep(0.01)
                continue
            
            # Solo procesar cada 2do frame para reducir carga de CPU
            frame_count += 1
            if frame_count % 2 != 0:
                time.sleep(0.01)
                continue

            frame = self.raw_frame.copy()

            if self.rotate:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            h, w, _ = frame.shape
            line_x = int(w * self.counter.line_ratio)
            
            # 1. IA Tracking (Optimizado con imgsz=320 para velocidad)
            results = self.detector.track(frame)
            
            # 2. Dibujar UI
            cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 4)
            cv2.putText(frame, "FUERA", (line_x - 70, 30), 0, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, "DENTRO", (line_x + 10, 30), 0, 0.6, (0, 255, 0), 2)

            if results[0].boxes.id is not None:
                ids = results[0].boxes.id.int().cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                self.counter.update(ids, boxes, w)
                
                for box, id in zip(boxes, ids):
                    x1, y1, x2, y2 = map(int, box)
                    cx = (x1 + x2) // 2
                    color = (0, 255, 0) if cx > line_x else (0, 0, 255)
                    label = "DENTRO" if cx > line_x else "FUERA"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{label} | ID:{id}", (x1, y1 - 10), 0, 0.5, color, 2)
            
            if self.counter.last_event:
                cv2.putText(frame, self.counter.last_event, (w//2 - 130, h - 45), 0, 0.8, (255,255,255), 2)

            # Pre-codificar el frame para el API (Calidad 70% para ahorrar ancho de banda)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self.encoded_frame = buffer.tobytes()
            
            time.sleep(0.005)

    def get_frame(self):
        return self.encoded_frame

