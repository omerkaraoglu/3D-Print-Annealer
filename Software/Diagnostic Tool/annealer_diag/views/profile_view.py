"""
profile_view.py — Real-time annealer profile plotter as a diagnostic view.

Parses >>-tagged protocol lines from the firmware and renders a live
planned-vs-actual temperature chart using matplotlib embedded in PySide6.
"""

import time
from datetime import datetime

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QPlainTextEdit, QGridLayout, QSplitter, QWidget, QFrame,
)
from PySide6.QtCore import Qt

from annealer_diag.base_view import BaseDiagnosticView
from annealer_diag.theme import COLORS, apply_mpl_theme

C_PLAN = "#89b4fa"
C_ACT  = "#f38ba8"
C_PRED = "#f9e2af"
C_SP   = "#cba6f7"
C_HTR  = "#fab387"
C_HOLD = "#a6e3a1"
C_DONE = "#a6e3a1"


def _planned_trajectory(steps, start_temp):
    t_list = [0.0]
    T_list = [start_temp]
    cur = start_temp

    for s in steps:
        tgt  = s["target"]
        rate = s["rate_min"]
        hold = s["hold_min"]
        now  = t_list[-1]

        if s["type"] == "RAMP" and rate > 0:
            dt = abs(tgt - cur) / rate
            n  = max(2, int(dt * 20))
            for i in range(1, n + 1):
                t_list.append(now + dt * i / n)
                T_list.append(cur + (tgt - cur) * i / n)
            cur = tgt
        else:
            t_list.append(now)
            T_list.append(tgt)
            cur = tgt

        if hold > 0:
            t_list.append(t_list[-1] + hold)
            T_list.append(cur)

    return np.array(t_list), np.array(T_list)


def _hold_spans(steps, start_temp):
    spans = []
    t = 0.0
    cur = start_temp
    for s in steps:
        if s["type"] == "RAMP" and s["rate_min"] > 0:
            t += abs(s["target"] - cur) / s["rate_min"]
        cur = s["target"]
        if s["hold_min"] > 0:
            spans.append((t, t + s["hold_min"]))
            t += s["hold_min"]
    return spans


class ProfileView(BaseDiagnosticView):
    VIEW_NAME = "Profile"
    ACTIVATION_PATTERNS = [r"^>>PROFILE_START"]

    _DRAW_THROTTLE_MS = 100

    def __init__(self, serial_manager, parent=None):
        super().__init__(serial_manager, parent)

        self._expected_steps = 0
        self._steps = []
        self._start_temp = 25.0
        self._actual_t = []
        self._actual_T = []
        self._predicted_T = []
        self._heater_out = []
        self._setpoint_T = []
        self._profile_active = False
        self._profile_done = False
        self._last_draw_time = 0.0

        self._plan_line = None
        self._act_line = None
        self._pred_line = None
        self._sp_line = None
        self._htr_line = None

        self._last_step = 0
        self._last_state = 0
        self._peak_temp = 0.0
        self._peak_heater = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(2)

        # ── Button bar ─────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_stop = QPushButton("Stop Profile")
        self._btn_stop.setToolTip("Stop the running profile (PROFILE: STOP)")
        self._btn_stop.setStyleSheet(
            f"QPushButton {{ color: {COLORS['red']}; border-color: {COLORS['red']}; }}"
            f"QPushButton:hover {{ background-color: {COLORS['red']}; color: {COLORS['bg_dark']}; }}"
        )
        self._btn_stop.clicked.connect(self._on_stop_profile_clicked)
        btn_row.addWidget(self._btn_stop)

        self._btn_set0 = QPushButton("Heater Off")
        self._btn_set0.setToolTip("Set temperature to 0 — heater off (SET 20)")
        self._btn_set0.clicked.connect(self._on_heater_off_clicked)
        btn_row.addWidget(self._btn_set0)

        self._serial_manager.mode_changed.connect(self._on_mode_changed)
        self._on_mode_changed(self._serial_manager.current_mode)

        self._btn_plant = QPushButton("Show Plant")
        self._btn_plant.setToolTip("Print plant model and PID parameters (PLANT)")
        self._btn_plant.clicked.connect(lambda: self._send("PLANT"))
        btn_row.addWidget(self._btn_plant)

        btn_row.addStretch()

        self._status_label = QLabel("Waiting for profile…")
        self._status_label.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 11px; padding: 2px 4px;"
        )
        btn_row.addWidget(self._status_label)

        layout.addLayout(btn_row)

        # ── Main splitter: plots on top, info+log on bottom ────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(3)

        # ── Plots container ────────────────────────────────────────────────────
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)

        self._fig = Figure(figsize=(13, 7))
        gs = self._fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.08)
        self._ax_temp = self._fig.add_subplot(gs[0])
        self._ax_htr = self._fig.add_subplot(gs[1], sharex=self._ax_temp)
        apply_mpl_theme(self._fig, [self._ax_temp, self._ax_htr])

        self._canvas = FigureCanvasQTAgg(self._fig)
        plot_layout.addWidget(self._canvas, stretch=1)

        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        plot_layout.addWidget(self._toolbar)

        splitter.addWidget(plot_widget)

        # ── Bottom panel: info cards + event log ───────────────────────────────
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        bottom_layout.setSpacing(8)

        # Info cards
        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; }}"
        )
        info_grid = QGridLayout(info_frame)
        info_grid.setContentsMargins(10, 8, 10, 8)
        info_grid.setSpacing(4)

        self._info_labels = {}
        fields = [
            ("Elapsed",     0, 0), ("Step",        0, 2),
            ("Actual",      1, 0), ("Setpoint",    1, 2),
            ("Predicted",   2, 0), ("Error",       2, 2),
            ("Heater",      3, 0), ("Peak Heater", 3, 2),
            ("State",       4, 0), ("Peak Temp",   4, 2),
        ]
        for name, row, col in fields:
            lbl_name = QLabel(f"{name}:")
            lbl_name.setStyleSheet(
                f"color: {COLORS['fg_dim']}; font-size: 11px; border: none; "
                "font-weight: bold; background: transparent;"
            )
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet(
                f"color: {COLORS['fg']}; font-size: 12px; border: none; "
                "font-family: 'Consolas', 'Courier New', monospace; background: transparent;"
            )
            info_grid.addWidget(lbl_name, row, col, Qt.AlignmentFlag.AlignRight)
            info_grid.addWidget(lbl_val, row, col + 1, Qt.AlignmentFlag.AlignLeft)
            self._info_labels[name] = lbl_val

        info_grid.setColumnStretch(1, 1)
        info_grid.setColumnStretch(3, 1)
        bottom_layout.addWidget(info_frame, stretch=2)

        # Event log
        log_frame = QFrame()
        log_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; }}"
        )
        log_inner = QVBoxLayout(log_frame)
        log_inner.setContentsMargins(6, 4, 6, 4)
        log_inner.setSpacing(2)

        log_title = QLabel("Event Log")
        log_title.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 11px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        log_inner.addWidget(log_title)

        self._event_log = QPlainTextEdit()
        self._event_log.setReadOnly(True)
        self._event_log.setMaximumBlockCount(500)
        self._event_log.setStyleSheet(
            f"font-size: 10px; font-family: 'Consolas', 'Courier New', monospace; "
            f"background-color: {COLORS['bg_dark']}; border: none; padding: 2px;"
        )
        log_inner.addWidget(self._event_log)

        bottom_layout.addWidget(log_frame, stretch=3)

        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

        self._setup_empty_axes()

    def _send(self, cmd: str):
        if self._serial_manager.is_connected():
            self._serial_manager.send_command(cmd)

    def _on_mode_changed(self, mode: str) -> None:
        locked = mode in ("TUNE", "LEARN")
        self._btn_set0.setEnabled(not locked)
        if locked:
            self._btn_set0.setToolTip(
                f"Disabled while {mode} is running — let the sweep finish "
                f"or stop it from the {mode.title()} tab first."
            )
        else:
            self._btn_set0.setToolTip("Set temperature to 0 — heater off (SET 20)")

    def _on_stop_profile_clicked(self) -> None:
        if self._serial_manager.current_mode != "PROFILE" and not self._profile_active:
            self._send("PROFILE: STOP")
            return
        reply = QMessageBox.question(
            self,
            "Stop Profile",
            "Stop the running profile?\n\n"
            "The heater will turn off and the load will cool naturally. "
            "The profile cannot be resumed once stopped.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._send("PROFILE: STOP")

    def _on_heater_off_clicked(self) -> None:
        if self._serial_manager.is_tune_or_learn_active():
            QMessageBox.information(
                self,
                "Heater Off blocked",
                f"Heater Off is disabled while {self._serial_manager.current_mode} "
                f"is running. Stop the sweep from its own tab first.",
            )
            return
        reply = QMessageBox.question(
            self,
            "Heater Off",
            "Send SET 20?\n\n"
            "This turns the heater off and clears the active setpoint. "
            "Any running profile or hold will be cancelled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._send("SET 20")

    def _log_event(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._event_log.appendPlainText(f"[{ts}] {text}")

    def _state_name(self, state: int) -> str:
        return {0: "Idle", 1: "Ramping", 2: "Holding"}.get(state, f"Unknown({state})")

    def _setup_empty_axes(self):
        for ax in (self._ax_temp, self._ax_htr):
            ax.clear()
        apply_mpl_theme(self._fig, [self._ax_temp, self._ax_htr])

        self._ax_temp.set_ylabel("Temperature  (°C)", fontsize=11)
        self._ax_temp.set_title("Annealer — waiting for profile…",
                     color=COLORS["fg"], fontsize=12, fontweight="bold")
        self._ax_temp.set_xlim(0, 1)
        self._ax_temp.set_ylim(0, 300)
        self._ax_temp.tick_params(labelbottom=False)

        self._ax_htr.set_xlabel("Time  (min)", fontsize=11)
        self._ax_htr.set_ylabel("Heater  (%)", fontsize=11)
        self._ax_htr.set_xlim(0, 1)
        self._ax_htr.set_ylim(0, 105)

        self._canvas.draw_idle()

    def _build_plot(self):
        for ax in (self._ax_temp, self._ax_htr):
            ax.clear()
        apply_mpl_theme(self._fig, [self._ax_temp, self._ax_htr])

        pt, pT = _planned_trajectory(self._steps, self._start_temp)
        total_min = pt[-1] if len(pt) else 60.0

        for t0, t1 in _hold_spans(self._steps, self._start_temp):
            self._ax_temp.axvspan(t0, t1, alpha=0.10, color=C_HOLD, zorder=1)
            self._ax_htr.axvspan(t0, t1, alpha=0.10, color=C_HOLD, zorder=1)

        self._plan_line, = self._ax_temp.plot(
            pt, pT, color=C_PLAN, linewidth=2.5, label="Planned", zorder=2
        )

        self._act_line, = self._ax_temp.plot(
            [], [], color=C_ACT, linewidth=1.5,
            marker="o", markersize=3,
            label="Actual", zorder=5
        )

        self._pred_line, = self._ax_temp.plot(
            [], [], color=C_PRED, linewidth=1.2, linestyle="--",
            marker="s", markersize=2.5,
            label="Predicted", zorder=4
        )

        self._sp_line, = self._ax_temp.plot(
            [], [], color=C_SP, linewidth=1.0, linestyle=":",
            label="Setpoint", zorder=3
        )

        self._htr_line, = self._ax_htr.plot(
            [], [], color=C_HTR, linewidth=1.5,
            drawstyle="steps-post",
            label="Heater Output", zorder=5
        )

        y_lo = min(self._start_temp, min(s["target"] for s in self._steps)) - 5
        y_hi = max(s["target"] for s in self._steps) + 10
        self._ax_temp.set_xlim(-total_min * 0.01, total_min * 1.05)
        self._ax_temp.set_ylim(y_lo, y_hi)
        self._ax_temp.set_ylabel("Temperature  (°C)", fontsize=11)
        self._ax_temp.tick_params(labelbottom=False)
        self._ax_temp.legend(
            facecolor=COLORS["bg_light"], edgecolor=COLORS["border"],
            labelcolor=COLORS["fg"], fontsize=9, loc="upper left", ncol=4
        )
        self._ax_temp.set_title("Annealer Profile — building…",
                     color=COLORS["fg"], fontsize=12, fontweight="bold")

        self._ax_htr.set_xlabel("Time  (min)", fontsize=11)
        self._ax_htr.set_ylabel("Heater  (%)", fontsize=11)
        self._ax_htr.set_ylim(-2, 105)
        self._ax_htr.legend(
            facecolor=COLORS["bg_light"], edgecolor=COLORS["border"],
            labelcolor=COLORS["fg"], fontsize=9, loc="upper right"
        )

        self._canvas.draw_idle()

    def _update_info(self, elapsed, temp, predicted, heater_pct, sp, step, state):
        error = temp - sp
        if temp > self._peak_temp:
            self._peak_temp = temp
        if heater_pct > self._peak_heater:
            self._peak_heater = heater_pct

        self._info_labels["Elapsed"].setText(f"{elapsed:.1f} min")
        self._info_labels["Step"].setText(f"{step} / {len(self._steps)}")
        self._info_labels["Actual"].setText(f"{temp:.1f} °C")
        self._info_labels["Setpoint"].setText(f"{sp:.1f} °C")
        self._info_labels["Predicted"].setText(f"{predicted:.1f} °C")
        self._info_labels["Error"].setText(f"{error:+.1f} °C")
        self._info_labels["Heater"].setText(f"{heater_pct:.1f} %")
        self._info_labels["Peak Heater"].setText(f"{self._peak_heater:.1f} %")
        self._info_labels["State"].setText(self._state_name(state))
        self._info_labels["Peak Temp"].setText(f"{self._peak_temp:.1f} °C")

    def on_serial_line(self, line: str):
        # Capture [PROFILE] events for the log
        if "[PROFILE]" in line:
            clean = line.strip()
            if clean.startswith("\n"):
                clean = clean.lstrip("\n")
            self._log_event(clean)

        if not line.startswith(">>"):
            return

        parts = line[2:].split()
        if not parts:
            return
        tag = parts[0]

        if tag == "PROFILE_START":
            try:
                self._expected_steps = int(parts[1])
                self._start_temp = float(parts[2])
            except (IndexError, ValueError):
                return
            self._steps.clear()
            self._actual_t.clear()
            self._actual_T.clear()
            self._predicted_T.clear()
            self._heater_out.clear()
            self._setpoint_T.clear()
            self._plan_line = None
            self._act_line = None
            self._pred_line = None
            self._sp_line = None
            self._htr_line = None
            self._profile_active = True
            self._profile_done = False
            self._last_step = 0
            self._last_state = 0
            self._peak_temp = self._start_temp
            self._peak_heater = 0.0
            self._event_log.clear()
            self._log_event(f"Profile started — {self._expected_steps} steps, "
                          f"T₀ = {self._start_temp:.1f}°C")
            self._status_label.setText(
                f"Receiving plan: 0 / {self._expected_steps} steps…"
            )
            self._setup_empty_axes()

        elif tag == "STEP":
            try:
                stype    = parts[1]
                target   = float(parts[2])
                rate_min = float(parts[3])
                hold_min = float(parts[4])
            except (IndexError, ValueError):
                return
            self._steps.append(dict(type=stype, target=target,
                                    rate_min=rate_min, hold_min=hold_min))
            n = len(self._steps)
            step_desc = (f"RAMP → {target:.0f}°C @ {rate_min:.1f}°C/min"
                        if stype == "RAMP" else f"SET → {target:.0f}°C")
            if hold_min > 0:
                step_desc += f", hold {hold_min:.1f} min"
            self._log_event(f"Step {n}: {step_desc}")
            self._status_label.setText(
                f"Receiving plan: {n} / {self._expected_steps} steps…"
            )
            if n == self._expected_steps:
                self._status_label.setText(
                    f"Profile ready: {n} steps, T₀ = {self._start_temp:.1f}°C"
                )
                self._build_plot()

        elif tag == "PLOT":
            try:
                elapsed = float(parts[1])
                temp    = float(parts[2])
            except (IndexError, ValueError):
                return

            # Extended format: >>PLOT elapsed actual predicted pid_output setpoint step state
            predicted = temp
            heater    = 0.0
            sp        = temp
            step      = 1
            state     = 1
            has_extended = len(parts) >= 8
            if has_extended:
                try:
                    predicted = float(parts[3])
                    heater    = float(parts[4]) * 100.0
                    sp        = float(parts[5])
                    step      = int(parts[6])
                    state     = int(parts[7])
                except (ValueError,):
                    has_extended = False
            if not has_extended and len(self._actual_t) == 0:
                self._log_event("⚠ Firmware sending legacy PLOT format — "
                              "predicted/heater/setpoint unavailable")

            self._actual_t.append(elapsed)
            self._actual_T.append(temp)
            self._predicted_T.append(predicted)
            self._heater_out.append(heater)
            self._setpoint_T.append(sp)

            if self._act_line is None and self._steps:
                self._build_plot()

            if self._act_line is not None:
                self._act_line.set_data(self._actual_t, self._actual_T)
            if self._pred_line is not None:
                self._pred_line.set_data(self._actual_t, self._predicted_T)
            if self._sp_line is not None:
                self._sp_line.set_data(self._actual_t, self._setpoint_T)
            if self._htr_line is not None:
                self._htr_line.set_data(self._actual_t, self._heater_out)

            if self._ax_temp is not None:
                self._ax_temp.set_title(
                    f"Annealer Profile  —  {elapsed:.1f} min elapsed"
                    f"   T = {temp:.1f}°C",
                    color=COLORS["fg"], fontsize=12, fontweight="bold"
                )
            self._status_label.setText(
                f"Recording: {elapsed:.1f} min, {temp:.1f}°C, "
                f"heater {heater:.0f}%"
            )

            self._update_info(elapsed, temp, predicted, heater, sp, step, state)

            if step != self._last_step:
                self._log_event(f"Entered step {step}/{len(self._steps)}")
                self._last_step = step
            if state != self._last_state:
                self._log_event(f"State → {self._state_name(state)}")
                self._last_state = state

            self._throttled_draw()

        elif tag == "PROFILE_DONE":
            try:
                elapsed = float(parts[1]) if len(parts) > 1 else 0.0
            except ValueError:
                elapsed = 0.0
            self._profile_done = True
            self._profile_active = False
            self._log_event(f"Profile complete — {elapsed:.1f} min total, "
                          f"peak {self._peak_temp:.1f}°C")
            self._status_label.setText(f"Profile Complete ({elapsed:.1f} min)")
            self._ax_temp.set_title(
                f"Annealer Profile  —  Complete  ({elapsed:.1f} min)",
                color=C_DONE, fontsize=12, fontweight="bold"
            )
            self._canvas.draw_idle()
            self._auto_save_png()

    def _throttled_draw(self):
        now = time.monotonic()
        if (now - self._last_draw_time) * 1000 >= self._DRAW_THROTTLE_MS:
            self._canvas.draw_idle()
            self._last_draw_time = now

    def _auto_save_png(self):
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"profile_{ts}.png"
        try:
            self._fig.savefig(fname, dpi=150, facecolor=self._fig.get_facecolor())
        except Exception:
            pass

    def reset(self):
        self._expected_steps = 0
        self._steps.clear()
        self._start_temp = 25.0
        self._actual_t.clear()
        self._actual_T.clear()
        self._predicted_T.clear()
        self._heater_out.clear()
        self._setpoint_T.clear()
        self._plan_line = None
        self._act_line = None
        self._pred_line = None
        self._sp_line = None
        self._htr_line = None
        self._profile_active = False
        self._profile_done = False
        self._last_draw_time = 0.0
        self._last_step = 0
        self._last_state = 0
        self._peak_temp = 0.0
        self._peak_heater = 0.0
        self._event_log.clear()
        self._status_label.setText("Waiting for profile…")
        self._setup_empty_axes()
