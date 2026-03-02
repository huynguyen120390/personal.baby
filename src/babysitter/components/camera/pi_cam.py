from picamera2 import Picamera2

class Camera:
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.picam2 = None


    def start(self):
        self.picam2 = Picamera2()
        self.config = self.picam2.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self.picam2.configure(self.config)
        self.picam2.start()

    def is_opened(self):
        return self.picam2.started  # better property in newer versions

    def capture_frame(self):
        return self.picam2.capture_array()

    def stop(self):
        if self.picam2 is not None:
            self.picam2.stop()

    def close(self):
        if self.picam2 is not None:
            self.picam2.close()
            self.picam2 = None