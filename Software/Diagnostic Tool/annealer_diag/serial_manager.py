import threading
import time

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal


class SerialManager(QObject):
    line_received = Signal(str)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    # Emits the current firmware mode whenever it changes. Values are
    # one of: "IDLE", "TUNE", "LEARN", "PROFILE", "PID", "RAMP".
    # Views use this to decide whether destructive commands like
    # "Heater Off" should be disabled / require confirmation.
    mode_changed = Signal(str)

    # Substrings → mode label. Order matters: longer / more specific
    # markers come first so we don't mis-classify (e.g. "Mode: PROFILE"
    # would also contain the substring "Mode: P", and "TUNING Complete"
    # must not match the bare "TUNING" token).
    _MODE_MARKERS = (
        ("Tuning Complete",                "IDLE"),
        ("[LEARN] *** Sweep complete",     "IDLE"),
        ("Mode: TUNING",                   "TUNE"),
        ("Mode: LEARN",                    "LEARN"),
        ("Mode: PROFILE",                  "PROFILE"),
        ("Mode: RAMP",                     "RAMP"),
        ("Mode: PID",                      "PID"),
        ("Mode: IDLE",                     "IDLE"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._mode: str = "IDLE"

    @property
    def current_mode(self) -> str:
        return self._mode

    def is_tune_or_learn_active(self) -> bool:
        return self._mode in ("TUNE", "LEARN")

    def connect(self, port: str, baud: int = 115200) -> None:
        # ESP32 dev boards have a two-transistor auto-reset circuit driven
        # by DTR/RTS — EN is pulled low only when the two lines are in
        # OPPOSITE states. The OS asserts modem-control lines to its
        # default when a port is opened, which on a fresh handle pulses
        # EN low and resets the chip. We construct the Serial object
        # without opening, pin DTR=RTS=False, *then* open so the lines
        # come up matched and the chip stays running.
        s = serial.Serial()
        s.port = port
        s.baudrate = baud
        s.timeout = 0.1
        s.dtr = False
        s.rts = False
        s.open()
        self._serial = s
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        self.connection_changed.emit(True)

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._serial is not None and self._serial.is_open:
            # Match DTR/RTS before close so the line transitions the OS
            # makes as it tears down the handle don't fire the reset
            # circuit. Same-state at close → no EN pulse → no reboot.
            try:
                self._serial.dtr = False
                self._serial.rts = False
            except Exception:
                pass
            self._serial.close()
        self._serial = None
        if self._mode != "IDLE":
            self._mode = "IDLE"
            self.mode_changed.emit("IDLE")
        self.connection_changed.emit(False)

    def hard_reset(self) -> bool:
        """Pulse the ESP32's EN line via RTS to reboot the chip.

        Uses esptool's classic hard-reset sequence: hold RTS asserted
        for 100 ms (drives EN low through the auto-reset transistor),
        then release. DTR is held deasserted throughout so IO0 stays
        high — the chip boots into run mode, not the ROM bootloader.
        Returns True if the pulse was issued, False if not connected.
        """
        if self._serial is None or not self._serial.is_open:
            return False
        try:
            self._serial.dtr = False
            self._serial.rts = True
            time.sleep(0.1)
            self._serial.rts = False
            time.sleep(0.05)
            return True
        except serial.SerialException:
            return False

    def send_command(self, text: str) -> None:
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.write((text + "\n").encode("utf-8"))

    def begin_exclusive(self) -> "serial.Serial":
        """Pause the line-reader and hand the raw Serial to the caller.

        Used by the screenshot view to perform binary tile reads that
        can't go through readline()/UTF-8 decoding. The port itself is
        not closed (which would reset most ESP32 boards). Caller MUST
        invoke end_exclusive() to restart the reader.
        """
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("serial not connected")
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join(timeout=2.0)
            self._thread = None
        return self._serial

    def end_exclusive(self) -> None:
        """Restart the line-reader after begin_exclusive()."""
        if self._serial is None or not self._serial.is_open:
            return
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def list_ports(self) -> list[tuple[str, str]]:
        return [
            (p.device, p.description or p.device)
            for p in serial.tools.list_ports.comports()
        ]

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                raw = self._serial.readline()
                if raw:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self._maybe_update_mode(line)
                        self.line_received.emit(line)
            except serial.SerialException as exc:
                self.error_occurred.emit(str(exc))
                self.disconnect()
                break

    def _maybe_update_mode(self, line: str) -> None:
        new_mode: str | None = None
        for needle, label in self._MODE_MARKERS:
            if needle in line:
                new_mode = label
                break
        if new_mode is not None and new_mode != self._mode:
            self._mode = new_mode
            self.mode_changed.emit(new_mode)
