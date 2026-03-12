from dataclasses import dataclass

import numpy as np

@dataclass
class VisionResult:
    yolo_result: any = None
    yolo_annotated_rgb: np.ndarray = None
    gpt_result: any = None
    human_present: bool =False
    human_count: int =0

@dataclass
class FramePacket:
    frame_rgb: np.ndarray = None
    vision_result: VisionResult = None
    timestamp: float = None
    

