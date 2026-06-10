"""
learn_view.py — Real-time LEARN / NCR-sweep visualiser as a diagnostic view.

Uses incremental line artist updates for time-series panels (temp, output)
and only rebuilds the lightweight panels (state, NCR bars, event log).

Supports dual NCR sweep: heat-up (S2/S3) then cool-down (S4/S5) with
separate bar groups for heating and cooling NCR.
"""

import re
import time
from collections import defaultdict

import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QWidget,
)
from PySide6.QtCore import Qt, QTimer

from annealer_diag.base_view import BaseDiagnosticView
from annealer_diag.theme import COLORS

NCR_LUT_SIZE = 37
BUCKET_WIDTH = 5
BUCKET_BASE  = 20

STATE_COLORS = {
    0: "#64748b", 1: "#f59e0b", 2: "#ef4444", 3: "#22d3ee",
    4: "#c084fc", 5: "#38bdf8",
}
STATE_LABELS = {
    0: "IDLE", 1: "WAIT STABLE", 2: "HEATING", 3: "OBS HEAT",
    4: "HEAT TO MAX", 5: "OBS COOL",
}
EVENT_COLORS = {
    "START":       "#f59e0b",
    "STABLE":      "#22d3ee",
    "ADVANCE":     "#a78bfa",
    "REACHED":     "#f472b6",
    "CONVERGED_H": "#4ade80",
    "CONVERGED_C": "#38bdf8",
    "EXTENDING":   "#fb923c",
    "SAVED":       "#34d399",
    "HEAT_DONE":   "#c084fc",
    "SETTLED":     "#c084fc",
    "COOL_ADV":    "#818cf8",
    "COMPLETE":    "#facc15",
}

RE_TELEMETRY = re.compile(
    r"Temp:\s*(?P<temp>[\d.]+)\s*C\s*"
    r"\(Pred:\s*(?P<pred>[\d.]+)\)\s*"
    r"\|\s*SP:\s*(?P<sp>[\d.]+)"
    r"(?:\s*->\s*(?P<sp_final>[\d.]+)"
    r"(?:\s*\(\s*(?P<ramp_rate>[\d.]+)\s*C/min\))?)?"
    r"\s*\|\s*True RMS Out:\s*(?P<out>[\d.]+)\s*%"
    r"(?:\s*\|\s*Mode:\s*(?P<mode>.+))?"
)

RE_LEARN_MODE = re.compile(
    r"Mode:\s*LEARN\s+S(?P<state>\d+)\s+Bkt(?P<bucket>\d+)"
    r"\(~(?P<approx_temp>\d+)C\)"
    r"(?:\s+obs\s+(?P<obs_elapsed>[\d.]+)/(?P<obs_required>[\d.]+)s)?"
)

RE_LEARN_STABLE = re.compile(
    r"\[LEARN\]\s*Stable at\s*(?P<room>[\d.]+)C\.\s*Starting heat-up sweep at bucket\s*(?P<bucket>\d+)"
)
RE_LEARN_BUCKET_ADVANCE = re.compile(
    r"\[LEARN\]\s*-->\s*Bucket\s*(?P<bucket>\d+)\s*\(~(?P<temp>\d+)C\)\.\s*Heating to\s*(?P<sp>[\d.]+)C"
)
RE_LEARN_HEAT_REACHED = re.compile(
    r"\[LEARN\]\s*Heat bucket\s*(?P<bucket>\d+)\s*\(~(?P<temp>\d+)C\)\s*reached\.\s*Heater OFF"
)
RE_LEARN_HEAT_CONVERGED = re.compile(
    r"\[LEARN\]\s*Heat bucket\s*(?P<bucket>\d+)\s*converged[^:]*:\s*(?P<ncr>[\d.]+)\s*C/s"
)
RE_LEARN_COOL_CONVERGED = re.compile(
    r"\[LEARN\]\s*Cool bucket\s*(?P<bucket>\d+)\s*converged[^:]*:\s*(?P<ncr>[\d.]+)\s*C/s"
)
RE_LEARN_EXTENDING = re.compile(
    r"\[LEARN\]\s*(?:Heat|Cool) bucket\s*(?P<bucket>\d+)\s*slope drift\s*(?P<drift>[\d.]+)%"
)
RE_LEARN_HEAT_DONE = re.compile(r"\[LEARN\]\s*\*\*\*\s*Heating sweep complete")
RE_LEARN_SETTLED_200 = re.compile(r"\[LEARN\]\s*Settled at 200C")
RE_LEARN_COOL_ADVANCE = re.compile(
    r"\[LEARN\]\s*-->\s*Cool bucket\s*(?P<bucket>\d+)\s*\(~(?P<temp>\d+)C\)"
)
RE_LEARN_COMPLETE = re.compile(r"\[LEARN\]\s*\*\*\*\s*Full sweep complete")
RE_LEARN_START    = re.compile(r"\[LEARN\]\s*Starting dual NCR sweep")
RE_LEARN_WAITING  = re.compile(r"\[LEARN\]\s*Waiting 60s for room-temp stability")

RE_LEARN_FIT = re.compile(
    r"\[LEARN\]\s*Fit:\s*(?P<slope>[-\d.]+)\s+(?P<temp>[\d.]+)\s+Bkt(?P<bucket>\d+)"
)

RE_NCR_SAVED = re.compile(
    r"\[NCR\]\s*Saved (?:cool )?bucket\s*(?P<bucket>\d+)\s*\(~(?P<temp>\d+)C\):\s*(?P<ncr>[\d.]+)\s*C/s"
)


class LearnData:
    def __init__(self):
        self.timestamps:   list = []
        self.temps:        list = []
        self.preds:        list = []
        self.setpoints:    list = []
        self.outputs:      list = []
        self.learn_states: list = []
        self.learn_buckets: list = []

        self.obs_elapsed:  float = 0.0
        self.obs_required: float = 30.0

        self.converged_ncr_heat: dict = {}
        self.converged_ncr_cool: dict = {}
        self.bucket_events:  list = []

        # Fitted slope lines: (wall_t, temp, slope_C_per_s)
        self.current_fit:  object = None   # yellow line (latest)
        self.saved_fits:   list   = []     # green lines (permanent)

        self.room_temp:      object = None
        self.start_time:     object = None
        self.sweep_complete: bool   = False
        self.current_state:  int    = 0
        self.current_bucket: int    = 0

        self.bucket_extensions:   defaultdict = defaultdict(int)
        self.bucket_drift_history: defaultdict = defaultdict(list)

    def wall_t(self) -> float:
        if self.start_time is None:
            return 0.0
        return time.monotonic() - self.start_time


def _aggregate_state_runs(states, t_min):
    """Collapse per-sample states into (start, end, state) runs for efficient barh."""
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


class LearnView(BaseDiagnosticView):
    VIEW_NAME = "Learn"
    ACTIVATION_PATTERNS = [
        r"\[LEARN\]\s*Starting dual NCR sweep",
        r"\[LEARN\]\s*Waiting",
    ]

    _REDRAW_INTERVAL_MS = 1000

    def __init__(self, serial_manager, parent=None):
        super().__init__(serial_manager, parent)

        self._data = LearnData()
        self._redraw_pending = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(2)

        # ── Button bar ─────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_learn = QPushButton("Learn NCR")
        self._btn_learn.setToolTip("Start dual NCR sweep: heat-up then cool-down (LEARN)")
        self._btn_learn.clicked.connect(lambda: self._send("LEARN"))
        btn_row.addWidget(self._btn_learn)

        self._btn_plant = QPushButton("Show Plant")
        self._btn_plant.setToolTip("Print plant model and NCR tables (PLANT)")
        self._btn_plant.clicked.connect(lambda: self._send("PLANT"))
        btn_row.addWidget(self._btn_plant)

        btn_row.addStretch()

        self._status_label = QLabel("Waiting for LEARN data…")
        self._status_label.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 11px; padding: 2px 4px;"
        )
        btn_row.addWidget(self._status_label)

        layout.addLayout(btn_row)

        # ── Figure + side event log ────────────────────────────────────────────
        self._fig = Figure(facecolor=COLORS["bg_dark"])

        gs = GridSpec(3, 2, figure=self._fig,
                      hspace=0.55, wspace=0.30,
                      left=0.06, right=0.96, top=0.95, bottom=0.07)

        self._ax_temp   = self._fig.add_subplot(gs[0, :])
        self._ax_output = self._fig.add_subplot(gs[1, 0])
        self._ax_state  = self._fig.add_subplot(gs[1, 1])
        self._ax_ncr    = self._fig.add_subplot(gs[2, :])

        self._all_axes = [
            self._ax_temp, self._ax_output,
            self._ax_state, self._ax_ncr,
        ]

        self._line_temp, = self._ax_temp.plot([], [], color="#38bdf8", linewidth=1.0, label="Actual")
        self._line_pred, = self._ax_temp.plot([], [], color="#818cf8", linewidth=0.6, alpha=0.5, label="Predicted")
        self._line_sp,   = self._ax_temp.plot([], [], color="#f87171", linewidth=0.8, linestyle="--", label="Setpoint")
        self._line_out,  = self._ax_output.plot([], [], color="#ef4444", linewidth=0.7)
        self._fill_out   = None
        self._fit_lines  = []  # transient slope-line artists on temp panel

        self._init_static_axes()

        self._canvas = FigureCanvasQTAgg(self._fig)

        self._event_list_label = QLabel("Event Log")
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

    def _send(self, cmd: str):
        if self._serial_manager.is_connected():
            self._serial_manager.send_command(cmd)

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
        ax.set_title("Temperature & Setpoint", fontsize=9, color=COLORS["fg"], pad=4)
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

        for ax, title in (
            (self._ax_state,  "State Machine"),
            (self._ax_ncr,    f"Learned NCR (0/{NCR_LUT_SIZE})"),
        ):
            self._style_ax(ax)
            ax.set_title(title, fontsize=9, color=COLORS["fg"], pad=4)

    # ── Serial parsing ─────────────────────────────────────────────────────────

    def on_serial_line(self, line: str):
        d = self._data

        if RE_LEARN_START.search(line) or RE_LEARN_WAITING.search(line):
            if d.start_time is None:
                d.start_time = time.monotonic()
            d.sweep_complete = False
            d.current_state = 1
            d.bucket_events.append((d.wall_t(), -1, "START", "Dual NCR sweep initiated"))
            self._status_label.setText("LEARN sweep initiated — waiting for stable room temp…")
            self._schedule_redraw()
            return

        m = RE_LEARN_STABLE.search(line)
        if m:
            d.room_temp = float(m.group("room"))
            b = int(m.group("bucket"))
            d.current_bucket = b
            d.current_state = 2
            d.bucket_events.append((d.wall_t(), b, "STABLE", f"Room={d.room_temp:.1f}C, first bucket={b}"))
            self._status_label.setText(f"Stable at {d.room_temp:.1f}°C — starting at bucket {b}")
            self._schedule_redraw()
            return

        m = RE_LEARN_BUCKET_ADVANCE.search(line)
        if m:
            b = int(m.group("bucket"))
            d.current_bucket = b
            d.current_state = 2
            d.bucket_events.append((d.wall_t(), b, "ADVANCE", f"Heating to {m.group('sp')}C"))
            self._status_label.setText(f"Bucket {b} (~{BUCKET_BASE + b * BUCKET_WIDTH}°C) — heating…")
            self._schedule_redraw()
            return

        m = RE_LEARN_HEAT_REACHED.search(line)
        if m:
            b = int(m.group("bucket"))
            d.current_state = 3
            d.bucket_events.append((d.wall_t(), b, "REACHED", "Heater OFF, observing heat NCR"))
            self._schedule_redraw()
            return

        m = RE_LEARN_FIT.search(line)
        if m:
            slope = float(m.group("slope"))
            temp  = float(m.group("temp"))
            d.current_fit = (d.wall_t(), temp, slope)
            self._schedule_redraw()
            return

        m = RE_LEARN_HEAT_CONVERGED.search(line)
        if m:
            b   = int(m.group("bucket"))
            ncr = float(m.group("ncr"))
            d.converged_ncr_heat[b] = ncr
            if d.current_fit is not None:
                d.saved_fits.append(d.current_fit)
                d.current_fit = None
            d.bucket_events.append((d.wall_t(), b, "CONVERGED_H", f"Heat NCR={ncr:.6f} C/s"))
            self._schedule_redraw()
            return

        m = RE_LEARN_COOL_CONVERGED.search(line)
        if m:
            b   = int(m.group("bucket"))
            ncr = float(m.group("ncr"))
            d.converged_ncr_cool[b] = ncr
            if d.current_fit is not None:
                d.saved_fits.append(d.current_fit)
                d.current_fit = None
            d.bucket_events.append((d.wall_t(), b, "CONVERGED_C", f"Cool NCR={ncr:.6f} C/s"))
            self._schedule_redraw()
            return

        m = RE_LEARN_EXTENDING.search(line)
        if m:
            b     = int(m.group("bucket"))
            drift = float(m.group("drift"))
            d.bucket_extensions[b] += 1
            d.bucket_drift_history[b].append((d.wall_t(), drift))
            d.bucket_events.append((d.wall_t(), b, "EXTENDING", f"Drift {drift:.1f}%"))
            self._schedule_redraw()
            return

        m = RE_NCR_SAVED.search(line)
        if m:
            b   = int(m.group("bucket"))
            ncr = float(m.group("ncr"))
            d.bucket_events.append((d.wall_t(), b, "SAVED", f"NCR={ncr:.6f} C/s"))
            self._schedule_redraw()
            return

        if RE_LEARN_HEAT_DONE.search(line):
            d.current_state = 4
            d.bucket_events.append((d.wall_t(), -1, "HEAT_DONE", "Heating sweep done, going to 200C"))
            self._status_label.setText("Heating sweep complete — heating to 200°C for cooldown…")
            self._schedule_redraw()
            return

        if RE_LEARN_SETTLED_200.search(line):
            d.current_state = 5
            d.bucket_events.append((d.wall_t(), -1, "SETTLED", "Settled at 200C, starting cooldown"))
            self._status_label.setText("Settled at 200°C — cooldown NCR sweep…")
            self._schedule_redraw()
            return

        m = RE_LEARN_COOL_ADVANCE.search(line)
        if m:
            b = int(m.group("bucket"))
            d.current_bucket = b
            d.current_state = 5
            d.bucket_events.append((d.wall_t(), b, "COOL_ADV", f"Cool bucket ~{m.group('temp')}C"))
            self._status_label.setText(f"Cool bucket {b} (~{BUCKET_BASE + b * BUCKET_WIDTH}°C) — observing…")
            self._schedule_redraw()
            return

        if RE_LEARN_COMPLETE.search(line):
            d.sweep_complete = True
            d.current_state = 0
            nh = len(d.converged_ncr_heat)
            nc = len(d.converged_ncr_cool)
            d.bucket_events.append((d.wall_t(), -1, "COMPLETE", "Both LUTs learned & linearized"))
            self._status_label.setText(f"Sweep complete — heat:{nh} cool:{nc} buckets")
            self._schedule_redraw()
            return

        m = RE_TELEMETRY.match(line)
        if m:
            mode_str = m.group("mode") or ""
            if d.start_time is None and "LEARN" in mode_str:
                d.start_time = time.monotonic()

            if d.start_time is not None:
                t = d.wall_t()
                d.timestamps.append(t)
                d.temps.append(float(m.group("temp")))
                d.preds.append(float(m.group("pred")))
                d.setpoints.append(float(m.group("sp")))
                d.outputs.append(float(m.group("out")))

                ml = RE_LEARN_MODE.search(mode_str)
                if ml:
                    st  = int(ml.group("state"))
                    bkt = int(ml.group("bucket"))
                    d.learn_states.append(st)
                    d.learn_buckets.append(bkt)
                    d.current_state  = st
                    d.current_bucket = bkt
                    if ml.group("obs_elapsed"):
                        d.obs_elapsed  = float(ml.group("obs_elapsed"))
                        d.obs_required = float(ml.group("obs_required"))
                else:
                    d.learn_states.append(d.current_state)
                    d.learn_buckets.append(d.current_bucket)

                self._schedule_redraw()

    def _on_event_scroll(self, value: int):
        bar = self._event_list.verticalScrollBar()
        self._event_autoscroll = (value == bar.maximum())

    # ── Redraw ─────────────────────────────────────────────────────────────────

    def _schedule_redraw(self):
        if not self._redraw_pending:
            self._redraw_pending = True
            QTimer.singleShot(self._REDRAW_INTERVAL_MS, self._do_redraw)

    def _do_redraw(self):
        self._redraw_pending = False
        d = self._data

        if not d.timestamps:
            return

        t_min = np.array(d.timestamps) / 60.0
        temps = np.array(d.temps)
        preds = np.array(d.preds)
        sps   = np.array(d.setpoints)
        outs  = np.array(d.outputs)
        states  = np.array(d.learn_states)
        conv_heat    = dict(d.converged_ncr_heat)
        conv_cool    = dict(d.converged_ncr_cool)
        events       = list(d.bucket_events)
        obs_elapsed  = d.obs_elapsed
        obs_required = d.obs_required
        cur_state    = d.current_state
        cur_bucket   = d.current_bucket
        sweep_done   = d.sweep_complete
        extensions   = dict(d.bucket_extensions)
        current_fit  = d.current_fit
        saved_fits   = list(d.saved_fits)

        # ── Panel 1: Temperature ──────────────────────────────────────────────
        self._line_temp.set_data(t_min, temps)
        self._line_pred.set_data(t_min, preds)
        self._line_sp.set_data(t_min, sps)

        ax = self._ax_temp
        x_lo = t_min[0] - 0.2
        x_hi = t_min[-1] + 0.5
        ax.set_xlim(x_lo, x_hi)
        lo = min(temps.min(), sps.min()) - 3
        hi = max(temps.max(), sps.max()) + 3
        ax.set_ylim(lo, hi)

        # Remove old fit-line artists
        for ln in self._fit_lines:
            ln.remove()
        self._fit_lines = []

        def _draw_fit(wall_t_sec, ref_temp, slope_c_per_s, color, alpha):
            ref_min = wall_t_sec / 60.0
            slope_per_min = slope_c_per_s * 60.0
            y0 = ref_temp + slope_per_min * (x_lo - ref_min)
            y1 = ref_temp + slope_per_min * (x_hi - ref_min)
            ln, = ax.plot([x_lo, x_hi], [y0, y1],
                          color=color, linewidth=0.8, alpha=alpha, zorder=5)
            self._fit_lines.append(ln)

        for (ft, ftemp, fslope) in saved_fits:
            _draw_fit(ft, ftemp, fslope, "#4ade80", 0.7)

        if current_fit is not None:
            _draw_fit(current_fit[0], current_fit[1], current_fit[2], "#facc15", 0.9)

        # ── Panel 2: Heater Output ───────────────────────────────────────────
        self._line_out.set_data(t_min, outs)
        if self._fill_out is not None:
            self._fill_out.remove()
        self._fill_out = self._ax_output.fill_between(
            t_min, outs, color="#ef4444", alpha=0.3
        )
        self._ax_output.set_xlim(t_min[0] - 0.2, t_min[-1] + 0.5)
        self._ax_output.set_ylim(-2, max(105, outs.max() + 5))

        # ── Panel 3: State Machine ───────────────────────────────────────────
        ax = self._ax_state
        ax.clear()
        self._style_ax(ax)

        runs = _aggregate_state_runs(states, t_min)
        for (t0, t1, s) in runs:
            ax.barh(0, t1 - t0, left=t0, height=0.6,
                    color=STATE_COLORS.get(s, "#64748b"), edgecolor="none")

        status_text = f"State {cur_state}: {STATE_LABELS.get(cur_state, '?')}"
        if cur_state in (3, 5):
            pct = (obs_elapsed / obs_required * 100) if obs_required > 0 else 0
            status_text += f"  [{obs_elapsed:.0f}/{obs_required:.0f}s = {pct:.0f}%]"
        status_text += f"  |  Bucket {cur_bucket} (~{BUCKET_BASE + cur_bucket * BUCKET_WIDTH}C)"
        if sweep_done:
            status_text = "SWEEP COMPLETE"

        ax.text(0.5, 0.85, status_text, transform=ax.transAxes,
                ha="center", va="center", fontsize=8, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor=STATE_COLORS.get(cur_state, "#64748b"), alpha=0.7))

        n_labels = len(STATE_LABELS)
        for i, (s, label) in enumerate(STATE_LABELS.items()):
            ax.text(0.02 + i * (0.96 / n_labels), 0.15, f"S{s}: {label}",
                    transform=ax.transAxes, fontsize=5, color=STATE_COLORS[s], va="center")

        ax.set_title("State Machine", fontsize=9, color="white", pad=4)
        ax.set_xlabel("Time (min)", fontsize=8)
        ax.set_yticks([])
        ax.set_ylim(-1.2, 1.2)
        ax.grid(True, axis="x", alpha=0.15, color="white")

        # ── Panel 4: NCR Bar Chart (dual: heat + cool) ──────────────────────
        ax = self._ax_ncr
        ax.clear()
        self._style_ax(ax)

        all_buckets = sorted(set(conv_heat.keys()) | set(conv_cool.keys()))
        if all_buckets:
            x_positions = np.arange(len(all_buckets))
            bar_width = 0.35
            temp_labels = [f"{BUCKET_BASE + b * BUCKET_WIDTH}" for b in all_buckets]

            heat_vals = [conv_heat.get(b, 0.0) for b in all_buckets]
            cool_vals = [conv_cool.get(b, 0.0) for b in all_buckets]

            heat_colors = ["#facc15" if b == cur_bucket and cur_state in (2, 3)
                           else "#4ade80" for b in all_buckets]
            cool_colors = ["#facc15" if b == cur_bucket and cur_state == 5
                           else "#38bdf8" for b in all_buckets]

            bars_h = ax.bar(x_positions - bar_width / 2, heat_vals, bar_width,
                            color=heat_colors, edgecolor=COLORS["border"],
                            label="Heat-up")
            bars_c = ax.bar(x_positions + bar_width / 2, cool_vals, bar_width,
                            color=cool_colors, edgecolor=COLORS["border"],
                            label="Cool-down")

            for bar, b in zip(bars_h, all_buckets):
                ext = extensions.get(b, 0)
                if ext > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            f"+{ext}", ha="center", va="bottom", fontsize=5, color="#fb923c")

            ax.set_xticks(x_positions)
            ax.set_xticklabels(temp_labels)
            ax.set_ylabel("NCR (C/s)", fontsize=8)
            ax.legend(loc="upper left", fontsize=6, facecolor=COLORS["bg_light"],
                      edgecolor=COLORS["border"], labelcolor=COLORS["fg"])
            ax.tick_params(axis="x", rotation=45, labelsize=6,
                           colors=COLORS["fg"], labelcolor=COLORS["fg"])
        else:
            ax.text(0.5, 0.5, "Waiting for first\nbucket convergence…",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=9, color="#64748b")

        nh = len(conv_heat)
        nc = len(conv_cool)
        ax.set_title(f"Learned NCR (heat:{nh} cool:{nc} / {NCR_LUT_SIZE})",
                     fontsize=9, color="white", pad=4)
        ax.set_xlabel("Temp (°C)", fontsize=8)
        ax.grid(True, axis="y", alpha=0.15, color="white")

        # ── Event Log ────────────────────────────────────────────────────────
        self._event_list.clear()
        for et, bucket, etype, detail in events:
            color = EVENT_COLORS.get(etype, COLORS["fg_dim"])
            minutes = et / 60.0
            bkt_str = f"B{bucket}" if bucket >= 0 else "---"
            text    = f"{minutes:5.1f}m {bkt_str:>4s} {etype:<12s} {detail}"

            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            self._event_list.addItem(item)

        if self._event_autoscroll:
            self._event_list.scrollToBottom()

        self._canvas.draw_idle()

    def reset(self):
        self._data = LearnData()
        self._redraw_pending = False

        for line in (self._line_temp, self._line_pred, self._line_sp, self._line_out):
            line.set_data([], [])
        if self._fill_out is not None:
            self._fill_out.remove()
            self._fill_out = None
        for ln in self._fit_lines:
            ln.remove()
        self._fit_lines = []

        for ax in (self._ax_state, self._ax_ncr):
            ax.clear()
            self._style_ax(ax)

        self._ax_state.set_title("State Machine", fontsize=9, color="white", pad=4)
        self._ax_ncr.set_title(f"Learned NCR (heat:0 cool:0 / {NCR_LUT_SIZE})", fontsize=9, color="white", pad=4)

        self._event_list.clear()

        self._canvas.draw_idle()
        self._status_label.setText("Waiting for LEARN data…")
