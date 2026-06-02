import time
from collections import deque

class MalocaCounter:
    def __init__(self, capacity, line_ratio):
        self.capacity = capacity
        self.line_ratio = line_ratio
        self.counts = {
            "entran": 0,
            "salen": 0,
            "actual": 0,
            "disponible": capacity
        }
        
        # Parámetros de estabilidad
        self.MIN_HEIGHT = 50
        self.track_data = {} # ID -> {"last_x": int, "zone": str}
        self.total_entered_ids = set() # Para el conteo acumulado de 'entran'
        self.total_exited_ids = set()  # Para el conteo acumulado de 'salen'
        self.last_event = ""
        self.last_event_time = 0

    def update(self, ids, boxes, width):
        line_x = int(width * self.line_ratio)
        current_time = time.time()
        
        if current_time - self.last_event_time > 2:
            self.last_event = ""

        active_ids = set(ids)
        current_inside_count = 0

        for box, id in zip(boxes, ids):
            x1, y1, x2, y2 = box
            height = y2 - y1
            cx = int((x1 + x2) / 2)

            if height < self.MIN_HEIGHT: continue

            # DETERMINAR POSICIÓN ACTUAL (Esto es lo que manda para el Dashboard)
            is_inside = cx > line_x
            if is_inside:
                current_inside_count += 1

            # LÓGICA DE EVENTOS (Cruce de línea)
            if id in self.track_data:
                prev_x = self.track_data[id]["last_x"]
                
                # Entró: Cruzó de izquierda a derecha
                if prev_x <= line_x and cx > line_x:
                    self.counts["entran"] += 1
                    self.last_event = "ESTUDIANTE ENTRÓ"
                    self.last_event_time = current_time
                
                # Salió: Cruzó de derecha a izquierda
                elif prev_x >= line_x and cx < line_x:
                    self.counts["salen"] += 1
                    self.last_event = "ESTUDIANTE SALIÓ"
                    self.last_event_time = current_time
            
            self.track_data[id] = {"last_x": cx, "is_inside": is_inside}

        # ACTUALIZAR DASHBOARD (Sincronización Total)
        self.counts["actual"] = current_inside_count
        self.counts["disponible"] = max(0, self.capacity - self.counts["actual"])
        
        # Limpieza de memoria
        self.track_data = {k: v for k, v in self.track_data.items() if k in active_ids}
        
        return line_x
