import cv2
import time
from core.video_loader import VideoLoader
from core.detector import Detector
from core.tracker import Tracker
from core.speed_estimator import SpeedEstimator
from core.postgres_logger import PostgresLogger
import os
from dotenv import load_dotenv

load_dotenv()

# --------------------------------Configuración-------------------------------- #
# - Ubicación del video de entrada -
VIDEO_SOURCE = r"C:\Users\augus\OneDrive\Escritorio\Vehicle tracker\VehicleTracker\video\video_test.mp4"


# - Cuántos frames saltarse entre procesamientos -
SKIP_FRAMES = 3
# - Factor de corrección de velocidad -      
CORRECTION_FACTOR = 1  

# - Configuración de Base de Datos (Variables de entorno) -
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT"))
}

def main():
    print("--- INICIANDO TRAFFIC VISION SYSTEM ---")
    
    loader = VideoLoader(VIDEO_SOURCE).start()
    detector = Detector() 
    tracker = Tracker()  
    
    try:
        logger = PostgresLogger(DB_CONFIG, batch_size=15, flush_interval=1.0, retention_months=3)
    except Exception as e:
        print("Abortando: Fallo crítico en Base de Datos.")
        loader.stop()
        return

    try:
        speed_estimator = SpeedEstimator()
    except Exception as e:
        print(f"Error crítico: {e}")
        print("Ejecuta calibration_tool.py primero.")
        loader.stop()
        logger.stop()
        return

    frame_cnt = 0
    current_detections = None 
    
    vehicle_speeds = {}   
    vehicle_directions = {}

    try:
        while True:
            if loader.stopped and not loader.more():
                break

            frame = loader.read()
            if frame is None:
                time.sleep(0.001)
                continue
                
            frame_cnt += 1
            
            current_time = frame_cnt / loader.fps 
            
            if frame_cnt % SKIP_FRAMES == 0:
                raw_detections = detector.detect(frame)
                
                current_detections = tracker.update(raw_detections)
                
                for tracker_id, box, class_id in zip(current_detections.tracker_id, current_detections.xyxy, current_detections.class_id):
                    
                    speed = speed_estimator.estimate(tracker_id, box, current_time)
                    
                    if speed is not None:
                        final_speed = int(speed * CORRECTION_FACTOR)
                        vehicle_speeds[tracker_id] = final_speed
                        
                        history = speed_estimator.vehicle_history.get(tracker_id, [])
                        direction = "DESCONOCIDO"
                        if len(history) > 1:
                            _, _, y_now = history[-1]
                            _, _, y_old = history[0]
                            direction = "Incoming" if y_now > y_old else "Outgoing"
                            vehicle_directions[tracker_id] = direction

                        cls_name = tracker.CLASS_NAMES_DICT.get(class_id, "Vehiculo")
                        logger.log(tracker_id, cls_name, final_speed, direction)

            display_frame = frame.copy()
            
            if current_detections is not None:
                for tracker_id, box, class_id in zip(current_detections.tracker_id, current_detections.xyxy, current_detections.class_id):
                    x1, y1, x2, y2 = map(int, box)
                    
                    cls_name = tracker.CLASS_NAMES_DICT.get(class_id, "Vehiculo")
                    speed = vehicle_speeds.get(tracker_id, 0)
                    direction = vehicle_directions.get(tracker_id, "")
                    
                    color = (255, 255, 0) if direction == "Incoming" else (0, 0, 255)
                    
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                    
                    cv2.putText(display_frame, f"#{tracker_id} {cls_name}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    if speed > 0:
                        label = f"{speed} km/h {direction}"
                        cv2.putText(display_frame, label, (x1, y2 + 25), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("TrafficVision Pro - DB Connected", cv2.resize(display_frame, (1280, 720)))

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        print("[INFO] Cerrando sistema...")
        loader.stop()
        logger.stop()
        cv2.destroyAllWindows()
        print("[INFO] Sistema finalizado.")

if __name__ == "__main__":
    main()