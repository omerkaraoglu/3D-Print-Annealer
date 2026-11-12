"""Build EMC_Simulation_Results.pdf: chart-centric report from charts/*.png (make_emc_charts.py) with short captions (reportlab)."""
import os, datetime, json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__)); CH = os.path.join(HERE, "charts")
OUT = os.path.join(HERE, "..", "..", "EMC_Simulation_Results.pdf")
if not os.path.exists(os.path.join(CH, "01_margins.png")):
    import subprocess, sys; subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "make_emc_charts.py")], check=True)
ss = getSampleStyleSheet()
H1 = ss["Heading1"]; H1.fontSize = 15; H1.spaceBefore = 6; H1.spaceAfter = 4
CAP = ParagraphStyle("cap", parent=ss["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#333333"), spaceBefore=2, spaceAfter=8)
N = ParagraphStyle("n", parent=ss["BodyText"], fontSize=9, leading=12)
W = A4[0] - 30 * mm
def fig(name, caption, w=W):
    p = os.path.join(CH, name)
    if not os.path.exists(p): p = os.path.join(HERE, name)          # the flicker scripts' own plots live beside them
    iw, ih = ImageReader(p).getSize()
    return KeepTogether([Image(p, width=w, height=w * ih / iw), Paragraph(caption, CAP)])
def P(t, st=N): return Paragraph(t, st)

story = [P("Rev3.0 filament-dryer controller — EMC simulation results", ss["Title"]),
         P("Post-layout EMC assessment, EU household appliance (EN 55014-1/-2, IEC 61000-3-2, IEC 61000-3-3). Models run 2026-11-12; charts rebuilt %s by "
           "<font face='Courier'>sim/emc/make_emc_charts.py</font> from the JSON results. The text discussion is in <font face='Courier'>EMC_PostLayout_Assessment.md</font>." % datetime.date.today().isoformat()),
         Spacer(1, 3 * mm)]
story.append(P("1. One look: where every item stands", H1))
story.append(fig("01_margins.png", "Margin to the applicable limit for every simulated item. Positive is a pass. Flicker margins are 20·log10(limit / value) so that they share the dB axis with the emission items. "
                 "Two items fail: the current heater-firing pattern (flicker) and the pass-1/2 topology with the heater branch outside the filter (conducted, already fixed in copper). "
                 "The RGB bus with every line toggling in phase is the pathological test pattern; normal display content passes."))
story.append(PageBreak())
story.append(P("2. Flicker (IEC 61000-3-3) — the heater's switching pattern", H1))
story.append(fig("08_turn_on_step.png", "What the triac does: in an 'on' cycle it fires 230 µs after each zero crossing (left), so the 1 kW heater starts with a 0.44 A step with a rise of about 1.5 µs (right). "
                 "Switching whole cycles is what keeps the harmonics clean (section 4); which cycles are switched is what sets the flicker."))
story.append(fig("06_patterns.png", "The two patterns compared in this report at duty 0.80: the current firmware decides every 20 ms with a sigma-delta modulator (top), "
                 "the recommended firmware uses a 20 s frame of 800 on-cycles followed by 200 off-cycles with the rounding error carried to the next frame (bottom)."))
story.append(fig("02_validation.png", "The flickermeter model reproduces the IEC 61000-4-15 test points: rectangular modulation at 1 to 1620 changes per minute gives P_st = 1.00 within +2.8 % "
                 "(allowed ±5 %); the 8.8 Hz sine gives P_inst = 1.03 (allowed ±8 %). The 4800/min point is outside the band for a reason that does not affect heater patterns (its fundamental is above the 35 Hz low-pass)."))
story.append(PageBreak())
story.append(fig("03_pst_vs_duty.png", "The result that decides it: with the current firmware P_st exceeds 1.0 for duties 0.07–0.46 and 0.54–0.935, worst 1.70 at duty 0.80, and P_lt exceeds 0.65 almost everywhere "
                 "(at steady duty P_lt equals P_st, and the dryer runs for hours). The 20 s burst frame stays at 0.51–0.54 for every duty."))
story.append(fig("07_modulation.png", "Why it fails: the per-cycle pattern puts 0.1–0.5 % of voltage modulation between 5 and 20 Hz, where the eye-lamp weighting of the flickermeter peaks (8.8 Hz). "
                 "Each marker is one of the three strongest modulation components at that duty; marker area is the amplitude."))
story.append(fig("04_worst_pst_vs_period.png", "Every pattern family tried, worst P_st over all duties against its switching period. Nothing that switches faster than about once per second passes; "
                 "fixed-period bursts have at most two voltage changes per period and reach P_lt ≤ 0.65 from a 20 s period; the error-carry variant keeps the long-term mean exact. "
                 "Second-order noise shaping is worse: with whole-cycle switching the usable band is only 0–25 Hz and its limit-cycle tones land in the sensitive band."))
story.append(PageBreak())
story.append(fig("05_thermal_ripple.png", "The price of the long frame: worst-case peak-to-peak chamber temperature ripple as a share of the full-power temperature rise, for three chamber time constants. "
                 "At 20 s and a 3-minute time constant it is about 3 % (3 K on a 100 K rise), which the PID can be retuned around (lower derivative gain, anti-windup, thermocouple averaged over the frame)."))
story.append(fig("plot_pinst_example.png", "Instantaneous flicker sensation P_inst from the flickermeter: the current firmware at duty 0.80 (top, continuous 10/20 Hz modulation) and the recommended 20 s frame at duty 0.50 (bottom, "
                 "two short events per frame that decay within a second)."))
story.append(PageBreak())
story.append(P("3. Conducted emission (EN 55014-1) — the triac at the mains port", H1))
story.append(fig("09_conducted_spectrum.png", "Quasi-peak reading at the LISN of the heater's 100 Hz train of 0.44 A current steps, against the EN 55014-1 Table 5 limits. "
                 "With the LC filter on the PSU branch only (passes 1–2) the heater branch was 27 dB over at 150 kHz; with the filter at the mains input (pass 3 onwards) it is 11 dB under, 6 dB under if the ZCD edge fires the triac late at 40 V. "
                 "An X2 capacitor on the heater branch alone would not have been enough. Model uncertainty about ±6 dB."))
story.append(fig("10_conducted_margin.png", "The same comparison as a margin at 150 kHz, the worst frequency. Only the full LC filter in the heater path gives a comfortable margin."))
story.append(PageBreak())
story.append(P("4. Harmonic currents (IEC 61000-3-2)", H1))
story.append(fig("11_harmonics.png", "Whole-cycle control adds no integer harmonics; the only source is the turn-on notch after each zero crossing. With the firmware's 230 µs the worst order sits at 14 % of its Class A limit; "
                 "even a 1 ms notch would stay at 66 %. The PSU (10 W) is below the 75 W threshold."))
story.append(P("5. Radiated emission (EN 55014-1, 30–1000 MHz)", H1))
story.append(fig("12_radiated.png", "Differential-mode loop estimates at 3 m against the FAR limit: the two switching converters are irrelevant (loops of 10–20 mm²). The 110 mm RGB bus is the only credible source: "
                 "with all 28 lines toggling in phase on every pixel clock it would exceed the limit by up to 14 dB at 200 MHz; with normal display content it is 4–10 dB under. "
                 "Pass 4 adds 33 Ω series arrays on all lines (slower edges) and RF-return capacitors at the connector."))
story.append(PageBreak())
story.append(fig("13_cm_budget.png", "Common-mode current each cable may carry before the FAR 3 m limit is reached. This is a budget, not a prediction: the driving ground-noise voltage at the connectors "
                 "can only be measured. A few microamps on the mains lead is the entire allowance, which is why the common-mode choke and the input filter matter more than any on-board detail."))
story.append(P("6. Models and limits", H1))
story.append(Table([
    ["Flicker", "Full IEC 61000-4-15 flickermeter (adaptor, squaring demodulator, 35 Hz / 0.05 Hz / eye-lamp weighting filters, 300 ms smoothing, CPF statistics over 10 min) on an exact R-L time-domain model: 230 V behind Z_ref = (0.24+j0.15)+(0.16+j0.10) Ω, heater 52.9 Ω, triac fired 230 µs after the zero crossing, bit-exact ISR pattern. Limits P_st 1.0, P_lt 0.65, d_c 3.3 %, d_max 4 %, T_max 500 ms, and the test-point values, are taken from the standards as known (the only local IEC 61000-3-3 is a preview without the limits clause)."],
    ["Conducted", "One-pulse step spectrum into a 50 Ω / 50 µH LISN, rise time from the series inductance, CISPR 16-1-1 Band B quasi-peak pulse weighting for a 100 Hz train; ideal filter elements; the HLK-10M05 is a black box (vendor EMC claim)."],
    ["Harmonics", "FFT of the idealised heater current with the turn-on notch against IEC 61000-3-2 Table 1."],
    ["Radiated", "Ott small-loop (differential) and short-wire / resonant-dipole (common-mode) formulas with trapezoid harmonic envelopes; loop areas and trace lengths from the final board; +6 dB ground reflection."],
    ["Not simulated", "No 3D field solver, no full-board conducted model, no immunity simulation, no cable common-mode prediction. The pre-compliance test plan (assessment report §7) settles the open items."],
], colWidths=[26 * mm, W - 26 * mm], style=TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                                       ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey), ("LEFTPADDING", (0, 0), (-1, -1), 3)])))
# wrap the long cells
def footer(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica", 7)
    canvas.drawString(15 * mm, 8 * mm, "Rev3.0 filament-dryer controller — EMC simulation results — %s" % datetime.date.today().isoformat())
    canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, "page %d" % doc.page); canvas.restoreState()
# convert table cells to paragraphs for wrapping
tbl = story[-1]; cells = [[Paragraph(c, ParagraphStyle("c", parent=N, fontSize=8, leading=10)) if isinstance(c, str) else c for c in r] for r in tbl._cellvalues]
story[-1] = Table(cells, colWidths=[26 * mm, W - 26 * mm], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey), ("LEFTPADDING", (0, 0), (-1, -1), 3)]))
doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title="Rev3.0 EMC simulation results", author="Rev3.0 design tools")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("written", os.path.abspath(OUT))
