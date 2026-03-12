from __future__ import annotations
from dataclasses import dataclass
import threading
from typing import Optional, Any
import time
import numpy as np

from src.babysitter.components.brain.vision_analyzer import VisionAnalyzer, VisionResult
from src.babysitter.components.camera.pi_cam import Camera
from src.babysitter.components.brain.gpt_describer import GptDescriber, GptDescribeConfig
from src.babysitter.components.brain.yolo_vision import YoloVision, YoloConfig
from src.babysitter.dataclasses.vision_packages import FramePacket
from src.babysitter.skills.contracts import AsyncSkill, ConditionalSkill, ConditionalSkill, SequenceSkill, SequenceSkill
from src.babysitter.skills.vision_skills import GptDescriberSkill, GptIntervalGateSkill, YoloSkill


class BabyMonitorController:
    def __init__(self):
        self.camera =None
        self.vision_analyzer = VisionAnalyzer()
       

        self._running = False
        self._last_gpt_ts = 0.0
        self._gpt_interval_s = 5.0   # don't spam GPT; tune later

    def start(self) -> None:
        if self.camera is None:
            self.camera = Camera()
        self.camera.start()
        if not self.camera.is_opened():
            self.camera.stop()
            self.camera.close()
            self.camera = None
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

    def observe_frame(self, prompt=None) -> Optional[FramePacket]:
        """
        Pull one frame and run lightweight vision work. Returns a packet for GUI to display.
        Heavy work (GPT) should be throttled or moved to a background thread later.
        """
        if not self._running or self.camera is None:
            return None

        frame = self.camera.capture_frame()
        if frame is None:
            return None

        result = self.vision_analyzer.analyze(frames=frame, prompt=prompt)
        
        timestamp = time.time()

        pkt = FramePacket(
            vision_result=result,
            frame_rgb=frame,
            timestamp=timestamp
        )
        return pkt
    
    
    
