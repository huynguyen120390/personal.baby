from picamera2 import Picamera2

class Camera:
    def __init__(self, camera_num=0, width=3280, height=2464):
        self.camera_num = camera_num
        self.width = width
        self.height = height
        self.picam2 = None
        print(Picamera2.global_camera_info())


    def start(self):
        self.picam2 = Picamera2(self.camera_num)
        self.config = self.picam2.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self.picam2.configure(self.config)
        self.picam2.start()
        self.picam2.set_controls({
            "AwbEnable": False,
            "ColourGains": (1.0, 1.0),
        })

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

    # @staticmethod
    # def assign_camera(max_cams=4):
        
