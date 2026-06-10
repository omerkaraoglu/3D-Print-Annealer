import re
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from annealer_diag.base_view import BaseDiagnosticView
from annealer_diag.connection_bar import ConnectionBar
from annealer_diag.serial_manager import SerialManager
from annealer_diag.terminal_widget import TerminalWidget
from annealer_diag.theme import DARK_STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annealer Diagnostics")
        self.setMinimumSize(1200, 800)

        self._serial_manager = SerialManager(self)
        self._views: list[BaseDiagnosticView] = []

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Vertical)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(4, 4, 4, 0)
        # Bigger gap between the (now logo-bearing) connection bar and
        # the tab widget so the tabs feel like they belong to a row
        # below the logo, not crammed against it.
        top_layout.setSpacing(8)

        self._connection_bar = ConnectionBar(self._serial_manager)
        top_layout.addWidget(self._connection_bar)

        self._tab_widget = QTabWidget()
        top_layout.addWidget(self._tab_widget)

        self._terminal = TerminalWidget(self._serial_manager)

        splitter.addWidget(top_widget)
        splitter.addWidget(self._terminal)

        total = 800
        splitter.setSizes([int(total * 0.70), int(total * 0.30)])

        self.setCentralWidget(splitter)

    def _connect_signals(self) -> None:
        self._serial_manager.connection_changed.connect(self._on_connection_changed)
        self._serial_manager.line_received.connect(self._route_line)

    def register_view(self, view: BaseDiagnosticView) -> None:
        self._views.append(view)
        self._tab_widget.addTab(view, view.VIEW_NAME)
        self._serial_manager.line_received.connect(view.on_serial_line)

    def _route_line(self, line: str) -> None:
        for view in self._views:
            for pattern in view.ACTIVATION_PATTERNS:
                if re.search(pattern, line):
                    self._tab_widget.setCurrentWidget(view)
                    return

    def _on_connection_changed(self, connected: bool) -> None:
        if not connected:
            for view in self._views:
                view.reset()

    def closeEvent(self, event) -> None:
        if self._serial_manager.is_connected():
            self._serial_manager.disconnect()
        super().closeEvent(event)


def main():
    import matplotlib
    matplotlib.use("QtAgg")

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()

    from annealer_diag.views.profile_view import ProfileView
    from annealer_diag.views.tune_view import TuneView
    from annealer_diag.views.learn_view import LearnView
    from annealer_diag.views.plant_view import PlantView
    from annealer_diag.views.screenshot_view import ScreenshotView

    window.register_view(ProfileView(window._serial_manager))
    window.register_view(LearnView(window._serial_manager))
    window.register_view(PlantView(window._serial_manager))
    window.register_view(TuneView(window._serial_manager))
    window.register_view(ScreenshotView(window._serial_manager))

    window.show()
    sys.exit(app.exec())
