

from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot, QThread
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton, QLayout,
    QHBoxLayout, QVBoxLayout, QSpinBox, QComboBox, QMessageBox
)

class QHBoxLayoutWrapper:
    def __init__(self, widget_wrapper_list:list):
        self._layout = QHBoxLayout()
        for widget in widget_wrapper_list:
            if isinstance(widget.get_widget(), QWidget):
                self._layout.addWidget(widget.get_widget())
            elif isinstance(widget.get_widget(), QLayout):
                self._layout.addLayout(widget.get_widget())

    def add_widget(self, widget):
        self._layout.addWidget(widget)
        return self

    def get_widget(self):
        return self._layout


class QVBoxLayoutWrapper:
    def __init__(self, widget_wrapper_list:list):
        self._layout = QVBoxLayout()
        for widget in widget_wrapper_list:
            if isinstance(widget.get_widget(), QWidget):
                self._layout.addWidget(widget.get_widget())
            elif isinstance(widget.get_widget(), QLayout):
                self._layout.addLayout(widget.get_widget())

    def add_widget(self, widget_wrapper):
        self._layout.addWidget(widget_wrapper.get_widget())
        return self

    def get_widget(self):
        return self._layout