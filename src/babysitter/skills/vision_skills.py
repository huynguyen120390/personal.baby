


import time

from pyparsing import Optional
import numpy as np

from src.babysitter.components.brain.gpt_describer import GptDescribeConfig, GptDescriber
from src.babysitter.components.brain.yolo_vision import YoloConfig, YoloVision
from src.babysitter.skills.contracts import BaseSkill, Context, SkillResult


class YoloSkill(BaseSkill):
    """Detect objects in an image using YOLOv8."""
    def __init__(self):
        super().__init__("yolo_detect")
        self.yolo_vision = YoloVision(YoloConfig(
            model_path="yolov8n.pt",
            conf=0.35,
            person_min_conf=0.7,
        ))
    
    def should_run(self, context) -> bool:
        # Input is expected to be a video frame (numpy array) for this skill to run
        return isinstance(context.input, np.ndarray)
    def run(self, context):

        frame = context.input

        yolo_prediction_result = self.yolo_vision.predict(frame)
        human_present, human_count = self.yolo_vision.person_present(yolo_prediction_result)
        annotated = self.yolo_vision.annotated_frame(yolo_prediction_result)

        updates = {
            "yolo_result": yolo_prediction_result,
            "yolo_annotated_rgb": annotated,
            "human_present": human_present,
            "human_count": human_count,
        }

        return SkillResult(
            updates=updates,
            output=updates,
            events=[f"{self.name}: detected human_present={human_present}, count={human_count}"]
        )
    
class GptDescriberSkill(BaseSkill):
    """Generate a natural language description of the scene using GPT."""
    def __init__(self):
        name = "gpt_describe"
        super().__init__(name)
        self.describer = GptDescriber(GptDescribeConfig(detail="low"))
    
    def should_run(self, context) -> bool:
        # Only run if a human is detected and we have an annotated frame
        return context.data.get("human_present", False) and "yolo_annotated_rgb" in context.data
    
    def run(self, context):
        annotated_frame = context.data["yolo_annotated_rgb"]
        prompt = context.prompt
        description = self.describer.describe_frame(annotated_frame, prompt=prompt)

        updates = {
            "gpt_description": description
        }

        return SkillResult(
            updates=updates,
            output=description,
            events=[f"{self.name}: generated description"]
        )
    
class GptIntervalGateSkill(BaseSkill):
    def __init__(self, interval_s: float = 15.0):
        super().__init__("gpt_interval_gate")
        self.interval_s = interval_s
        self._last_run_ts = 0.0

    def should_run(self, context: Context) -> bool:
        return context.data.get("human_present", False)

    def run(self, context: Context) -> SkillResult:
        now = time.time()
        allowed = (now - self._last_run_ts) >= self.interval_s

        if allowed:
            self._last_run_ts = now

        return SkillResult(
            updates={"gpt_allowed": allowed},
            output=allowed,
            events=[f"{self.name}: allowed={allowed}"]
        )
