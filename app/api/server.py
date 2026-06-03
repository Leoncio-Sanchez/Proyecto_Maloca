from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import os
import time
import json
from datetime import datetime

def create_app(monitor):
    app = FastAPI()

    # Rutas a los archivos HTML
    TEMPLATE_PATH = os.path.join("app", "templates", "dashboard.html")
    ANALYTICS_PATH = os.path.join("app", "templates", "analytics.html")
    DISTRIBUTION_PATH = os.path.join("app", "templates", "distribution.html")
    HISTORY_FILE = "data/history.json"

    # Asegurar que el archivo de historial existe
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)

    @app.get("/", response_class=HTMLResponse)
    def index():
        if not os.path.exists(TEMPLATE_PATH):
            return "Error: No se encuentra el archivo HTML en app/templates/dashboard.html"
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @app.get("/analytics", response_class=HTMLResponse)
    def analytics():
        if not os.path.exists(ANALYTICS_PATH):
            return "Error: No se encuentra el archivo HTML en app/templates/analytics.html"
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @app.get("/distribution", response_class=HTMLResponse)
    def distribution():
        if not os.path.exists(DISTRIBUTION_PATH):
            return "Error: No se encuentra el archivo HTML en app/templates/distribution.html"
        with open(DISTRIBUTION_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @app.get("/status")
    def status(): 
        counts = monitor.counter.counts.copy()
        counts["camera_online"] = monitor.camera_connected
        # Guardar en historial periódicamente (ej: cada vez que hay un cambio)
        save_to_history(counts)
        return counts

    @app.get("/api/distribution")
    def get_distribution_api():
        return monitor.get_distribution_data()

    @app.get("/api/config")
    def get_config_api():
        return {
            "line_position": monitor.counter.line_ratio,
            "tables": monitor.counter.tables_config
        }

    @app.post("/api/config")
    def update_config_api(config: dict):
        if "line_position" in config:
            monitor.counter.line_ratio = float(config["line_position"])
        if "tables" in config:
            tables = []
            for t in config["tables"]:
                tables.append({
                    "id": int(t["id"]),
                    "name": str(t["name"]),
                    "x": float(t["x"]),
                    "y": float(t["y"]),
                    "radius": float(t["radius"]),
                    "capacity": int(t["capacity"])
                })
            monitor.counter.tables_config = tables
        monitor.counter.save_config()
        return {"status": "success"}

    @app.get("/history")
    def get_history():
        history = []
        if os.path.exists(HISTORY_FILE) and os.path.getsize(HISTORY_FILE) > 0:
            with open(HISTORY_FILE, "r") as f:
                try:
                    history = json.load(f)
                except:
                    history = []
        return history

    def save_to_history(counts):
        try:
            history = []
            if os.path.exists(HISTORY_FILE) and os.path.getsize(HISTORY_FILE) > 0:
                with open(HISTORY_FILE, "r") as f:
                    try:
                        history = json.load(f)
                    except:
                        history = []
            
            now = datetime.now()
            entry = {
                "timestamp": now.isoformat(),
                "entran": counts["entran"],
                "salen": counts["salen"],
                "actual": counts["actual"],
                "disponible": counts["disponible"]
            }
            
            if not history or history[-1]["timestamp"][:16] != entry["timestamp"][:16]:
                history.append(entry)
                if len(history) > 2000:
                    history = history[-2000:]
                with open(HISTORY_FILE, "w") as f:
                    json.dump(history, f)
        except Exception as e:
            print(f"Error saving history: {e}")

    @app.get("/video_feed")
    def video_feed(view: str = None):
        def gen():
            while True:
                f = monitor.get_frame(view)
                if f:
                    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + f + b'\r\n')
                else:
                    time.sleep(0.1)
                time.sleep(0.01)
        
        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")
    
    return app
