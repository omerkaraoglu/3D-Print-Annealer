"""Charts for the EMC simulation report (matplotlib) -> charts/*.png. Data: estimates.json, validation.json,
sigma_delta_results.json, alternatives_results.json. One axis per chart, fixed series colours, limit lines dashed grey."""
import json, os, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "charts"); os.makedirs(OUT, exist_ok=True)
est = json.load(open(os.path.join(HERE, "estimates.json"), encoding="utf-8"))
val = json.load(open(os.path.join(HERE, "validation.json"), encoding="utf-8"))
sd = json.load(open(os.path.join(HERE, "sigma_delta_results.json"), encoding="utf-8"))
alt = json.load(open(os.path.join(HERE, "alternatives_results.json"), encoding="utf-8"))

C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "violet": "#6250d6",
     "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e4e3df", "good": "#0ca30c", "bad": "#d03b3b", "warn": "#ec835a", "fill": "#fcfcfb"}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": C["ink2"], "axes.labelcolor": C["ink"], "xtick.color": C["ink2"], "ytick.color": C["ink2"],
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "axes.titleweight": "bold", "axes.titlesize": 10.5, "legend.frameon": False, "legend.fontsize": 8, "figure.facecolor": "white", "axes.facecolor": C["fill"]})
def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=170); plt.close(fig); print("chart", name)
def limit_line(ax, y, text, color=C["ink2"], ls="--", xpos=0.99, va="bottom"):
    ax.axhline(y, color=color, ls=ls, lw=1.1, zorder=1)
    ax.text(xpos, y, text, transform=ax.get_yaxis_transform(), ha="right", va=va, fontsize=7.5, color=color)

# ---------------------------------------------------------------- 1. summary: margin to limit per item ----
items = [
    ("Flicker Pst, current firmware (worst duty)", 20 * math.log10(1.0 / 1.70), "fail"),
    ("Flicker Plt, current firmware (worst duty)", 20 * math.log10(0.65 / 1.70), "fail"),
    ("Flicker Pst, 20 s burst frame (worst duty)", 20 * math.log10(1.0 / 0.54), "pass"),
    ("Flicker Plt, 20 s burst frame (worst duty)", 20 * math.log10(0.65 / 0.54), "pass"),
    ("Conducted 150 kHz, filter in heater path (V_on 23 V)", est["conducted_heater_turn_on"]["cases"]["heater behind existing L40 120 uH + C40 1 uF + C1"]["worst_margin_dB"], "pass"),
    ("Conducted 150 kHz, filter in heater path (V_on 40 V)", est["conducted_heater_turn_on"]["cases"]["heater behind L40/C40, V_on 40 V"]["worst_margin_dB"], "pass"),
    ("Conducted 150 kHz, heater unfiltered (passes 1-2)", est["conducted_heater_turn_on"]["cases"]["as designed (no filter in heater path), V_on 23 V"]["worst_margin_dB"], "fail"),
    ("Harmonics, worst order vs Class A (t_d 230 us)", 20 * math.log10(1 / est["harmonics_61000_3_2"]["cases"]["t_d=230us"]["worst_ratio_to_classA"]), "pass"),
    ("Radiated, boost loop (worst frequency)", min(r["limit_far3m"] - r["E_3m_dBuVm"] for r in est["radiated_dm_loops"]["cases"]["boost loop (L11-U11-D111-C125, 0.5 A, 1.2 MHz, 15 ns)"].values()), "pass"),
    ("Radiated, RGB bus typical content (200 MHz)", 35.5 - 32.1, "pass"),
    ("Radiated, RGB bus all lines in phase (200 MHz)", 35.5 - 49.6, "uncertain"),
]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ys = np.arange(len(items))[::-1]
for y, (lab, m, v) in zip(ys, items):
    col = C["good"] if v == "pass" else C["bad"] if v == "fail" else C["warn"]
    ax.barh(y, m, color=col, height=0.62)
    if m >= 0: ax.text(m + 0.6, y, "%+.0f dB" % m, va="center", ha="left", fontsize=8, color=C["ink"])
    else: ax.text(m + 0.6, y, "%+.0f dB" % m, va="center", ha="left", fontsize=8, color="white", fontweight="bold")
ax.set_yticks(ys); ax.set_yticklabels([i[0] for i in items], fontsize=8)
ax.axvline(0, color=C["ink"], lw=1.2); ax.set_xlabel("margin to the limit (dB; flicker: 20·log10(limit / value))")
ax.set_title("Margin to the limit, every simulated item\n(green = pass, red = fail, orange = uncertain)", fontsize=9.5, loc="left")
ax.set_xlim(min(-32, min(i[1] for i in items) - 4), max(i[1] for i in items) + 8); ax.grid(axis="y", visible=False)
save(fig, "01_margins.png")

# ---------------------------------------------------------------- 2. flickermeter validation ----
fig, ax = plt.subplots(figsize=(8.2, 3.6))
r1 = sorted([r for r in val["rect"] if r["hp_order"] == 1 and r.get("phase_deg", 0) == 0], key=lambda r: r["cpm"])
r6 = sorted([r for r in val["rect"] if r["hp_order"] == 6 and r.get("phase_deg", 0) == 0], key=lambda r: r["cpm"])
ax.axhspan(0.95, 1.05, color=C["grid"], alpha=0.8, zorder=0); ax.text(1.05, 1.052, "±5 % acceptance band", fontsize=7.5, color=C["ink2"])
ax.plot([r["cpm"] for r in r1], [r["pst_cpf"] for r in r1], "-o", color=C["blue"], lw=2, ms=7, label="high-pass 1st order (used)")
ax.plot([r["cpm"] for r in r6], [r["pst_cpf"] for r in r6], "-s", color=C["orange"], lw=1.5, ms=5, label="high-pass 6th order")
for r in r1: ax.text(r["cpm"], r["pst_cpf"] + 0.012, "%.3f" % r["pst_cpf"], ha="center", fontsize=7, color=C["ink"])
ax.set_xscale("log"); ax.set_xlabel("rectangular voltage changes per minute (IEC 61000-4-15 test points, each at its own ΔV/V)"); ax.set_ylabel("P_st (target 1.00)")
ax.set_ylim(0.9, 1.4); ax.set_title("Flickermeter validation: P_st at the standard's test points"); ax.legend(loc="upper left")
ax.annotate("4800/min: fundamental above the 35 Hz low-pass,\nresponse set by the test rectangle's 3rd harmonic", xy=(4800, r1[-1]["pst_cpf"]), xytext=(20, 1.26), fontsize=7.5, color=C["ink2"], arrowprops=dict(arrowstyle="-", color=C["ink2"], lw=0.8))
save(fig, "02_validation.png")

# ---------------------------------------------------------------- helpers for pattern curves ----
def curve(family, param):
    pts = sorted(((v["duty_cmd"], v["pst"]) for k, v in alt["results"].items() if v["family"] == family and v["param"] == param))
    return np.array([p[0] for p in pts]), np.array([p[1] for p in pts])

# ---------------------------------------------------------------- 3. Pst vs duty: current vs recommended ----
fig, ax = plt.subplots(figsize=(8.2, 4.2))
d, p = curve("sd1", 1); ax.plot(d, p, color=C["blue"], lw=2, label="current firmware: sigma-delta, decision every cycle")
ax.fill_between(d, p, 1.0, where=p > 1.0, color=C["bad"], alpha=0.15, lw=0)
d2, p2 = curve("burst_dither", 1000); ax.plot(d2, p2, color=C["orange"], lw=2, label="recommended: 20 s burst frame with error carry")
d3, p3 = curve("burst_dither", 500); ax.plot(d3, p3, color=C["aqua"], lw=1.4, ls=":", label="10 s burst frame (fails P_lt)")
limit_line(ax, 1.0, "P_st limit 1.0"); limit_line(ax, 0.65, "P_lt limit 0.65 (steady duty: P_lt = P_st)", va="top")
ax.annotate("worst 1.70 at duty 0.80", xy=(0.8, 1.70), xytext=(0.55, 1.78), fontsize=8, color=C["ink"], arrowprops=dict(arrowstyle="-", color=C["ink2"], lw=0.8))
ax.annotate("worst 0.54 at duty 0.99", xy=(0.99, 0.54), xytext=(0.72, 0.30), fontsize=8, color=C["ink"], arrowprops=dict(arrowstyle="-", color=C["ink2"], lw=0.8))
ax.set_xlabel("heater duty (pid_output)"); ax.set_ylabel("P_st over 10 min"); ax.set_xlim(0, 1); ax.set_ylim(0, 1.9)
ax.set_title("Flicker P_st versus heater duty: current firmware and the recommended pattern"); ax.legend(loc="upper left")
save(fig, "03_pst_vs_duty.png")

# ---------------------------------------------------------------- 4. worst Pst vs switching period, by family ----
fig, ax = plt.subplots(figsize=(8.2, 4.0))
fams = {"sd1": ("sigma-delta, decision every K cycles", C["blue"], "o"), "burst": ("burst PWM, period N cycles", C["aqua"], "s"),
        "burst_dither": ("burst PWM + error carry", C["orange"], "D"), "sd2": ("2nd-order sigma-delta", C["violet"], "^")}
for fam, (lab, col, mk) in fams.items():
    rows = sorted([s for s in alt["summary"] if s["family"] == fam], key=lambda s: s["param"])
    x = [s["param"] / 50.0 for s in rows]; y = [s["pst_worst"] for s in rows]
    ax.plot(x, y, "-" + mk, color=col, lw=1.6, ms=6, label=lab)
    for s in rows:
        if fam in ("burst_dither",) or (fam == "sd1" and s["param"] in (1, 25, 100, 1000)): ax.text(s["param"] / 50.0, s["pst_worst"] + 0.05, "%.2f" % s["pst_worst"], ha="center", fontsize=7, color=C["ink"])
limit_line(ax, 1.0, "P_st limit 1.0"); limit_line(ax, 0.65, "P_lt limit 0.65", va="top")
ax.axvline(20, color=C["orange"], lw=0.8, ls=":"); ax.text(20, 0.08, "20 s frame\n(recommended)", ha="center", fontsize=7.5, color=C["orange"])
ax.set_xscale("log"); ax.set_xlabel("decision interval / burst period (s)"); ax.set_ylabel("worst P_st over all duties"); ax.set_ylim(0, 2.7)
ax.set_title("Worst-case flicker versus the switching period for each pattern family"); ax.legend(loc="upper right")
save(fig, "04_worst_pst_vs_period.png")

# ---------------------------------------------------------------- 5. thermal ripple cost vs period ----
fig, ax = plt.subplots(figsize=(8.2, 3.4))
rows = sorted([s for s in alt["summary"] if s["family"] in ("burst", "burst_dither")], key=lambda s: s["param"])
seen = set()
for tau, col in (("60", C["blue"]), ("180", C["orange"]), ("300", C["aqua"])):
    x = []; y = []
    for s in rows:
        if s["family"] == "burst":
            x.append(s["param"] / 50.0); y.append(s["thermal_ripple_pp_pct_worst"][tau])
    ax.plot(x, y, "-o", color=col, lw=1.6, ms=5, label="chamber time constant %s s" % tau)
    for xi, yi in zip(x, y):
        if xi in (5, 20, 60): ax.text(xi, yi + 0.6, "%.1f %%" % yi, ha="center", fontsize=7, color=C["ink"])
ax.axvline(20, color=C["orange"], lw=0.8, ls=":")
ax.set_xscale("log"); ax.set_xlabel("burst period (s)"); ax.set_ylabel("temperature ripple, % of full-power rise (pp)")
ax.set_title("Cost of a longer burst period: worst-case chamber temperature ripple"); ax.legend(loc="upper left")
save(fig, "05_thermal_ripple.png")

# ---------------------------------------------------------------- 6. switching patterns + P_inst traces (illustration) ----
def sd_pattern(duty, n):
    inc = round(duty * 65536); acc = 0; out = []
    for _ in range(n):
        acc += inc; on = acc >= 65536
        if on: acc -= 65536
        out.append(1 if on else 0)
    return np.array(out)
def burst_pattern(duty, n, N=1000):
    inc = round(duty * 65536); acc = 0; out = []
    while len(out) < n:
        acc += inc * N; n_on = acc >> 16; acc &= 0xFFFF
        out += [1] * n_on + [0] * (N - n_on)
    return np.array(out[:n])
fig, axs = plt.subplots(2, 1, figsize=(8.2, 4.4), sharex=False)
t = np.arange(150) * 0.02
axs[0].step(t, sd_pattern(0.8, 150) * 1000, where="post", color=C["blue"], lw=1.2); axs[0].set_ylabel("heater power (W)"); axs[0].set_title("Current firmware at duty 0.80: sigma-delta decides every 20 ms cycle (first 3 s)")
axs[0].set_ylim(-50, 1100); axs[0].set_yticks([0, 1000]); axs[0].set_xlabel("time (s)")
t2 = np.arange(3000) * 0.02
axs[1].step(t2, burst_pattern(0.8, 3000) * 1000, where="post", color=C["orange"], lw=1.2); axs[1].set_ylabel("heater power (W)"); axs[1].set_title("Recommended at duty 0.80: 20 s frame, 800 cycles on then 200 off (first 60 s)")
axs[1].set_ylim(-50, 1100); axs[1].set_yticks([0, 1000]); axs[1].set_xlabel("time (s)")
save(fig, "06_patterns.png")

# ---------------------------------------------------------------- 7. modulation content: dominant frequency per duty, current firmware ----
fig, ax = plt.subplots(figsize=(8.2, 3.8))
wt = lambda f: 1.0 / math.sqrt(1 + ((f - 8.8) / 6.0) ** 2) if f > 0 else 0   # not the real filter: only for the shaded guide band
ax.axhspan(5, 20, color=C["grid"], alpha=0.9, zorder=0); ax.text(0.01, 19.2, "5–20 Hz: eye-lamp weighting > 0.4 (peak at 8.8 Hz)", fontsize=7.5, color=C["ink2"])
for k, v in sorted(alt["results"].items()):
    if v["family"] == "sd1" and v["param"] == 1:
        for f, amp, w in v["weighted_peaks_f_hz_amp_pct_wamp"][:3]:
            ax.scatter(v["duty_cmd"], f, s=amp * 900 + 4, color=C["blue"], alpha=0.55, lw=0)
ax.scatter([], [], s=0.1 * 900, color=C["blue"], alpha=0.55, label="0.1 % modulation"); ax.scatter([], [], s=0.5 * 900, color=C["blue"], alpha=0.55, label="0.5 % modulation")
ax.set_xlabel("heater duty"); ax.set_ylabel("modulation frequency (Hz)"); ax.set_ylim(0, 26); ax.set_xlim(0, 1)
ax.set_title("Current firmware: dominant voltage-modulation components (marker area = amplitude in % of U)"); ax.legend(loc="upper right", labelspacing=1.4)
save(fig, "07_modulation.png")

# ---------------------------------------------------------------- 8. triac turn-on current step (mechanism) ----
fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.2))
t = np.linspace(0, 0.02, 4000); v = 325.3 * np.sin(2 * np.pi * 50 * t); R = 52.9
i = np.where(((t % 0.01) >= 230e-6), v / R, 0.0)
axs[0].plot(t * 1e3, v / 100, color=C["ink2"], lw=1, ls="--", label="mains voltage / 100 (V)"); axs[0].plot(t * 1e3, i, color=C["blue"], lw=1.6, label="heater current (A)")
axs[0].set_xlabel("time (ms)"); axs[0].set_title("One 'on' cycle (fired 230 µs after\neach zero crossing)", fontsize=9); axs[0].legend(loc="lower left")
tz = np.linspace(-0.1e-3, 0.6e-3, 2000); vz = 325.3 * np.sin(2 * np.pi * 50 * tz); tau = (2 * 50e-6 + 3e-6 + 20e-6) / R
iz = np.where(tz >= 230e-6, (vz / R) * (1 - np.exp(-(tz - 230e-6) / tau)), 0)
axs[1].plot(tz * 1e6, iz, color=C["blue"], lw=1.8); axs[1].axvline(230, color=C["ink2"], ls=":", lw=0.9)
axs[1].text(235, 0.05, "fires at 230 µs:\nv ≈ 23 V → step 0.44 A,\nrise ≈ 1.5 µs (LISN + element inductance)", fontsize=7.5, color=C["ink"])
axs[1].set_xlabel("time after the zero crossing (µs)"); axs[1].set_ylabel("heater current (A)"); axs[1].set_title("Zoom: the current step\nthat the LISN sees", fontsize=9)
save(fig, "08_turn_on_step.png")

# ---------------------------------------------------------------- 9. conducted spectrum (restyled) ----
cases = est["conducted_heater_turn_on"]["cases"]
# recompute curves with the same model as estimates.py (import it)
import importlib.util
spec = importlib.util.spec_from_file_location("estm", os.path.join(HERE, "estimates.py"))
src = open(os.path.join(HERE, "estimates.py"), encoding="utf-8").read().split("# ---------------------------------------------------------------- 2.")[0]
ns = {"__file__": os.path.join(HERE, "estimates.py")}
src = src.replace('json.dump(res, open(os.path.join(OUT, "estimates.json"), "w"), indent=1)', "")
src = src.replace('plt.savefig(os.path.join(OUT, "conducted_heater.png"), dpi=150)', "pass")
exec(src, ns)
freqs = ns["freqs"]; hr = ns["heater_reading"]; limq = ns["lim_mains_qp"]; lima = ns["lim_mains_av"]
fig, ax = plt.subplots(figsize=(8.2, 4.3))
sel = [("as designed (no filter in heater path), V_on 23 V", "heater branch unfiltered (passes 1–2)", C["bad"]),
       ("X2 0.47 uF across heater branch", "0.47 µF X2 across the heater branch only", C["yellow"]),
       ("heater behind existing L40 120 uH + C40 1 uF + C1", "filter in the heater path (pass 3+), V_on 23 V", C["blue"]),
       ("heater behind L40/C40, V_on 40 V", "filter in the heater path, V_on 40 V", C["aqua"])]
for key, lab, col in sel:
    ax.semilogx(freqs / 1e6, [hr(f, **ns["cases"][key]) for f in freqs], color=col, lw=2 if "pass 3" in lab else 1.4, label=lab)
ax.semilogx(freqs / 1e6, [limq(f) for f in freqs], color=C["ink"], ls="--", lw=1.2, label="EN 55014-1 Table 5 quasi-peak limit")
ax.semilogx(freqs / 1e6, [lima(f) for f in freqs], color=C["ink2"], ls=":", lw=1.1, label="EN 55014-1 Table 5 average limit")
ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("quasi-peak reading at the LISN (dBµV)"); ax.set_ylim(-20, 105)
ax.set_title("Conducted emission at the mains port from the heater triac's zero-cross turn-on"); ax.legend(loc="upper right", fontsize=7.5)
save(fig, "09_conducted_spectrum.png")

# ---------------------------------------------------------------- 10. conducted margin at 150 kHz by filter option ----
fig, ax = plt.subplots(figsize=(8.2, 3.4))
order = [("as designed (no filter in heater path), V_on 23 V", "unfiltered"), ("X2 0.22 uF across heater branch", "0.22 µF X2"), ("X2 0.47 uF across heater branch", "0.47 µF X2"),
         ("X2 1 uF across heater branch", "1 µF X2"), ("X2 0.47 uF + 47 uH series (heater branch)", "0.47 µF + 47 µH"), ("heater behind existing L40 120 uH + C40 1 uF + C1", "L40 + C40 + C1\n(pass 3+)")]
vals = [cases[k]["worst_margin_dB"] for k, _ in order]
cols = [C["good"] if v >= 0 else C["bad"] for v in vals]
ax.bar(range(len(order)), vals, color=cols, width=0.6)
for i, v in enumerate(vals): ax.text(i, v + (0.8 if v >= 0 else -0.8), "%+.0f dB" % v, ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color=C["ink"], lw=1.2); ax.set_xticks(range(len(order))); ax.set_xticklabels([l for _, l in order], fontsize=8)
ax.set_ylabel("margin to the QP limit at 150 kHz (dB)"); ax.set_title("What each filter option buys at 150 kHz (V_on 23 V)"); ax.grid(axis="x", visible=False)
save(fig, "10_conducted_margin.png")

# ---------------------------------------------------------------- 11. harmonics vs Class A ----
def harm_spectrum(td):
    fs = 200e3; T = 0.02; N = int(fs * T); t = np.arange(N) / fs
    v = math.sqrt(2) * 230 * np.sin(2 * np.pi * 50 * t); g = np.ones(N); half = N // 2; nd = int(td * fs); g[:nd] = 0; g[half:half + nd] = 0
    sp = np.fft.rfft(v / 52.9 * g) / N * 2; return {h: abs(sp[h]) for h in range(2, 41)}
classA = {3: 2.30, 5: 1.14, 7: 0.77, 9: 0.40, 11: 0.33, 13: 0.21, 2: 1.08, 4: 0.43, 6: 0.30}
for h in range(15, 40, 2): classA[h] = 0.15 * 15 / h
for h in range(8, 41, 2): classA[h] = 0.23 * 8 / h
fig, ax = plt.subplots(figsize=(8.2, 3.8))
orders = list(range(2, 41)); w = 0.28
for j, (td, col, lab) in enumerate(((230e-6, C["blue"], "t_d = 230 µs (firmware)"), (500e-6, C["orange"], "t_d = 500 µs"), (1000e-6, C["aqua"], "t_d = 1 ms (what-if)"))):
    hs = harm_spectrum(td); ax.bar([o + (j - 1) * w for o in orders], [max(hs[o], 1e-5) for o in orders], width=w, color=col, label=lab, lw=0)
ax.step(orders, [classA[o] for o in orders], where="mid", color=C["ink"], ls="--", lw=1.2, label="IEC 61000-3-2 Class A limit")
ax.set_yscale("log"); ax.set_ylim(1e-4, 5); ax.set_xlabel("harmonic order"); ax.set_ylabel("harmonic current (A rms)")
ax.set_title("Heater current harmonics from the turn-on notch versus the Class A limits"); ax.legend(loc="upper right", fontsize=7.5)
save(fig, "11_harmonics.png")

# ---------------------------------------------------------------- 12. radiated E-field vs frequency ----
rd = est["radiated_dm_loops"]["cases"]
fig, ax = plt.subplots(figsize=(8.2, 4.8))
fq = [30, 50, 100, 200, 300, 500, 1000]
lim = [rd["buck hot loop (C330/C331-U30-GND, 1 A, 580 kHz, 20 ns)"]["%dMHz" % f]["limit_far3m"] for f in fq]
ax.plot(fq, lim, color=C["ink"], ls="--", lw=1.3, label="EN 55014-1 Table 9 limit, FAR 3 m (QP)")
for key, lab, col in (("buck hot loop (C330/C331-U30-GND, 1 A, 580 kHz, 20 ns)", "buck switching loop", C["violet"]), ("boost loop (L11-U11-D111-C125, 0.5 A, 1.2 MHz, 15 ns)", "boost switching loop", C["aqua"])):
    ax.plot(fq, [rd[key]["%dMHz" % f]["E_3m_dBuVm"] for f in fq], "-o", color=col, lw=1.6, ms=5, label=lab)
rgb = [rd["RGB bus, 28 lines in phase, 33 MHz PCLK, 2 ns edges, 110 mm over 0.2 mm"]["%dMHz" % f]["E_3m_dBuVm"] for f in fq]
ax.plot(fq, rgb, "-o", color=C["bad"], lw=2, ms=5, label="RGB bus, all 28 lines in phase (worst test pattern)")
ax.plot(fq, [r - 17.5 for r in rgb], "-o", color=C["blue"], lw=2, ms=5, label="RGB bus, typical content (half the lines, uncorrelated)")
ax.fill_between(fq, rgb, lim, where=np.array(rgb) > np.array(lim), color=C["bad"], alpha=0.12, lw=0)
ax.set_xscale("log"); ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("E at 3 m (dBµV/m)"); ax.set_ylim(-15, 60)
ax.set_title("Radiated emission estimates (differential-mode loops, +6 dB ground reflection)"); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=7.5)
save(fig, "12_radiated.png")

# ---------------------------------------------------------------- 13. CM budget ----
cm = est["common_mode_current_budget_uA"]["budget"]
fig, ax = plt.subplots(figsize=(8.2, 3.8))
for (cable, col) in (("mains cable 2 m", C["blue"]), ("heater cable 1 m", C["orange"]), ("fan cable 0.5 m", C["aqua"]), ("TFT FPC 50 mm", C["violet"])):
    ax.plot(fq, [cm[cable]["%dMHz" % f] for f in fq], "-o", color=col, lw=1.6, ms=5, label=cable)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("allowed common-mode current (µA)")
ax.set_title("Common-mode current budget per cable before the FAR 3 m limit is reached"); ax.legend(loc="upper right", fontsize=7.5)
ax.text(31, 2.2, "a few µA on the mains lead is the whole budget:\nthe CM choke and the input filter are what keep it", fontsize=7.5, color=C["ink2"])
save(fig, "13_cm_budget.png")
print("done")
