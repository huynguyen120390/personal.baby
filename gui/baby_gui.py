from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QThread
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QSpinBox, QComboBox, QMessageBox
)

from components.gui.Buttons import PushButtonWrapper
from components.gui.Texts import LabelWrapper, TextEditWrapper
from components.gui.BoxLayouts import QHBoxLayoutWrapper, QVBoxLayoutWrapper
from configs.prompts import DEFAULT_PROMPT

class BabyMonitorGuui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Baby Monitor")
        self.setGeometry(100, 100, 400, 300)

        # Labels
        self.video_label = LabelWrapper("Camera Feed").set_style(color="blue", font_size=18)
        self.describe_box_label = LabelWrapper("Baby Behavior Description").set_style(color="blue", font_size=18)
        self.describe_box = (TextEditWrapper("Describe the baby's behavior here...")
                             .set_style(color="black", font_size=14)
                             .set_readonly(True))
        self.prompt_box_label = LabelWrapper("Current Prompt").set_style(color="blue", font_size=18)
        self.prompt_box= (TextEditWrapper(DEFAULT_PROMPT)
                          .set_style(color="black", font_size=14)
                          .set_readonly(True))

        # Buttons
        self.start_button = PushButtonWrapper("Start Monitoring", self, self.start_monitor).set_enabled(True)
        self.stop_button = PushButtonWrapper("Stop Monitoring", self, self.stop_monitor).set_enabled(False)
        self.describe_now_button = PushButtonWrapper("Describe Now", self, self.describe_now).set_enabled(False)

        # Layouts
        controls_layout = QHBoxLayoutWrapper([self.start_button, self.stop_button, self.describe_now_button])
        right_layout = QVBoxLayoutWrapper([self.describe_box_label, self.describe_box,
                                           self.describe_box_label, self.prompt_box,
                                           controls_layout])
        root_layout = QHBoxLayoutWrapper([self.video_label, right_layout])

    def start_monitor(self):
        print("Start monitoring...")
        try:
            self.start_button.set_enabled(False)
            self.stop_button.set_enabled(True)
            self.describe_now_button.set_enabled(True)
        except Exception as e:
            QMessageBox.critical(self, "An Error Occurred",
                                 "{} {}".format(type(e).__name__, str(e)))
            return
        finally:
            self.start_button.set_enabled(True)
            self.stop_button.set_enabled(False)
            self.describe_now_button.set_enabled(False)





