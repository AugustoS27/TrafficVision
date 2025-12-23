import cv2
import numpy as np
import os

class SpeedEstimator:
    def __init__(self, matrix_path="config/homography_matrix.npy"):
        if not os.path.exists(matrix_path):
            raise FileNotFoundError(f"CRÍTICO: No encontré '{matrix_path}'. Ejecuta calibration_tool.py primero.")
        
        self.H = np.load(matrix_path)
        print(f"[INFO] SpeedEstimator inicializado. Matriz cargada.")
        
        self.vehicle_history = {}

    def transform_point(self, point):
        pt_np = np.array([[point]], dtype='float32')
        
        dst = cv2.perspectiveTransform(pt_np, self.H)
        
        return dst[0][0]

    def estimate(self, tracker_id, box, current_time):
        x1, y1, x2, y2 = box
        
        cx = int((x1 + x2) / 2)
        cy = int(y2) 
        
        coord_meters = self.transform_point((cx, cy))
        
        if tracker_id not in self.vehicle_history:
            self.vehicle_history[tracker_id] = []
        
        history = self.vehicle_history[tracker_id]
        history.append((current_time, coord_meters[0], coord_meters[1]))
        
        if len(history) > 60:
            history.pop(0)
            
        if len(history) < 3:
            return None
            
        t_now, x_now, y_now = history[-1]
        t_old, x_old, y_old = history[0] 
        
        time_diff = t_now - t_old
        
        if time_diff == 0: 
            return None
        
        dist_meters = np.sqrt((x_now - x_old)**2 + (y_now - y_old)**2)
        
        speed_mps = dist_meters / time_diff
        
        speed_kmh = speed_mps * 3.6
        
        return int(speed_kmh)