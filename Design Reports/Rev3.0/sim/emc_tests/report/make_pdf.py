"""Builds Design Reports/Rev3.0/Rev3.0_EMC_Test_Simulation_Results.pdf from report/charts/*.pdf (vector, placed 1:1) with
PyMuPDF. Text values on the scorecard come from the three scopes' results.json (via common_style); run make_charts.py first.
Run: python -X utf8 make_pdf.py
"""
import json, math, os, datetime
import fitz
import make_charts as MC
from common_style import A, B, C, REPORT_ONLY, VERD, AS, WITH, LIM, CH, typo, HERE

OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "Rev3.0_EMC_Test_Simulation_Results.pdf"))
PW, PH = 595.28, 841.89
ML = 40.0; TOP = 34.0; BOTTOM = 40.0
FONTS = fitz.Archive(r"C:\Windows\Fonts")
CSS = """@font-face {font-family: A; src: url(arial.ttf);}
@font-face {font-family: A; src: url(arialbd.ttf); font-weight: bold;}
@font-face {font-family: A; src: url(ariali.ttf); font-style: italic;}
* {font-family: A; color: #1A1A1A;}
p {margin: 0; padding: 0;}
.cap {font-size: 8.5pt; color: #333333; line-height: 1.25;}
.sec {font-size: 8pt; color: #555555; letter-spacing: 0.5pt;}
.h1 {font-size: 13pt; font-weight: bold;}
.small {font-size: 8pt; color: #555555;}
td, th {font-size: 8pt; padding: 2.2pt 3pt 2.2pt 3pt; vertical-align: middle;}
th {text-align: left; border-bottom: 1px solid #1A1A1A;}
td {border-bottom: 0.5px solid #D8D8D8;}
"""
FOOT = "Rev3.0 controller  |  EMC test simulation results  |  simulation, not an accredited measurement"
DATE = "2026-11-18"


def esc(s):
    return typo(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bv(test_sub, part_sub):
    for r in B["verdict_table"]:
        if test_sub in r["test"] and part_sub in r["part"]:
            return r
    raise KeyError((test_sub, part_sub))


def chip(verdict, text):
    fg, bg = VERD[verdict]
    return '<td style="background-color:%s;"><b style="color:%s;">%s</b> %s</td>' % (bg, fg, esc(verdict), esc(text))


# ------------------------------------------------------------------------------------------------------------------
# scorecard rows, every number from results.json
# ------------------------------------------------------------------------------------------------------------------
def scorecard_rows():
    cf = MC.ce_final(); mc = cf[("as designed", "QP")]; mf = cf[("F1", "QP")]
    nom = min(v["margin_dB"] for k, v in A["A1_crosscheck_scopeB"]["nominal"]["as designed V_on 20 V"]["baseline | C_cs 20pF"].items() if k.startswith("QP"))
    h = A["A4_harmonics"]; sm = h["summary_pct_of_limit"]
    hw = max(v[0] for k, v in sm.items() if "decided" in k or "100pct" in k); hw20 = max(v[0] for k, v in sm.items() if ("decided" in k or "100pct" in k) and "V_on=20V" in k)
    fault = h["results"]["fault_half_wave"]; z = A["A0_zcd_timing"]
    fl = A["A5_flicker"]
    e = C["emission"]; pr = {c: MC.combo(c)[0] for c in ("PCLK", "typical UI", "worst pattern")}
    ri = C["radiated_immunity"]; lm = REPORT_ONLY["display_logic_margin_V"][0]
    inj = C["injected"]
    tcb = max(v["dT_worst_bound_degC"] for k, v in inj.items() if k.startswith("mains port") and isinstance(v, dict))
    moc = bv("Surge 1 kV L-N", "MOC3052"); k1 = bv("Surge 1 kV L-N", "K1 open"); s4 = bv("P-S1+P-S2b+P-S4", "800 V driver"); k1b = bv("Surge, P-S2b", "K1")
    rv = bv("Continuous check", "TVR14431"); tv = bv("Continuous check", "1.5KE440CA")
    u6 = bv("EFT 1 kV", "U6 input"); pe1 = B["eft"]["proposal_P_E1_1nF_on_ZCD_node"]
    esd = bv("ESD 4 kV contact", "Barrier"); y1 = bv("ESD, proposal P-D1", "Barrier"); ads = bv("ESD 4 kV contact", "ADS1115")
    cr = B["esd_barrier_vs_Cbar"]["crossing_Cbar_pF"]
    rows = [
        ("EN 55014-1", "Conducted emission, heater on (Table 5)", ("MARGINAL", "Monte Carlo 5th pct %.1f dB, worst %.1f dB, %d of %d runs < 6 dB (nominal %.1f dB)" % (mc["p5"], mc["min"], mc["n_below_6dB"], cf["n"], nom)),
         ("PASS", "worst %.1f dB, 5th pct %.1f dB" % (mf["min"], mf["p5"])), "F1"),
        ("", "Conducted emission, heater off (HLK alone)", ("NOT SIMULABLE", "HLK-10M05 is a black box; needs >= %.1f dB of its own" % REPORT_ONLY["hlk_needs_own_margin_dB"][0]),
         ("MEASURE", "heater-off LISN scan"), "-"),
        ("", "Clicks (4.4)", ("PASS", "triac: no clicks; relay K1 exempt"), ("PASS", "unchanged"), "-"),
        ("", "Radiated, PCLK harmonics (Table 9, FAR 3 m)", ("FAIL", "%+.1f dB (upper %+.1f dB)" % (e["worst_rows"]["PCLK"]["margin_nom"], e["worst_rows_upper"]["PCLK"]["margin_high"])),
         ("PASS", "%+.1f dB (upper %+.1f dB); model +-10 dB" % (pr["PCLK"]["nominal"]["margin_nom"], pr["PCLK"]["upper"]["margin_high"])), "6-9"),
        ("", "Radiated, typical UI content", ("FAIL", "%+.1f dB (upper %+.1f dB)" % (e["worst_rows"]["typical UI"]["margin_nom"], e["worst_rows_upper"]["typical UI"]["margin_high"])),
         ("PASS", "%+.1f dB (upper %+.1f dB)" % (pr["typical UI"]["nominal"]["margin_nom"], pr["typical UI"]["upper"]["margin_high"])), "6-9"),
        ("", "Radiated, 1-pixel stripes (not a normal mode)", ("FAIL", "%+.1f dB" % e["worst_rows"]["worst pattern"]["margin_nom"]),
         ("FAIL", "%+.1f dB (upper %+.1f dB): the UI must not show it" % (pr["worst pattern"]["nominal"]["margin_nom"], pr["worst pattern"]["upper"]["margin_high"])), "6-9, U1"),
        ("IEC 61000-3-2", "Harmonics, Class A", ("PASS", "worst order %.1f %% of the limit" % hw), ("PASS", "%.1f %% (V_on 20 V)" % hw20), "F1"),
        ("", "Zero-cross firing timing (6.2 and function)", ("RISK", "%d of %d cases lose the half-cycle: h2 %.0f %%, DC %.2f A" % (z["n_missed"], z["n_cases"], fault["worst_classA_pct_(avg/limit or max/1.5limit)"], fault["dc_component_A"])),
         ("PASS", "always fires at %.1f-%.1f V" % tuple(z["V_on_range_when_firing_V"])), "F1"),
        ("IEC 61000-3-3", "Flicker P_lt (limit 0.65)", ("MARGINAL", "%.3f (%.0f %% margin)" % (fl["worst_decided"]["Pst"], (0.65 - fl["worst_decided"]["Pst"]) / 0.65 * 100)),
         ("PASS", "%.3f (%.0f %% margin)" % (fl["worst_decided:1500"]["Pst"], (0.65 - fl["worst_decided:1500"]["Pst"]) / 0.65 * 100)), "F2"),
        ("EN 55014-2", "Surge 1 kV L-N (Table 12)", ("FAIL", "driver %.0f V vs %.0f V; K1 %.0f V vs %.0f V" % (moc["worst"], moc["limit"], k1["worst"], k1["limit"])),
         ("PASS", "%.0f V vs 800 V (%.0f %%); K1 %.0f V" % (s4["worst"], s4["margin_pct"], k1b["worst"])), "1, 2, 3"),
        ("", "Surge parts at 253 Vac steady state", ("MARGINAL", "RV1 TVR14431 %.0f %%" % rv["margin_pct"]), ("MARGINAL", "new TVS %.1f %%; RV1, RV3 %.0f %%" % (tv["margin_pct"], rv["margin_pct"])), "-"),
        ("", "EFT / burst 1 kV (Table 4)", ("FAIL", "U6 input %.1f V vs 6.5 V; false edges %d of 36" % (u6["worst"], len(B["eft"]["zcd_false_edge_cases"]))),
         ("PASS", "%.1f V peak, no false edges" % pe1["worst_abs_max"]), "4, E2"),
        ("", "Voltage dips (Table 13)", ("PASS", "no reset with HLK bulk >= 22 uF"), ("PASS", "unchanged"), "-"),
        ("", "ESD 4 kV on the probe: SELV barrier", ("MEASURE", "FAIL below about %.0f pF (%.2f kV at 20 pF)" % (cr["Cenv 30 pF | relay coil-contact 1500 Vac = 2121 Vpk"], esd["worst"] / 1000)),
         ("MEASURE", "LCR first; with Y1 %.0f V (PASS) but Y1 costs" % y1["worst"]), "5 if needed"),
        ("", "ESD: ADS1115 input (other points PASS)", ("MARGINAL", "%.3f V vs 0.3 V (voltage rule only)" % ads["worst"]), ("MARGINAL", "unchanged"), "-"),
        ("", "ESD: glass over the touch panel", ("NOT SIMULABLE", "bounded by comparison only"), ("MEASURE", "8 kV air on the glass"), "-"),
        ("", "Injected RF 3 V (Table 10)", ("PASS", "TC <= %.2f degC (bound); ZCD %.2f V" % (tcb, inj["ZCD"]["Cio 1.0 pF"]["max_Vpk_at_U6_in"])), ("PASS", "ZCD %.4f V" % inj["ZCD"]["Cio 1.0 pF + 1 nF C0G (scope B)"]["max_Vpk_at_U6_in"]), "4"),
        ("", "RF field 3 V/m: display inputs", ("FAIL", "risk: %.2f V vs %.2f V logic margin" % (ri["lossy Q 10 (nominal cables)"]["panel_input_noise_Vpk_max"], lm)),
         ("PASS", "%.2f V" % ri["lossy Q 10 + panel bonded 19 contacts"]["panel_input_noise_Vpk_max"]), "6"),
        ("", "RF field 3 V/m: thermocouple", ("PASS", "about 0 degC"), ("PASS", "unchanged"), "-"),
        ("", "Touch controller (GT911) under RF and ESD", ("NOT SIMULABLE", "firmware filtering unknown"), ("MEASURE", "bench test"), "-"),
    ]
    return rows


def scorecard_html():
    head = ('<table style="width:100%; border-collapse:collapse;">'
            '<tr><th style="width:12%;">Standard</th><th style="width:26%;">Test</th><th style="width:28%;">As designed</th>'
            '<th style="width:26%;">With the proposed changes</th><th style="width:8%;">Changes</th></tr>')
    body = ""
    for std, test, a, w, ch in scorecard_rows():
        body += "<tr><td><b>%s</b></td><td>%s</td>%s%s<td>%s</td></tr>" % (esc(std), esc(test), chip(*a), chip(*w), esc(ch))
    return head + body + "</table>"


# ------------------------------------------------------------------------------------------------------------------
# page model
# ------------------------------------------------------------------------------------------------------------------
class Doc:
    def __init__(self):
        self.doc = fitz.open(); self.toc = []

    def new(self, section, title):
        p = self.doc.new_page(width=PW, height=PH)
        y = TOP
        if section:
            p.insert_htmlbox(fitz.Rect(ML, y, PW - ML, y + 14), '<p class="sec">%s</p>' % esc(section.upper()), css=CSS, archive=FONTS)
            y += 13
        r = p.insert_htmlbox(fitz.Rect(ML, y, PW - ML, y + 40), '<p class="h1">%s</p>' % esc(title), css=CSS, archive=FONTS)
        y += 40 - r[0] + 8
        self.toc.append((section, title, len(self.doc)))
        return p, y

    def chart(self, p, y, name, caption=None, gap=12):
        src = fitz.open(os.path.join(CH, name + ".pdf"))
        w, h = src[0].rect.width, src[0].rect.height
        x0 = (PW - w) / 2
        p.show_pdf_page(fitz.Rect(x0, y, x0 + w, y + h), src, 0)
        y += h
        if caption:
            y += 3
            r = p.insert_htmlbox(fitz.Rect(ML, y, PW - ML, y + 60), '<p class="cap">%s</p>' % esc(caption), css=CSS, archive=FONTS)
            y += 60 - r[0]
        if y > PH - BOTTOM:
            raise RuntimeError("page overflow on %s: %.0f" % (name, y))
        return y + gap

    def html(self, p, y, html, height=400, gap=10):
        r = p.insert_htmlbox(fitz.Rect(ML, y, PW - ML, y + height), html, css=CSS, archive=FONTS)
        if r[1] < 0.999:
            raise RuntimeError("html scaled down (%.2f), enlarge the box: %s" % (r[1], html[:200]))
        y += height - r[0]
        return y + gap

    def finish(self):
        n = len(self.doc)
        for i, p in enumerate(self.doc):
            p.insert_htmlbox(fitz.Rect(ML, PH - 28, PW - ML - 60, PH - 14), '<p class="small">%s</p>' % esc(FOOT), css=CSS, archive=FONTS)
            p.insert_htmlbox(fitz.Rect(PW - ML - 60, PH - 28, PW - ML, PH - 14), '<p class="small" style="text-align:right;">page %d of %d</p>' % (i + 1, n),
                             css=CSS, archive=FONTS)
        self.doc.set_metadata({"title": "Rev3.0 controller - EMC test simulation results", "author": "EMC simulation campaign (scopes A, B, C)",
                               "subject": "EN 55014-1/-2, IEC 61000-3-2/-3-3 simulated on the Rev3.0 board", "creationDate": fitz.get_pdf_now()})


def tally_chart():
    import numpy as np
    import matplotlib.pyplot as plt
    from common_style import save, W, INK
    rows = scorecard_rows()
    order = ["FAIL", "RISK", "MARGINAL", "NOT SIMULABLE", "MEASURE", "PASS"]
    fig, ax = plt.subplots(figsize=(W, 1.08), gridspec_kw=dict(left=0.17, right=0.99, top=0.74, bottom=0.04))
    for y, (lab, idx) in enumerate((("with the changes", 3), ("as designed", 2))):
        x = 0
        for v in order:
            n = sum(1 for r in rows if r[idx][0] == v)
            if not n:
                continue
            fg, bg = VERD[v]
            ax.barh(y, n, left=x, color=bg, edgecolor="white", height=0.62)
            ax.text(x + n / 2, y, "%s %d" % (v if n > 1 or len(v) < 9 else v.split()[0], n), ha="center", va="center", fontsize=8, color=fg, fontweight="bold")
            x += n
    ax.set_yticks([0, 1]); ax.set_yticklabels(["with the changes", "as designed"], fontsize=8.5)
    ax.set_xlim(0, len(rows)); ax.axis("on"); ax.set_xticks([]); ax.tick_params(axis="y", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(False)
    ax.set_title("The %d rows above, counted by verdict" % len(rows), fontsize=9.5)
    save(fig, "a00_tally")


def tally_html():
    rows = scorecard_rows()
    order = ["FAIL", "RISK", "MARGINAL", "NOT SIMULABLE", "MEASURE", "PASS"]
    cells = ""
    for v in order:
        a = sum(1 for r in rows if r[2][0] == v); w = sum(1 for r in rows if r[3][0] == v)
        fg, bg = VERD[v]
        cells += ('<td style="background-color:%s; text-align:center; border-bottom:0px;"><b style="color:%s;">%s</b><br/>'
                  '%d as designed &#8594; %d with changes</td>' % (bg, fg, v, a, w))
    return ('<p class="cap"><b>The %d rows counted by verdict</b></p><table style="width:100%%; border-collapse:collapse;"><tr>%s</tr></table>'
            % (len(rows), cells))


def build():
    D = Doc()
    # ---------------------------------------------------------------- 1 scorecard
    p, y = D.new("", "Rev3.0 controller: EMC test simulation, the one-page answer")
    y = D.html(p, y - 4, '<p class="cap">READARK filament dryer / print annealer, hardware Rev3.0 (230 VAC, 1 kW heater on a BTA24 triac, HLK-10M05, ESP32, 7-inch RGB TFT). '
               'Every test of EN 55014-1, EN 55014-2, IEC 61000-3-2 and IEC 61000-3-3 simulated on the current board by three engineers (scopes A, B, C), reviewed and final, %s. '
               '<b>As designed</b> = current board with the decided firmware (1000-cycle burst frame, today\'s zero-cross timing).</p>' % DATE, height=60, gap=6)
    y = D.html(p, y, '<table style="width:100%; border-collapse:collapse;"><tr><td style="background-color:#DCD9F2; border-bottom:0px; font-size:8.5pt;">'
               '<b style="color:#3B3486;">These are simulations, not accredited measurements.</b> MARGINAL = less than 6 dB or 20 % margin. '
               'MEASURE = the verdict depends on a bench measurement. RISK = a finding outside the limit rules. Radiated results carry about ±10 dB.</td></tr></table>',
               height=40, gap=6)
    y = D.html(p, y, scorecard_html(), height=640, gap=2)
    y = D.html(p, y, '<p class="small">Changes: 1-9 hardware (board map, page 22), F1 = fire at the centre of the measured zero-cross window, F2 = 1500-cycle burst frame, '
               'E2 = firmware ZCD edge check, U1 = user-interface rule. With the changes every simulated test passes except the MEASURE items, the ADS1115 '
               'and 253 Vac part ratings (MARGINAL) and 1-pixel stripes (not a normal operating mode).</p>', height=40)
    y = D.html(p, y + 4, tally_html(), height=60)
    # ---------------------------------------------------------------- 2 contents (filled later)
    pc, yc = D.new("", "Contents and how to read the charts")
    contents_page = (pc, yc)
    # ---------------------------------------------------------------- 3 margins
    p, y = D.new("1  Margins at a glance", "Every test on one scale: as designed (circles) and with the changes (squares)")
    y = D.chart(p, y, "m01_margins", "Dots are the key number of each test; the whisker shows the worst Monte Carlo run (conducted) or the upper end of the uncertainty band "
                "(radiated: worst harmonic at Q 30 plus cable envelope; display inputs: Q 30). Dips have no margin number: no reset in any corner with bulk >= 22 uF. "
                "Radiated rows carry about +-10 dB of model uncertainty.")
    # ---------------------------------------------------------------- 4 zero cross
    p, y = D.new("2  Zero-cross firing", "One firmware timing fault links conducted emission, harmonics and function")
    y = D.chart(p, y, "z01_zcd_timing", "The ISR fires 230 us after the falling /ZCD edge, which marks the START of the opto window, not the zero. With a low-CTR H11AA1 "
                "(datasheet minimum 20 %) the 150 us pulse ends before the zero and the half-cycle is lost. F1 fires a >= 300 us pulse at the window centre. Shaded band: where the "
                "triac turns on, 8.7-17.7 V (+85 to +173 us).")
    y = D.chart(p, y, "z02_zcd_links", "(a) A later turn-on costs conducted margin; F1 keeps the turn-on at the gate threshold. (b) A lost half-cycle is half-wave control, which "
                "IEC 61000-3-2 6.2 prohibits above 100 W. (c) Low-CTR parts miss in every case; scope B found the same edge advance independently.")
    # ---------------------------------------------------------------- 5-7 conducted
    p, y = D.new("3  Conducted emission (EN 55014-1, 150 kHz to 30 MHz)", "Heater on: the neutral line at 0.5-1 MHz sets the margin")
    y = D.chart(p, y, "c01_ce_spectrum", "Quasi-peak (QP) and average (AV) levels at the line impedance stabilisation network (LISN) against Table 5. 'All bad ends' = every "
                "parameter at once (V_on 40 V). Spectra from A's first model; A's final model (probe capacitance, L1 core loss) gives %+.1f dB as designed and %+.1f dB with F1 "
                "(V_on 18 V) at that corner." % (A["A1_crosscheck_scopeB"]["all_worst_corner"]["as designed (V_on 40 V) | baseline"]["QP_N"]["margin_dB"],
                                                  A["A1_crosscheck_scopeB"]["all_worst_corner"]["F1 (V_on 18 V) | baseline"]["QP_N"]["margin_dB"]))
    cf = MC.ce_final()
    p, y = D.new("3  Conducted emission", "Monte Carlo: %d of %d runs below 6 dB today, none with F1" % (cf[("as designed", "QP")]["n_below_6dB"], cf["n"]))
    y = D.chart(p, y, "c02_ce_montecarlo", "Histogram and scatter: A's first model, the only one with per-run data. The scorecard and page 3 use A's final model (summary "
                "numbers printed in the chart). V_on dominates (rank correlation -0.87); the oven's chassis-to-reference-plane capacitance C_ch comes second.")
    p, y = D.new("3  Conducted emission", "What F1 cannot fix: the oven construction and the power supply module")
    y = D.chart(p, y, "c03_ce_oven", "QP margin with F1 for heater-to-chassis C_hc and chassis-to-reference-plane C_ch; the black line encloses >= 6 dB. Keep the oven inside "
                "it (for example C_ch <= 50 pF, or C_hc <= 100 pF); Y1 would add at most 2.6 dB.")
    y = D.chart(p, y, "c04_ce_hlk", "With the heater off only the HLK-10M05 emits, and its internals are not published: the curves show the noise current it may produce before "
                "the limit is reached. The board removes up to 6.5 dB less than Hi-Link's reference circuit at 1.2-15 MHz, so measure with the heater off.")
    # ---------------------------------------------------------------- 8 harmonics
    p, y = D.new("4  Harmonics (IEC 61000-3-2, Class A)", "Harmonic currents pass with a wide margin, as long as no half-cycle is lost")
    y = D.chart(p, y, "l01_harmonics", "Top: each order as a percentage of its Class A limit (log scale). Bottom: the worst order against heater duty for the current sigma-delta "
                "firmware and the decided burst-frame firmware; the dashed line is the 6.2 / Table 3 rule that applies to heating elements.")
    # ---------------------------------------------------------------- 9 flicker + clicks
    p, y = D.new("5  Flicker (IEC 61000-3-3) and clicks (EN 55014-1 4.4)", "Flicker: F2 turns MARGINAL into PASS; clicks pass")
    y = D.chart(p, y, "l02_flicker", "P_st against heater duty; at a steady duty P_lt = P_st, so the 0.65 line decides. The limits and the reference impedance are NOT read "
                "from the standard (the preview stops before clause 5); they come from Keysight note 5964-1917E. The current sigma-delta firmware fails (P_st 1.69).")
    y = D.chart(p, y, "c05_clicks", "Relay K1 switches the fan about once an hour: its arcs are exempt under 5.4.3.2 / 5.4.3.4 (the 3 ms arc would exceed even L + 44 dB). "
                "Triac bursts stay below the IF reference at V_on 20 V, so the continuous limits of the conducted test apply.")
    # ---------------------------------------------------------------- 10-11 surge
    p, y = D.new("6  Surge 1 kV line to neutral (EN 55014-2 5.6, Table 12)", "Today the triac driver and the fan relay are over-stressed")
    y = D.chart(p, y, "s01_surge_waves", "Worst cases of 48 sweeps (polarity, heater, K1, varistor tolerance, L40 saturation). Left: voltage across the triac (solid) and at "
                "LINE_FILT (dashed). Right: across the open K1 contact, whose only rating is the 50 Hz dielectric test.")
    y = D.chart(p, y, "s02_surge_stress", "Worst stress of each part as a share of its rating, as designed. No fuse opens. The HLK-10M05 bulk is a black box: our stress is "
                "0.94 x what Hi-Link's own reference circuit produces.")
    p, y = D.new("6  Surge", "The fix: an 800 V driver, a TVS across the triac and a second varistor before L40")
    y = D.chart(p, y, "s03_surge_ladder", "Each step re-simulated. PASS needs >= 20 % margin to 800 V, i.e. <= 640 V. A behavioural breakover model of the 600 V driver "
                "was inconclusive; either way it is operated beyond its absolute maximum. The TVS stand-off at 253 Vac is only 4.8 % (MARGINAL).")
    y = D.chart(p, y, "s04_frontend_sketch", "Numbers match the board map (page 22). The 800 V driver (1) and the TVS (2) protect the triac side, RV3 (3) protects K1, "
                "the 1 nF (4) fixes EFT, and Y1 (5) is fitted only if the LCR reading of the HLK barrier is too low.")
    # ---------------------------------------------------------------- 12 EFT
    p, y = D.new("7  Electrical fast transients, 1 kV burst (EN 55014-2 5.2, Table 4)", "A 1 nF capacitor on the zero-cross node fixes both EFT findings")
    y = D.chart(p, y, "e01_eft_waves", "Zero-cross (ZCD) node at the U6 Schmitt-trigger input during one burst pulse, worst of 36 stray-capacitance corners. Today the node "
                "reaches %.1f V on a 6.5 V input (absolute maximum) and dips below the switching threshold. With 1 nF C0G the idle-high node stays within %.2f-%.2f V "
                "in all %d corners." % (B["eft"]["worst"]["V_ZC_max"], B["eft"]["proposal_P_E1_1nF_on_ZCD_node"]["worst_off_min"],
                                         B["eft"]["proposal_P_E1_1nF_on_ZCD_node"]["worst_abs_max"], len(B["eft"]["proposal_P_E1_1nF_on_ZCD_node"]["rows"])))
    y = D.chart(p, y, "e02_eft_summary", "Left: lowest node voltage in every 'transistor off' corner; below VT- a false zero-cross edge is registered. Right: the heater power "
                "error during bursts with today's firmware and with P-E2 (an edge counts only if the pin is still low 50 us later). Criterion B is met functionally.")
    # ---------------------------------------------------------------- 13 dips
    p, y = D.new("8  Voltage dips (EN 55014-2 5.7, Table 13)", "Dips pass: the rails do not move with the derived HLK bulk capacitance")
    y = D.chart(p, y, "d01_dips", "HLK bulk, +5 V and +3V3 through the three Table 13 dips. Bulk 22 uF is derived from the HLK datasheet load curve; only 10 uF with a 90 V "
                "drop-out resets the ESP32. Even then the heater cannot run during reset (TRIG floats, the driver LED has no current); criterion C allows the restart.")
    # ---------------------------------------------------------------- 14 ESD
    p, y = D.new("9  Electrostatic discharge (EN 55014-2 5.1, Table 1)", "ESD: the verdict hangs on one LCR reading of the HLK-10M05")
    y = D.chart(p, y, "x01_esd_cbar", "4 kV contact on the thermocouple probe (assumed accessible, grounded junction). The floating SELV side shares the gun's charge with "
                "the barrier capacitance C_bar. Read the LCR value on the top axis; scope B's guide: >= about 210 pF passes, 140-200 pF marginal, below about 120 pF fails.")
    y = D.chart(p, y, "x02_esd_other", "Other discharge points as designed. The ADS1115 input reaches -0.296 V against -0.3 V, but its pin current is 7 uA against 10 mA. "
                "ESD on the glass cannot be simulated honestly: our 3 mm glass couples 0.16 x what the bare touch cover would; test 8 kV air on the glass.")
    # ---------------------------------------------------------------- 15-17 radiated
    p, y = D.new("10  Radiated emission (EN 55014-1 4.3.4, 30 to 1000 MHz)", "The mechanism: display return current drives the panel against the PCB")
    y = D.chart(p, y, "r01_re_mechanism", "The FPC returns the current of 28 fast lines on only 3 ground pins; the voltage across that return drives the panel metal against "
                "the PCB ground. The pair resonates near 182 MHz and the attached cables radiate. Common-mode (CM) results carry about +-10 dB.")
    y = D.chart(p, y, "r04_re_cables", "Common-mode current each cable may carry at the limit against the estimate for PCLK (Q 3 to Q 30 bar). The cables carry 25-36 dB "
                "too much: shielding the cables alone cannot close this gap; the source on the FPC return must be reduced.")
    p, y = D.new("10  Radiated emission", "As designed: PCLK alone exceeds Table 9 by up to 36 dB")
    y = D.chart(p, y, "r02_re_spectrum", "Field at 3 m per harmonic: dot at the nominal loss (Q 10), bar from Q 3 to Q 30 plus the cable and barrier envelope. Even harmonics of "
                "PCLK fall below the axis. Blue squares: worst harmonic with all four changes; only worst rows exist for the changes, not full spectra. Change 9 is now %s." % REPORT_ONLY["j10_option_name"][0])
    p, y = D.new("10  Radiated emission", "The proposal ladder: all four changes are needed for PCLK")
    y = D.chart(p, y, "r05_re_ladder", "Margin of the worst harmonic, nominal (dot) and upper end of the band (whisker), FAR 3 m; SAC 10 m gives the same picture. The floating-"
                "frame row checks the assumption that the panel frame is tied to panel ground; it also fails, so the bonding is needed either way.")
    y = D.chart(p, y, "r03_re_power", "Energy check of the model: the power delivered into the structure never exceeds what the display drivers can supply (an earlier, "
                "withdrawn model exceeded it by 11.9 dB).")
    # ---------------------------------------------------------------- 18 RF immunity
    p, y = D.new("11  RF immunity (EN 55014-2 5.4 injected, 5.5 radiated, criterion A)", "RF immunity: the thermocouple is safe; the display inputs need the bonding")
    y = D.chart(p, y, "f01_rf_immunity", "Left: thermocouple (TC) error against the 0.5 degC criterion A tolerance proposed by scope C for the owner to confirm. Right: "
                "common-mode noise at the panel inputs under 3 V/m with 80 % AM at 840 MHz, Q 3 to Q 30 bar; 0.99 V = 0.3 x VDD.")
    y = D.chart(p, y, "f02_rf_zcd", "Mains-port injection reaches the zero-cross node through the opto's input-output capacitance. The 1 nF of P-E1 also removes this path. "
                "Touch (GT911) behaviour depends on its firmware filtering and is not simulable.")
    # ---------------------------------------------------------------- 19 Y1
    p, y = D.new("12  The Y1 capacitor (proposal P-D1)", "Y1 fixes the ESD barrier but costs conducted emission and thermocouple accuracy")
    y = D.chart(p, y, "y01_y1_tradeoff", "Y1 (1 nF, SELV ground to neutral) collapses the ESD barrier voltage, but it also opens a 25-35 dB easier path for SELV ground noise: "
                "the buck (0.58 MHz) and boost (1.2 MHz) switching then likely fail the AV limit, and the grounded TC probe bound exceeds 0.5 degC. Measure before fitting it.")
    # ---------------------------------------------------------------- 20 PDN
    p, y = D.new("13  Power distribution network (PDN)", "PDN: one resonance on the +5V island sits on the 15th PCLK harmonic")
    ps = MC.pdn_summary()
    y = D.chart(p, y, "p01_pdn", "Cavity model of the In2 planes. Scope C rejected the first proposal, %s: it creates a %.1f ohm peak at %.1f MHz. %s X7R 0402, one each side of "
                "the J10 vias with its own GND via, takes 498.5 MHz from %.0f to %.1f ohm with no peak below 300 MHz. Every undamped option keeps a %.0f-%.0f ohm mode near 824 MHz; only "
                "the series-resistor options damp it. Option curves: C's stored 100-point sweep; dots: peaks from C's fine sweep."
                % (REPORT_ONLY["j10_rejected_name"][0], ps["rej_peak"][1], ps["rej_peak"][0], REPORT_ONLY["j10_option_name"][0], ps["none_498"], ps["rec_498"],
                   ps["m824"][0], ps["m824"][1]))
    # ---------------------------------------------------------------- 21 layout
    p, y = D.new("13  Layout audit", "Layout audit map of the current board")
    y = D.chart(p, y, "p02_layout_map", None, gap=6)
    notes = json.load(open(os.path.join(CH, "p02_layout_notes.json"), encoding="utf-8"))
    y = D.html(p, y, "".join('<p class="cap" style="margin-bottom:3pt;">%s</p>' % esc(n) for n in notes), height=150)
    om = C["emission"]["other_sources_min_margin_dB"]
    y = D.chart(p, y, "p03_hot_loops", "Board-level differential-mode sources keep their radiated margin (minimum %.0f dB for the 8080 data bus, %.0f dB buck, "
                "%.0f dB boost, %.0f dB crystal): the radiated problem is the display's common mode, not these loops." % (om["8080 data"], om["buck"], om["boost"], om["crystal"]))
    # ---------------------------------------------------------------- 22 where the changes go
    p, y = D.new("14  Where the changes go", "Nine hardware changes on the board, plus firmware, UI and mechanical items")
    y = D.chart(p, y, "w01_changes_map", None, gap=4)
    y = D.chart(p, y, "w02_changes_matrix", "The 19 contacts are drawn at an illustrative spacing; their real positions follow the frame design. RV3 has no footprint yet: "
                "it belongs on LINE_FUSED between F3 and L40.", gap=4)
    # ---------------------------------------------------------------- 23 measure first
    p, y = D.new("15  What to measure first", "Three bench checks settle the open verdicts")
    y = D.chart(p, y, "w03_measure_first", "1: thresholds = C_bar crossings minus about 5 pF for the optos, relay and heatsink. 2: the panel datasheet lists only GND pins 3, 29 "
                "and 36, so the frame connection is an assumption. 3: the board's extra insertion loss falls to -6.5 dB at 1.2-15 MHz relative to Hi-Link's circuit.")
    y = D.html(p, y, '<p class="cap"><b>Next bench tests named by the engineers:</b> surge 1 kV at 90/270 deg with a 1 kV differential probe across the triac; EFT with an '
               'ISR count log; dips with a programmable source; near-field and FAR scan with and without the panel bonding; LISN with and without Y1; injection with '
               'a grounded and an insulated thermocouple probe; 8 kV air on the glass centre, corners and over the FPC tails.</p>', height=70)
    # ---------------------------------------------------------------- 24 coverage
    p, y = D.new("16  What the simulation could not cover", "Coverage of the campaign")
    y = D.chart(p, y, "w04_coverage", "Blank cell = not relevant. Not simulable: HLK-10M05 internals (bounded only), touch ESD and immunity, the ESP32 module "
                "(40/80/240 MHz clocks, radio), relay arc statistics, firmware lock-up. Radio rules under RED (EN 300 328, EN 301 489-1/-17, EN 62311) need their own assessment.")
    # ---------------------------------------------------------------- contents
    yc = contents_page[1]; pc = D.doc[1]
    seen = set()
    for sec, title, pg in D.toc:
        if pg <= 2:
            continue
        grp = sec.split()[0]
        if grp not in seen:
            seen.add(grp)
            yc += 3
            txt = '<p class="cap"><b>%s</b> &#160; %s</p>' % (esc(sec), esc(title))
        else:
            txt = '<p class="cap" style="margin-left:14pt;">%s</p>' % esc(title)
        r = pc.insert_htmlbox(fitz.Rect(ML, yc, PW - ML - 40, yc + 24), txt, css=CSS, archive=FONTS)
        pc.insert_htmlbox(fitz.Rect(PW - ML - 36, yc, PW - ML, yc + 14), '<p class="cap" style="text-align:right;">%d</p>' % pg, css=CSS, archive=FONTS)
        yc += 24 - r[0] + 1.5
    yc += 10
    print("contents end", yc)
    key = ('<table style="width:100%%; border-collapse:collapse;">'
           '<tr><th colspan="2">How to read the charts</th></tr>'
           '<tr><td style="width:34%%;"><b style="color:%s;">orange-red line / circle</b></td><td>as designed (current board, decided firmware)</td></tr>'
           '<tr><td><b style="color:%s;">blue line / square</b></td><td>with the proposed changes</td></tr>'
           '<tr><td><b>black dashed line</b></td><td>limit or part rating, labelled on the chart</td></tr>'
           '<tr><td style="background-color:%s;"><b style="color:%s;">PASS</b></td><td>at least 6 dB or 20 %% margin</td></tr>'
           '<tr><td style="background-color:%s;"><b style="color:%s;">MARGINAL</b></td><td>0-6 dB or 0-20 %% margin (also RISK: a finding outside the limit rules)</td></tr>'
           '<tr><td style="background-color:%s;"><b style="color:%s;">FAIL</b></td><td>above the limit or rating</td></tr>'
           '<tr><td style="background-color:%s;"><b style="color:%s;">NOT SIMULABLE</b></td><td>cannot be simulated honestly; a bound or argument is given</td></tr>'
           '<tr><td style="background-color:%s;"><b style="color:%s;">MEASURE</b></td><td>the verdict depends on a bench measurement</td></tr>'
           '</table>') % (AS, WITH, VERD["PASS"][1], VERD["PASS"][0], VERD["MARGINAL"][1], VERD["MARGINAL"][0], VERD["FAIL"][1], VERD["FAIL"][0],
                          VERD["NOT SIMULABLE"][1], VERD["NOT SIMULABLE"][0], VERD["MEASURE"][1], VERD["MEASURE"][0])
    yc = D.html(pc, yc, key, height=215, gap=10); print("key end", yc)
    abbr = ("<p class='cap'><b>Abbreviations.</b> AV average detector; CE conducted emission; CM / DM common / differential mode; CTR current transfer ratio of the "
            "opto; EFT electrical fast transient (burst); ESD electrostatic discharge; FAR fully anechoic room; FPC flexible printed circuit (display tail); "
            "HLK the HLK-10M05 mains power module; LISN line impedance stabilisation network; MC Monte Carlo; PCLK 33.3 MHz pixel clock; PDN power distribution "
            "network; Q quality factor of the panel-PCB resonance; QP quasi-peak detector; RE radiated emission; SAC semi-anechoic chamber; SELV the low-voltage side; "
            "TC thermocouple; UI user interface; V_on triac turn-on voltage; ZCD zero-cross detector. F1, F2, E2, U1 and 1-9 are the proposed changes (page 22).</p>")
    D.html(pc, yc, abbr, height=110)
    D.finish()
    D.doc.save(OUT, garbage=4, deflate=True)
    print("wrote", OUT, len(D.doc), "pages")


if __name__ == "__main__":
    build()
