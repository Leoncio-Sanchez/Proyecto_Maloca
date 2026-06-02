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
        counts = monitor.counter.counts
        # Guardar en historial periódicamente (ej: cada vez que hay un cambio)
        save_to_history(counts)
        return counts

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
    def video_feed():
        def gen():
            while True:
                f = monitor.get_frame()
                if f:
                    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + f + b'\r\n')
                else:
                    time.sleep(0.1)
                time.sleep(0.01)
        
        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")
    
    return app
