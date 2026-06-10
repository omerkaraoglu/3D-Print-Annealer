from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from annealer_diag.theme import COLORS

# Fixed pixel height for the logo. The pixmap is downscaled to this
# height with aspect ratio preserved, which means the logo sits at
# the same place and same size on every screen regardless of window
# width — it lives in the always-visible top connection bar.
_LOGO_HEIGHT_PX = 40
# Padding around the logo. The bar's own min height is set to match
# (logo + vertical padding) so other widgets vertically below the bar
# sit lower than the logo's bottom edge instead of overlapping it,
# and the right padding pushes the Port:/combobox/Connect cluster
# clear of the logo's right edge.
_LOGO_PAD_TOP    = 8
_LOGO_PAD_BOTTOM = 8
_LOGO_PAD_LEFT   = 10
_LOGO_PAD_RIGHT  = 28
_LOGO_PATH = Path(__file__).parent / "resources" / "readark-logo-white-bg-removed.png"
# Product brand mark — sits centered in the empty area between the
# connection controls cluster and the right-side status. Loaded
# lazily; if the file isn't present the slot stays empty (no crash).
_ANNEALX_LOGO_PATH = Path(__file__).parent / "resources" / "annealx-logo.png"
_ANNEALX_LOGO_HEIGHT_PX = 48

_CONNECT_STYLE = f"""
QPushButton {{
    background-color: #2d4a2d;
    color: {COLORS["green"]};
    border: 1px solid {COLORS["green"]};
    border-radius: 4px;
    padding: 5px 14px;
    min-width: 90px;
}}
QPushButton:hover {{
    background-color: {COLORS["green"]};
    color: {COLORS["bg_dark"]};
}}
QPushButton:pressed {{
    background-color: #7ec47a;
    color: {COLORS["bg_dark"]};
}}
"""

_DISCONNECT_STYLE = f"""
QPushButton {{
    background-color: #4a1a1a;
    color: {COLORS["red"]};
    border: 1px solid {COLORS["red"]};
    border-radius: 4px;
    padding: 5px 14px;
    min-width: 90px;
}}
QPushButton:hover {{
    background-color: {COLORS["red"]};
    color: {COLORS["bg_dark"]};
}}
QPushButton:pressed {{
    background-color: #d06080;
    color: {COLORS["bg_dark"]};
}}
"""

# Amber "deliberate-action" styling for Reset MCU — visually distinct
# from the green Connect / red Disconnect cluster so it's not mistaken
# for a normal-flow control. Disabled appearance matches the global
# QSS so the button cleanly grays out when no port is open.
_RESET_STYLE = f"""
QPushButton {{
    background-color: #3a2a10;
    color: {COLORS["orange"]};
    border: 1px solid {COLORS["orange"]};
    border-radius: 4px;
    padding: 5px 12px;
    min-width: 80px;
}}
QPushButton:hover {{
    background-color: {COLORS["orange"]};
    color: {COLORS["bg_dark"]};
}}
QPushButton:pressed {{
    background-color: #ffd093;
    color: {COLORS["bg_dark"]};
}}
QPushButton:disabled {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["fg_dim"]};
    border-color: {COLORS["border"]};
}}
"""


class ConnectionBar(QWidget):
    def __init__(self, serial_manager, parent=None):
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._build_ui()
        self._connect_signals()
        self._refresh_ports()

    def _build_ui(self) -> None:
        # Pin the bar's overall height so the logo's full vertical box
        # is reserved — the tab widget below the connection bar then
        # naturally sits below the logo's bottom edge with proper
        # clearance, rather than the logo's pixmap overflowing into
        # the rows beneath it. Size to whichever brand mark is taller
        # so neither gets clipped.
        bar_height = (
            max(_LOGO_HEIGHT_PX, _ANNEALX_LOGO_HEIGHT_PX)
            + _LOGO_PAD_TOP + _LOGO_PAD_BOTTOM
        )
        self.setFixedHeight(bar_height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(_LOGO_PAD_LEFT, _LOGO_PAD_TOP,
                                  4, _LOGO_PAD_BOTTOM)
        layout.setSpacing(8)

        # Brand logo — far left, fixed height, aspect-preserved. Lives
        # in the connection bar (which is shared across every tab) so
        # it's pinned in the same screen position no matter which view
        # is active.
        self._logo_label = QLabel()
        if _LOGO_PATH.is_file():
            pixmap = QPixmap(str(_LOGO_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(
                    _LOGO_HEIGHT_PX,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._logo_label.setPixmap(scaled)
        self._logo_label.setFixedHeight(_LOGO_HEIGHT_PX)
        # Right padding here is what keeps the Port:/dropdown/Connect
        # cluster clear of the logo's right edge.
        self._logo_label.setContentsMargins(0, 0, _LOGO_PAD_RIGHT, 0)
        layout.addWidget(self._logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(QLabel("Port:"))

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)
        layout.addWidget(self._port_combo)

        self._refresh_btn = QPushButton("⟳")
        self._refresh_btn.setToolTip("Refresh port list")
        self._refresh_btn.setFixedWidth(32)
        layout.addWidget(self._refresh_btn)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setStyleSheet(_CONNECT_STYLE)
        layout.addWidget(self._connect_btn)

        # Hard reset — pulses EN low via RTS. Disabled until connected
        # so the click is a no-op for a port we haven't opened.
        self._reset_btn = QPushButton("Reset MCU")
        self._reset_btn.setToolTip("Pulse EN low via RTS — reboots the ESP32 without reflashing")
        self._reset_btn.setStyleSheet(_RESET_STYLE)
        self._reset_btn.setEnabled(False)
        layout.addWidget(self._reset_btn)

        baud_label = QLabel("115200 baud")
        baud_label.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 12px;")
        layout.addWidget(baud_label)

        # One stretch pushes the AnnealX brand mark all the way to the
        # right edge so it sits next to the connection status, filling
        # the otherwise-empty area between the connection controls and
        # the right-aligned status.
        layout.addStretch()

        self._annealx_label = QLabel()
        if _ANNEALX_LOGO_PATH.is_file():
            pix = QPixmap(str(_ANNEALX_LOGO_PATH))
            if not pix.isNull():
                self._annealx_label.setPixmap(
                    pix.scaledToHeight(
                        _ANNEALX_LOGO_HEIGHT_PX,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        self._annealx_label.setFixedHeight(_ANNEALX_LOGO_HEIGHT_PX)
        # Gap between the logo and the "Connected to ..." text so they
        # don't visually collide.
        self._annealx_label.setContentsMargins(0, 0, 16, 0)
        layout.addWidget(self._annealx_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._status_label = QLabel("Disconnected")
        self._status_label.setStyleSheet(f"color: {COLORS['fg_dim']};")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        self._refresh_btn.clicked.connect(self._refresh_ports)
        self._connect_btn.clicked.connect(self._toggle_connection)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        self._serial_manager.connection_changed.connect(self._on_connection_changed)

    def _on_reset_clicked(self) -> None:
        # Modal confirm — Reset MCU is one click away from clobbering
        # an in-progress TUNE / LEARN / PROFILE run, so make the user
        # acknowledge before we pulse EN. Cancel is the default focus
        # button so a stray Enter keypress doesn't trigger the reset.
        box = QMessageBox(self)
        box.setWindowTitle("Reset MCU")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Reset the MCU now?")
        box.setInformativeText(
            "This reboots the ESP32 immediately. Any in-progress TUNE, "
            "LEARN, or PROFILE run will be aborted, and the heater "
            "output drops to 0 % during the boot cycle."
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        if self._serial_manager.hard_reset():
            # Briefly surface the action in the status bar so the user
            # sees a confirmation that the pulse fired.
            self._status_label.setText("Reset pulse sent")
            self._status_label.setStyleSheet(f"color: {COLORS['orange']};")

    def _refresh_ports(self) -> None:
        self._port_combo.clear()
        for device, description in self._serial_manager.list_ports():
            display = f"{device} — {description}" if description != device else device
            self._port_combo.addItem(display, userData=device)
        if self._port_combo.count() == 0:
            self._port_combo.addItem("No ports found", userData=None)

    def _toggle_connection(self) -> None:
        if self._serial_manager.is_connected():
            self._serial_manager.disconnect()
        else:
            port = self._port_combo.currentData()
            if port:
                try:
                    self._serial_manager.connect(port)
                except Exception as exc:
                    self._status_label.setText(f"Error: {exc}")
                    self._status_label.setStyleSheet(f"color: {COLORS['red']};")

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            port = self._port_combo.currentData() or ""
            self._status_label.setText(f"Connected to {port}")
            self._status_label.setStyleSheet(f"color: {COLORS['green']};")
            self._connect_btn.setText("Disconnect")
            self._connect_btn.setStyleSheet(_DISCONNECT_STYLE)
            self._port_combo.setEnabled(False)
            self._refresh_btn.setEnabled(False)
            self._reset_btn.setEnabled(True)
        else:
            self._status_label.setText("Disconnected")
            self._status_label.setStyleSheet(f"color: {COLORS['fg_dim']};")
            self._connect_btn.setText("Connect")
            self._connect_btn.setStyleSheet(_CONNECT_STYLE)
            self._port_combo.setEnabled(True)
            self._refresh_btn.setEnabled(True)
            self._reset_btn.setEnabled(False)
