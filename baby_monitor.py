"""
monitor_baby_oop.py

Webcam -> YOLO (local) -> (throttled) GPT image description -> overlay -> CSV log

Design goals:
- Clean OOP structure
- Easy to extend (save frames, add risk scoring, multi-camera, summarization)
- No global state except defaults
"""

from __future__ import annotations

import base64
import csv
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import cv2
from ultralytics import YOLO
from openai import OpenAI


# -----------------------------
# Config
# -----------------------------

@dataclass(frozen=True)
class MonitorConfig:
    camera_index: int = 0
    windows_backend: int = cv2.CAP_DSHOW  # Windows: cv2.CAP_DSHOW is often most stable
    yolo_model_path: str = "yolov8n.pt"
    yolo_conf: float = 0.35
    person_min_conf: float = 0.45

    gpt_model: str = "gpt-4.1-mini"
    gpt_detail: str = "low"
    describe_every_sec: float = 15.0
    source_name: str = "laptop_webcam"

    log_path: Path = Path("logs/monitor_log.csv")

    prompt: str = """You are analyzing a camera frame for child safety monitoring.

Describe the scene briefly in 3–6 short lines.

Focus on:

1) Who are present:
   - Identify baby, adult, animal, or other people if visible. How many? (e.g. "1 baby in center, 1 adult on left")
   - Approximate age category (infant/toddler/adult) only if reasonably clear.
   - Their position in the frame (left/right/center/background).
   - Tell what they are doing if clear. Anything unusual or concerning?

2) Nanny behavior (if nanny is visible):
   - If nanny is observable, note if they are paying attention to the baby or looking away.

3) Baby safety assessment (if a baby or young child is visible):
   - Is the baby’s face clearly visible?
   - Is anything covering or very close to the mouth or nose?
   - Is the baby pressed into a soft surface?
   - Baby posture (on back / side / stomach / sitting / being held / unknown).

4) Environmental hazards:
   - Blankets, pillows, cords, small objects, toys near face,
   - Clutter or objects that could pose choking or suffocation risk.

Be cautious.
If something is unclear, say "uncertain".
Do not guess details that are not visible.
"""


# -----------------------------
# Utilities
# -----------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def put_multiline_text(img, text: str, x: int = 10, y: int = 60, line_h: int = 22) -> None:
    for i, line in enumerate(text.splitlines()):
        cv2.putText(
            img,
            line[:140],
            (x, y + i * line_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )


# -----------------------------
# CSV Logger
# -----------------------------

class CsvLogger:
    def __init__(self, path: Path):
        self.path = path
        self._ensure_header()

    def _ensure_header(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "timestamp_utc",
                        "source",
                        "people_count",
                        "yolo_person_present",
                        "prompt",
                        "gpt_model",
                        "detail",
                        "description",
                    ]
                )

    def append(
        self,
        *,
        source: str,
        people_count: int,
        person_present: bool,
        prompt: str,
        gpt_model: str,
        detail: str,
        description: str,
    ) -> None:
        row = [
            utc_now_iso(),
            source,
            people_count,
            int(bool(person_present)),
            prompt.strip().replace("\r\n", "\n"),
            gpt_model,
            detail,
            description.strip().replace("\r\n", "\n"),
        ]
        with self.path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)


# -----------------------------
# GPT Vision Describer
# -----------------------------

class GptVisionDescriber:
    def __init__(self, client: OpenAI):
        self.client = client

    @staticmethod
    def frame_to_data_url(frame_bgr) -> str:
        ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise RuntimeError("Failed to encode frame to JPG.")
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def describe(self, frame_bgr, *, prompt: str, model: str, detail: str) -> str:
        data_url = self.frame_to_data_url(frame_bgr)
        resp = self.client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url, "detail": detail},
                    ],
                }
            ],
        )
        return resp.output_text


# -----------------------------
# YOLO Person Gate
# -----------------------------

class PersonGate:
    def __init__(self, *, min_conf: float):
        self.min_conf = float(min_conf)

    @staticmethod
    def _person_class_id(names: dict) -> Optional[int]:
        # names is dict[int, str]
        for k, v in names.items():
            if v == "person":
                return int(k)
        return None

    def present(self, yolo_result) -> Tuple[bool, int]:
        person_id = self._person_class_id(yolo_result.names)
        if person_id is None or yolo_result.boxes is None:
            return False, 0

        count = 0
        for b in yolo_result.boxes:
            if int(b.cls[0]) == person_id and float(b.conf[0]) >= self.min_conf:
                count += 1
        return (count > 0), count


# -----------------------------
# Throttle helper
# -----------------------------

class Throttle:
    def __init__(self, every_sec: float):
        self.every_sec = float(every_sec)
        self._last_t = 0.0

    def ready(self, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        return (now - self._last_t) >= self.every_sec

    def mark(self, now: Optional[float] = None) -> None:
        self._last_t = time.time() if now is None else now

    def age_sec(self, now: Optional[float] = None) -> float:
        now = time.time() if now is None else now
        return max(0.0, now - self._last_t)


# -----------------------------
# Monitor App
# -----------------------------

class BabyMonitorApp:
    def __init__(self, cfg: MonitorConfig):
        self.cfg = cfg

        # Video
        self.cap = cv2.VideoCapture(cfg.camera_index, cfg.windows_backend)
        if not self.cap.isOpened():
            raise RuntimeError(
                "Could not open webcam. Try camera index 1 or remove CAP_DSHOW."
            )

        # Detection + gating
        self.yolo = YOLO(cfg.yolo_model_path)
        self.person_gate = PersonGate(min_conf=cfg.person_min_conf)

        # GPT
        self.describer = GptVisionDescriber(OpenAI())

        # Logging
        self.logger = CsvLogger(cfg.log_path)

        # Timing
        self.throttle = Throttle(cfg.describe_every_sec)

        # State
        self.last_description: str = "No description yet."
        self.last_people_count: int = 0
        self.last_person_present: bool = False

    def close(self) -> None:
        try:
            self.cap.release()
        finally:
            cv2.destroyAllWindows()

    def _run_yolo(self, frame_bgr):
        results = self.yolo.predict(source=frame_bgr, conf=self.cfg.yolo_conf, verbose=False)
        return results[0]

    def _maybe_describe_and_log(self, frame_bgr, *, person_present: bool, people_count: int) -> None:
        now = time.time()
        if not person_present:
            return
        if not self.throttle.ready(now):
            return

        # Mark immediately to prevent double-trigger during delays
        self.throttle.mark(now)

        try:
            desc = self.describer.describe(
                frame_bgr,
                prompt=self.cfg.prompt,
                model=self.cfg.gpt_model,
                detail=self.cfg.gpt_detail,
            )
            self.last_description = desc

            self.logger.append(
                source=self.cfg.source_name,
                people_count=people_count,
                person_present=person_present,
                prompt=self.cfg.prompt,
                gpt_model=self.cfg.gpt_model,
                detail=self.cfg.gpt_detail,
                description=desc,
            )
        except Exception as e:
            self.last_description = f"Describe error: {type(e).__name__}: {e}"

    def _overlay_ui(self, img_bgr, *, people_count: int):
        h, w = img_bgr.shape[:2]

        panel_width = 500  # adjust as needed
        canvas = cv2.copyMakeBorder(
            img_bgr,
            0, 0,
            0, panel_width,
            cv2.BORDER_CONSTANT,
            value=(30, 30, 30),
        )

        status = f"People: {people_count} | GPT every {int(self.cfg.describe_every_sec)}s | Press q to quit"
        cv2.putText(
            canvas,
            status,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )

        age = int(self.throttle.age_sec())
        text = f"GPT:\n{self.last_description}\n\n(Last update: {age}s ago)"

        put_multiline_text(canvas, text, x=w + 20, y=40)

        return canvas

    def run(self) -> None:
        print("Press 'q' to quit.")
        cv2.namedWindow("Webcam + YOLO + GPT Describe (Throttled)", cv2.WINDOW_NORMAL)

        while True:
            ok, frame = self.cap.read()
            if not ok:
                break

            r = self._run_yolo(frame)
            annotated = r.plot()

            present, num = self.person_gate.present(r)
            self.last_people_count = num
            self.last_person_present = present

            self._maybe_describe_and_log(frame, person_present=present, people_count=num)

            # IMPORTANT: if _overlay_ui returns a canvas, assign it back
            annotated = self._overlay_ui(annotated, people_count=num)

            cv2.imshow("Webcam + YOLO + GPT Describe (Throttled)", annotated)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


# -----------------------------
# Entry point
# -----------------------------

if __name__ == "__main__":
    cfg = MonitorConfig(
        camera_index=0,
        describe_every_sec=15.0,
        gpt_detail="low",
    )

    app = BabyMonitorApp(cfg)
    try:
        app.run()
    finally:
        app.close()
