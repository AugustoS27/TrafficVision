import cv2
import numpy as np
import os

#-------------------------------------PARAMETROS A CONFIGURAR-------------------------------------

#Introduce la ruta a tu video de calibración aquí
VIDEO_PATH = r"C:\Users\augus\OneDrive\Escritorio\Vehicle tracker\VehicleTracker\video\f.jpg"

#Introduce el ancho estimada del área a calibrar en metros
REAL_WIDTH = 24.5

#Intoduce la longitud estimada del área a calibrar en metros
REAL_LENGTH = 72.0

#-------------------------------------------------------------------------------------------------

OUTPUT_FILE = "config/homography_matrix.npy"
WINDOW_NAME = "Calibracion (Click para puntos, W/A/S/D navegar)"

points = []

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) < 4:
            points.append((x, y))
            print(f"[PUNTO] {len(points)}/4: ({x}, {y})")

def main():
    if not os.path.exists(VIDEO_PATH):
        print("Error: No se encuentra el video.")
        return


    cap = cv2.VideoCapture(VIDEO_PATH, cv2.CAP_MSMF)
    if not cap.isOpened(): cap = cv2.VideoCapture(VIDEO_PATH)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    current_idx = 0
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()
    
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    print("--- INSTRUCCIONES ---")
    print("1. Usa W/A/S/D para buscar un frame claro.")
    print("2. Marca 4 puntos (Esq-Sup -> Der-Sup -> Esq-Inf -> Der-Inf).")
    print("3. Pulsa 'C' para calcular.")
    
    while True:
        display_img = frame.copy()
        
        cv2.putText(display_img, f"Frame: {current_idx}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        for i, pt in enumerate(points):
            cv2.circle(display_img, pt, 5, (0, 0, 255), -1)
            cv2.putText(display_img, str(i+1), pt, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)

        if len(points) == 4:
            pts_np = np.array(points, np.int32).reshape((-1, 1, 2))
            cv2.polylines(display_img, [pts_np], True, (0, 255, 0), 2)

        cv2.imshow(WINDOW_NAME, display_img)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('q'): break
        if key == ord('r'): points.clear()

        new_idx = current_idx
        if key == ord('d'): new_idx += 1
        elif key == ord('a'): new_idx -= 1
        elif key == ord('w'): new_idx += 30
        elif key == ord('s'): new_idx -= 30

        if new_idx != current_idx:
            new_idx = max(0, min(new_idx, total_frames - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, new_idx)
            ret, new_frame = cap.read()
            if ret:
                frame = new_frame
                current_idx = new_idx

        if key == ord('c') and len(points) == 4:
            src_pts = np.float32(points)
            
            dst_meters = np.float32([
                [0, 0], 
                [REAL_WIDTH, 0], 
                [0, REAL_LENGTH], 
                [REAL_WIDTH, REAL_LENGTH]
            ])
            H_meters = cv2.getPerspectiveTransform(src_pts, dst_meters)
            
            os.makedirs("config", exist_ok=True)
            np.save(OUTPUT_FILE, H_meters)
            print(f"\n Matriz FÍSICA guardada. Ahora 1 unidad = 1 metro.")


            scale_viz = 20 
            w_px = int(REAL_WIDTH * scale_viz)
            h_px = int(REAL_LENGTH * scale_viz)
            dst_visual = np.float32([[0,0], [w_px,0], [0,h_px], [w_px,h_px]])
            
            H_visual = cv2.getPerspectiveTransform(src_pts, dst_visual)
            warped = cv2.warpPerspective(frame, H_visual, (w_px, h_px))
            
            cv2.imshow("Validacion Visual (Escala x20)", warped)
            print("Revisa la ventana pequeña. Si las lineas estan rectas, todo OK.")
            print("Presiona cualquier tecla para cerrar...")
            cv2.waitKey(0)
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()