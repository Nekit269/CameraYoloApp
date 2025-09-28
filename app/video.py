import cv2
from ultralytics import YOLO
import threading

models = {}

def load_models():
    for name in ["yolov8n", "yolov8s"]:
        model_path = f"app/yolo/{name}.pt"
        models[name] = YOLO(model_path)

class VideoStream:
    def __init__(self, url: str, model_name: str, threshold: float):
        self.url = url
        self.model_name = model_name
        self.threshold = threshold
        self.model_lock = threading.Lock()

        if url == "0":
            self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(url)
        self.cap_lock = threading.Lock()
        
        self.running = True
        self.frame = None
        self.lock = threading.Lock()
        self.new_frame_event = threading.Event()

        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            with self.cap_lock:
                cap = self.cap

            success, frame = cap.read()
            if not success:
                continue

            with self.model_lock:
                model_name = self.model_name
                threshold = self.threshold

            if model_name is not None:
                if model_name not in models:
                    model_path = f"app/yolo/{model_name}.pt"
                    models[model_name] = YOLO(model_path)
                model = models[model_name]

                results = model(frame, conf=threshold, verbose=False)
                frame = results[0].plot()

            with self.lock:
                self.frame = frame
                self.new_frame_event.set()

    def update_params(self, model_name: str = None, threshold: float = None):
        with self.model_lock:
            if model_name:
                if model_name == "None":
                    self.model_name = None
                else:
                    self.model_name = model_name
            if threshold is not None:
                self.threshold = threshold

    def update_url(self, new_url: str):
        with self.cap_lock:
            self.cap.release()

            if new_url == "0":
                self.cap = cv2.VideoCapture(0)
            else:
                self.cap = cv2.VideoCapture(new_url)
            self.url = new_url

    def get_frame(self):
        self.new_frame_event.wait()
        with self.lock:
            frame = self.frame.copy()
        self.new_frame_event.clear()

        _, buffer = cv2.imencode(".jpg", frame)
        return buffer.tobytes()

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()
        

class VideoManager:
    def __init__(self):
        self.streams = {}
        self.user_to_camera = {}

    def start_stream(self, user_id: int, camera_id: int, url: str, 
                     model_name: str, threshold: float):
        if user_id in self.streams:
            self.streams[user_id].stop()
        self.user_to_camera[user_id] = camera_id
        self.streams[user_id] = VideoStream(url, model_name, threshold)

    def update_params(self, user_id: int, model_name: str = None, 
                      threshold: float = None):
        if user_id in self.streams:
            self.streams[user_id].update_params(model_name, threshold)

    def update_url(self, user_id: int, camera_id: int, new_url: str):
        if user_id in self.streams \
            and self.user_to_camera[user_id] == camera_id:
            self.streams[user_id].update_url(new_url)

    def get_frames(self, user_id: int):
        if user_id not in self.streams:
            return None
        stream = self.streams[user_id]
        while True:
            frame = stream.get_frame()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    def stop_stream(self, user_id: int):
        if user_id in self.streams:
            self.streams[user_id].stop()
            del self.streams[user_id]
