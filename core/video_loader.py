import cv2
from threading import Thread
from queue import Queue
import time

class VideoLoader:
    def __init__(self, source=0, queue_size=30):
        self.stream = cv2.VideoCapture(source)
        if not self.stream.isOpened():
            raise ValueError(f"No se pudo abrir la fuente: {source}")
        
        self.fps = self.stream.get(cv2.CAP_PROP_FPS)
        if self.fps == 0 or self.fps is None:
            self.fps = 30.0 # Valor por defecto seguro
        print(f"[INFO] VideoLoader detectó {self.fps:.2f} FPS")

        self.stopped = False
        self.Q = Queue(maxsize=queue_size)
        self.thread = Thread(target=self.update, args=(), daemon=True)

    def start(self):
        self.thread.start()
        return self

    def update(self):
        while True:
            if self.stopped: break
            
            if self.Q.full():
                time.sleep(0.005)
                continue

            (grabbed, frame) = self.stream.read()

            if not grabbed:
                self.stopped = True
                break

            self.Q.put(frame)
            
    def read(self):
        return self.Q.get() if not self.Q.empty() else None

    def more(self):
        return self.Q.qsize() > 0

    def stop(self):
        self.stopped = True
        self.stream.release()