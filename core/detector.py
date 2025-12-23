from ultralytics import YOLO
import supervision as sv 
import numpy as np 

class Detector:
    def __init__(self, model_name='yolov8n.pt'):
        self.model = YOLO(model_name)
    
    def detect(self, frame):
        results = self.model(frame, verbose=False, conf=0.5)[0]
        
        detections = sv.Detections.from_ultralytics(results)
        
        target_classes = [2, 3, 5, 7]
        detections = detections[np.isin(detections.class_id, target_classes)]
        
        return detections