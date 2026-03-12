


from dataclasses import dataclass
import threading
import time
import datetime as dt

import numpy as np

from src.babysitter.components.brain.gpt_describer import GptDescribeConfig, GptDescriber
from src.babysitter.components.brain.yolo_vision import YoloConfig, YoloVision
from src.babysitter.dataclasses.vision_packages import VisionResult
from src.babysitter.skills.contracts import AsyncSkill, ConditionalSkill, Context, SequenceSkill
from src.babysitter.skills.vision_skills import GptDescriberSkill, GptIntervalGateSkill, YoloSkill




class VisionAnalyzer:
    def __init__(self):
        self.describer = GptDescriber(GptDescribeConfig(detail="low"))
        self.yolo_vision = YoloVision(YoloConfig(
            model_path="yolov8n.pt",
            conf=0.35,
            person_min_conf=0.7,
        ))

        self.pipeline, self.async_gpt= self.build_vision_pipeline()
        self._state = Context()

    def analyze(self, frames, prompt=None):
        # Placeholder for analysis logic
        # This method should be implemented to process the data and update the brain's state
        if isinstance(frames, np.ndarray): #TODO: maybe check size as well
            return self.analyze_frame_with_skills(frames, prompt)
        else:
            print("Unsupported input type for analyze(): expected np.ndarray")
            return None
        
    def analyze_frame_with_skills(self, frame, prompt=None):
        context = Context(input=frame, prompt=prompt, data=dict(Context().data), events=[])
        self.async_gpt.pull_completed_into(context)

        result =self.pipeline.run(context)
        context.data.update(result.updates)
        context.events.extend(result.events)

        self._state.data.update(context.data)
        self._state.events.extend(context.events)

        return VisionResult(
            yolo_result=context.data.get("yolo_result"),
            yolo_annotated_rgb=context.data.get("yolo_annotated_rgb"),
            gpt_result=context.data.get("gpt_description") if context.data.get("human_present") else None,
            human_present=context.data.get("human_present", False),
            human_count=context.data.get("human_count", 0),
        )

    def build_vision_pipeline(self):
        yolo_skill = YoloSkill()
        gpt_gate_skill = GptIntervalGateSkill(interval_s=15.0)
        gpt_describe_skill = GptDescriberSkill()
        async_gpt = AsyncSkill(inner_skill=gpt_describe_skill, store_key="gpt_description", max_inflight=1)

        gated_async_gpt = ConditionalSkill(
                            inner_skill=async_gpt,
                            predicate=lambda ctx: ctx.data.get("human_present", False) and ctx.data.get("gpt_allowed", False),
                            name="gated_async_gpt")
        pipeline = SequenceSkill(skills=[yolo_skill, gpt_gate_skill, gated_async_gpt], name="vision_pipeline")

        return pipeline, async_gpt


        


    # def analyze_frame(self, frame, prompt=None) -> VisionResult:
    #     # Declare some vars
    #     with self._gpt_lock:
    #         gpt_description = self._latest_gpt
    #     # This method should be implemented to analyze a single frame and update the brain's state
    #     # YOLO
    #     yolo_result, annotated, human_present, human_count = self.analyze_frame_with_yolo(frame)
    #     # Trigger GPT every N seconds if human is present; use the description for something (logging, alerting, etc.)
    #     if human_present:
    #         now = time.time()
    #         if human_present and now - self._last_gpt_ts >= self._gpt_interval_s:
    #             self._last_gpt_ts = now
    #             self._try_start_gpt_thread(frame, prompt, now)

        
    #     result = VisionResult(yolo_result=yolo_result,
    #                           yolo_annotated_rgb=annotated, 
    #                           gpt_result=gpt_description if human_present else None,
    #                           human_present=human_present,
    #                           human_count=human_count)
        
    #     return result



    # def analyze_frame_with_yolo(self, frame):
    #     yolo_prediction_result = self.yolo_vision.predict(frame)
    #     human_present, human_count = self.yolo_vision.person_present(yolo_prediction_result)
    #     annotated = self.yolo_vision.annotated_frame(yolo_prediction_result)  # for GUI display
    #     return yolo_prediction_result, annotated, human_present, human_count
    
    # def analyze_frame_with_gpt(self, frame, prompt) -> str:
    #     # This method should be implemented to analyze frames using GPT and update the brain's state

    #     description = self.describer.describe_frame(frame, prompt)
    #     print(f"GPT description: {description}")
    #     return description

    # def _try_start_gpt_thread(self, frame: np.ndarray, prompt: str | None, ts: float):
    #     # ✅ don’t start a new GPT call if one is still running
    #     with self._gpt_lock:
    #         if self._gpt_inflight:
    #             return
    #         self._gpt_inflight = True

    #     # ✅ copy frame so worker thread doesn’t see a mutated/reused buffer
    #     frame_copy = frame.copy()

    #     t = threading.Thread(
    #         target=self._gpt_worker,
    #         args=(frame_copy, prompt, ts),
    #         daemon=True
    #     )
    #     t.start()

    # def _gpt_worker(self, frame_copy: np.ndarray, prompt: str | None, ts: float):
    #     try:
    #         desc = self.describer.describe_frame(frame_copy, prompt)
    #         with self._gpt_lock:
    #             self._latest_gpt = desc
    #             self._latest_gpt_ts = ts
    #         print(f"GPT description: {desc}")
    #     except Exception as e:
    #         print(f"GPT worker error: {e}")
    #     finally:
    #         with self._gpt_lock:
    #             self._gpt_inflight = False