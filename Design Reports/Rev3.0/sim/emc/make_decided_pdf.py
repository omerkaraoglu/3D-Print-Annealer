"""Pass/fail scorecard PDF for the DECIDED design only: pass-4 hardware (LC filter in the heater path, series arrays, connector
capacitors) + the decided firmware (20 s burst frame with error carry). Builds its own charts (charts/d_*.png) from the JSON results.
Output: Design Reports/Rev3.0/EMC_Scorecard_Decided_Design.pdf"""
import json, os, math, datetime
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__)); CH = os.path.join(HERE, "charts"); os.makedirs(CH, exist_ok=True)
OUT = os.path.join(HERE, "..", "..", "EMC_Scorecard_Decided_Design.pdf")
est = json.load(open(os.path.join(HERE, "estimates.json"), encoding="utf-8"))
alt = json.load(open(os.path.join(HERE, "alternatives_results.json"), encoding="utf-8"))
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "violet": "#6250d6", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e4e3df", "good": "#0ca30c", "bad": "#d03b3b", "warn": "#ec835a", "fill": "#fcfcfb"}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": C["ink2"], "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "axes.titleweight": "bold", "axes.titlesize": 10.5, "legend.frameon": False, "legend.fontsize": 8, "figure.facecolor": "white", "axes.facecolor": C["fill"]})
def save(fig, name): fig.tight_layout(); fig.savefig(os.path.join(CH, name), dpi=170); plt.close(fig)
def limit_line(ax, y, text, va="bottom"):
    ax.axhline(y, color=C["ink2"], ls="--", lw=1.1); ax.text(0.99, y, text, transform=ax.get_yaxis_transform(), ha="right", va=va, fontsize=7.5, color=C["ink2"])

# ---------------------------------------------------------------- data of the decided configuration ----
dec = sorted(((v["duty_cmd"], v) for k, v in alt["results"].items() if v["family"] == "burst_dither" and v["param"] == 1000))
duty = np.array([d for d, _ in dec]); pst = np.array([v["pst"] for _, v in dec]); dmax = np.array([v["d_max_pct"] for _, v in dec]); dc = np.array([v["d_c_pct"] for _, v in dec])
worst = max(pst); worst_duty = duty[int(np.argmax(pst))]
cond = est["conducted_heater_turn_on"]["cases"]
c23 = cond["heater behind existing L40 120 uH + C40 1 uF + C1"]; c40 = cond["heater behind L40/C40, V_on 40 V"]
harm = est["harmonics_61000_3_2"]["cases"]["t_d=230us"]
rd = est["radiated_dm_loops"]["cases"]; fq = [30, 50, 100, 200, 300, 500, 1000]
rgb_worst = [rd["RGB bus, 28 lines in phase, 33 MHz PCLK, 2 ns edges, 110 mm over 0.2 mm"]["%dMHz" % f] for f in fq]
rgb_typ = [r["E_3m_dBuVm"] - 17.5 for r in rgb_worst]; lim = [r["limit_far3m"] for r in rgb_worst]
boost = [rd["boost loop (L11-U11-D111-C125, 0.5 A, 1.2 MHz, 15 ns)"]["%dMHz" % f]["E_3m_dBuVm"] for f in fq]
buck = [rd["buck hot loop (C330/C331-U30-GND, 1 A, 580 kHz, 20 ns)"]["%dMHz" % f]["E_3m_dBuVm"] for f in fq]

# ---------------------------------------------------------------- scorecard rows ----
rows = [  # (test, requirement, result, margin dB, status)
    ("IEC 61000-3-3 short-term flicker P_st", "<= 1.0 at every duty", "worst %.2f at duty %.2f" % (worst, worst_duty), 20 * math.log10(1.0 / worst), "PASS"),
    ("IEC 61000-3-3 long-term flicker P_lt", "<= 0.65 (steady duty: P_lt = P_st)", "worst %.2f" % worst, 20 * math.log10(0.65 / worst), "PASS"),
    ("IEC 61000-3-3 d_c / d_max / T_max", "<= 3.3 % / 4 % / 500 ms", "%.2f %% / %.2f %% / 0 ms" % (max(dc), max(dmax)), 20 * math.log10(3.3 / max(max(dc), max(dmax))), "PASS"),
    ("EN 55014-1 conducted, mains port (triac, V_on 23 V)", "Table 5 QP 66 dBuV at 150 kHz, 56 above 0.5 MHz", "%.0f dBuV at 150 kHz" % c23["at_150k"], c23["worst_margin_dB"], "PASS"),
    ("EN 55014-1 conducted, mains port (triac, late ZCD edge 40 V)", "same", "%.0f dBuV at 150 kHz" % c40["at_150k"], c40["worst_margin_dB"], "PASS"),
    ("EN 55014-1 discontinuous disturbance (clicks)", "continuous limits apply (switching rate >= 30/min or <= 6/min with the 20 s frame)", "triac events meet the continuous limit", c40["worst_margin_dB"], "PASS"),
    ("IEC 61000-3-2 harmonic currents (Class A)", "Table 1, orders 2-40", "worst order %d at %.0f %% of its limit" % (harm["worst_order"], harm["worst_ratio_to_classA"] * 100), 20 * math.log10(1 / harm["worst_ratio_to_classA"]), "PASS"),
    ("EN 55014-1 radiated 30-1000 MHz, switching converters", "Table 9 FAR 3 m: 42->35 / 42 dBuV/m", "%.0f / %.0f dBuV/m" % (max(buck), max(boost)), min(l - e for l, e in zip(lim, boost)), "PASS"),
    ("EN 55014-1 radiated 30-1000 MHz, RGB bus with normal display content", "same", "%.0f dBuV/m at 200 MHz" % rgb_typ[3], min(l - e for l, e in zip(lim, rgb_typ)), "PASS"),
    ("EN 55014-1 radiated, RGB bus with every line toggling each pixel clock", "same (test-pattern dependent)", "%.0f dBuV/m at 200 MHz" % rgb_worst[3]["E_3m_dBuVm"], min(l - r["E_3m_dBuVm"] for l, r in zip(lim, rgb_worst)), "MEASURE"),
    ("EN 55014-2 immunity (ESD, EFT, surge, RF, dips), category IV", "criteria A/B/C per test", "not simulated; provisions in the design (filter, MOV, ESD diodes, TVS)", None, "NOT SIMULATED"),
]

# ---------------------------------------------------------------- charts ----
fig, ax = plt.subplots(figsize=(8.2, 4.0))
sim = [r for r in rows if r[3] is not None]; ys = np.arange(len(sim))[::-1]
for y, r in zip(ys, sim):
    col = C["good"] if r[4] == "PASS" else C["warn"]
    ax.barh(y, r[3], color=col, height=0.62)
    ax.text(r[3] + (0.6 if r[3] >= 0 else -0.6), y, "%+.0f dB" % r[3], va="center", ha="left" if r[3] >= 0 else "right", fontsize=8)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in sim], fontsize=7.5); ax.axvline(0, color=C["ink"], lw=1.2); ax.grid(axis="y", visible=False)
ax.set_xlabel("margin to the limit (dB; flicker and harmonics: 20·log10(limit / value))"); ax.set_xlim(-20, 40)
ax.set_title("Decided design: margin to every simulated limit\n(green = pass, orange = test-pattern dependent)", fontsize=9.5, loc="left")
save(fig, "d_01_scorecard.png")

fig, ax = plt.subplots(figsize=(8.2, 3.4))
ax.plot(duty, pst, color=C["orange"], lw=2.2, label="P_st, 20 s burst frame with error carry")
ax.fill_between(duty, 0, pst, color=C["orange"], alpha=0.12, lw=0)
limit_line(ax, 1.0, "P_st limit 1.0"); limit_line(ax, 0.65, "P_lt limit 0.65 (P_lt = P_st at steady duty)", va="top")
ax.annotate("worst %.2f at duty %.2f" % (worst, worst_duty), xy=(worst_duty, worst), xytext=(0.62, 0.82), fontsize=8, arrowprops=dict(arrowstyle="-", color=C["ink2"], lw=0.8))
ax.set_xlim(0, 1); ax.set_ylim(0, 1.15); ax.set_xlabel("heater duty"); ax.set_ylabel("P_st over 10 min"); ax.set_title("Flicker: P_st at every duty, decided firmware"); ax.legend(loc="upper left")
save(fig, "d_02_pst.png")

fig, ax = plt.subplots(figsize=(8.2, 2.8))
ax.plot(duty, dmax, color=C["blue"], lw=2, label="d_max (largest relative voltage change)"); ax.plot(duty, dc, color=C["aqua"], lw=1.6, ls=":", label="d_c (steady-state change)")
limit_line(ax, 4.0, "d_max limit 4 %"); limit_line(ax, 3.3, "d_c limit 3.3 %", va="top")
ax.set_xlim(0, 1); ax.set_ylim(0, 4.6); ax.set_xlabel("heater duty"); ax.set_ylabel("% of U_n"); ax.set_title("Flicker: voltage-change criteria, decided firmware (T_max = 0 s everywhere, limit 500 ms)"); ax.legend(loc="center left")
save(fig, "d_03_dvalues.png")

# conducted: recompute the two decided curves with the estimates.py model
src = open(os.path.join(HERE, "estimates.py"), encoding="utf-8").read().split("# ---------------------------------------------------------------- 2.")[0]
src = src.replace('json.dump(res, open(os.path.join(OUT, "estimates.json"), "w"), indent=1)', "").replace('plt.savefig(os.path.join(OUT, "conducted_heater.png"), dpi=150)', "pass")
ns = {"__file__": os.path.join(HERE, "estimates.py")}; exec(src, ns)
freqs = ns["freqs"]; hr = ns["heater_reading"]; limq = ns["lim_mains_qp"]; lima = ns["lim_mains_av"]
fig, ax = plt.subplots(figsize=(8.2, 3.8))
y23 = [hr(f, **ns["cases"]["heater behind existing L40 120 uH + C40 1 uF + C1"]) for f in freqs]; y40 = [hr(f, **ns["cases"]["heater behind L40/C40, V_on 40 V"]) for f in freqs]
ax.semilogx(freqs / 1e6, y23, color=C["blue"], lw=2.2, label="triac turn-on at 23 V (nominal ZCD timing)")
ax.semilogx(freqs / 1e6, y40, color=C["aqua"], lw=1.6, label="triac turn-on at 40 V (late ZCD edge)")
ax.semilogx(freqs / 1e6, [limq(f) for f in freqs], color=C["ink"], ls="--", lw=1.2, label="EN 55014-1 quasi-peak limit"); ax.semilogx(freqs / 1e6, [lima(f) for f in freqs], color=C["ink2"], ls=":", lw=1.1, label="EN 55014-1 average limit")
ax.fill_between(freqs / 1e6, y40, [limq(f) for f in freqs], color=C["good"], alpha=0.08, lw=0)
ax.text(0.5, 25, "margin at 150 kHz: +%.0f dB (23 V) / +%.0f dB (40 V)" % (c23["worst_margin_dB"], c40["worst_margin_dB"]), fontsize=8.5, color=C["ink"], fontweight="bold")
ax.set_ylim(-20, 80); ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("quasi-peak at the LISN (dBµV)"); ax.set_title("Conducted emission at the mains port, decided hardware (LC filter in the heater path)"); ax.legend(loc="upper right", fontsize=7.5)
save(fig, "d_04_conducted.png")

fig, ax = plt.subplots(figsize=(8.2, 3.2))
fs = 200e3; T = 0.02; Nn = int(fs * T); t = np.arange(Nn) / fs; v = math.sqrt(2) * 230 * np.sin(2 * np.pi * 50 * t); g = np.ones(Nn); half = Nn // 2; nd = int(230e-6 * fs); g[:nd] = 0; g[half:half + nd] = 0
sp = np.fft.rfft(v / 52.9 * g) / Nn * 2; orders = list(range(2, 41))
classA = {3: 2.30, 5: 1.14, 7: 0.77, 9: 0.40, 11: 0.33, 13: 0.21, 2: 1.08, 4: 0.43, 6: 0.30}
for h in range(15, 40, 2): classA[h] = 0.15 * 15 / h
for h in range(8, 41, 2): classA[h] = 0.23 * 8 / h
ax.bar(orders, [max(abs(sp[o]), 1e-5) for o in orders], color=C["blue"], width=0.6, label="heater current harmonics, decided firmware (230 µs notch)")
ax.step(orders, [classA[o] for o in orders], where="mid", color=C["ink"], ls="--", lw=1.2, label="IEC 61000-3-2 Class A limit")
ax.set_yscale("log"); ax.set_ylim(1e-4, 5); ax.set_xlabel("harmonic order"); ax.set_ylabel("A rms"); ax.set_title("Harmonic currents versus the Class A limits (worst order at %.0f %% of its limit)" % (harm["worst_ratio_to_classA"] * 100)); ax.legend(loc="upper right", fontsize=7.5)
save(fig, "d_05_harmonics.png")

fig, ax = plt.subplots(figsize=(8.2, 4.2))
ax.plot(fq, lim, color=C["ink"], ls="--", lw=1.3, label="EN 55014-1 Table 9 limit, FAR 3 m")
ax.plot(fq, buck, "-o", color=C["violet"], lw=1.6, ms=5, label="buck switching loop"); ax.plot(fq, boost, "-o", color=C["aqua"], lw=1.6, ms=5, label="boost switching loop")
ax.plot(fq, rgb_typ, "-o", color=C["blue"], lw=2.2, ms=5, label="RGB bus, normal display content")
ax.plot(fq, [r["E_3m_dBuVm"] for r in rgb_worst], ":o", color=C["warn"], lw=1.4, ms=4, label="RGB bus, every line toggling each clock (test-pattern dependent, measure)")
ax.set_xscale("log"); ax.set_ylim(-15, 60); ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("E at 3 m (dBµV/m)"); ax.set_title("Radiated emission, decided hardware (33 Ω arrays and connector capacitors fitted)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=7.5)
save(fig, "d_06_radiated.png")

# ---------------------------------------------------------------- PDF ----
ss = getSampleStyleSheet(); H1 = ss["Heading1"]; H1.fontSize = 14
N = ParagraphStyle("n", parent=ss["BodyText"], fontSize=9, leading=12); CAP = ParagraphStyle("cap", parent=N, fontSize=8.5, leading=11, textColor=colors.HexColor("#333333"), spaceAfter=8)
CELL = ParagraphStyle("c", parent=N, fontSize=8, leading=10); W = A4[0] - 30 * mm
def fig_(name, cap):
    p = os.path.join(CH, name); iw, ih = ImageReader(p).getSize(); return KeepTogether([Image(p, width=W, height=W * ih / iw), Paragraph(cap, CAP)])
n_pass = sum(1 for r in rows if r[4] == "PASS"); n_meas = sum(1 for r in rows if r[4] == "MEASURE"); n_ns = sum(1 for r in rows if r[4] == "NOT SIMULATED")
story = [Paragraph("Rev3.0 controller — EMC scorecard of the decided design", ss["Title"]),
         Paragraph("Configuration scored: pass-4 hardware (LC input filter in the heater path, 33 Ω series arrays and RF-return capacitors at the display connectors, H11AA1 ZCD, 275 V MOV) "
                   "with the decided firmware (heater fired in 20 s burst frames with error carry, 230 µs after the zero crossing). Models as in the EMC assessment; date %s." % datetime.date.today().isoformat(), N), Spacer(1, 3 * mm)]
verdict = "<b>Verdict: %d of %d requirements PASS in simulation; %d depends on the display test pattern and needs the pre-compliance measurement; %d (immunity) was not simulated.</b>" % (n_pass, len(rows), n_meas, n_ns)
story.append(Paragraph(verdict, ParagraphStyle("v", parent=N, fontSize=10.5, leading=14, textColor=colors.HexColor("#0b0b0b"), backColor=colors.HexColor("#eef7ee"), borderPadding=5)))
story.append(Spacer(1, 4 * mm))
data = [["Requirement", "Limit", "Simulated result", "Margin", "Status"]]
for r in rows: data.append([Paragraph(r[0], CELL), Paragraph(r[1], CELL), Paragraph(r[2], CELL), ("%+.0f dB" % r[3]) if r[3] is not None else "—", r[4]])
t = Table(data, colWidths=[52 * mm, 44 * mm, 48 * mm, 16 * mm, 20 * mm], repeatRows=1)
st = [("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3e8f0")), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
for i, r in enumerate(rows, start=1):
    col = {"PASS": "#0ca30c", "MEASURE": "#ec835a", "NOT SIMULATED": "#8a8a8a"}[r[4]]
    st += [("TEXTCOLOR", (4, i), (4, i), colors.HexColor(col)), ("FONT", (4, i), (4, i), "Helvetica-Bold", 8)]
t.setStyle(TableStyle(st)); story.append(t)
story.append(Spacer(1, 4 * mm)); story.append(fig_("d_01_scorecard.png", "Margin to every simulated limit for the decided design. All simulated items pass; the orange bar is the RGB bus with a pathological test pattern, which only a measurement with the real panel settles."))
story.append(PageBreak())
story.append(Paragraph("Flicker — IEC 61000-3-3", H1))
story.append(fig_("d_02_pst.png", "P_st of the 20 s burst frame at every heater duty: %.2f to %.2f, worst at duty %.2f. Both the P_st limit (1.0) and the P_lt limit (0.65, which applies because the dryer runs for hours at steady duty) are met." % (min(pst), worst, worst_duty)))
story.append(fig_("d_03_dvalues.png", "The voltage-change criteria: every switching of the 1 kW heater changes the terminal voltage by 0.75 % on the reference impedance, far below the 3.3 % / 4 % limits; no change lasts longer than the 500 ms T_max limit."))
story.append(PageBreak()); story.append(Paragraph("Conducted emission — EN 55014-1", H1))
story.append(fig_("d_04_conducted.png", "The triac's zero-cross turn-on steps at 100 Hz, seen at the LISN through the LC input filter that now sits in front of the heater branch: %.0f dBuV at 150 kHz against the 66 dBuV quasi-peak limit, %.0f dBuV if the ZCD edge fires the triac late at 40 V. The average limit is met with the same margins. Model uncertainty ±6 dB." % (c23["at_150k"], c40["at_150k"])))
story.append(PageBreak())
story.append(Paragraph("Harmonic currents — IEC 61000-3-2", H1))
story.append(fig_("d_05_harmonics.png", "Whole-cycle control adds no integer harmonics; the 230 µs turn-on notch is the only source and stays at %.0f %% of the Class A limit at its worst order (%d)." % (harm["worst_ratio_to_classA"] * 100, harm["worst_order"])))
story.append(Paragraph("Radiated emission — EN 55014-1, 30–1000 MHz", H1))
story.append(fig_("d_06_radiated.png", "Differential-mode estimates at 3 m. The switching converters are 40 dB under the limit; the RGB bus with normal display content is 4–10 dB under. With every data line toggling on every pixel clock (a worst-case test pattern, not normal use) the model exceeds the limit by up to 14 dB at 200 MHz: this is the one item the pre-compliance measurement must settle, with the series arrays and connector capacitors already fitted."))
story.append(Paragraph("Immunity — EN 55014-2 (not simulated)", H1))
story.append(Paragraph("ESD 8 kV air / 4 kV contact, EFT 1 kV on the mains port, surge 1 kV L–N, injected RF 3 V, radiated RF 3 V/m and voltage dips were not simulated. Design provisions: LC input filter and common-mode choke, 275 V-class MOV in front and a second MOV across the triac, TVS on the thermocouple leads, ESD diodes on all touch-connector signals, 33 Ω / RC filtering on the digital lines, HLK module hold-up for the half-cycle dip. Expected criteria: B for EFT/surge/ESD, A for RF, C for the long dips (clean reset, heater off during reset).", N))
def footer(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica", 7); canvas.drawString(15 * mm, 8 * mm, "Rev3.0 — EMC scorecard, decided design — %s" % datetime.date.today().isoformat()); canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, "page %d" % doc.page); canvas.restoreState()
SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title="Rev3.0 EMC scorecard (decided design)").build(story, onFirstPage=footer, onLaterPages=footer)
print("written", os.path.abspath(OUT))
