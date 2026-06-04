import uvicorn
from app.monitor import MonitorSystem
from app.api.server import create_app

# CONFIGURACIÓN PROFESIONAL
CAMERA_SOURCE = "http://10.70.87.151:8080/video"
CAPACITY = 30
LINE_POSITION = 0.5    # Línea vertical al centro (50% del ancho)
ROTATE_VIDEO = True    # Mantener rotación si el celular está vertical

# 1. Iniciamos el motor de monitoreo
monitor = MonitorSystem(CAMERA_SOURCE, CAPACITY, LINE_POSITION, rotate=ROTATE_VIDEO)

# 2. Iniciamos el servidor Web
app = create_app(monitor)

if __name__ == "__main__":
    print(f">>> SISTEMA MALOCA PRO")
    print(f">>> LINEA VERTICAL ACTIVADA")
    uvicorn.run(app, host="0.0.0.0", port=8000)
