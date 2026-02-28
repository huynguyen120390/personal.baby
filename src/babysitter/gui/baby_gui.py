from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QMessageBox
)

from src.babysitter.components.gui.Buttons import PushButtonWrapper
from src.babysitter.components.gui.Texts import LabelWrapper, TextEditWrapper
from src.babysitter.components.gui.BoxLayouts import QHBoxLayoutWrapper, QVBoxLayoutWrapper
from src.babysitter.configs.prompts import DEFAULT_PROMPT
from src.babysitter.controller.BabyMonitorController import BabyMonitorController


class GuiConfig:
    source_name: str = "pi_cam"
    log_path: Path = Path("logs/monitor_log.csv")


class BabyMonitorGui(QWidget):
    def __init__(self, cfg: GuiConfig):
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


        # Controller
        self.controller = BabyMonitorController()


        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.controller.update_frame)

        #self.describer_timer = QTimer()
       # self.describer_timer.timeout.connect(self.controller.describe_now)


    def start_monitor(self):
        print("Start monitoring...")
        try:
            self.start_button.set_enabled(False)
            self.stop_button.set_enabled(True)
            self.describe_now_button.set_enabled(True)
            self.controller.start()

            self.frame_timer.start(30)  # Update frame every 30 ms (~33 FPS)
            #self.describer_timer.start(5000)  # Describe every 5 seconds


        except Exception as e:
            QMessageBox.critical(self, "An Error Occurred",
                                 "{} {}".format(type(e).__name__, str(e)))
            return
        finally:
            self.start_button.set_enabled(True)
            self.stop_button.set_enabled(False)
            self.describe_now_button.set_enabled(False)


    def stop_monitor(self):
        print("Stop monitoring...")
        self.frame_timer.stop()
        #self.describer_timer.stop()
        self.controller.stop()


if __name__ == "__main__":
    cfg = GuiConfig(
        source_name="pi_cam",
        log_path=Path("logs/monitor_log.csv")
    )

    m = BabyMonitorGui(cfg)
    m.resize(800, 600)
    m.show()




