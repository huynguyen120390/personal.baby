# gui_qt_monitor.py
from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QThread
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QSpinBox, QComboBox, QMessageBox
)

from components.vision.yolo_vision import YoloVision, YoloConfig
from components.vision.gpt_describer import GptDescriber, GptDescribeConfig


# -------------------------
# Logging
# -------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CsvLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "timestamp_utc",
                    "source",
                    "people_count",
                    "person_present",
                    "prompt",
                    "gpt_model",
                    "detail",
                    "description",
                ])

    def append(self, *, source: str, people_count: int, person_present: bool,
               prompt: str, gpt_model: str, detail: str, description: str):
        with self.path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                utc_now_iso(),
                source,
                people_count,
                int(person_present),
                prompt.strip().replace("\r\n", "\n"),
                gpt_model,
                detail,
                description.strip().replace("\r\n", "\n"),
            ])


# -------------------------
# GPT worker (threaded)
# -------------------------

class DescribeWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, describer: GptDescriber, frame_bgr, prompt: str):
        super().__init__()
        self.describer = describer
        self.frame = frame_bgr
        self.prompt = prompt

    @Slot()
    def run(self):
        try:
            text = self.describer.describe_frame(self.frame, self.prompt)
            # TODO: only speak when high risk detected?
            self.describer.speak(text)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


# -------------------------
# GUI
# -------------------------

@dataclass(frozen=True)
class GuiConfig:
    source_name: str = "laptop_webcam"
    log_path: Path = Path("logs/monitor_log.csv")
    camera_backend: int = cv2.CAP_DSHOW  # try cv2.CAP_MSMF if slow
    yolo_conf: float = 0.35
    person_min_conf: float = 0.45


DEFAULT_PROMPT = """You are analyzing a camera frame for child safety monitoring.

Describe the scene briefly in 3–6 short lines.

Focus on:

1) Who are present:
   - Identify baby, adult, animal, or other people if visible. How many? (e.g. "1 baby in center, 1 adult on left")
   - Approximate age category (infant/toddler/adult) only if reasonably clear.
   - Their position in the frame (left/right/center/background).
   - Tell what they are doing if clear. Anything unusual or concerning?
   - What is nanny doing? 

2) Baby safety assessment (if a baby or young child is visible):
   - Is the baby’s face clearly visible?
   - Is anything covering or very close to the mouth or nose?
   - Is the baby pressed into a soft surface?
   - Baby posture (on back / side / stomach / sitting / being held / unknown).

3) Environmental hazards:
   - Blankets, pillows, cords, small objects, toys near face,
   - Clutter or objects that could pose choking or suffocation risk.

Be cautious.
If something is unclear, say "uncertain".
Do not guess details that are not visible.
"""


class BabyMonitorQt(QWidget):
    def __init__(self, cfg: GuiConfig):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("Baby Monitor - Qt")

        # --- UI widgets ---
        self.video_label = QLabel("Camera not started.")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(960, 540)

        self.desc_box = QTextEdit()
        self.desc_box.setReadOnly(True)
        self.desc_box.setPlaceholderText("GPT description will appear here... (scrollable)")

        self.prompt_box = QTextEdit()
        self.prompt_box.setPlainText(DEFAULT_PROMPT)
        self.prompt_box.setMinimumHeight(180)

        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.start)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)

        self.btn_describe = QPushButton("Describe Now")
        self.btn_describe.clicked.connect(self.on_describe_now)
        self.btn_describe.setEnabled(False)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 600)
        self.interval_spin.setValue(15)
        self.interval_spin.setSuffix(" s")

        self.detail_combo = QComboBox()
        self.detail_combo.addItems(["low", "high", "auto"])
        self.detail_combo.setCurrentText("low")

        # Layout
        controls = QHBoxLayout()
        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)
        controls.addWidget(QLabel("Auto describe:"))
        controls.addWidget(self.interval_spin)
        controls.addWidget(QLabel("detail:"))
        controls.addWidget(self.detail_combo)
        controls.addWidget(self.btn_describe)
        controls.addStretch(1)

        right = QVBoxLayout()
        right.addWidget(QLabel("GPT output (scrollable)"))
        right.addWidget(self.desc_box, 2)
        right.addWidget(QLabel("Prompt (editable)"))
        right.addWidget(self.prompt_box, 1)
        right.addLayout(controls)

        root = QHBoxLayout(self)
        root.addWidget(self.video_label, 2)
        root.addLayout(right, 1)

        # --- CV/GPT ---
        self.cap: Optional[cv2.VideoCapture] = None
        self.vision = YoloVision(YoloConfig(
            model_path="yolov8n.pt",
            conf=self.cfg.yolo_conf,
            person_min_conf=self.cfg.person_min_conf,
        ))

        self.logger = CsvLogger(self.cfg.log_path)

        # We'll rebuild describer config when detail changes
        self.describer = GptDescriber(GptDescribeConfig(detail="low"))

        # --- state ---
        self._last_frame = None
        self._last_yolo = None
        self.last_describe_t = 0.0
        self._describe_in_flight = False

        # --- timers ---
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame)

        self.describe_timer = QTimer(self)
        self.describe_timer.timeout.connect(self.maybe_describe)

    def append_status(self, msg: str):
        self.desc_box.append(msg)

    def start(self):
        # Camera
        if self.cap is None:
            self.cap = cv2.VideoCapture(0, self.cfg.camera_backend)

        if not self.cap.isOpened():
            QMessageBox.critical(self, "Camera Error", "Could not open camera. Try a different backend or close other apps.")
            return

        # Warm-up
        for _ in range(5):
            self.cap.read()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_describe.setEnabled(True)

        self.frame_timer.start(30)       # ~33 fps
        self.describe_timer.start(250)   # check 4x/sec

        self.append_status("Started.")

    def stop(self):
        self.frame_timer.stop()
        self.describe_timer.stop()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_describe.setEnabled(False)

        self.video_label.setText("Stopped.")
        self.append_status("Stopped.")

    def update_frame(self):
        if self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            return

        r = self.vision.predict(frame)
        annotated = self.vision.annotated_frame(r)

        # show video
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg))

        # save latest for describe
        self._last_frame = frame
        self._last_yolo = r

    def _update_describer_detail(self):
        detail = self.detail_combo.currentText()
        self.describer = GptDescriber(GptDescribeConfig(detail=detail))

    def maybe_describe(self):
        if self._last_frame is None or self._last_yolo is None:
            return

        interval = self.interval_spin.value()
        now = time.time()

        present, num = self.vision.person_present(self._last_yolo)
        if not present:
            return
        if (now - self.last_describe_t) < interval:
            return

        self.last_describe_t = now
        self.start_describe_async(reason=f"[auto] People={num}", people_count=num, person_present=True)

    def on_describe_now(self):
        if self._last_frame is None or self._last_yolo is None:
            self.append_status("No frame yet.")
            return

        present, num = self.vision.person_present(self._last_yolo)
        self.start_describe_async(reason="[manual]", people_count=num, person_present=present)

    def start_describe_async(self, *, reason: str, people_count: int, person_present: bool):
        if self._describe_in_flight:
            return

        self._describe_in_flight = True
        self._update_describer_detail()

        prompt = self.prompt_box.toPlainText().strip()
        if not prompt:
            prompt = DEFAULT_PROMPT

        frame_copy = self._last_frame.copy()
        self.append_status(f"{reason} → describing...")

        # Thread + Worker
        thread = QThread()
        worker = DescribeWorker(self.describer, frame_copy, prompt)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(lambda text: self.on_describe_finished(
            text=text,
            people_count=people_count,
            person_present=person_present,
            prompt=prompt,
        ))
        worker.error.connect(self.on_describe_error)

        # cleanup
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._describe_cleanup)

        thread.start()

        # keep refs so they don't get GC'd immediately
        self._describe_thread = thread
        self._describe_worker = worker

    @Slot()
    def _describe_cleanup(self):
        self._describe_in_flight = False
        self._describe_thread = None
        self._describe_worker = None

    def on_describe_finished(self, *, text: str, people_count: int, person_present: bool, prompt: str):
        self.append_status("✅ GPT:\n" + text)

        # log to CSV
        try:
            self.logger.append(
                source=self.cfg.source_name,
                people_count=people_count,
                person_present=person_present,
                prompt=prompt,
                gpt_model=self.describer.cfg.model,
                detail=self.describer.cfg.detail,
                description=text,
            )
        except Exception as e:
            self.append_status(f"❌ Log error: {type(e).__name__}: {e}")

        self._describe_in_flight = False

    def on_describe_error(self, msg: str):
        self.append_status("❌ GPT error: " + msg)
        self._describe_in_flight = False


if __name__ == "__main__":
    app = QApplication(sys.argv)

    cfg = GuiConfig(
        source_name="laptop_webcam",
        log_path=Path("logs/monitor_log.csv"),
        camera_backend=cv2.CAP_DSHOW,  # if slow, try cv2.CAP_MSMF
    )

    w = BabyMonitorQt(cfg)
    w.resize(1500, 850)
    w.show()

    sys.exit(app.exec())
