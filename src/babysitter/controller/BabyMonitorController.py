

from src.babysitter.components.camera.pi_cam import Camera
from src.babysitter.components import GptDescriber, GptDescribeConfig
from src.babysitter.components import YoloVision, YoloConfig

class BabyMonitorController:
    def __init__(self):
        self.camera = Camera()
        self.describer = GptDescriber(GptDescribeConfig(detail="low"))
        self.vision = YoloVision(YoloConfig(
            model_path="yolov8n.pt",
            conf=0.35,
            person_min_conf=0.7,
        ))

    def start(self):

        # Start and check camera
        self.camera.start()
        if not self.camera.is_opened():
            raise RuntimeError("Failed to start the camera.")

        # Warm up the camera by capturing a few frames
        for _ in range(5):
            self.camera.capture_frame()


    def update_frame(self):
        frame = self.camera.capture_frame()
        if frame is None:
            print("Warning: Failed to capture frame.")
            return

        result = self.vision.predict(frame)
        annotated = self.vision.annotated_frame(result)




    def stop(self):
        self.camera.stop()
