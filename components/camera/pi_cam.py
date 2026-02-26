from picamera2 import Picamera2

class Camera:
    def __init__(self, width=1280, height=720):
        self.picam2 = Picamera2()
        self.config = self.picam2.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"}
        )
        self.picam2.configure(self.config)


    def start(self):
        self.picam2.start()

    def is_opened(self):
        return self.picam2.running

    def capture_frame(self):
        return self.picam2.capture_array()


    def stop(self):
        self.picam2.stop()
        self.picam2.close()