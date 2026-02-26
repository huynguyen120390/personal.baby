

from components.camera.pi_cam import Camera

class BabyMonitorController:
    def __init__(self):
        self.camera = Camera()

    def start(self):

        # Start and check camera
        self.camera.start()
        if not self.camera.is_opened():
            raise RuntimeError("Failed to start the camera.")

        # Warm up the camera by capturing a few frames
        for _ in range(5):
            self.camera.capture_frame()

    def stop(self):
        pass