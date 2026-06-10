import html
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from annealer_diag.theme import COLORS


class _HistoryLineEdit(QLineEdit):
    def __init__(self, history: list[str], parent=None):
        super().__init__(parent)
        self._history = history
        self._history_index = -1

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up:
            if self._history and self._history_index < len(self._history) - 1:
                self._history_index += 1
                self.setText(self._history[self._history_index])
        elif event.key() == Qt.Key.Key_Down:
            if self._history_index > 0:
                self._history_index -= 1
                self.setText(self._history[self._history_index])
            elif self._history_index == 0:
                self._history_index = -1
                self.clear()
        else:
            self._history_index = -1
            super().keyPressEvent(event)


def _colorize(line: str) -> str:
    escaped = html.escape(line)

    if ">>" in line:
        color = COLORS["accent"]
    elif "[LEARN]" in line:
        color = COLORS["yellow"]
    elif "[NCR]" in line:
        color = COLORS["green"]
    elif "[TUNE]" in line:
        color = COLORS["orange"]
    elif "error" in line.lower() or "fault" in line.lower():
        color = COLORS["red"]
    else:
        color = COLORS["fg"]

    return f'<pre style="margin:0;color:{color};">{escaped}</pre>'


class TerminalWidget(QWidget):
    def __init__(self, serial_manager, parent=None):
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._history: list[str] = []

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        # Bottom margin so the command-input row isn't flush against the
        # window's bottom edge — gives the field some visual breathing
        # room and matches the inset of the other panels.
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(10000)
        font = QFont("Consolas", 10)
        self._output.setFont(font)
        self._output.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._output.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._output)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        prompt = QLabel(">")
        prompt.setStyleSheet(f"color: {COLORS['accent']}; font-family: Consolas; font-size: 10pt;")
        input_row.addWidget(prompt)

        self._input = _HistoryLineEdit(self._history)
        self._input.setPlaceholderText("Enter command…")
        input_row.addWidget(self._input, stretch=1)

        self._send_btn = QPushButton("Send")
        input_row.addWidget(self._send_btn)

        layout.addLayout(input_row)

    def _connect_signals(self) -> None:
        self._serial_manager.line_received.connect(self.append_line)
        self._send_btn.clicked.connect(self._send)
        self._input.returnPressed.connect(self._send)

    def append_line(self, line: str) -> None:
        self._output.appendHtml(_colorize(line))

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return

        self._history.insert(0, text)
        self._input.clear()

        echo = f'<pre style="margin:0;color:{COLORS["cyan"]};">&gt; {html.escape(text)}</pre>'
        self._output.appendHtml(echo)

        self._serial_manager.send_command(text)

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)

        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self._output.clear)
        menu.addAction(clear_action)

        copy_all_action = QAction("Copy All", self)
        copy_all_action.triggered.connect(self._copy_all)
        menu.addAction(copy_all_action)

        save_action = QAction("Save Log…", self)
        save_action.triggered.connect(self._save_log)
        menu.addAction(save_action)

        menu.exec(self._output.mapToGlobal(pos))

    def _copy_all(self) -> None:
        text = self._output.toPlainText()
        QApplication.clipboard().setText(text)

    def _save_log(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"annealer_log_{timestamp}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", default_name, "Text Files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._output.toPlainText())
