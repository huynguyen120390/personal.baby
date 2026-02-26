
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QThread
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QSpinBox, QComboBox, QMessageBox
)



class PushButtonWrapper(object):
    def __init__(self, text, parent, callback):
        """
        Initializes a QPushButton with the given text and parent widget.
        If a callback function is provided, it will be connected to the button's clicked signal.
        :param text: The text to display on the button.
        :param parent: The parent widget of the button (optional).
        :param callback: A function to call when the button is clicked (optional). The function should take no arguments.
        """
        self._button = QPushButton(text, parent)
        self._button.clicked.connect(callback)


    def set_style(self, background_color:str="#d9534f",
                        text_color:str="white",
                        border_radius:int=15,
                        font_size:int=16,
                        disabled_colo:str="#a9a9a9"):
        stylesheet = f"""
        QPushButton {{
            background-color: {background_color};
            color: {text_color};
            border-radius: {border_radius}px;
            font-size: {font_size}px;
            border: none;
        }}
        QPushButton:hover {{
            opacity: 0.85;
        }}
        QPushButton:pressed {{
            background-color: {disabled_color};
        }}
        QPushButton:disabled {{
            background-color: {disabled_color};
            color: #eeeeee;
        }}
        """
        self._button.setStyleSheet(stylesheet)

    def set_enabled(self, enabled:bool):
        self._button.setEnabled(enabled)

    def get_widget(self):
        return self._button