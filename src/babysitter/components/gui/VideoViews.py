import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class VideoViewWrapper(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._label = QLabel("Camera Feed")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumSize(900, 700)
        self._label.setStyleSheet("background: black; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def set_frame_rgb(self, frame_rgb: np.ndarray) -> None:
        if frame_rgb is None:
            return

        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            self._label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation  # smoother is heavier on Pi
        )
        self._label.setPixmap(pix)
    
    def get_widget(self):
        return self