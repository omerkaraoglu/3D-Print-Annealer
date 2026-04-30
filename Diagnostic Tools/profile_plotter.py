#!/usr/bin/env python3
"""
annealer_plot.py  —  Real-time profile plotter + serial terminal for the
                     3D Print Annealer firmware.

Three threads:
  Main      — matplotlib event loop, drains the data queue, updates the chart
  reader    — reads serial lines, puts them in the queue
  writer    — blocks on input(), sends typed commands to the device

Usage:
    python annealer_plot.py                   # auto-detect port
    python annealer_plot.py COM5              # Windows
    python annealer_plot.py /dev/ttyUSB0      # Linux / Mac

  NOTE: run from a real terminal (cmd, PowerShell, VS Code terminal).
        IDLE's stdin handling breaks the input thread.

Dependencies:
    pip install pyserial matplotlib numpy
"""

import sys
import time
import queue
import threading
import serial
import serial.tools.list_ports
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


BAUD = 115200

# ── Colour palette (dark theme) ───────────────────────────────────────────────
BG     = "#1e1e2e"
FG     = "#cdd6f4"
GRID   = "#45475a"
C_PLAN = "#89b4fa"   # blue  — planned profile
C_ACT  = "#f38ba8"   # pink  — actual temperature
C_HOLD = "#a6e3a1"   # green — hold-phase shading
C_DONE = "#a6e3a1"   # green — title when complete


# ── Port selection ────────────────────────────────────────────────────────────

def pick_port(hint=None):
    if hint:
        return hint
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        sys.exit("No serial ports found.")
    if len(ports) == 1:
        print(f"Auto-selected {ports[0].device}  ({ports[0].description})")
        return ports[0].device
    print("Available serial ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}]  {p.device}  —  {p.description}")
    idx = int(input("Select port number: "))
    return ports[idx].device


# ── Planned-profile trajectory ────────────────────────────────────────────────

def planned_trajectory(steps, start_temp):
    """
    Returns (time_min, temperature) numpy arrays tracing the ideal profile.
    RAMP steps are sampled densely; SET steps are a vertical jump.
    """
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
            n  = max(2, int(dt * 20))           # ~3-second sample density
            for i in range(1, n + 1):
                t_list.append(now + dt * i / n)
                T_list.append(cur + (tgt - cur) * i / n)
            cur = tgt
        else:
            t_list.append(now)                  # vertical jump for SET
            T_list.append(tgt)
            cur = tgt

        if hold > 0:
            t_list.append(t_list[-1] + hold)
            T_list.append(cur)

    return np.array(t_list), np.array(T_list)


def hold_spans(steps, start_temp):
    """Returns [(t_start, t_end), …] in minutes for every hold phase."""
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


# ── Plot setup ────────────────────────────────────────────────────────────────

def build_plot(steps, start_temp):
    pt, pT    = planned_trajectory(steps, start_temp)
    total_min = pt[-1] if len(pt) else 60.0

    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    for t0, t1 in hold_spans(steps, start_temp):
        ax.axvspan(t0, t1, alpha=0.10, color=C_HOLD, zorder=1)

    ax.plot(pt, pT, color=C_PLAN, linewidth=2.5, label="Planned", zorder=2)

    (aline,) = ax.plot([], [], color=C_ACT, linewidth=1.5,
                       marker="o", markersize=5,
                       label="Actual (30 s samples)", zorder=5)

    y_lo = min(start_temp, min(s["target"] for s in steps)) - 5
    y_hi = max(s["target"] for s in steps) + 10
    ax.set_xlim(-total_min * 0.01, total_min * 1.05)
    ax.set_ylim(y_lo, y_hi)
    ax.set_xlabel("Time  (min)", color=FG, fontsize=11)
    ax.set_ylabel("Temperature  (°C)", color=FG, fontsize=11)
    ax.tick_params(colors=FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.grid(color=GRID, linestyle="--", linewidth=0.5, alpha=0.6)
    ax.legend(facecolor="#313244", edgecolor=GRID, labelcolor=FG, fontsize=10)
    ax.set_title("Annealer — waiting for first data point…",
                 color=FG, fontsize=12, fontweight="bold")

    plt.tight_layout()
    plt.ion()
    plt.show()
    return fig, ax, aline


# ── Background threads ────────────────────────────────────────────────────────

def serial_reader(ser, q, stop):
    """Reads lines from serial and puts them in the queue."""
    while not stop.is_set():
        try:
            raw = ser.readline()
            if raw:
                q.put(raw.decode("utf-8", errors="replace").strip())
        except Exception:
            break


def input_worker(ser, write_lock, stop):
    """Blocks on input() and forwards typed commands to the device."""
    print("\n" + "─" * 60)
    print("  Serial terminal — type commands and press Enter to send")
    print("  Examples:  SET 80   |   RAMP 100 2.0   |   PROFILE: STOP")
    print("─" * 60 + "\n")
    while not stop.is_set():
        try:
            cmd = input("> ")
            if cmd.strip():
                with write_lock:
                    ser.write((cmd.strip() + "\n").encode())
        except (EOFError, OSError):
            break


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    port = pick_port(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"\nOpening {port} at {BAUD} baud.")
    print("Waiting for a PROFILE to start on the device…")

    ser        = serial.Serial(port, BAUD, timeout=0.1)
    data_q     = queue.Queue()
    write_lock = threading.Lock()
    stop       = threading.Event()

    threading.Thread(target=serial_reader,
                     args=(ser, data_q, stop), daemon=True).start()
    threading.Thread(target=input_worker,
                     args=(ser, write_lock, stop), daemon=True).start()

    # ── State ──────────────────────────────────────────────────────────────────
    expected_steps = 0
    steps          = []
    start_temp     = 25.0
    actual_t       = []
    actual_T       = []
    fig            = None
    ax_obj         = None
    aline          = None
    done           = False

    try:
        while not done:
            # ── Drain the incoming data queue ──────────────────────────────────
            while not data_q.empty():
                line = data_q.get()

                if not line.startswith(">>"):
                    print(line)          # regular telemetry → console
                    continue

                parts = line[2:].split()
                if not parts:
                    continue
                tag = parts[0]

                # >>PROFILE_START  count  start_temp
                if tag == "PROFILE_START":
                    expected_steps = int(parts[1])
                    start_temp     = float(parts[2])
                    steps.clear();  actual_t.clear();  actual_T.clear()
                    fig = ax_obj = aline = None
                    print(f"\n▶  Profile starting  |  {expected_steps} steps"
                          f"  |  T₀ = {start_temp:.1f}°C")

                # >>STEP  type  target  rate_min  hold_min
                elif tag == "STEP":
                    stype    = parts[1]
                    target   = float(parts[2])
                    rate_min = float(parts[3])
                    hold_min = float(parts[4])
                    steps.append(dict(type=stype, target=target,
                                      rate_min=rate_min, hold_min=hold_min))
                    rate_str = f"  @  {rate_min:.3f} °C/min" if stype == "RAMP" else ""
                    hold_str = f"  hold {hold_min:.1f} min"  if hold_min   else ""
                    print(f"     {len(steps):2}. {stype:4}  →  {target:6.1f}°C"
                          f"{rate_str}{hold_str}")

                    if len(steps) == expected_steps:
                        print("\n  Building chart…")
                        fig, ax_obj, aline = build_plot(steps, start_temp)

                # >>PLOT  elapsed_min  actual_temp
                elif tag == "PLOT":
                    elapsed = float(parts[1])
                    temp    = float(parts[2])
                    actual_t.append(elapsed)
                    actual_T.append(temp)
                    print(f"  t = {elapsed:7.2f} min   T = {temp:.2f}°C")

                    if fig is None and steps:      # lazy build if needed
                        fig, ax_obj, aline = build_plot(steps, start_temp)

                    if aline is not None:
                        aline.set_data(actual_t, actual_T)
                        ax_obj.set_title(
                            f"Annealer Profile  —  {elapsed:.1f} min elapsed"
                            f"   T = {temp:.1f}°C",
                            color=FG, fontsize=12, fontweight="bold")

                # >>PROFILE_DONE  elapsed_min
                elif tag == "PROFILE_DONE":
                    elapsed = float(parts[1]) if len(parts) > 1 else 0.0
                    print(f"\n✓  Profile complete  ({elapsed:.1f} min total)")
                    if fig:
                        ax_obj.set_title(
                            f"Annealer Profile  —  Complete  ({elapsed:.1f} min)",
                            color=C_DONE, fontsize=12, fontweight="bold")
                        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
                        fname = f"profile_{ts}.png"
                        fig.savefig(fname, dpi=150,
                                    facecolor=fig.get_facecolor())
                        print(f"  Chart saved  →  {fname}")
                    done = True

            # ── Keep the matplotlib window alive ───────────────────────────────
            if plt.get_fignums():
                plt.pause(0.05)
            else:
                time.sleep(0.05)

            # Exit cleanly if the user closes the chart window
            if fig is not None and not plt.fignum_exists(fig.number):
                print("\n  Chart window closed.")
                done = True

    except KeyboardInterrupt:
        print("\n  Interrupted by user.")
    finally:
        stop.set()
        ser.close()
        if fig and plt.fignum_exists(fig.number):
            plt.ioff()
            plt.show()


if __name__ == "__main__":
    main()
