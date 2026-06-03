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
        self.cap = None
        self.camera_connected = False
        
        # Buffer de frames y estado de tracking
        self.raw_frame = None
        self.current_raw_frame = None
        self.latest_ids = []
        self.latest_boxes = []
        self.running = True
        
        # Thread de Captura (Lectura constante para evitar lag)
        threading.Thread(target=self._capture, daemon=True).start()
        # Thread de Procesamiento (IA + UI)
        threading.Thread(target=self._run, daemon=True).start()

    def _capture(self):
        # Inicializar la captura en segundo plano para evitar bloquear el arranque del servidor
        self.cap = cv2.VideoCapture(self.source)
        
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self.camera_connected = False
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.source)
                continue
                
            ret, frame = self.cap.read()
            if not ret:
                self.camera_connected = False
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.source)
                continue
            
            self.camera_connected = True
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
            
            # Guardar el frame rotado y limpio
            self.current_raw_frame = frame.copy()
            
            # 1. IA Tracking (Optimizado con imgsz=320 para velocidad)
            results = self.detector.track(frame)
            
            # 2. Obtener IDs y Boxes de la detección y guardarlos
            if results[0].boxes.id is not None:
                self.latest_ids = results[0].boxes.id.int().cpu().numpy()
                self.latest_boxes = results[0].boxes.xyxy.cpu().numpy()
            else:
                self.latest_ids = []
                self.latest_boxes = []

            # Actualizar lógica del contador (siempre pasar w y h)
            self.counter.update(self.latest_ids, self.latest_boxes, w, h)
            
            time.sleep(0.005)

    def get_frame(self, view=None):
        if self.current_raw_frame is None:
            return None
            
        frame = self.current_raw_frame.copy()
        h, w, _ = frame.shape
        line_x = int(w * self.counter.line_ratio)

        # RENDER 1: VISTA DASHBOARD (Solo línea divisoria y conteo de cruces)
        if view == 'dashboard':
            cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 4)
            cv2.putText(frame, "FUERA", (line_x - 70, 30), 0, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, "DENTRO", (line_x + 10, 30), 0, 0.6, (0, 255, 0), 2)

            if len(self.latest_ids) > 0:
                for box, id in zip(self.latest_boxes, self.latest_ids):
                    x1, y1, x2, y2 = map(int, box)
                    cx = (x1 + x2) // 2
                    color = (0, 255, 0) if cx > line_x else (0, 0, 255)
                    label = "DENTRO" if cx > line_x else "FUERA"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{label} | ID:{id}", (x1, y1 - 10), 0, 0.45, color, 2, lineType=cv2.LINE_AA)

            if self.counter.last_event:
                cv2.putText(frame, self.counter.last_event, (w//2 - 130, h - 45), 0, 0.8, (255, 255, 255), 2)

        # RENDER 2: VISTA DISTRIBUCIÓN (Solo mesas y personas asignadas a mesas)
        elif view == 'distribution':
            # Dibujar Zonas de Mesas
            for t in self.counter.tables_config:
                tx = int(t["x"] * w)
                ty = int(t["y"] * h)
                tr = int(t["radius"] * min(w, h))
                
                # Buscar estado de la mesa
                t_state = next((ts for ts in self.counter.distribution_data["tables"] if ts["id"] == t["id"]), None)
                count = t_state["count"] if t_state else 0
                
                if count == 0:
                    cv2.circle(frame, (tx, ty), tr, (163, 222, 78), 2, lineType=cv2.LINE_AA)
                    cv2.circle(frame, (tx, ty), 4, (163, 222, 78), -1)
                elif count < t["capacity"]:
                    cv2.circle(frame, (tx, ty), tr, (183, 178, 255), 2, lineType=cv2.LINE_AA)
                    cv2.circle(frame, (tx, ty), 4, (183, 178, 255), -1)
                else:
                    cv2.circle(frame, (tx, ty), tr, (106, 81, 255), 3, lineType=cv2.LINE_AA)
                    cv2.circle(frame, (tx, ty), 4, (106, 81, 255), -1)

                label_text = f"{t['name']}: {count}/{t['capacity']}"
                cv2.putText(frame, label_text, (tx - 45, ty + 5), 0, 0.4, (255, 255, 255), 1, lineType=cv2.LINE_AA)

            # Dibujar rectángulos de personas asociadas a las mesas (solo las del lado DENTRO)
            if len(self.latest_ids) > 0:
                for box, id in zip(self.latest_boxes, self.latest_ids):
                    x1, y1, x2, y2 = map(int, box)
                    cx = (x1 + x2) // 2
                    if cx > line_x:
                        assigned_table = "Libre"
                        for t_state in self.counter.distribution_data["tables"]:
                            if int(id) in t_state["people_ids"]:
                                assigned_table = t_state["name"]
                                break
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"ID:{id} ({assigned_table})", (x1, y1 - 10), 0, 0.45, (0, 255, 0), 2, lineType=cv2.LINE_AA)

        # RENDER 3: VISTA COMPLETA (Por defecto si no se especifica)
        else:
            cv2.line(frame, (line_x, 0), (line_x, h), (0, 0, 255), 4)
            # Mesas
            for t in self.counter.tables_config:
                tx = int(t["x"] * w)
                ty = int(t["y"] * h)
                tr = int(t["radius"] * min(w, h))
                cv2.circle(frame, (tx, ty), tr, (255, 255, 255), 1, lineType=cv2.LINE_AA)

            if len(self.latest_ids) > 0:
                for box, id in zip(self.latest_boxes, self.latest_ids):
                    x1, y1, x2, y2 = map(int, box)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

        # Pre-codificar el frame para el API
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return buffer.tobytes()

    def get_distribution_data(self):
        return self.counter.distribution_data

