"""
tune_view.py — Real-time auto-tuner visualiser.

Parses telemetry and [TUNE] event lines to show the full auto-tune process:
  - Temperature & predicted temperature vs time
  - Heater output vs time
  - State machine timeline (S1 stabilise → S2 dead-time → S3 slope)
  - Identified plant parameters and SIMC results once complete

Also has a "Visualize Tuning" button that sends PLANT and renders the
post-tune parameter summary (step/impulse responses + identified values).
"""

import re
import time

import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QWidget,
)
from PySide6.QtCore import Qt, QTimer

from annealer_diag.base_view import BaseDiagnosticView
from annealer_diag.theme import COLORS

# ── Telemetry regex (shared with learn_view) ──────────────────────────────────
RE_TELEMETRY = re.compile(
    r"Temp:\s*(?P<temp>[\d.]+)\s*C\s*"
    r"\(Pred:\s*(?P<pred>[\d.]+)\)\s*"
    r"\|\s*SP:\s*(?P<sp>[\d.]+)"
    r"(?:\s*->\s*(?P<sp_final>[\d.]+)"
    r"(?:\s*\(\s*(?P<ramp_rate>[\d.]+)\s*C/min\))?)?"
    r"\s*\|\s*True RMS Out:\s*(?P<out>[\d.]+)\s*%"
    r"(?:\s*\|\s*Mode:\s*(?P<mode>.+))?"
)

RE_TUNE_MODE = re.compile(
    r"Mode:\s*TUNING\s*\(State\s*(?P<state>\d+)\)"
    r"\s*\|\s*Tmr:\s*(?P<timer>[\d.]+)\s*s"
)

# ── Event regexes ─────────────────────────────────────────────────────────────
RE_TUNE_START     = re.compile(r"Starting Auto-Tune\.")
RE_TUNE_STEADY    = re.compile(r"\[TUNE\]\s*Steady state confirmed")
RE_TUNE_THETA     = re.compile(r"\[TUNE\]\s*Dead Time \(theta\) found:\s*([\d.]+)")
RE_TUNE_SLOPE_OBS = re.compile(r"\[TUNE\]\s*Observing maximum slope")
RE_TUNE_SLOPE_DONE = re.compile(r"\[TUNE\]\s*Slope measurement complete")
RE_TUNE_COMPLETE  = re.compile(r"--- Tuning Complete ---")


STATE_COLORS = {
    0: "#64748b",   # idle
    1: "#f59e0b",   # stabilising
    2: "#ef4444",   # finding theta (step applied)
    3: "#22d3ee",   # slope observation
}
STATE_LABELS = {
    0: "IDLE",
    1: "STABILISE (60 s)",
    2: "STEP → FIND θ",
    3: "SLOPE OBS (60 s)",
}

EVENT_COLORS = {
    "START":      "#f59e0b",
    "STEADY":     "#22d3ee",
    "THETA":      "#c084fc",
    "SLOPE_OBS":  "#38bdf8",
    "SLOPE_DONE": "#4ade80",
    "COMPLETE":   "#facc15",
}


def _aggregate_state_runs(states, t_min):
    if len(states) < 2:
        return []
    runs = []
    run_start = t_min[0]
    run_state = states[0]
    for i in range(1, len(states)):
        if states[i] != run_state:
            runs.append((run_start, t_min[i], run_state))
            run_start = t_min[i]
            run_state = states[i]
    runs.append((run_start, t_min[-1], run_state))
    return runs


class TuneData:
    def __init__(self):
        self.timestamps:  list[float] = []
        self.temps:       list[float] = []
        self.preds:       list[float] = []
        self.outputs:     list[float] = []
        self.states:      list[int]   = []
        self.timers:      list[float] = []

        self.events: list[tuple[float, str, str]] = []

        self.start_time: float | None = None
        self.current_state: int = 0
        self.current_timer: float = 0.0
        self.tune_complete: bool = False

        self.start_temp: float | None = None
        self.theta_found: float | None = None
        self.temp_at_theta: float | None = None
        self.step_applied_time: float | None = None


    def wall_t(self) -> float:
        if self.start_time is None:
            return 0.0
        return time.monotonic() - self.start_time


class TuneView(BaseDiagnosticView):
    VIEW_NAME = "Tune"
    ACTIVATION_PATTERNS = [
        r"Starting Auto-Tune\.",
        r"\[TUNE\]",
    ]

    _REDRAW_INTERVAL_MS = 500

    def __init__(self, serial_manager, parent=None):
        super().__init__(serial_manager, parent)

        self._data = TuneData()
        self._redraw_pending = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(2)

        # ── Button bar ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_tune = QPushButton("Autotune")
        self._btn_tune.setToolTip("Start autotuner — heater will be driven automatically (TUNE)")
        self._btn_tune.clicked.connect(self._on_autotune_clicked)
        btn_row.addWidget(self._btn_tune)

        btn_row.addStretch()

        self._status_label = QLabel("Waiting for TUNE…")
        self._status_label.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 11px; padding: 2px 4px;"
        )
        btn_row.addWidget(self._status_label)

        layout.addLayout(btn_row)

        # ── Figure ────────────────────────────────────────────────────────────
        self._fig = Figure(facecolor=COLORS["bg_dark"])
        gs = GridSpec(2, 2, figure=self._fig,
                      hspace=0.45, wspace=0.30,
                      left=0.06, right=0.96, top=0.95, bottom=0.09)

        self._ax_temp    = self._fig.add_subplot(gs[0, :])
        self._ax_output  = self._fig.add_subplot(gs[1, 0])
        self._ax_state   = self._fig.add_subplot(gs[1, 1])

        self._all_axes = [
            self._ax_temp, self._ax_output,
            self._ax_state,
        ]

        self._line_temp, = self._ax_temp.plot([], [], color="#38bdf8", linewidth=1.0, label="Actual")
        self._line_pred, = self._ax_temp.plot([], [], color="#818cf8", linewidth=0.6, alpha=0.5, label="Predicted")
        self._line_out,  = self._ax_output.plot([], [], color="#ef4444", linewidth=0.7)
        self._fill_out   = None

        # Annotation lines on temp panel
        self._annot_lines = []

        self._init_static_axes()

        self._canvas = FigureCanvasQTAgg(self._fig)

        # ── Event log (right side) ────────────────────────────────────────────
        self._event_list_label = QLabel("Tune Events")
        self._event_list_label.setStyleSheet(
            f"color: {COLORS['fg']}; font-size: 11px; font-weight: bold;"
            f" padding: 4px 4px 2px 4px;"
        )

        self._event_list = QListWidget()
        self._event_list.setUniformItemSizes(True)
        self._event_list.setFont(QFont("Consolas", 9))
        self._event_list.setStyleSheet(
            f"QListWidget {{"
            f"  background-color: {COLORS['bg_medium']};"
            f"  color: {COLORS['fg']};"
            f"  border: 1px solid {COLORS['border']};"
            f"  border-radius: 4px;"
            f"  padding: 2px;"
            f"}}"
            f"QListWidget::item {{ padding: 1px 4px; }}"
        )
        self._event_list.verticalScrollBar().valueChanged.connect(
            self._on_event_scroll
        )
        self._event_autoscroll = True

        events_panel = QWidget()
        events_layout = QVBoxLayout(events_panel)
        events_layout.setContentsMargins(4, 0, 0, 0)
        events_layout.setSpacing(0)
        events_layout.addWidget(self._event_list_label)
        events_layout.addWidget(self._event_list, stretch=1)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(4)
        body_row.addWidget(self._canvas, stretch=4)
        body_row.addWidget(events_panel, stretch=1)
        layout.addLayout(body_row, stretch=1)

        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        layout.addWidget(self._toolbar)

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_autotune_clicked(self):
        if not self._serial_manager.is_connected():
            return
        reply = QMessageBox.warning(
            self,
            "Start Autotune",
            "Start auto-tuning?\n\n"
            "This will override the tuned parameters. Make sure the oven "
            "is cool at room temperature and the room temperature is stabilized.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._data = TuneData()
            self._serial_manager.send_command("TUNE")

    # ── Axis styling ──────────────────────────────────────────────────────────

    def _style_ax(self, ax):
        ax.set_facecolor(COLORS["bg_medium"])
        ax.tick_params(colors=COLORS["fg"], labelcolor=COLORS["fg"], labelsize=7)
        ax.xaxis.label.set_color(COLORS["fg"])
        ax.yaxis.label.set_color(COLORS["fg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])

    def _init_static_axes(self):
        ax = self._ax_temp
        self._style_ax(ax)
        ax.set_title("Temperature", fontsize=9, color=COLORS["fg"], pad=4)
        ax.set_ylabel("°C", fontsize=8)
        ax.legend(loc="upper left", fontsize=6, facecolor=COLORS["bg_light"],
                  edgecolor=COLORS["border"], labelcolor=COLORS["fg"])
        ax.grid(True, alpha=0.15, color="white")

        ax = self._ax_output
        self._style_ax(ax)
        ax.set_title("Heater Output", fontsize=9, color=COLORS["fg"], pad=4)
        ax.set_ylabel("Output %", fontsize=8)
        ax.set_ylim(-2, 105)
        ax.grid(True, alpha=0.15, color="white")

        self._style_ax(self._ax_state)
        self._ax_state.set_title("Tuner State", fontsize=9, color=COLORS["fg"], pad=4)

    # ── Serial parsing ────────────────────────────────────────────────────────

    def on_serial_line(self, line: str):
        d = self._data

        # ── Tune events ───────────────────────────────────────────────────
        if RE_TUNE_START.search(line):
            if d.start_time is None:
                d.start_time = time.monotonic()
            d.current_state = 1
            d.tune_complete = False
            d.events.append((d.wall_t(), "START", "Auto-tune initiated — stabilising 60 s"))
            self._status_label.setText("Autotuning — waiting 60 s for stable baseline…")
            self._schedule_redraw()
            return

        if RE_TUNE_STEADY.search(line):
            d.current_state = 2
            if d.timestamps:
                d.start_temp = d.temps[-1]
                d.step_applied_time = d.wall_t()
            d.events.append((d.wall_t(), "STEADY", f"Baseline stable at {d.start_temp or 0:.1f}°C — step applied"))
            self._status_label.setText("Step applied — finding dead time θ…")
            self._schedule_redraw()
            return

        m = RE_TUNE_THETA.search(line)
        if m:
            d.theta_found = float(m.group(1))
            d.current_state = 3
            if d.timestamps:
                d.temp_at_theta = d.temps[-1]
            d.events.append((d.wall_t(), "THETA", f"θ = {d.theta_found:.2f} s"))
            self._status_label.setText(f"θ = {d.theta_found:.2f} s found — observing slope 60 s…")
            self._schedule_redraw()
            return

        if RE_TUNE_SLOPE_OBS.search(line):
            d.events.append((d.wall_t(), "SLOPE_OBS", "Max slope observation started"))
            self._schedule_redraw()
            return

        if RE_TUNE_SLOPE_DONE.search(line):
            d.events.append((d.wall_t(), "SLOPE_DONE", "Slope measured — calculating SIMC"))
            self._schedule_redraw()
            return

        if RE_TUNE_COMPLETE.search(line):
            d.tune_complete = True
            d.current_state = 0
            d.events.append((d.wall_t(), "COMPLETE", "Tuning complete"))
            self._status_label.setText("Tuning complete — parameters saved")
            self._schedule_redraw()
            return

        # ── Telemetry ─────────────────────────────────────────────────────
        m = RE_TELEMETRY.match(line)
        if m:
            mode_str = m.group("mode") or ""
            if d.start_time is None and "TUNING" in mode_str:
                d.start_time = time.monotonic()

            if d.start_time is not None:
                t = d.wall_t()
                d.timestamps.append(t)
                d.temps.append(float(m.group("temp")))
                d.preds.append(float(m.group("pred")))
                d.outputs.append(float(m.group("out")))

                tm = RE_TUNE_MODE.search(mode_str)
                if tm:
                    st = int(tm.group("state"))
                    tmr = float(tm.group("timer"))
                    d.states.append(st)
                    d.timers.append(tmr)
                    d.current_state = st
                    d.current_timer = tmr
                else:
                    d.states.append(d.current_state)
                    d.timers.append(d.current_timer)

                self._schedule_redraw()

    def _on_event_scroll(self, value: int):
        bar = self._event_list.verticalScrollBar()
        self._event_autoscroll = (value == bar.maximum())

    # ── Redraw ────────────────────────────────────────────────────────────────

    def _schedule_redraw(self):
        if not self._redraw_pending:
            self._redraw_pending = True
            QTimer.singleShot(self._REDRAW_INTERVAL_MS, self._do_redraw)

    def _do_redraw(self):
        self._redraw_pending = False
        d = self._data

        # ── Temperature panel ─────────────────────────────────────────────
        if d.timestamps:
            t_s = np.array(d.timestamps)
            temps = np.array(d.temps)
            preds = np.array(d.preds)
            outs = np.array(d.outputs)
            states = np.array(d.states) if d.states else np.zeros(len(t_s), dtype=int)

            self._line_temp.set_data(t_s, temps)
            self._line_pred.set_data(t_s, preds)

            ax = self._ax_temp
            x_lo = t_s[0] - 1
            x_hi = t_s[-1] + 2
            ax.set_xlim(x_lo, x_hi)
            lo = min(temps.min(), preds.min()) - 2
            hi = max(temps.max(), preds.max()) + 2
            ax.set_ylim(lo, hi)

            for ln in self._annot_lines:
                ln.remove()
            self._annot_lines = []

            if d.start_temp is not None:
                ln = ax.axhline(d.start_temp, color="#f59e0b", linewidth=0.7,
                                linestyle=":", alpha=0.6)
                self._annot_lines.append(ln)

            if d.step_applied_time is not None:
                ln = ax.axvline(d.step_applied_time, color="#ef4444", linewidth=0.8,
                                linestyle="--", alpha=0.6)
                self._annot_lines.append(ln)

            if d.theta_found is not None and d.step_applied_time is not None:
                theta_abs = d.step_applied_time + d.theta_found
                ln = ax.axvline(theta_abs, color="#c084fc", linewidth=0.8,
                                linestyle="--", alpha=0.7)
                self._annot_lines.append(ln)
                if d.temp_at_theta is not None:
                    ln = ax.axhline(d.temp_at_theta, color="#c084fc", linewidth=0.5,
                                    linestyle=":", alpha=0.4)
                    self._annot_lines.append(ln)

            state_label = STATE_LABELS.get(d.current_state, "?")
            title = f"Temperature — State {d.current_state}: {state_label}"
            if d.current_state > 0:
                title += f"  [{d.current_timer:.0f} s]"
            if d.tune_complete:
                title = "Temperature — TUNE COMPLETE"
            ax.set_title(title, fontsize=9, color=COLORS["fg"], pad=4)
            ax.set_xlabel("Time (s)", fontsize=8)

            # ── Output panel ──────────────────────────────────────────────
            self._line_out.set_data(t_s, outs)
            if self._fill_out is not None:
                self._fill_out.remove()
            self._fill_out = self._ax_output.fill_between(
                t_s, outs, color="#ef4444", alpha=0.3
            )
            self._ax_output.set_xlim(t_s[0] - 1, t_s[-1] + 2)
            self._ax_output.set_ylim(-2, max(105, outs.max() + 5))
            self._ax_output.set_xlabel("Time (s)", fontsize=8)

            # ── State panel ───────────────────────────────────────────────
            ax = self._ax_state
            ax.clear()
            self._style_ax(ax)

            runs = _aggregate_state_runs(list(d.states), t_s.tolist()) if len(d.states) >= 2 else []
            for (t0, t1, s) in runs:
                ax.barh(0, t1 - t0, left=t0, height=0.6,
                        color=STATE_COLORS.get(s, "#64748b"), edgecolor="none")

            status_text = f"S{d.current_state}: {STATE_LABELS.get(d.current_state, '?')}"
            if d.current_state > 0:
                status_text += f"  [{d.current_timer:.0f} s]"
            if d.tune_complete:
                status_text = "TUNE COMPLETE"

            ax.text(0.5, 0.85, status_text, transform=ax.transAxes,
                    ha="center", va="center", fontsize=8, color="white", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor=STATE_COLORS.get(d.current_state, "#64748b"), alpha=0.7))

            for i, (s, label) in enumerate(STATE_LABELS.items()):
                ax.text(0.02 + i * 0.24, 0.15, f"S{s}: {label}",
                        transform=ax.transAxes, fontsize=5, color=STATE_COLORS[s], va="center")

            ax.set_title("Tuner State", fontsize=9, color="white", pad=4)
            ax.set_xlabel("Time (s)", fontsize=8)
            ax.set_yticks([])
            ax.set_ylim(-1.2, 1.2)
            ax.grid(True, axis="x", alpha=0.15, color="white")

        # ── Event log ─────────────────────────────────────────────────────
        self._event_list.clear()
        for et, etype, detail in d.events:
            color = EVENT_COLORS.get(etype, COLORS["fg_dim"])
            text = f"{et:6.1f}s  {etype:<12s}  {detail}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            self._event_list.addItem(item)

        if self._event_autoscroll:
            self._event_list.scrollToBottom()

        self._canvas.draw_idle()

    def reset(self):
        self._data = TuneData()
        self._redraw_pending = False

        for line in (self._line_temp, self._line_pred, self._line_out):
            line.set_data([], [])
        if self._fill_out is not None:
            self._fill_out.remove()
            self._fill_out = None
        for ln in self._annot_lines:
            ln.remove()
        self._annot_lines = []

        self._ax_state.clear()
        self._style_ax(self._ax_state)
        self._ax_state.set_title("Tuner State", fontsize=9, color="white", pad=4)

        self._event_list.clear()
        self._canvas.draw_idle()
        self._status_label.setText("Waiting for TUNE…")
