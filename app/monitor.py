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
        self.current_frame = None
        self.running = True
        
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.source)
                continue

            if self.rotate:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            h, w, _ = frame.shape
            line_x = int(w * self.counter.line_ratio)
            
            # 1. IA Tracking
            results = self.detector.track(frame)
            
            # 2. Dibujar Línea de Límite (Roja y Clara)
            cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 4)
            cv2.putText(frame, "FUERA", (line_x - 70, 30), 0, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, "DENTRO", (line_x + 10, 30), 0, 0.6, (0, 255, 0), 2)

            if results[0].boxes.id is not None:
                ids = results[0].boxes.id.int().cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                
                # Actualizar Lógica de Posición
                self.counter.update(ids, boxes, w)
                
                for box, id in zip(boxes, ids):
                    x1, y1, x2, y2 = map(int, box)
                    cx = (x1 + x2) // 2
                    
                    # Determinar etiqueta basada en POSICIÓN
                    if cx > line_x:
                        label = "DENTRO"
                        color = (0, 255, 0) # Verde
                    else:
                        label = "FUERA"
                        color = (0, 0, 255) # Rojo

                    # Dibujar Rectángulo y Etiqueta
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.rectangle(frame, (x1, y1 - 25), (x1 + 130, y1), color, -1)
                    cv2.putText(frame, f"{label} | ID:{id}", (x1 + 5, y1 - 7), 0, 0.5, (255, 255, 255), 2)
            
            # Mostrar evento de cruce momentáneo
            if self.counter.last_event:
                cv2.rectangle(frame, (w//2 - 150, h - 80), (w//2 + 150, h - 30), (0,0,0), -1)
                cv2.putText(frame, self.counter.last_event, (w//2 - 130, h - 45), 0, 0.8, (255,255,255), 2)

            self.current_frame = frame
            time.sleep(0.01)

    def get_frame(self):
        if self.current_frame is None: return None
        _, b = cv2.imencode('.jpg', self.current_frame)
        return b.tobytes()
