"""
plant_view.py — Visualiser for the PLANT serial command output.

Parses plant model parameters, PID gains, and NCR lookup tables,
then renders:
  1. Step response & impulse response of the identified plant model.
  2. Raw NCR values (heating = green dots, cooling = blue dots),
     linearized/curve-fitted values (lighter tones), and the averaged
     curve of the fitted values (purple line).
"""

import re

import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

from annealer_diag.base_view import BaseDiagnosticView
from annealer_diag.theme import COLORS

NCR_LUT_SIZE = 37
BUCKET_WIDTH = 5
BUCKET_BASE = 20

RE_MODEL_TYPE   = re.compile(r"Model:\s*(.+)")
RE_GAIN         = re.compile(r"Gain \([Kk]['\)]?\):\s*([-\d.]+)")
RE_TAU          = re.compile(r"Time Constant \(tau\):\s*([-\d.]+)")
RE_THETA        = re.compile(r"Dead Time \(theta\):\s*([-\d.]+)")
RE_KC           = re.compile(r"Kc:\s*([-\d.]+)")
RE_TI           = re.compile(r"Ti:\s*([-\d.]+)")
RE_LAMBDA       = re.compile(r"Lambda Setting:\s*([-\d.]+)")

RE_NCR_ROW = re.compile(
    r"\s*(\d+)C\s*\|\s*([-\d.]+)\s*\|\s*([-\d.]+)\s*\|\s*(\w+)"
)


class PlantData:
    def __init__(self):
        self.model_type: str = ""
        self.K: float = 0.0
        self.tau: float = 0.0
        self.theta: float = 0.0
        self.Kc: float = 0.0
        self.Ti: float = 0.0
        self.lambda_val: float = 0.0

        self.heat_temps: list[int] = []
        self.heat_raw: list[float] = []
        self.heat_fit: list[float] = []
        self.heat_status: list[str] = []

        self.cool_temps: list[int] = []
        self.cool_raw: list[float] = []
        self.cool_fit: list[float] = []
        self.cool_status: list[str] = []

        self.complete: bool = False


class PlantView(BaseDiagnosticView):
    VIEW_NAME = "Plant"
    ACTIVATION_PATTERNS = [r"--- Plant Data ---"]

    def __init__(self, serial_manager, parent=None):
        super().__init__(serial_manager, parent)

        self._data = PlantData()
        self._section = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_plant = QPushButton("Visualize Plant")
        self._btn_plant.setToolTip("Send PLANT command and visualize the response")
        self._btn_plant.clicked.connect(self._on_visualize)
        btn_row.addWidget(self._btn_plant)

        btn_row.addStretch()

        self._status_label = QLabel("Waiting for PLANT data…")
        self._status_label.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 11px; padding: 2px 4px;"
        )
        btn_row.addWidget(self._status_label)

        layout.addLayout(btn_row)

        self._fig = Figure(facecolor=COLORS["bg_dark"])
        gs = GridSpec(2, 2, figure=self._fig,
                      hspace=0.45, wspace=0.30,
                      left=0.07, right=0.96, top=0.94, bottom=0.08)

        self._ax_step = self._fig.add_subplot(gs[0, 0])
        self._ax_impulse = self._fig.add_subplot(gs[1, 0])
        self._ax_ncr = self._fig.add_subplot(gs[:, 1])

        self._all_axes = [self._ax_step, self._ax_impulse, self._ax_ncr]
        for ax in self._all_axes:
            self._style_ax(ax)

        self._init_empty_axes()

        self._canvas = FigureCanvasQTAgg(self._fig)
        layout.addWidget(self._canvas, stretch=1)

        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        layout.addWidget(self._toolbar)

    def _on_visualize(self):
        if self._serial_manager.is_connected():
            self._data = PlantData()
            self._section = ""
            self._serial_manager.send_command("PLANT")

    def _style_ax(self, ax):
        ax.set_facecolor(COLORS["bg_medium"])
        ax.tick_params(colors=COLORS["fg"], labelcolor=COLORS["fg"], labelsize=7)
        ax.xaxis.label.set_color(COLORS["fg"])
        ax.yaxis.label.set_color(COLORS["fg"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])

    def _init_empty_axes(self):
        for ax, title in (
            (self._ax_step, "Step Response"),
            (self._ax_impulse, "Impulse Response"),
            (self._ax_ncr, "NCR Tables"),
        ):
            ax.set_title(title, fontsize=9, color=COLORS["fg"], pad=4)
            ax.grid(True, alpha=0.15, color="white")
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", fontsize=9, color="#64748b")

    def on_serial_line(self, line: str):
        d = self._data

        if "--- Plant Data ---" in line:
            d = PlantData()
            self._data = d
            self._section = "plant"
            self._status_label.setText("Receiving plant data…")
            return

        if "--- PID Parameters ---" in line:
            self._section = "pid"
            return

        if "--- NCR Heat-Up Table" in line:
            self._section = "heat_header"
            return

        if "--- NCR Cool-Down Table" in line:
            self._section = "cool_header"
            return

        if line.strip().startswith("Temp |"):
            if self._section == "heat_header":
                self._section = "heat"
            elif self._section == "cool_header":
                self._section = "cool"
            return

        if "----------------------" in line and self._section in ("cool", "heat"):
            d.complete = True
            self._section = ""
            self._status_label.setText(
                f"Plant: {d.model_type}  |  K={d.K:.4f}  tau={d.tau:.4f}  "
                f"theta={d.theta:.4f}  |  Kc={d.Kc:.4f}  Ti={d.Ti:.4f}"
            )
            self._redraw()
            return

        if self._section == "plant":
            m = RE_MODEL_TYPE.search(line)
            if m:
                d.model_type = m.group(1).strip()
                return
            m = RE_GAIN.search(line)
            if m:
                d.K = float(m.group(1))
                return
            m = RE_TAU.search(line)
            if m:
                d.tau = float(m.group(1))
                return
            m = RE_THETA.search(line)
            if m:
                d.theta = float(m.group(1))
                return

        if self._section == "pid":
            m = RE_KC.search(line)
            if m:
                d.Kc = float(m.group(1))
                return
            m = RE_TI.search(line)
            if m:
                d.Ti = float(m.group(1))
                return
            m = RE_LAMBDA.search(line)
            if m:
                d.lambda_val = float(m.group(1))
                return

        if self._section == "heat":
            m = RE_NCR_ROW.search(line)
            if m:
                d.heat_temps.append(int(m.group(1)))
                d.heat_raw.append(float(m.group(2)))
                d.heat_fit.append(float(m.group(3)))
                d.heat_status.append(m.group(4))
                return

        if self._section == "cool":
            m = RE_NCR_ROW.search(line)
            if m:
                d.cool_temps.append(int(m.group(1)))
                d.cool_raw.append(float(m.group(2)))
                d.cool_fit.append(float(m.group(3)))
                d.cool_status.append(m.group(4))
                return

    def _redraw(self):
        d = self._data
        if not d.complete:
            return

        self._draw_step_response(d)
        self._draw_impulse_response(d)
        self._draw_ncr(d)
        self._canvas.draw_idle()

    def _draw_step_response(self, d: PlantData):
        ax = self._ax_step
        ax.clear()
        self._style_ax(ax)

        K, tau, theta = d.K, d.tau, d.theta
        is_integrating = (tau == 0.0)

        if is_integrating:
            t_end = max(theta * 5, 30.0)
        else:
            t_end = theta + tau * 6
        t_end = max(t_end, 1.0)

        t = np.linspace(0, t_end, 500)

        if is_integrating:
            y = np.where(t > theta, K * (t - theta), 0.0)
            title = f"Step Response (Integrating, K'={K:.4f}, θ={theta:.2f}s)"
        else:
            y = np.where(t > theta, K * (1.0 - np.exp(-(t - theta) / tau)), 0.0)
            title = f"Step Response (FOPDT, K={K:.4f}, τ={tau:.2f}s, θ={theta:.2f}s)"

        ax.plot(t, y, color="#38bdf8", linewidth=1.5)
        ax.axvline(theta, color="#f59e0b", linewidth=0.8, linestyle="--", alpha=0.7, label=f"θ={theta:.2f}s")
        if not is_integrating:
            ax.axhline(K, color="#f87171", linewidth=0.8, linestyle=":", alpha=0.5, label=f"K={K:.4f}")

        ax.set_title(title, fontsize=8, color=COLORS["fg"], pad=4)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Output", fontsize=8)
        ax.legend(loc="lower right", fontsize=6, facecolor=COLORS["bg_light"],
                  edgecolor=COLORS["border"], labelcolor=COLORS["fg"])
        ax.grid(True, alpha=0.15, color="white")

    def _draw_impulse_response(self, d: PlantData):
        ax = self._ax_impulse
        ax.clear()
        self._style_ax(ax)

        K, tau, theta = d.K, d.tau, d.theta
        is_integrating = (tau == 0.0)

        if is_integrating:
            t_end = max(theta * 5, 30.0)
        else:
            t_end = theta + tau * 6
        t_end = max(t_end, 1.0)

        t = np.linspace(0, t_end, 500)

        if is_integrating:
            y = np.where(t > theta, K, 0.0)
            title = f"Impulse Response (Integrating, K'={K:.4f})"
        else:
            y = np.where(t > theta, (K / tau) * np.exp(-(t - theta) / tau), 0.0)
            title = f"Impulse Response (FOPDT, K/τ={K/tau:.4f})"

        ax.plot(t, y, color="#c084fc", linewidth=1.5)
        ax.axvline(theta, color="#f59e0b", linewidth=0.8, linestyle="--", alpha=0.7, label=f"θ={theta:.2f}s")

        ax.set_title(title, fontsize=8, color=COLORS["fg"], pad=4)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Output", fontsize=8)
        ax.legend(loc="upper right", fontsize=6, facecolor=COLORS["bg_light"],
                  edgecolor=COLORS["border"], labelcolor=COLORS["fg"])
        ax.grid(True, alpha=0.15, color="white")

    def _draw_ncr(self, d: PlantData):
        ax = self._ax_ncr
        ax.clear()
        self._style_ax(ax)

        heat_temps = np.array(d.heat_temps, dtype=float)
        heat_raw = np.array(d.heat_raw)
        heat_fit = np.array(d.heat_fit)
        cool_temps = np.array(d.cool_temps, dtype=float)
        cool_raw = np.array(d.cool_raw)
        cool_fit = np.array(d.cool_fit)

        # Raw NCR: non-zero = dots, zero = cross markers
        heat_nz = heat_raw > 0
        heat_z = ~heat_nz
        cool_nz = cool_raw > 0
        cool_z = ~cool_nz

        ax.scatter(heat_temps[heat_nz], heat_raw[heat_nz], color="#4ade80", s=18, zorder=5,
                   label="Raw Heat", marker="o", alpha=0.9)
        ax.scatter(cool_temps[cool_nz], cool_raw[cool_nz], color="#38bdf8", s=18, zorder=5,
                   label="Raw Cool", marker="o", alpha=0.9)
        if heat_z.any():
            ax.scatter(heat_temps[heat_z], heat_raw[heat_z], color="#4ade80", s=30, zorder=5,
                       marker="x", alpha=0.5, linewidths=1.0)
        if cool_z.any():
            ax.scatter(cool_temps[cool_z], cool_raw[cool_z], color="#38bdf8", s=30, zorder=5,
                       marker="x", alpha=0.5, linewidths=1.0)

        # Linearized / curve-fitted: slightly different tones
        ax.plot(heat_temps, heat_fit, color="#86efac", linewidth=1.2, linestyle="-",
                zorder=4, label="Fit Heat", alpha=0.8)
        ax.plot(cool_temps, cool_fit, color="#7dd3fc", linewidth=1.2, linestyle="-",
                zorder=4, label="Fit Cool", alpha=0.8)

        # Averaged curve of the fitted values (purple line)
        if len(heat_fit) == len(cool_fit) and len(heat_fit) > 0:
            avg_fit = (np.abs(heat_fit) + np.abs(cool_fit)) / 2.0
            ax.plot(heat_temps, avg_fit, color="#c084fc", linewidth=2.0,
                    zorder=6, label="Avg Fit", alpha=0.95)
        elif len(heat_fit) > 0:
            ax.plot(heat_temps, np.abs(heat_fit), color="#c084fc", linewidth=2.0,
                    zorder=6, label="Avg Fit (heat only)", alpha=0.95)

        ax.set_title("NCR Values — Raw, Fitted & Averaged", fontsize=9,
                     color=COLORS["fg"], pad=4)
        ax.set_xlabel("Temperature (°C)", fontsize=8)
        ax.set_ylabel("NCR (°C/s)", fontsize=8)
        ax.legend(loc="upper left", fontsize=6, facecolor=COLORS["bg_light"],
                  edgecolor=COLORS["border"], labelcolor=COLORS["fg"], ncol=3)
        ax.grid(True, alpha=0.15, color="white")

    def reset(self):
        self._data = PlantData()
        self._section = ""
        for ax in self._all_axes:
            ax.clear()
            self._style_ax(ax)
        self._init_empty_axes()
        self._canvas.draw_idle()
        self._status_label.setText("Waiting for PLANT data…")
