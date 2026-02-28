# vision_yolo.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional

import cv2
from ultralytics import YOLO


@dataclass(frozen=True)
class YoloConfig:
    model_path: str = "yolov8n.pt"
    conf: float = 0.35
    person_min_conf: float = 0.45


class YoloVision:
    def __init__(self, cfg: YoloConfig):
        self.cfg = cfg
        self.model = YOLO(cfg.model_path)

    def predict(self, frame_bgr):
        """Returns the first ultralytics result object for this frame."""
        results = self.model.predict(source=frame_bgr, conf=self.cfg.conf, verbose=False)
        return results[0]

    @staticmethod
    def annotated_frame(result):
        """Returns an annotated BGR image (numpy array) drawn by Ultralytics."""
        return result.plot()

    @staticmethod
    def _person_class_id(names: dict) -> Optional[int]:
        for k, v in names.items():
            if v == "person":
                return int(k)
        return None

    def person_present(self, result) -> Tuple[bool, int]:
        """Returns (present, count) using person_min_conf."""
        pid = self._person_class_id(result.names)
        if pid is None or result.boxes is None:
            return False, 0

        count = 0
        for b in result.boxes:
            if int(b.cls[0]) == pid and float(b.conf[0]) >= self.cfg.person_min_conf:
                count += 1
        return (count > 0), count
