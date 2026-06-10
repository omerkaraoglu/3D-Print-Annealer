from abc import abstractmethod

from PySide6.QtWidgets import QWidget


class BaseDiagnosticView(QWidget):
    VIEW_NAME: str = "Unnamed"
    ACTIVATION_PATTERNS: list = []

    def __init__(self, serial_manager, parent=None):
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._active = False

    @abstractmethod
    def on_serial_line(self, line: str): ...

    @abstractmethod
    def reset(self): ...

    def set_active(self, active: bool):
        self._active = active
