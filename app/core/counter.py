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
        self.MIN_HEIGHT = 15
        self.track_data = {} # ID -> {"last_x": int, "zone": str}
        self.total_entered_ids = set() # Para el conteo acumulado de 'entran'
        self.total_exited_ids = set()  # Para el conteo acumulado de 'salen'
        self.last_event = ""
        self.last_event_time = 0

        # CONFIGURACIÓN PERSISTENTE DE MESAS Y LÍNEA
        self.config_file = "data/config.json"
        self.tables_config = []
        self.load_config()

        # Estado inicial de distribución
        self.distribution_data = {
            "total_people": 0,
            "total_tables": len(self.tables_config),
            "tables": [],
            "unassigned_people": []
        }

    def load_config(self):
        import os
        import json
        
        default_config = {
            "line_position": self.line_ratio,
            "tables": [
                {"id": 1, "name": "Mesa 01", "x": 0.58, "y": 0.30, "radius": 0.10, "capacity": 4},
                {"id": 2, "name": "Mesa 02", "x": 0.76, "y": 0.30, "radius": 0.10, "capacity": 4},
                {"id": 3, "name": "Mesa 03", "x": 0.92, "y": 0.30, "radius": 0.10, "capacity": 4},
                {"id": 4, "name": "Mesa 04", "x": 0.58, "y": 0.70, "radius": 0.10, "capacity": 4},
                {"id": 5, "name": "Mesa 05", "x": 0.76, "y": 0.70, "radius": 0.10, "capacity": 4},
                {"id": 6, "name": "Mesa 06", "x": 0.92, "y": 0.70, "radius": 0.10, "capacity": 4},
            ]
        }
        
        if os.path.exists(self.config_file) and os.path.getsize(self.config_file) > 0:
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                self.line_ratio = config.get("line_position", self.line_ratio)
                self.tables_config = config.get("tables", default_config["tables"])
            except Exception as e:
                print(f"Error loading config: {e}")
                self.tables_config = default_config["tables"]
        else:
            self.tables_config = default_config["tables"]
            self.save_config()

    def save_config(self):
        import os
        import json
        
        if not os.path.exists("data"):
            os.makedirs("data")
            
        config = {
            "line_position": self.line_ratio,
            "tables": self.tables_config
        }
        
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update(self, ids, boxes, width, height=None):
        # Si no se provee el alto, asumimos una proporción estándar 4:3
        if height is None:
            height = int(width * 0.75)

        line_x = int(width * self.line_ratio)
        current_time = time.time()
        
        if current_time - self.last_event_time > 2:
            self.last_event = ""

        active_ids = set(ids)
        current_inside_count = 0

        # Estructura temporal para ocupación de mesas
        table_occupants = {t["id"]: [] for t in self.tables_config}
        unassigned_ids = []

        for box, id in zip(boxes, ids):
            x1, y1, x2, y2 = box
            height_box = y2 - y1
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            if height_box < self.MIN_HEIGHT: continue

            # DETERMINAR POSICIÓN ACTUAL (Esto es lo que manda para el Dashboard)
            is_inside = cx > line_x
            if is_inside:
                current_inside_count += 1

                # Asignar a la mesa más cercana si está dentro del radio de detección
                closest_table_id = None
                min_dist = float('inf')

                for t in self.tables_config:
                    tx = int(t["x"] * width)
                    ty = int(t["y"] * height)
                    tr = int(t["radius"] * min(width, height))

                    dist = ((cx - tx)**2 + (cy - ty)**2)**0.5
                    if dist < tr and dist < min_dist:
                        min_dist = dist
                        closest_table_id = t["id"]

                if closest_table_id is not None:
                    table_occupants[closest_table_id].append(int(id))
                else:
                    unassigned_ids.append(int(id))

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
        
        # ACTUALIZAR DATOS DE DISTRIBUCIÓN
        self.distribution_data = {
            "total_people": current_inside_count,
            "total_tables": len(self.tables_config),
            "tables": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "count": len(table_occupants[t["id"]]),
                    "capacity": t["capacity"],
                    "x_ratio": t["x"],
                    "y_ratio": t["y"],
                    "people_ids": table_occupants[t["id"]]
                } for t in self.tables_config
            ],
            "unassigned_people": unassigned_ids
        }

        # Limpieza de memoria
        self.track_data = {k: v for k, v in self.track_data.items() if k in active_ids}
        
        return line_x
