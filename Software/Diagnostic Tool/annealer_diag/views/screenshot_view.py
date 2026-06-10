"""
screenshot_view.py — LVGL screen-capture page for the diag tool.

Sends SHOT / SHOT ALL to the firmware, parses the binary tile stream,
and saves each captured frame as a native + nearest-neighbor-upscaled
PNG. A QThread worker owns the serial port exclusively during capture
so the line-reader doesn't steal bytes from the binary stream.

The wire protocol lives in annealer_diag.screenshot_protocol — shared
with the standalone screenshot.py CLI tool.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

from annealer_diag.base_view import BaseDiagnosticView
from annealer_diag.screenshot_protocol import Frame, capture_frames, save_png
from annealer_diag.theme import COLORS


# Default output directory — the project root's shots/ folder. Resolved
# from this file's location so it doesn't matter where Python was launched.
_DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "shots"


class _CaptureWorker(QObject):
    """Runs capture_frames() on a background thread.

    The view passes the already-paused (exclusive) Serial object so this
    worker doesn't need to know about SerialManager. Emits per-frame and
    per-protocol-event signals consumed by the view.
    """

    frame_saved = Signal(str, str, QImage)     # name, primary_path, preview_image
    event = Signal(str, str)                   # kind, detail
    finished = Signal(int, str)                # n_saved, error_or_empty
    progress = Signal(int)                     # tiles received this frame (cumulative)

    def __init__(self, ser, command: str, out_dir: Path, scale: int,
                 idle_timeout_s: float, parent=None) -> None:
        super().__init__(parent)
        self._ser = ser
        self._command = command
        self._out_dir = out_dir
        self._scale = scale
        self._idle_timeout_s = idle_timeout_s

    def run(self) -> None:
        saved = 0
        err = ""
        tile_count = 0

        def on_event(kind: str, detail: str) -> None:
            nonlocal tile_count
            if kind == "tile":
                tile_count += 1
                self.progress.emit(tile_count)
            elif kind == "begin":
                tile_count = 0
                self.progress.emit(0)
            self.event.emit(kind, detail)

        try:
            for frame in capture_frames(
                self._ser,
                self._command,
                idle_timeout_s=self._idle_timeout_s,
                progress=on_event,
            ):
                paths = save_png(frame, self._out_dir, scale=self._scale)
                primary = str(paths[0]) if paths else ""
                qimg = QImage(
                    frame.rgb888, frame.w, frame.h, frame.w * 3,
                    QImage.Format.Format_RGB888,
                ).copy()  # copy to detach from the bytes lifetime
                self.frame_saved.emit(frame.name, primary, qimg)
                saved += 1
        except Exception as e:  # noqa: BLE001 — surface to the UI
            err = f"{type(e).__name__}: {e}"

        self.finished.emit(saved, err)


class ScreenshotView(BaseDiagnosticView):
    VIEW_NAME = "Screenshot"
    # No firmware log line announces an incoming screenshot, so don't
    # auto-switch to this tab — it stays user-initiated.
    ACTIVATION_PATTERNS: list[str] = []

    def __init__(self, serial_manager, parent=None) -> None:
        super().__init__(serial_manager, parent)
        self._out_dir: Path = _DEFAULT_OUT_DIR
        self._thread: QThread | None = None
        self._worker: _CaptureWorker | None = None

        self._build_ui()
        self._wire_signals()
        self._update_enabled_state()

    # ── UI construction ────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Row 1 — action buttons + status
        top = QHBoxLayout()
        top.setSpacing(8)

        self._btn_shot = QPushButton("Capture current screen")
        self._btn_shot.setToolTip("Send SHOT — captures whatever screen the LVGL UI is on")
        self._btn_shot.clicked.connect(lambda: self._start_capture("SHOT", 5.0))
        top.addWidget(self._btn_shot)

        self._btn_all = QPushButton("Capture all screens")
        self._btn_all.setToolTip("Send SHOT ALL — cycles every built screen, ~14 s each at 115200 baud")
        self._btn_all.clicked.connect(lambda: self._start_capture("SHOT ALL", 20.0))
        top.addWidget(self._btn_all)

        top.addStretch()

        self._status = QLabel("Disconnected")
        self._status.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 11px; padding: 2px 4px;"
        )
        top.addWidget(self._status)

        root.addLayout(top)

        # Row 2 — output dir + scale
        meta = QHBoxLayout()
        meta.setSpacing(8)

        meta.addWidget(QLabel("Output:"))
        self._out_label = QLabel(str(self._out_dir))
        self._out_label.setStyleSheet(
            f"color: {COLORS['fg_dim']}; padding: 2px 6px; "
            f"background: {COLORS['bg_medium']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 3px;"
        )
        self._out_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        meta.addWidget(self._out_label, stretch=1)

        self._btn_choose = QPushButton("Choose…")
        self._btn_choose.clicked.connect(self._choose_out_dir)
        meta.addWidget(self._btn_choose)

        self._btn_open = QPushButton("Open folder")
        self._btn_open.clicked.connect(self._open_out_dir)
        meta.addWidget(self._btn_open)

        meta.addSpacing(12)
        meta.addWidget(QLabel("Upscale:"))
        self._scale_spin = QSpinBox()
        self._scale_spin.setRange(0, 8)
        self._scale_spin.setValue(4)
        self._scale_spin.setToolTip("Nearest-neighbor multiplier for the second saved PNG (0 = disabled)")
        self._scale_spin.setSuffix("×")
        meta.addWidget(self._scale_spin)

        root.addLayout(meta)

        # Row 3 — progress bar (hidden when idle)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate by default
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self._progress.setFixedHeight(6)
        root.addWidget(self._progress)

        # Row 4 — preview (left) and event log (right), 1:1 split.
        body = QHBoxLayout()
        body.setSpacing(8)

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(320, 240)
        self._preview.setStyleSheet(
            f"background: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px;"
        )
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._set_preview_placeholder()
        body.addWidget(self._preview, stretch=1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._log.setPlaceholderText("Capture events appear here.")
        body.addWidget(self._log, stretch=1)

        root.addLayout(body, stretch=1)

    def _set_preview_placeholder(self) -> None:
        self._preview.setPixmap(QPixmap())
        self._preview.setText("No screenshot captured yet")
        self._preview.setStyleSheet(
            f"background: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px; "
            f"color: {COLORS['fg_dim']};"
        )

    # ── Signal wiring ──────────────────────────────────────────────────
    def _wire_signals(self) -> None:
        self._serial_manager.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected: bool) -> None:
        self._update_enabled_state()
        if not connected:
            self._status.setText("Disconnected")
        else:
            self._status.setText("Idle")

    def _update_enabled_state(self) -> None:
        connected = self._serial_manager.is_connected()
        busy = self._thread is not None
        self._btn_shot.setEnabled(connected and not busy)
        self._btn_all.setEnabled(connected and not busy)
        self._scale_spin.setEnabled(not busy)
        self._btn_choose.setEnabled(not busy)

    # ── Capture lifecycle ──────────────────────────────────────────────
    def _start_capture(self, command: str, idle_timeout_s: float) -> None:
        if not self._serial_manager.is_connected():
            self._append_log("not connected")
            return
        if self._thread is not None:
            return  # already capturing

        try:
            ser = self._serial_manager.begin_exclusive()
        except RuntimeError as e:
            self._append_log(f"error: {e}")
            return

        self._status.setText(f"Capturing — {command}")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate while waiting for BEGIN
        self._append_log(f"--- {datetime.now().strftime('%H:%M:%S')}  {command}")

        self._worker = _CaptureWorker(
            ser, command, self._out_dir, self._scale_spin.value(), idle_timeout_s,
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.event.connect(self._on_event)
        self._worker.progress.connect(self._on_progress)
        self._worker.frame_saved.connect(self._on_frame_saved)
        self._worker.finished.connect(self._on_capture_finished)
        self._thread.start()
        self._update_enabled_state()

    def _on_capture_finished(self, n_saved: int, err: str) -> None:
        # Tear down the worker thread before re-arming the reader so we
        # don't get a race on shared Serial state.
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
            self._worker = None

        self._serial_manager.end_exclusive()

        self._progress.setVisible(False)
        if err:
            self._status.setText(f"Error: {err}")
            self._append_log(f"error: {err}")
        else:
            suffix = "s" if n_saved != 1 else ""
            self._status.setText(f"Idle — last run saved {n_saved} PNG{suffix}")
            self._append_log(f"done — {n_saved} PNG{suffix}")
        self._update_enabled_state()

    # ── Worker signal handlers ─────────────────────────────────────────
    def _on_event(self, kind: str, detail: str) -> None:
        if kind == "sent":
            self._append_log(f"→ {detail}")
        elif kind == "begin":
            self._append_log(f"begin: {detail}")
        elif kind == "end":
            self._append_log(f"end:   {detail}")
        elif kind == "warn":
            self._append_log(f"warn:  {detail}")
        elif kind == "log":
            self._append_log(detail)

    def _on_progress(self, tile_count: int) -> None:
        # 320×240 / 20-line buffer ⇒ 12 tiles per frame. Use that as the
        # determinate range so the bar feels responsive.
        if tile_count == 0:
            self._progress.setRange(0, 0)
        else:
            self._progress.setRange(0, 12)
            self._progress.setValue(min(tile_count, 12))

    def _on_frame_saved(self, name: str, path: str, qimg: QImage) -> None:
        self._append_log(f"saved {path}")
        if qimg.isNull():
            return
        # Scale to fit the preview while preserving aspect ratio.
        target = self._preview.size()
        pm = QPixmap.fromImage(qimg).scaled(
            target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation,
        )
        self._preview.setText("")
        self._preview.setPixmap(pm)
        self._preview.setStyleSheet(
            f"background: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 4px;"
        )

    # ── Output dir handling ────────────────────────────────────────────
    def _choose_out_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output directory", str(self._out_dir))
        if d:
            self._out_dir = Path(d)
            self._out_label.setText(str(self._out_dir))

    def _open_out_dir(self) -> None:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        # Cross-platform "reveal in file manager".
        if sys.platform.startswith("win"):
            os.startfile(self._out_dir)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{self._out_dir}"')
        else:
            os.system(f'xdg-open "{self._out_dir}"')

    # ── Utility ────────────────────────────────────────────────────────
    def _append_log(self, text: str) -> None:
        self._log.appendPlainText(text)

    # ── BaseDiagnosticView API ─────────────────────────────────────────
    def on_serial_line(self, line: str) -> None:
        # Nothing to parse — the screenshot stream bypasses the line
        # reader (we take exclusive control during capture).
        pass

    def reset(self) -> None:
        if self._thread is not None:
            # A disconnect arrived mid-capture. Best effort: stop the
            # worker so we don't dangle a thread on a dead port.
            self._thread.quit()
            self._thread.wait(1000)
            self._thread = None
            self._worker = None
        self._progress.setVisible(False)
        self._status.setText("Disconnected")
        self._set_preview_placeholder()
        self._log.clear()
