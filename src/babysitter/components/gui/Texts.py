
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QThread
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QSpinBox, QComboBox, QMessageBox
)


class LabelWrapper:
    def __init__(self, text, color=None, min_width=200, min_height=50):
        self.text = text
        self.color = color
        self._label = QLabel(text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumSize(min_width, min_height)


    def set_style(self, color:str="black", font_size:int=16):
        stylesheet = f"""
        QLabel {{
            color: {color};
            font-size: {font_size}px;
        }}
        """
        self._label.setStyleSheet(stylesheet)

    def get_widget(self):
        return self._label


class TextEditWrapper:
    def __init__(self, placeholder="", min_width=200, min_height=50):
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(placeholder)
        self._text_edit.setMinimumSize(min_width, min_height)

    def set_style(self, color:str="black", font_size:int=16):
        stylesheet = f"""
        QTextEdit {{
            color: {color};
            font-size: {font_size}px;
        }}
        """
        self._text_edit.setStyleSheet(stylesheet)

    def set_readonly(self, readonly:bool):
        self._text_edit.setReadOnly(readonly)

    def get_widget(self):
        return self._text_edit