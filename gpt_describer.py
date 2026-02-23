# gpt_describer.py
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

import cv2
from openai import OpenAI
import pyttsx3


@dataclass(frozen=True)
class GptDescribeConfig:
    model: str = "gpt-4.1-mini"
    detail: str = "low"  # "low" | "high" | "auto"
    jpeg_quality: int = 85


class GptDescriber:
    def __init__(self, cfg: GptDescribeConfig, client: Optional[OpenAI] = None):
        self.cfg = cfg
        self.client = client or OpenAI()

    def _frame_to_data_url(self, frame_bgr) -> str:
        ok, buf = cv2.imencode(
            ".jpg",
            frame_bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), int(self.cfg.jpeg_quality)],
        )
        if not ok:
            raise RuntimeError("Failed to encode frame to JPG.")
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def describe_frame(self, frame_bgr, prompt: str) -> str:
        data_url = self._frame_to_data_url(frame_bgr)
        resp = self.client.responses.create(
            model=self.cfg.model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url, "detail": self.cfg.detail},
                ],
            }],
        )
        return resp.output_text

    def speak(self, text):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
