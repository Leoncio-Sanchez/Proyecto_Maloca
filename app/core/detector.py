import cv2
import numpy as np
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, model_name="yolov8n.pt"):
        self.model = YOLO(model_name)
    
    def track(self, frame):
        # Tracking solo para clase 0 (persona)
        return self.model.track(frame, persist=True, classes=0, verbose=False)
