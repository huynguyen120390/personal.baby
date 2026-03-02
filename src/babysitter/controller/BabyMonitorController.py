from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any
import time
import numpy as np

from src.babysitter.components.camera.pi_cam import Camera
from src.babysitter.components.brain.gpt_describer import GptDescriber, GptDescribeConfig
from src.babysitter.components.brain.yolo_vision import YoloVision, YoloConfig


@dataclass
class FramePacket:
    frame_rgb: np.ndarray                 # (H,W,3) RGB888
    yolo_result: Optional[Any] = None     # whatever your YOLO returns
    annotated_rgb: Optional[np.ndarray] = None
    timestamp: float = 0.0


class BabyMonitorController:
    def __init__(self):
        self.camera =None
        self.describer = GptDescriber(GptDescribeConfig(detail="low"))
        self.vision = YoloVision(YoloConfig(
            model_path="yolov8n.pt",
            conf=0.35,
            person_min_conf=0.7,
        ))

        self._running = False
        self._last_gpt_ts = 0.0
        self._gpt_interval_s = 5.0   # don't spam GPT; tune later

    def start(self) -> None:
        if self.camera is None:
            self.camera = Camera()
        self.camera.start()
        if not self.camera.is_opened():
            raise RuntimeError("Failed to start the camera.")

        # Warm up camera
        for _ in range(5):
            _ = self.camera.capture_frame()

        self._running = True

    def stop(self) -> None:
        self._running = False
        if self.camera is not None:
            self.camera.stop()
            self.camera.close()
            self.camera = None

    @property
    def is_running(self) -> bool:
        return self._running

    def observe_frame(self) -> Optional[FramePacket]:
        """
        Pull one frame and run lightweight vision work. Returns a packet for GUI to display.
        Heavy work (GPT) should be throttled or moved to a background thread later.
        """
        if not self._running or self.camera is None:
            return None

        frame = self.camera.capture_frame()
        if frame is None:
            return None

        # YOLO step (keep it relatively lightweight)
        result = self.vision.predict(frame)

        # If annotated_frame returns a numpy RGB image, great.
        # If it draws in-place, adjust accordingly.
        annotated = self.vision.annotated_frame(result)

        pkt = FramePacket(
            frame_rgb=frame,
            yolo_result=result,
            annotated_rgb=annotated,
            timestamp=time.time(),
        )

        # Optional: throttle GPT (NOT per-frame)
        # You can also trigger only when person/baby detected.
        # if time.time() - self._last_gpt_ts > self._gpt_interval_s:
        #     self._last_gpt_ts = time.time()
        #     ... queue GPT job in a background thread ...

        return pkt