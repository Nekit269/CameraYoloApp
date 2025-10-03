"""
Классическая потоковая логика на threading + ultralytics YOLO.

"""
from typing import Dict, Optional, Generator
import threading

import cv2
from ultralytics import YOLO

# Глобальный кэш загруженных моделей
models: Dict[str, YOLO] = {}


def load_models():
    """
    Предзагрузка базовых моделей (если требуются).
    """
    for name in ["yolov8n", "yolov8s"]:
        model_path = f"app/yolo/{name}.pt"
        models[name] = YOLO(model_path)


class VideoStream:
    """
    Оборачивает cv2.VideoCapture + модель YOLO в отдельный поток.
    """

    def __init__(self, url: str, model_name: Optional[str], threshold: float):
        self.url = url
        self.model_name = None if model_name == "None" else model_name
        self.threshold = threshold
        self.model_lock = threading.Lock()

        # VideoCapture (0 означает локальную камеру)
        if url == "0":
            self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(url)
        self.cap_lock = threading.Lock()

        # Флаги и синхронизация
        self.running = True
        self.frame = None
        self.lock = threading.Lock()
        self.new_frame_event = threading.Event()

        # Запуск фонового потока
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self) -> None:
        """
        Постоянно читает кадры, применяет модель (если задана) и сохраняет результат.
        """
        while self.running:
            with self.cap_lock:
                cap = self.cap

            success, frame = cap.read()
            if not success:
                # Если источник временно недоступен — продолжаем попытки.
                continue

            with self.model_lock:
                model_name = self.model_name
                threshold = self.threshold

            if model_name is not None:
                # Если модель не в кэше, загрузим её
                if model_name not in models:
                    model_path = f"app/yolo/{model_name}.pt"
                    models[model_name] = YOLO(model_path)
                model = models[model_name]

                results = model(frame, conf=threshold, verbose=False)
                frame = results[0].plot()

            with self.lock:
                self.frame = frame
                # Сигнал о наличии нового кадра
                self.new_frame_event.set()

    def update_params(
        self, 
        model_name: Optional[str] = None, 
        threshold: Optional[float] = None,
    ) -> None:
        """
        Обновляет model_name / threshold в потокобезопасном режиме.
        """
        with self.model_lock:
            if model_name:
                if model_name == "None":
                    self.model_name = None
                else:
                    self.model_name = model_name
            if threshold is not None:
                self.threshold = threshold

    def update_url(self, new_url: str) -> None:
        """
        Меняет источник захвата видео (освобождая старый).
        """
        with self.cap_lock:
            self.cap.release()

            if new_url == "0":
                self.cap = cv2.VideoCapture(0)
            else:
                self.cap = cv2.VideoCapture(new_url)
            self.url = new_url

    def get_frame(self) -> bytes:
        """
        Блокирует до появления нового кадра, возвращает JPEG-байты.
        """
        self.new_frame_event.wait()
        with self.lock:
            frame = self.frame.copy()
        self.new_frame_event.clear()

        _, buffer = cv2.imencode(".jpg", frame)
        return buffer.tobytes()

    def stop(self) -> None:
        """
        Останавливает поток и освобождает ресурсы.
        """
        self.running = False
        self.thread.join()
        self.cap.release()


class VideoManager:
    """
    Менеджер стримов: одна стрим-сессия на пользователя.
    """

    def __init__(self):
        self.streams: Dict[int, VideoStream] = {}
        self.user_to_camera: Dict[int, int] = {}

    def start_stream(
        self, 
        user_id: int, 
        camera_id: int, 
        url: str, 
        model_name: Optional[str], 
        threshold: float,
    ) -> None:
        """
        Запускает новый поток для user_id; останавливает предыдущий, если был.
        """
        if user_id in self.streams:
            self.streams[user_id].stop()
        self.user_to_camera[user_id] = camera_id
        self.streams[user_id] = VideoStream(url, model_name, threshold)

    def update_params(
        self, 
        user_id: int, 
        model_name: Optional[str] = None, 
        threshold: Optional[float] = None
    ) -> None:
        """
        Обновляет model_name / threshold у стрима конкретного пользователя.
        """
        if user_id in self.streams:
            self.streams[user_id].update_params(model_name, threshold)

    def update_url(self, user_id: int, camera_id: int, new_url: str) -> None:
        """
        Обновляет источник видео у стрима конкретного пользователя.
        """
        if user_id in self.streams and self.user_to_camera[user_id] == camera_id:
            self.streams[user_id].update_url(new_url)

    def get_frames(self, user_id: int) -> Optional[Generator[bytes, None, None]]:
        """
        Генератор multipart/jpeg-кадров для StreamingResponse.
        """
        if user_id not in self.streams:
            return None
        stream = self.streams[user_id]
        while True:
            frame = stream.get_frame()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    def stop_stream(self, user_id: int) -> None:
        """
        Остановить стрим конкретного пользователя.
        """
        if user_id in self.streams:
            self.streams[user_id].stop()
            del self.streams[user_id]
