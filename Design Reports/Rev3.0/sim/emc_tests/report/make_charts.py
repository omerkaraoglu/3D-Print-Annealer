"""Charts for Rev3.0_EMC_Test_Simulation_Results.pdf -> report/charts/<name>.pdf (vector, placed 1:1) and .png (preview).

Every number comes from the three scopes' results.json, from report/curves/*.json (regen_curves.py, the engineers'
scripts run read-only) or from common_style.REPORT_ONLY (file and section given there).
Run: python -X utf8 make_charts.py [chart names...]
"""
import math, sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from common_style import *

ACON = A["A1_conducted"]


def bv(test_sub, part_sub):
    """row of scope B's verdict table"""
    for r in B["verdict_table"]:
        if test_sub in r["test"] and part_sub in r["part"]:
            return r
    raise KeyError((test_sub, part_sub))


# =====================================================================================================================
# 1. margins at a glance
# =====================================================================================================================
def margin_rows():
    ce = ce_final()
    e = C["emission"]
    ri = C["radiated_immunity"]; lm = REPORT_ONLY["display_logic_margin_V"][0]
    zt = REPORT_ONLY["zcd_toggle_threshold_V"][0]
    inj = C["injected"]
    tc_bound = max(v["dT_worst_bound_degC"] for k, v in inj.items() if k.startswith("mains port") and isinstance(v, dict))
    pr = {c: combo(c)[0] for c in ("PCLK", "typical UI", "worst pattern")}
    dbrows = [  # label, before (main, whisker or None), after (main, whisker)
        ("Conducted emission, quasi-peak", (ce[("as designed", "QP")]["p5"], ce[("as designed", "QP")]["min"]),
         (ce[("F1", "QP")]["p5"], ce[("F1", "QP")]["min"])),
        ("Conducted emission, average", (ce[("as designed", "AV")]["p5"], ce[("as designed", "AV")]["min"]),
         (ce[("F1", "AV")]["p5"], ce[("F1", "AV")]["min"])),
        ("Radiated emission, PCLK harmonics", (e["worst_rows"]["PCLK"]["margin_nom"], e["worst_rows_upper"]["PCLK"]["margin_high"]),
         (pr["PCLK"]["nominal"]["margin_nom"], pr["PCLK"]["upper"]["margin_high"])),
        ("Radiated emission, typical UI", (e["worst_rows"]["typical UI"]["margin_nom"], e["worst_rows_upper"]["typical UI"]["margin_high"]),
         (pr["typical UI"]["nominal"]["margin_nom"], pr["typical UI"]["upper"]["margin_high"])),
        ("Radiated emission, 1-pixel stripes", (e["worst_rows"]["worst pattern"]["margin_nom"], e["worst_rows_upper"]["worst pattern"]["margin_high"]),
         (pr["worst pattern"]["nominal"]["margin_nom"], pr["worst pattern"]["upper"]["margin_high"])),
        ("RF field 3 V/m, display inputs", (db(lm / ri["lossy Q 10 (nominal cables)"]["panel_input_noise_Vpk_max"]),
                                             db(lm / ri["lossy Q 30 (nominal cables)"]["panel_input_noise_Vpk_max"])),
         (db(lm / ri["lossy Q 10 + panel bonded 19 contacts"]["panel_input_noise_Vpk_max"]), None)),
        ("Injected RF 3 V, ZCD node", (db(zt / inj["ZCD"]["Cio 1.0 pF"]["max_Vpk_at_U6_in"]), None),
         (db(zt / inj["ZCD"]["Cio 1.0 pF + 1 nF C0G (scope B)"]["max_Vpk_at_U6_in"]), None)),
        ("Injected RF 3 V, thermocouple", (db(REPORT_ONLY["tc_criterion_degC"][0] / tc_bound), None),
         (db(REPORT_ONLY["tc_criterion_degC"][0] / tc_bound), None)),
    ]
    fl = A["A5_flicker"]; h = A["A4_harmonics"]
    harm_worst = max(v[0] for k, v in h["summary_pct_of_limit"].items() if "decided" in k or "100pct" in k)
    harm_f1 = max(v[0] for k, v in h["summary_pct_of_limit"].items() if ("decided" in k or "100pct" in k) and "V_on=20V" in k)
    pctrows = [
        ("Surge: triac driver U5 (600 V part)", bv("Surge 1 kV L-N", "MOC3052")["margin_pct"], bv("P-S1+P-S4", "800 V driver")["margin_pct"]),
        ("Surge: triac Q1 BTA24", bv("Surge 1 kV L-N", "BTA24 Q1")["margin_pct"], bv("P-S1+P-S4", "Q1 BTA24")["margin_pct"]),
        ("Surge: relay K1 open contact", bv("Surge 1 kV L-N", "K1 open")["margin_pct"], bv("Surge, P-S2b", "K1")["margin_pct"]),
        ("Surge parts at 253 Vac (RV1 / TVS)", bv("Continuous check", "TVR14431")["margin_pct"], bv("Continuous check", "1.5KE440CA")["margin_pct"]),
        ("Surge: lowest other part (R6/R7)", bv("Surge 1 kV L-N", "R6/R7")["margin_pct"], bv("Surge 1 kV L-N", "R6/R7")["margin_pct"]),
        ("EFT: U6 input vs 6.5 V abs. max", bv("EFT 1 kV", "U6 input")["margin_pct"],
         (6.5 - B["eft"]["proposal_P_E1_1nF_on_ZCD_node"]["worst_abs_max"]) / 6.5 * 100),
        ("EFT: triac gate vs VGD 0.2 V", bv("EFT 1 kV", "gate")["margin_pct"], bv("EFT 1 kV", "gate")["margin_pct"]),
        ("ESD probe: SELV barrier, C_bar 20 pF", bv("ESD 4 kV contact", "Barrier")["margin_pct"], bv("ESD, proposal P-D1", "Barrier")["margin_pct"]),
        ("ESD probe: ADS1115 input", bv("ESD 4 kV contact", "ADS1115")["margin_pct"], bv("ESD 4 kV contact", "ADS1115")["margin_pct"]),
        ("Harmonics, worst order (Class A)", 100 - harm_worst, 100 - harm_f1),
        ("Harmonics if a half-cycle is lost", 100 - h["results"]["fault_half_wave"]["worst_classA_pct_(avg/limit or max/1.5limit)"], 100 - harm_f1),
        ("Flicker P_lt (limit 0.65)", (fl["limits"]["Plt"] - fl["worst_decided"]["Pst"]) / fl["limits"]["Plt"] * 100,
         (fl["limits"]["Plt"] - fl["worst_decided:1500"]["Pst"]) / fl["limits"]["Plt"] * 100),
        ("Flicker P_st (limit 1.0)", (1 - fl["worst_decided"]["Pst"]) * 100, (1 - fl["worst_decided:1500"]["Pst"]) * 100),
        ("Dips: 3V3 minimum vs 2.43 V reset", bv("Dip 40 %", "3V3")["margin_pct"], bv("Dip 40 %", "3V3")["margin_pct"]),
    ]
    return dbrows, pctrows


def chart_margins():
    from matplotlib.transforms import blended_transform_factory
    dbrows, pctrows = margin_rows()
    fig = plt.figure(figsize=(W, 9.35))
    gs = fig.add_gridspec(2, 1, height_ratios=[len(dbrows) + 1.0, len(pctrows) + 1.0], hspace=0.34, left=0.36, right=0.975, top=0.925, bottom=0.05)
    panels = [(fig.add_subplot(gs[0]), dbrows, "dB", (-62, 62), 6, "margin to the limit (dB)"),
              (fig.add_subplot(gs[1]), [(r[0], (r[1], None), (r[2], None)) for r in pctrows], "%", (-100, 100), 20,
               "margin to the limit or rating (%) = (limit - value) / limit")]
    titles = ["dB rows: radiated emission is the big gap today", "% rows: surge, EFT and the ESD barrier fail today"]
    pending = []
    for (ax, rows, unit, xl, mband, xlabel), title in zip(panels, titles):
        n = len(rows)
        ax.set_xlim(*xl); ax.set_ylim(-0.6, n - 0.4)
        ax.axvspan(xl[0], 0, color=VERD["FAIL"][1], lw=0, zorder=0)
        ax.axvspan(0, mband, color=VERD["MARGINAL"][1], lw=0, zorder=0)
        ax.axvspan(mband, xl[1], color=VERD["PASS"][1], lw=0, zorder=0, alpha=0.6)
        tr = blended_transform_factory(ax.transData, ax.transAxes)
        from matplotlib.transforms import offset_copy
        tro = offset_copy(tr, fig=fig, y=3, units="points")
        ax.text((xl[0] + 0) / 2, 1.0, "FAIL", transform=tro, ha="center", va="bottom", fontsize=8, color=VERD["FAIL"][0], fontweight="bold", clip_on=False)
        ax.text(mband / 2, 1.0, "MARGINAL", transform=tro, ha="center", va="bottom", fontsize=8, color=VERD["MARGINAL"][0], fontweight="bold", clip_on=False)
        ax.text((mband + xl[1]) / 2, 1.0, "PASS", transform=tro, ha="center", va="bottom", fontsize=8, color=VERD["PASS"][0], fontweight="bold", clip_on=False)
        ax.axvline(0, color=LIM, lw=1.0, zorder=1)
        ax.grid(False)
        ys = np.arange(n)[::-1]
        for y, (lab, bef, aft) in zip(ys, rows):
            for (main, wh), col, mk, dy in ((bef, AS, "o", 0.21), (aft, WITH, "s", -0.21)):
                yy = y + dy
                mc = max(min(main, xl[1] - 1), xl[0] + 1)
                if wh is not None:
                    w = max(min(wh, xl[1] - 1), xl[0] + 1)
                    ax.plot([mc, w], [yy, yy], color=col, lw=1.6, zorder=3, solid_capstyle="butt")
                    ax.plot([w], [yy], marker="|", color=col, ms=7, zorder=3)
                ax.plot([mc], [yy], marker=mk, color=col, ms=5.5, zorder=4, mec="white", mew=0.6)
                f1 = lambda v: "0.0" if abs(v) < 0.05 else "%+.1f" % v
                txt = f1(main) + (" (%s)" % f1(wh) if wh is not None else "") + (" dB" if unit == "dB" else " %")
                right = max(mc, wh if wh is not None else mc); left = min(mc, wh if wh is not None else mc)
                pending.append((ax, [(right, yy, "left", "center", 6, 0), (left, yy, "right", "center", -6, 0),
                                     (max(right, mband), yy, "left", "center", 6, 0), (xl[1], yy, "right", "center", -3, 0)], txt, col))
        ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=8)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel(xlabel)
        ax.set_title(title, fontsize=9, loc="left", pad=16)
    h = [Line2D([], [], marker="o", color=AS, ls="none", ms=5.5, label="as designed"),
         Line2D([], [], marker="s", color=WITH, ls="none", ms=5.5, label="with the proposed changes"),
         Line2D([], [], color=INK2, lw=1.6, marker="|", ms=7, label="whisker: worst Monte Carlo run, or upper end of the uncertainty band")]
    fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.01, 1.0), ncol=3, fontsize=8, handletextpad=0.4, columnspacing=1.2)
    pl = Placer(fig)
    for ax, cands, txt, col in pending:
        pl.place(ax, cands, txt, fontsize=8, color=col, zorder=5)
    save(fig, "m01_margins")


# =====================================================================================================================
# 2. zero-cross firing
# =====================================================================================================================
def chart_zcd_timing():
    from matplotlib.transforms import offset_copy
    rows = A["A0_zcd_timing"]["rows"]
    low = [r for r in rows if r["ctr10_pct"] == 20 and r["VT+"] == 1.5 and r["T_factor"] == 1.0][0]
    high = [r for r in rows if r["ctr10_pct"] == 100 and r["VT+"] == 1.5 and r["T_factor"] == 1.0][0]
    von = A["A0_zcd_timing"]["V_on_range_when_firing_V"]
    w = 2 * np.pi * 50; vpk = 230 * math.sqrt(2)
    X0, X1 = -1300, 1300
    t = np.linspace(X0, X1, 2000)
    v = vpk * np.sin(w * t * 1e-6)
    t_latch = math.asin(3.5 / vpk) / w * 1e6
    t_on = [math.asin(x / vpk) / w * 1e6 for x in von]
    fig = plt.figure(figsize=(W, 6.1))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.75], hspace=0.07, left=0.2, right=0.985, top=0.935, bottom=0.075)
    ax = fig.add_subplot(gs[0]); bx = fig.add_subplot(gs[1], sharex=ax)
    for r, col in ((low, S5), (high, S3)):
        for sgn in (1, -1):
            ax.axhline(sgn * r["window_threshold_V"], color=col, lw=0.9, ls=":")
    ax.axhspan(von[0], von[1], color=S4, alpha=0.35, lw=0)
    ax.plot(t, v, color=INK, lw=1.5)
    ax.set_ylim(-140, 140); ax.set_ylabel("mains voltage (V)")
    up = lambda d: offset_copy(ax.transData, fig=fig, y=d, units="points")
    ax.text(X0 + 15, low["window_threshold_V"], "H11AA1 window, CTR 20 %%: |v| < %.0f V (+-%d us)" % (low["window_threshold_V"], low["half_window_us"]),
            fontsize=8, color="#9B4F80", va="bottom", transform=up(3))
    ax.text(X1 - 15, -high["window_threshold_V"], "window, CTR 100 %%: |v| < %.0f V (+-%d us)" % (high["window_threshold_V"], high["half_window_us"]),
            fontsize=8, color="#00704F", va="top", ha="right", transform=up(-3))
    ax.text(X0 + 15, von[0], "triac gate threshold %.1f-%.1f V (shaded)" % tuple(von), fontsize=8, va="top", color="#7A5000", transform=up(-3))
    ax.axvline(0, color=INK2, lw=0.8)
    ax.text(0, -136, "zero crossing", fontsize=8, color=INK2, va="bottom", transform=offset_copy(ax.transData, fig=fig, x=4, units="points"))
    ax.set_title("Today's gate pulse can end before the zero crossing; F1 fires at the window centre", fontsize=9.5)
    plt.setp(ax.get_xticklabels(), visible=False)
    lanes = []
    def lane(y, segs, col, lab, low_active=False):
        hi, lo = (y + 0.62, y) if not low_active else (y, y + 0.62)
        xs = [X0]; ys = [lo]
        for a_, b_ in segs:
            xs += [a_, a_, b_, b_]; ys += [lo, hi, hi, lo]
        xs.append(X1); ys.append(lo)
        bx.plot(xs, ys, color=col, lw=2.0, solid_joinstyle="miter")
        lanes.append((y, lab))
    d_off = 20
    yv = [8.3, 7.2, 5.9, 4.8, 3.3, 2.0]
    lane(yv[0], [(-low["half_window_us"] + d_off, low["half_window_us"])], S5, "/ZCD, CTR 20 %", low_active=True)
    lane(yv[1], [(-high["half_window_us"] + d_off, high["half_window_us"])], S3, "/ZCD, CTR 100 %", low_active=True)
    lane(yv[2], [(low["pulse_start_us_rel_zero"], low["pulse_end_us"])], AS, "gate today, CTR 20 %")
    lane(yv[3], [(high["pulse_start_us_rel_zero"], high["pulse_end_us"])], AS, "gate today, CTR 100 %")
    lane(yv[4], [(-150, 150)], WITH, "gate with F1, CTR 20 %")
    lane(yv[5], [(-150, 150)], WITH, "gate with F1, CTR 100 %")
    bx.set_yticks([y + 0.31 for y, _ in lanes]); bx.set_yticklabels([l for _, l in lanes], fontsize=8)
    bx.tick_params(axis="y", length=0); bx.grid(axis="y", visible=False)
    bx.set_ylim(1.4, 9.75)
    ytop = yv[1] - 0.25
    bx.plot([0, 0], [1.4, ytop], color=INK2, lw=0.8)
    bx.fill_between([t_on[0], t_on[1]], 1.4, ytop, color=S4, alpha=0.35, lw=0)
    tx = 260
    b_ = lambda d: offset_copy(bx.transData, fig=fig, y=d, units="points")
    bx.text(-low["half_window_us"] + d_off + 15, yv[0] + 0.62, "falling edge = start of the window, %d us before the zero" % (low["half_window_us"] - d_off),
            fontsize=8, color="#9B4F80", va="bottom", transform=b_(3))
    bx.text(X0 + 15, yv[2] + 0.62, "ISR: /ZCD edge + 230 us, pulse 150 us", fontsize=8, color=AS, va="bottom", transform=b_(4))
    bx.text(tx, yv[2], "ends %d us BEFORE the zero: fires the old\nhalf-cycle at %.0f V, the new one is lost" % (-low["pulse_end_us"], low["V_on_V"]),
            fontsize=8, color=AS, va="bottom", transform=b_(3))
    bx.text(tx, yv[3], "spans the zero: fires at the gate threshold", fontsize=8, color=AS, va="bottom", transform=b_(3))
    bx.text(tx, yv[4], "centre of the measured window, >= 300 us:\nthe MOC latches at |v| = 3.5 V (+%.0f us)" % t_latch, fontsize=8, color=WITH, va="bottom", transform=b_(3))
    bx.text(tx, yv[5], "triac on at %.1f-%.1f V (+%.0f to +%.0f us, shaded)" % (von[0], von[1], t_on[0], t_on[1]), fontsize=8, color=WITH, va="bottom", transform=b_(3))
    bx.set_xlim(X0, X1)
    bx.set_xlabel("time from the mains zero crossing (us)")
    save(fig, "z01_zcd_timing")


def chart_zcd_links():
    rows = A["A0_zcd_timing"]["rows"]
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.95), gridspec_kw=dict(wspace=0.55, left=0.075, right=0.985, top=0.80, bottom=0.2))
    ax = axs[0]
    vs = ACON["V_on_sweep"]; xv = [float(k) for k in vs]; yv = [vs[k]["QP"]["margin_dB"] for k in vs]
    ax.axhspan(0, 6, color=VERD["MARGINAL"][1], lw=0); ax.axhspan(-5, 0, color=VERD["FAIL"][1], lw=0)
    rng = A["A0_zcd_timing"]["V_on_range_when_firing_V"]
    ax.plot(rng, [20.0, 20.0], color=WITH, lw=3, solid_capstyle="butt")
    ax.plot(xv, yv, "o-", color=INK, ms=4)
    ax.set_xlim(0, 47); ax.set_ylim(-1, 22)
    ax.set_xlabel("triac turn-on voltage (V)"); ax.set_ylabel("QP margin, nominal (dB)")
    ax.set_title("(a) Emission: -3 dB\nper 10 V of turn-on", fontsize=8.5)
    ax = axs[1]
    h = A["A4_harmonics"]
    norm = h["summary_pct_of_limit"]["V_on=20V|100pct"][0]
    fault = h["results"]["fault_half_wave"]
    vals = [norm, fault["worst_classA_pct_(avg/limit or max/1.5limit)"]]
    ax.bar([0, 1], vals, color=[WITH, AS], width=0.6)
    for x, y in zip([0, 1], vals):
        ax.text(x, y + 4, "%.1f %%" % y, ha="center", fontsize=8)
    ax.axhline(100, color=LIM, ls="--", lw=1)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["full-wave", "half-cycle\nlost"], fontsize=8)
    ax.set_ylim(0, 128); ax.set_ylabel("worst order, % of Class A")
    ax.text(1, 45, "h2, DC\n%.2f A" % fault["dc_component_A"], ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.set_title("(b) Harmonics: half-wave\ncontrol, banned by 6.2", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax = axs[2]
    ctrs = sorted(set(r["ctr10_pct"] for r in rows))
    cats = [("MISSED", AS, "half-cycle lost"), ("UNCERTAIN", S4, "uncertain"), ("fires", WITH, "fires")]
    bottom = np.zeros(len(ctrs))
    for key, col, lab in cats:
        cnt = np.array([sum(1 for r in rows if r["ctr10_pct"] == c and r["outcome"].startswith(key)) for c in ctrs])
        ax.bar(range(len(ctrs)), cnt, bottom=bottom, color=col, width=0.65, label=lab)
        bottom += cnt
    ax.set_xticks(range(len(ctrs))); ax.set_xticklabels(["%g" % c for c in ctrs], fontsize=8)
    ax.set_xlabel("H11AA1 CTR at 10 mA (%)"); ax.set_ylabel("timing cases")
    ax.set_ylim(0, 13.5)
    ax.legend(loc="upper left", fontsize=8, ncol=1, handlelength=1, borderaxespad=0.1, labelspacing=0.2)
    ax.set_title("(c) Function: %d of %d\ncases lose the half-cycle" % (A["A0_zcd_timing"]["n_missed"], A["A0_zcd_timing"]["n_cases"]), fontsize=8.5)
    ax.grid(axis="x", visible=False)
    pl = Placer(fig)
    a = axs[0]
    pl.place(a, [(rng[0], 20.0, "right", "center", -4, 0)], "F1", fontsize=8, color=WITH)
    for x, y in zip(xv, yv):
        pl.place(a, [(x, y, "left", "bottom", 6, 5), (x, y, "right", "bottom", -6, 5), (x, y, "left", "top", 6, -6), (x, y, "right", "top", -6, -6),
                     (x, y, "center", "bottom", 0, 8), (x, y, "center", "top", 0, -8)],
                 "%.1f" % y, fontsize=8, color=INK)
    xl1 = axs[1].get_xlim()
    pl.place(axs[1], [(xl1[1], 100, "right", "bottom", -2, 3), (xl1[0], 100, "left", "bottom", 2, 3)], "limit", fontsize=8)
    save(fig, "z02_zcd_links")


# =====================================================================================================================
# 3. conducted emission
# =====================================================================================================================
def chart_ce_spectrum():
    sc = ACON["M1_heater_100pct_fan_on"]["scan"]; aw = ACON["corners_all_worst_scan"]
    p3 = ACON["proposals_at_all_worst_corner"]["P3: firmware fires at the ZCD window centre (V_on <= 15 V)"]["scan"]
    f = np.array(sc["f"]) / 1e6
    fl = np.geomspace(0.15e6, 30e6, 400)
    qp = [A_COMMON.lim_qp(x) for x in fl]; av = [A_COMMON.lim_av(x) for x in fl]
    wq = ACON["corners"]["all_worst"]["QP"]
    f1 = ACON["proposals_at_all_worst_corner"]["P3: firmware fires at the ZCD window centre (V_on <= 15 V)"]["margins_all_worst"]["QP"]
    nom = ACON["M1_heater_100pct_fan_on"]["worst"]["QP"]
    fig, axs = plt.subplots(2, 1, figsize=(W, 8.6), sharex=True, gridspec_kw=dict(hspace=0.2, left=0.085, right=0.975, top=0.94, bottom=0.075))
    for ax, line in zip(axs, ("N", "L")):
        ax.plot(fl / 1e6, qp, color=LIM, ls="--", lw=1.2); ax.plot(fl / 1e6, av, color=LIM, ls=":", lw=1.3)
        ax.text(6.0, 61.0, "QP limit (Table 5)", fontsize=8, color=LIM, va="bottom")
        ax.text(6.0, 51.0, "AV limit", fontsize=8, color=LIM, va="bottom")
        ax.plot(np.array(aw["f"]) / 1e6, aw[line]["QP"], color=AS, lw=1.6)
        ax.plot(np.array(p3["f"]) / 1e6, p3[line]["QP"], color=WITH, lw=1.6)
        ax.plot(f, sc[line]["QP"], color=AS, lw=1.0, ls=(0, (4, 2)))
        ax.plot(f, sc[line]["AV"], color=INK2, lw=0.9)
        ax.set_xscale("log"); ax.set_xlim(0.15, 30); ax.set_ylim(0, 86)
        ax.set_ylabel("level at the LISN (dBuV)")
        ax.set_xticks([0.15, 0.3, 0.5, 1, 2, 5, 10, 30]); ax.set_xticklabels(["0.15", "0.3", "0.5", "1", "2", "5", "10", "30"])
        hd = [Line2D([], [], color=AS, lw=1.6, label="as designed, all bad ends at once"), Line2D([], [], color=WITH, lw=1.6, label="with F1, same corner"),
              Line2D([], [], color=AS, lw=1.0, ls=(0, (4, 2)), label="as designed, nominal (V_on 20 V)")]
        ax.legend(handles=hd, loc="upper right", ncol=3, fontsize=8, bbox_to_anchor=(1.0, 1.01), handlelength=2.2, columnspacing=1.0)
        ax.text(0.17, 27, "AV, nominal", fontsize=8, color=INK2)
    axs[0].set_title("N line: firmware fix F1 lifts the worst corner from %+.1f dB to %+.1f dB (nominal %+.1f dB)" % (wq["margin_dB"], f1["margin_dB"], nom["margin_dB"]), fontsize=9.5)
    axs[1].set_title("L line: the same picture, with more margin than N", fontsize=9.5)
    axs[1].set_xlabel("frequency (MHz)")
    save(fig, "c01_ce_spectrum")


def chart_ce_mc():
    m0 = np.array([r["QP_margin"] for r in ACON["monte_carlo"]["rows"]])
    m1 = np.array([r["QP_margin"] for r in ACON["monte_carlo_proposal_Von_8_18"]["rows"]])
    v0 = [r["params"]["V_on"] for r in ACON["monte_carlo"]["rows"]]
    v1 = [r["params"]["V_on"] for r in ACON["monte_carlo_proposal_Von_8_18"]["rows"]]
    fig, axs = plt.subplots(2, 1, figsize=(W, 8.4), gridspec_kw=dict(hspace=0.48, left=0.085, right=0.975, top=0.94, bottom=0.08))
    ax = axs[0]
    edges = np.arange(-1, 21, 1.0); ctr = edges[:-1] + 0.5
    h0, _ = np.histogram(m0, edges); h1, _ = np.histogram(m1, edges)
    ax.axvspan(-1, 0, color=VERD["FAIL"][1], lw=0); ax.axvspan(0, 6, color=VERD["MARGINAL"][1], lw=0)
    ax.bar(ctr - 0.21, h0, width=0.42, color=AS)
    ax.bar(ctr + 0.21, h1, width=0.42, color=WITH)
    s0, s1 = ACON["monte_carlo"]["QP_margin_dB"], ACON["monte_carlo_proposal_Von_8_18"]["QP_margin_dB"]
    n0 = int(np.sum(m0 < 6)); n1 = int(np.sum(m1 < 6))
    ax.text(3.0, 34.0, "MARGINAL\n(< 6 dB)", fontsize=8, color=VERD["MARGINAL"][0], fontweight="bold", ha="center", va="center")
    cf = ce_final()
    a_, f_ = cf[("as designed", "QP")], cf[("F1", "QP")]
    ax.text(6.3, 30.5, "final model (+ probe C, L1 core loss): as designed worst %.1f, 5th pct %.1f,"
            % (a_["min"], a_["p5"]), fontsize=8, color=INK2)
    ax.text(6.3, 28.0, "median %.1f dB, %d runs < 6 dB; with F1 %.1f / %.1f / %.1f dB, %d runs < 6 dB." % (a_["median"], a_["n_below_6dB"], f_["min"], f_["p5"], f_["median"], f_["n_below_6dB"]),
            fontsize=8, color=INK2)
    ax.text(6.3, 35.5, "bars = A's first model: as designed worst %.1f, 5th pct %.1f, median %.1f dB; %d/%d < 6 dB"
            % (abs(s0["min"]) if abs(s0["min"]) < 0.05 else s0["min"], s0["p5"], s0["median"], n0, len(m0)), fontsize=8, color=AS)
    ax.text(6.3, 33.0, "with F1 (V_on 8-18 V): worst %.1f, 5th pct %.1f, median %.1f dB; %d runs < 6 dB" % (s1["min"], s1["p5"], s1["median"], n1),
            fontsize=8, color=WITH)
    ax.set_xlim(-1, 21); ax.set_ylim(0, 38)
    ax.set_xlabel("worst QP margin of one Monte Carlo run (dB)"); ax.set_ylabel("runs (of 120)")
    ax.set_title("Monte Carlo, 120 runs each: with F1 every run keeps at least 6 dB (both models)", fontsize=9.5)
    ax.grid(axis="x", visible=False)
    ax = axs[1]
    ax.axhspan(-1, 0, color=VERD["FAIL"][1], lw=0); ax.axhspan(0, 6, color=VERD["MARGINAL"][1], lw=0)
    ax.scatter(v0, m0, s=12, color=AS, alpha=0.85, lw=0)
    ax.scatter(v1, m1, s=12, color=WITH, alpha=0.85, lw=0, marker="s")
    vs = ACON["V_on_sweep"]
    ax.plot([float(k) for k in vs], [vs[k]["QP"]["margin_dB"] for k in vs], "-", color=INK, lw=1.2, marker="D", ms=4)
    ax.text(41, 6.9, "nominal, other\nparameters fixed", fontsize=8, color=INK, va="bottom")
    ax.text(41, 15.5, "as designed draws\n(V_on 10-40 V)", fontsize=8, color=AS)
    ax.text(5.6, 2.2, "F1 draws (V_on 8-18 V)", fontsize=8, color=WITH)
    rho = ACON["monte_carlo"]["spearman_rho_vs_QP_margin"]
    ax.text(41, 10.8, "rank correlation with\nthe margin: V_on %.2f,\nC_ch %.2f, C_hc %.2f" % (rho["V_on"], rho["C_ch"], rho["C_hc"]), fontsize=8, color=INK2)
    ax.set_xlim(5, 50); ax.set_ylim(-1, 21)
    ax.set_xlabel("triac turn-on voltage V_on in the run (V)"); ax.set_ylabel("worst QP margin (dB)")
    ax.set_title("Turn-on voltage drives the margin: about 3 dB per 10 V", fontsize=9.5)
    save(fig, "c02_ce_montecarlo")


def chart_ce_oven():
    g = A["A1_F1_construction_grid"]
    hc, ch = g["C_hc_pF"], g["C_ch_pF"]
    keys = list(g["tables"])
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.0), gridspec_kw=dict(wspace=0.12, left=0.1, right=0.985, top=0.80, bottom=0.17))
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap([VERD["FAIL"][1], VERD["MARGINAL"][1], "#E6F3EA", VERD["PASS"][1]])
    norm = BoundaryNorm([-5, 0, 6, 9, 20], cmap.N)
    for ax, k, ttl in zip(axs, keys, ("other parameters nominal", "other parameters at their bad ends")):
        M = np.array([[g["tables"][k]["C_hc=%dpF|C_ch=%dpF" % (round(a), round(b))]["QP_margin_dB"] for b in ch] for a in hc])
        ax.imshow(M, cmap=cmap, norm=norm, aspect="auto", origin="lower")
        for i in range(len(hc)):
            for j in range(len(ch)):
                ax.text(j, i, "%.1f" % M[i, j], ha="center", va="center", fontsize=8, color=INK)
        # outline the >= 6 dB region
        for i in range(len(hc)):
            for j in range(len(ch)):
                if M[i, j] >= 6:
                    for (di, dj, x0, y0, x1, y1) in ((1, 0, j - .5, i + .5, j + .5, i + .5), (-1, 0, j - .5, i - .5, j + .5, i - .5),
                                                    (0, 1, j + .5, i - .5, j + .5, i + .5), (0, -1, j - .5, i - .5, j - .5, i + .5)):
                        ii, jj = i + di, j + dj
                        if not (0 <= ii < len(hc) and 0 <= jj < len(ch)) or M[ii, jj] < 6:
                            ax.plot([x0, x1], [y0, y1], color=INK, lw=1.8, solid_capstyle="projecting")
        ax.set_xticks(range(len(ch))); ax.set_xticklabels(["%g" % x for x in ch])
        ax.set_yticks(range(len(hc))); ax.set_yticklabels(["%g" % round(x) for x in hc])
        ax.set_xlabel("chassis to reference plane C_ch (pF)")
        ax.set_title(ttl, fontsize=8.5)
        ax.grid(False)
    axs[0].set_ylabel("heater to chassis\nC_hc (pF)")
    axs[1].set_yticklabels([])
    fig.suptitle("With F1, the oven construction decides the last dB: inside the black line the margin is >= 6 dB",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    fig.text(0.012, 0.875, "QP margin (dB), worst of L and N, F1 at V_on 18 V (upper end of the F1 range)", fontsize=8, color=INK2)
    save(fig, "c03_ce_oven")


def chart_ce_hlk():
    hb = ACON["M3_heater_off_HLK_bound"]
    fq = [0.15, 0.3, 0.5, 1, 5, 30]
    dm = [hb["max_HLK_DM_current_for_QP_limit_dBuA"]["%gMHz" % x] for x in fq]
    cm = [hb["max_HLK_CM_current_for_QP_limit_dBuA"]["%gMHz" % x] for x in fq]
    av = [hb["max_HLK_DM_current_for_AV_limit_dBuA"]["%gMHz" % x] for x in fq]
    fig, ax = plt.subplots(figsize=(W, 4.2), gridspec_kw=dict(left=0.085, right=0.975, top=0.88, bottom=0.14))
    ax.plot(fq, dm, "o-", color=INK, ms=5)
    ax.plot(fq, av, "o--", color=INK2, ms=4)
    ax.plot(fq, cm, "s-", color=S5, ms=5)
    ax.set_xscale("log"); ax.set_xlim(0.12, 40); ax.set_ylim(10, 112)
    ax.set_xticks(fq); ax.set_xticklabels(["%g" % x for x in fq])
    ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("HLK noise current (dBuA)")
    ax.set_title("Heater off: the HLK-10M05 is a black box; this is the noise it may emit before the limit", fontsize=9.5)
    pl = Placer(fig)
    for xs, ys, col in ((fq, dm, INK), (fq, cm, S5)):
        for x, y in zip(xs, ys):
            pl.place(ax, [(x, y, "center", "bottom", 0, 7), (x, y, "center", "top", 0, -7), (x, y, "left", "center", 8, 0), (x, y, "right", "center", -8, 0),
                          (x, y, "left", "bottom", 6, 6), (x, y, "right", "bottom", -6, 6), (x, y, "left", "top", 6, -6), (x, y, "right", "top", -6, -6),
                          (x, y, "center", "bottom", 0, 12), (x, y, "center", "top", 0, -12), (x, y, "left", "center", 12, 0), (x, y, "right", "center", -12, 0),
                          (x, y, "center", "bottom", 0, 20), (x, y, "center", "bottom", 0, 26)],
                     "%.0f" % y, fontsize=8, color=col)
    for i, (s, col) in enumerate((("differential mode, QP limit (solid)", INK), ("differential mode, AV limit (dashed)", INK2), ("common mode, QP limit (squares)", S5))):
        pl.place(ax, [(1.6, 100 - i * 8, "left", "center"), (2.5, 100 - i * 8, "left", "center")], s, fontsize=8, color=col)
    save(fig, "c04_ce_hlk")


def chart_clicks():
    rk = A["A3_clicks"]["relay_K1"]; tr = A["A3_clicks"]["triac"]
    fq = ["0.15MHz", "0.5MHz", "1.4MHz", "30MHz"]
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.8), gridspec_kw=dict(width_ratios=[1.65, 1], wspace=0.38, left=0.085, right=0.985, top=0.80, bottom=0.19))
    ax = axs[0]
    x = np.arange(len(fq)); wdt = 0.26
    for i, (k, col) in enumerate((("showering_0.1ms", S6), ("showering_1ms", WITH), ("showering_3ms", "#003F6B"))):
        vals = [rk["results"][k][f]["QP_dBuV"] for f in fq]
        ax.bar(x + (i - 1) * wdt, vals, width=wdt, color=col)
        for xi in x:
            ax.text(xi + (i - 1) * wdt, 3, k.replace("showering_", "").replace("ms", " ms"), rotation=90, fontsize=8,
                    color="white" if i else INK, ha="center", va="bottom")
    L = [rk["results"]["showering_1ms"][f]["L_dBuV"] for f in fq]
    for xi, l in zip(x, L):
        ax.plot([xi - 0.42, xi + 0.42], [l, l], color=LIM, ls="--", lw=1.1)
        ax.plot([xi - 0.42, xi + 0.42], [l + rk["Lq_relaxation_dB"], l + rk["Lq_relaxation_dB"]], color=LIM, ls=":", lw=1.3)
    ax.text(3.48, L[-1], "L", fontsize=8, va="center")
    ax.text(3.48, L[-1] + rk["Lq_relaxation_dB"], "L + 44 dB", fontsize=8, va="center")
    ax.set_xlim(-0.5, 4.1)
    ax.set_xticks(x); ax.set_xticklabels([f.replace("MHz", " MHz") for f in fq])
    ax.set_ylabel("QP, one relay break (dBuV)"); ax.set_ylim(0, 125)
    ax.set_title("Relay K1 arcing (bars: arc 0.1 / 1 / 3 ms): exempt\nunder 5.4.3.2 / 5.4.3.4, %.3f clicks per minute" % rk["click_rate_N_per_min"], fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax = axs[1]
    v20 = [tr["V_on=20V"][f]["peak_env_over_IF_ref_dB"] for f in fq[:3]]
    v40 = [tr["V_on=40V"][f]["peak_env_over_IF_ref_dB"] for f in fq[:3]]
    xx = np.arange(3)
    ax.bar(xx - 0.18, v20, width=0.36, color=WITH)
    ax.bar(xx + 0.18, v40, width=0.36, color=AS)
    ax.axhline(0, color=LIM, ls="--", lw=1.1)
    ax.text(2.55, 0.5, "IF reference", fontsize=8, ha="right", va="bottom")
    ax.text(-0.18, v20[0] - 0.4, "20 V", fontsize=8, color=WITH, ha="center", va="top")
    ax.text(0.18, v40[0] + 0.4, "40 V", fontsize=8, color=AS, ha="center", va="bottom")
    ax.text(-0.45, -13.6, "bar labels: triac turn-on voltage", fontsize=8, color=INK2, va="bottom")
    ax.set_xticks(xx); ax.set_xticklabels(["0.15", "0.5", "1.4"]); ax.set_xlabel("MHz")
    ax.set_ylabel("IF envelope peak vs\nreference (dB)"); ax.set_ylim(-14, 4)
    ax.set_title("Triac: no clicks registered;\ncontinuous limits apply", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    save(fig, "c05_clicks")


def chart_harmonics():
    h = A["A4_harmonics"]; res = h["results"]
    fig, axs = plt.subplots(2, 1, figsize=(W, 8.6), gridspec_kw=dict(hspace=0.45, left=0.085, right=0.975, top=0.94, bottom=0.08))
    ax = axs[0]
    series = [(res["V_on=40V"]["100pct"], AS, "o", 5), (res["V_on=20V"]["100pct"], WITH, "s", 4.5), (res["fault_half_wave"], S5, "^", 4.5)]
    for r, col, mk, ms in series:
        hs = np.array([x["h"] for x in r["rows"]]); pc = np.array([max(x["avg_pct_classA"], x["max_pct_classA"]) for x in r["rows"]])
        sel = pc > 0
        ax.plot(hs[sel], pc[sel], marker=mk, color=col, ls="none", ms=ms)
    ax.axhline(100, color=LIM, ls="--", lw=1.2)
    ax.text(40.5, 118, "Class A limit", fontsize=8, ha="right", va="bottom")
    ax.set_yscale("log"); ax.set_ylim(0.05, 400); ax.set_xlim(1, 41)
    ax.set_yticks([0.1, 1, 10, 100]); ax.set_yticklabels(["0.1 %", "1 %", "10 %", "100 %"])
    ax.set_xlabel("harmonic order (even orders appear only when a half-cycle is lost)"); ax.set_ylabel("current, % of the Class A limit")
    fw = res["fault_half_wave"]
    ax.text(3.0, 200, "triangles: half-cycle lost (today's timing, 22 of 40 cases): h2 %.1f %%, DC %.2f A" % (fw["worst_classA_pct_(avg/limit or max/1.5limit)"], fw["dc_component_A"]),
            fontsize=8, color=S5, va="center")
    r40 = res["V_on=40V"]["100pct"]; r20 = res["V_on=20V"]["100pct"]
    ax.text(14, 0.2, "circles: full power, V_on 40 V (as designed, worst): h%d at %.1f %%" % (r40["worst_classA_order"], r40["worst_classA_pct_(avg/limit or max/1.5limit)"]),
            fontsize=8, color=AS)
    ax.text(14, 0.085, "squares: full power, V_on 20 V (F1 keeps V_on <= 18 V): %.1f %%" % r20["worst_classA_pct_(avg/limit or max/1.5limit)"], fontsize=8, color=WITH)
    ax.set_title("Full-wave control stays far below Class A; losing half-cycles brings h2 to %.0f %%" % fw["worst_classA_pct_(avg/limit or max/1.5limit)"], fontsize=9.5)
    ax = axs[1]
    sm = h["summary_pct_of_limit"]
    def ser(fam, von, col_idx):
        ks = sorted([k for k in sm if k.startswith("V_on=%dV|%s_" % (von, fam))], key=lambda k: float(k.split("_")[-1]))
        return [float(k.split("_")[-1]) for k in ks], [sm[k][col_idx] for k in ks]
    ax.axhspan(80, 100, color=VERD["MARGINAL"][1], lw=0)
    d, y = ser("current", 40, 0); ax.plot(d, y, "-", color=S5, lw=1.4)
    d, y3 = ser("current", 40, 2); ax.plot(d, y3, "--", color=S5, lw=1.2)
    d, y = ser("decided", 40, 0); ax.plot(d, y, "-", color=AS, lw=1.6)
    d, y = ser("decided", 20, 0); ax.plot(d, y, "-", color=WITH, lw=1.6)
    ax.axhline(100, color=LIM, ls="--", lw=1.2); ax.text(0.99, 101, "limit", fontsize=8, ha="right", va="bottom")
    ax.text(0.09, 90, "dashed: current sigma-delta firmware, Table 3 rule of 6.2: %.1f %% at duty 0.02 (MARGINAL)" % sm["V_on=40V|current_0.020"][2], fontsize=8, color=S5)
    ax.text(0.1, 63, "solid: current firmware, Class A", fontsize=8, color=S5, va="bottom")
    ax.text(0.62, 25, "decided firmware, V_on 40 V", fontsize=8, color=AS)
    ax.text(0.62, 5.5, "decided firmware, V_on 20 V", fontsize=8, color=WITH, va="bottom")
    ax.set_xlim(0, 1); ax.set_ylim(0, 110)
    ax.set_xlabel("heater duty"); ax.set_ylabel("worst order, % of limit")
    ax.set_title("Decided firmware: <= %.1f %% of the limit at every duty (PASS)" % max(sm[k][0] for k in sm if "decided" in k), fontsize=9.5)
    save(fig, "l01_harmonics")


def chart_flicker():
    fl = A["A5_flicker"]
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.4), gridspec_kw=dict(width_ratios=[1.75, 1], wspace=0.42, left=0.08, right=0.985, top=0.80, bottom=0.16))
    ax = axs[0]
    fams = [("current", S5), ("decided", AS), ("decided:1500", WITH), ("decided:2000", S3)]
    for fam, col in fams:
        cs = sorted([c for c in fl["cases"] if c["family"] == fam], key=lambda c: c["duty"])
        ax.plot([c["duty"] for c in cs], [c["Pst"] for c in cs], "-o" if fam != "current" else "-", color=col, ms=3, lw=1.5 if fam != "decided:2000" else 1.0)
    ax.axhspan(fl["limits"]["Plt"] * 0.8, fl["limits"]["Plt"], color=VERD["MARGINAL"][1], lw=0)
    ax.axhline(fl["limits"]["Pst"], color=LIM, ls="--", lw=1.2); ax.text(0.6, fl["limits"]["Pst"] + 0.03, "P_st limit 1.0", fontsize=8, va="bottom")
    ax.axhline(fl["limits"]["Plt"], color=LIM, ls=":", lw=1.3); ax.text(0.06, 0.59, "P_lt limit 0.65 (= P_st at steady duty)", fontsize=8, va="center")
    wc = fl["worst_current"]
    ax.annotate("%.2f at duty %.2f" % (wc["Pst"], wc["duty"]), xy=(wc["duty"], wc["Pst"]), xytext=(0.33, 1.80), fontsize=8, color=S5, va="center",
                arrowprops=dict(arrowstyle="-", color=S5, lw=0.8))
    ax.text(0.5, 1.42, "current firmware", fontsize=8, color=S5, ha="center")
    ax.text(0.22, 0.31, "1000-cycle frame (decided): worst %.3f" % fl["worst_decided"]["Pst"], fontsize=8, color=AS)
    ax.text(0.22, 0.18, "1500-cycle frame (F2): worst %.3f" % fl["worst_decided:1500"]["Pst"], fontsize=8, color=WITH)
    ax.text(0.22, 0.05, "2000-cycle frame: worst %.3f" % fl["worst_decided:2000"]["Pst"], fontsize=8, color=S3)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.85)
    ax.set_xlabel("heater duty"); ax.set_ylabel("P_st over 10 min")
    ax.set_title("F2 (1500-cycle frame) lowers the worst P_lt\nfrom %.3f to %.3f: 28 %% margin" % (fl["worst_decided"]["Pst"], fl["worst_decided:1500"]["Pst"]), fontsize=8.5)
    ax = axs[1]
    se = fl["single_events"]
    items = [("d_c, heater step", fl["worst_decided"]["d_c_pct"], fl["limits"]["dc_pct"]),
             ("d_max, heater step", fl["worst_decided"]["d_max_pct"], fl["limits"]["dmax_pct"]),
             ("d_max, cold heater", se["heater_step_cold_5pct"]["dU_pct"], fl["limits"]["dmax_pct"]),
             ("d_max, HLK inrush", se["HLK_inrush_power_on"]["d_max_pct"], fl["limits"]["dmax_pct"]),
             ("d_max, fan start", se["fan_start_assumed"]["d_max_pct"], fl["limits"]["dmax_pct"])]
    ys = np.arange(len(items))[::-1]
    for y, (lab, v, l) in zip(ys, items):
        ax.barh(y, v / l * 100, color=AS, height=0.55)
        ax.text(v / l * 100 + 2, y, "%.2f %% of %.1f %%" % (v, l), va="center", fontsize=8)
    ax.axvline(100, color=LIM, ls="--", lw=1.1); ax.text(97, len(items) - 0.45, "limit", fontsize=8, ha="right")
    ax.set_yticks(ys); ax.set_yticklabels([i[0] for i in items], fontsize=8)
    ax.set_xlim(0, 105); ax.set_ylim(-0.6, len(items) - 0.2); ax.set_xlabel("% of the limit")
    ax.grid(axis="y", visible=False)
    ax.set_title("Voltage changes: all far\nbelow the limits; T_max 0 s", fontsize=8.5)
    save(fig, "l02_flicker")


def _rating_lines(ax, items, x1):
    for v, txt, ls in items:
        ax.axhline(v, color=LIM, ls=ls, lw=1.1)
        from matplotlib.transforms import offset_copy
        ax.text(x1, v, txt, fontsize=8, ha="right", va="bottom", color=LIM, transform=offset_copy(ax.transData, fig=ax.figure, y=3, units="points"))


def chart_surge_waves():
    sw = curve("surge_waves.json")
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.4), sharey=True, gridspec_kw=dict(wspace=0.08, left=0.085, right=0.985, top=0.83, bottom=0.14))
    ax = axs[0]
    for key, col in (("as designed", AS), ("P-S2b + P-S4", WITH)):
        d = sw[key]
        ax.plot(d["t_us"], d["V_triac"], color=col, lw=1.6)
        ax.plot(d["t_us"], d["V_LINE_FILT"], color=col, lw=1.0, ls=(0, (4, 2)))
    _rating_lines(ax, [(600, "MOC3052 driver VDRM 600 V", "--"), (800, "BTA24 / 800 V driver VDRM 800 V", ":")], 98)
    a = sw["as designed"]; b = sw["P-S2b + P-S4"]
    ax.text(16, 930, "triac peak %.0f V today" % a["peaks"]["V_triac_pk"], fontsize=8, color=AS)
    ax.text(45, 490, "%.0f V with the TVS" % b["peaks"]["V_triac_pk"], fontsize=8, color=WITH)
    ax.text(55, 110, "dashed: LINE_FILT node", fontsize=8, color=INK2)
    ax.set_xlim(-10, 100); ax.set_ylim(-50, 1300)
    ax.set_xlabel("time after the surge (us)"); ax.set_ylabel("voltage (V)")
    ax.set_title("Triac side (L40 knee 6 A): 780 V today\nagainst the 600 V driver", fontsize=8.5)
    ax = axs[1]
    for key, col in (("as designed | knee 20 A", AS), ("P-S2b + P-S4 | knee 20 A", WITH)):
        d = sw[key]
        ax.plot(d["t_us"], d["V_K1_contact"], color=col, lw=1.6)
    _rating_lines(ax, [(750 * math.sqrt(2), "K1 open contact 750 Vac = 1061 Vpk", "--")], 98)
    a = sw["as designed | knee 20 A"]; b = sw["P-S2b + P-S4 | knee 20 A"]
    ax.text(10, a["peaks"]["V_K1_open_contacts_pk"] + 22, "%.0f V today" % a["peaks"]["V_K1_open_contacts_pk"], fontsize=8, color=AS)
    ax.text(30, 830, "%.0f V with RV3 (P-S2b)" % b["peaks"]["V_K1_open_contacts_pk"], fontsize=8, color=WITH)
    ax.set_xlim(-10, 100); ax.set_xlabel("time after the surge (us)")
    ax.set_title("Relay K1 open contact (L40 knee 20 A):\n1162 V today, no impulse rating", fontsize=8.5)
    fig.suptitle("Surge 1 kV L-N at +90 deg, heater off, K1 open: as designed vs with P-S2b + P-S4",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    save(fig, "s01_surge_waves")


def stress_bars(ax, items, title, xmax=140):
    ys = np.arange(len(items))[::-1]
    ax.axvspan(80, 100, color=VERD["MARGINAL"][1], lw=0); ax.axvspan(100, xmax, color=VERD["FAIL"][1], lw=0)
    for y, (lab, pct, verdict, note) in zip(ys, items):
        if pct is None:
            tag(ax, 3, y, verdict, ha="left", fs=8)
            continue
        ax.barh(y, min(pct, xmax), color=AS, height=0.8, zorder=2)
        if pct > 62:
            ax.text(3, y, note, va="center", ha="left", fontsize=8, color="white", fontweight="bold", zorder=3)
        else:
            ax.text(min(pct, xmax) + 2, y, note, va="center", fontsize=8, color=INK, zorder=3)
    ax.axvline(100, color=LIM, lw=1.1, ls="--")
    ax.text(101.5, len(items) - 0.35, "rating", fontsize=8, ha="left", va="bottom")
    ax.set_yticks(ys); ax.set_yticklabels([i[0] for i in items], fontsize=8); ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, xmax); ax.set_ylim(-0.6, len(items) + 0.3)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("worst stress, % of the part's rating (80-100 % = MARGINAL, > 100 % = FAIL)")
    ax.set_title(title, fontsize=9.5)


def chart_surge_stress():
    rows = [r for r in B["verdict_table"] if r["test"] == "Surge 1 kV L-N"]
    names = {"BTA24 Q1": "triac Q1 BTA24 off-state", "MOC3052": "triac driver U5 MOC3052", "K1 open": "relay K1 open contact", "dV/dt": "triac dV/dt",
             "RV1 TVR14431 current": "varistor RV1 current", "RV1 energy": "varistor RV1 energy", "F3 8 A": "fuse F3 I2t (does not open)",
             "F1 1 A": "fuse F1 I2t (does not open)", "H11AA1": "opto H11AA1 LED current", "R6/R7": "resistors R6/R7 voltage", "HLK-10M05": "HLK-10M05 bulk capacitor"}
    items = []
    for r in rows:
        nm = [v for k, v in names.items() if k in r["part"]][0]
        if r["verdict"].startswith("NOT SIMULABLE"):
            items.append((nm + "\n(black box: %.2f x vendor circuit)" % r["worst"], None, "NOT SIMULABLE", ""))
            continue
        pct = r["worst"] / r["limit"] * 100
        unit = r["unit"].replace("A2s", "A2s").replace("us", "us")
        items.append((nm, pct, r["verdict"], "%s of %s %s  %s" % (_fmt(r["worst"]), _fmt(r["limit"]), unit, r["verdict"])))
    fig, ax = plt.subplots(figsize=(W, 3.9), gridspec_kw=dict(left=0.27, right=0.985, top=0.9, bottom=0.14))
    stress_bars(ax, items, "As designed: the driver and K1 exceed their ratings; the triac sits at 97 %", xmax=150)
    save(fig, "s02_surge_stress")


def chart_surge_ladder():
    lad = [("as designed: MOC3052 (600 V)", bv("Surge 1 kV L-N", "MOC3052")),
           ("P-S1: 800 V driver alone", bv("P-S1 alone", "800 V driver")),
           ("P-S1 + P-S3 (RV2 -> 14 mm varistor)", bv("P-S3 alone", "800 V driver")),
           ("P-S1 + P-S2b + P-S3", bv("P-S1+P-S2b+P-S3", "800 V driver")),
           ("P-S1 + P-S4 (RV2 -> 1.5KE440CA TVS)", bv("P-S1+P-S4", "800 V driver")),
           ("P-S1 + P-S2b + P-S4 (recommended)", bv("P-S1+P-S2b+P-S4", "800 V driver"))]
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.8), gridspec_kw=dict(width_ratios=[3.1, 1], wspace=0.12, left=0.315, right=0.985, top=0.84, bottom=0.14))
    ax = axs[0]
    ys = np.arange(len(lad))[::-1]
    for i, (y, (lab, r)) in enumerate(zip(ys, lad)):
        ax.barh(y, r["worst"], color=AS if i == 0 else WITH, height=0.55)
        tag(ax, 850, y, r["verdict"], text="%s\n%.0f V, %+.1f %%" % (r["verdict"], r["worst"], r["margin_pct"]), ha="left", fs=8)
    from matplotlib.transforms import offset_copy
    ax.axvline(600, color=LIM, ls="--", lw=1.1); ax.text(600, len(lad) - 0.35, "600 V", fontsize=8, ha="right", transform=offset_copy(ax.transData, fig=fig, x=-4, units="points"))
    ax.axvline(800, color=LIM, ls=":", lw=1.3); ax.text(800, len(lad) - 0.35, "800 V", fontsize=8, ha="right", transform=offset_copy(ax.transData, fig=fig, x=-4, units="points"))
    ax.set_yticks(ys); ax.set_yticklabels([l[0] for l in lad], fontsize=8); ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 1180); ax.set_ylim(-0.6, len(lad) + 0.15); ax.grid(axis="y", visible=False)
    ax.set_xticks([0, 200, 400, 600, 800])
    ax.set_xlabel("peak across the triac and driver (V)")
    ax.set_title("Triac and driver vs their VDRM", fontsize=9)
    ax = axs[1]
    k0 = bv("Surge 1 kV L-N", "K1 open"); k1 = bv("Surge, P-S2b", "K1")
    ax.bar([0, 1], [k0["worst"], k1["worst"]], color=[AS, WITH], width=0.6)
    for x, r in zip([0, 1], [k0, k1]):
        tag(ax, x, r["worst"] + 170, r["verdict"], text="%s\n%.0f V" % (r["verdict"], r["worst"]), fs=8)
    ax.axhline(k0["limit"], color=LIM, ls="--", lw=1.1); ax.text(1.48, k0["limit"] + 30, "1061 V", fontsize=8, ha="right", va="bottom")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["as\ndesigned", "+ P-S2b\n(RV3)"], fontsize=8)
    ax.set_ylim(0, 1600); ax.set_yticks([]); ax.set_xlim(-0.5, 1.5)
    ax.set_title("Relay K1 contact", fontsize=9)
    ax.grid(axis="both", visible=False)
    fig.suptitle("Surge proposals: an 800 V driver alone is not enough; the TVS across the triac gives 24 % margin",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    save(fig, "s03_surge_ladder")


def chart_frontend_sketch():
    fig, ax = plt.subplots(figsize=(W, 4.4), gridspec_kw=dict(left=0.005, right=0.995, top=0.995, bottom=0.005))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    yL, yN = 40, 7
    def wire(xs, ys, new=False):
        ax.plot(xs, ys, color=WITH if new else INK, lw=1.8 if new else 1.2, ls=(0, (3, 2)) if new else "-", solid_capstyle="butt", zorder=2)
    def box(x, y, w, h, txt, new=False, ec=None, fc=None):
        e = ec or (WITH if new else INK); f = fc or ("#E3EEF8" if new else "white")
        ax.add_patch(mpatches.FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.15", fc=f, ec=e, lw=1.6 if new else 1.0, zorder=3))
        ax.text(x, y, txt, ha="center", va="center", fontsize=8, zorder=4)
    def mark(x, y, num, col=WITH):
        badge(ax, x, y, num, col, r=1.6, key="fe%s" % num)
    def shunt(x, txt, new=False, w=6.6, h=4.8):
        ym = (yL + yN) / 2
        wire([x, x], [yL, ym + h / 2 + 0.15], new); wire([x, x], [ym - h / 2 - 0.15, yN], new)
        box(x, ym, w, h, txt, new)
    ax.text(1.5, 57.5, "Mains front end, simplified from the schematic. Blue dashed = proposed part; the number is the change number on the board map.",
            fontsize=8, va="center")
    ax.text(1.2, yN, "N", fontsize=8.5, ha="center", va="center", fontweight="bold")
    ax.text(1.2, yL, "L", fontsize=8.5, ha="center", va="center", fontweight="bold")
    wire([3, 95], [yN, yN])
    wire([3, 4.85], [yL, yL]); box(8, yL, 6, 3.4, "F3 8 A"); wire([11.15, 25.85], [yL, yL])
    box(30, yL, 8.0, 4.8, "L40\n100 uH"); wire([34.15, 83.35], [yL, yL])
    box(86, yL, 5.4, 4.8, "Q1\nBTA24"); wire([88.85, 95], [yL, yL])
    ax.text(18.5, yL + 2.4, "LINE_FUSED", fontsize=8, ha="center", va="bottom")
    ax.text(41.5, yL + 2.4, "LINE_FILT", fontsize=8, ha="center", va="bottom")
    shunt(14.5, "RV3\nTVR14431", new=True, w=8.6); mark(20.6, 28.6, "3")
    shunt(24.5, "K1\nto fan", w=6.2)
    shunt(36.8, "C40\n1 uF", w=6.2); shunt(44, "C1\n100 nF", w=7.0); shunt(51.2, "RV1\n14 mm", w=6.2)
    wire([60, 60], [yL, 27.35]); box(60, 24, 10.6, 6.4, "F1, L1 CMC\nHLK-10M05"); wire([60, 60], [20.65, yN])
    wire([65.45, 69.25], [24, 24])
    box(75.5, 24, 12.2, 6.4, "SELV world\nESP32, TFT, TC")
    wire([75.5, 75.5], [20.65, 16.35], new=True); wire([75.5, 75.5], [11.65, yN], new=True)
    box(75.5, 14, 12.4, 4.4, "Y1 1 nF, only\nif LCR says so", new=True, ec=VERD["MEASURE"][0], fc=VERD["MEASURE"][1])
    mark(84.2, 17.4, "5", col=VERD["MEASURE"][0])
    box(75.5, 33.0, 10.8, 4.4, "ZCD: R6/R7,\nH11AA1, U6")
    wire([65.0, 70.4], [27.35, 30.65]); wire([75.5, 75.5], [30.65, 27.35])
    wire([81.05, 81.85], [33.0, 33.0], new=True)
    box(87.0, 33.0, 10.0, 4.4, "1 nF C0G\nto SELV GND", new=True); mark(94.0, 37.6, "4")
    wire([95, 95], [yL, 28.15]); box(95, 24, 5.6, 8, "heater\n1 kW"); wire([95, 95], [19.85, yN])
    wire([82.3, 82.3], [yL, 49.5], new=False); wire([89.7, 89.7], [yL, 49.5], new=False)
    wire([82.3, 83.65], [49.5, 49.5]); wire([88.35, 89.7], [49.5, 49.5])
    box(86, 49.5, 4.4, 3.4, "TVS", new=True); mark(92.0, 52.6, "2")
    ax.text(80.0, 49.5, "RV2 -> 1.5KE440CA", fontsize=8, ha="right", va="center", color=WITH)
    box(56, 50.5, 11.0, 4.4, "U5 driver\n600 -> 800 V", new=True); mark(64.0, 54.2, "1")
    wire([56, 56, 85.0, 85.0], [48.15, 45.6, 45.6, 42.55])
    save(fig, "s04_frontend_sketch")


def chart_eft_waves():
    ew = curve("eft_waves.json")
    th = B["eft"]["thresholds"]
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.3), sharey=True, gridspec_kw=dict(wspace=0.08, left=0.085, right=0.985, top=0.82, bottom=0.15))
    for ax, (k, d), ttl in zip(axs, ew.items(), ("+ pulse: 11.3 V on a 6.5 V input today", "- pulse: dips below VT- (false edge) today")):
        a = d["as designed (8 pF node)"]; b = d["P-E1 1 nF C0G"]
        ax.axhspan(6.5, 13, color=VERD["FAIL"][1], lw=0)
        ax.plot(a["t_ns"], a["V_zcd"], color=AS, lw=1.3)
        ax.plot(b["t_ns"], b["V_zcd"], color=WITH, lw=1.8)
        hline(ax, 6.5, "U6 absolute maximum 6.5 V", va="top")
        hline(ax, th["VT+_min"], "VT+ min %.2f V" % th["VT+_min"], va="bottom", ls=":", x=0.995)
        hline(ax, th["VT-_max"], "VT- max %.2f V" % th["VT-_max"], va="top", ls=":", x=0.995)
        ax.set_xlim(0, 600); ax.set_ylim(-6, 12.5)
        ax.set_xlabel("time from the burst pulse (ns)")
        ax.set_title(ttl, fontsize=8.5)
        ax.text(250, 9.2, "as designed: %.2f to %.2f V" % (min(a["V_zcd"]), max(a["V_zcd"])), fontsize=8, color=AS)
        ax.text(250, -4.5, "with 1 nF (P-E1): %.2f to %.2f V" % (min(b["V_zcd"]), max(b["V_zcd"])), fontsize=8, color=WITH)
    axs[0].set_ylabel("ZCD node vs SELV GND (V)")
    fig.suptitle("EFT 1 kV burst, worst corner (C_hlk 20 pF, transistor off): the 1 nF holds the node at 3.3 V",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    save(fig, "e01_eft_waves")


def chart_eft_summary():
    cases = B["eft"]["cases"]; th = B["eft"]["thresholds"]; prop = B["eft"]["proposal_P_E1_1nF_on_ZCD_node"]
    fig, axs = plt.subplots(1, 2, figsize=(W, 3.9), gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.42, left=0.085, right=0.985, top=0.80, bottom=0.2))
    ax = axs[0]
    off = [c for c in cases if "transistor off" in c["case"]]
    pr_off = [p for p in prop["rows"] if p["transistor"] == "off"]
    ax.axhspan(-6, th["VT-_max"], color=VERD["FAIL"][1], lw=0)
    ax.scatter(np.arange(len(off)), [c["V_ZC_min"] for c in off], color=AS, s=18, zorder=3)
    ax.axhline(prop["worst_off_min"], color=WITH, lw=1.6)
    ax.text(17.5, 4.2, "with 1 nF: lowest %.2f V (%d corners)" % (prop["worst_off_min"], len(pr_off)), fontsize=8, color=WITH, ha="right", va="center")
    ax.axhline(th["VT-_max"], color=LIM, ls=":", lw=1.2); ax.text(17.5, -2.5, "below the dotted VT- max (%.2f V)\n= false edge" % th["VT-_max"], fontsize=8, ha="right", va="center")
    nfe = len(B["eft"]["zcd_false_edge_cases"])
    ax.set_xlim(-0.8, 17.8); ax.set_ylim(-5.5, 5)
    ax.set_xticks([]); ax.set_xlabel("18 burst corners, transistor off (polarity, C_hlk, strays)")
    ax.set_ylabel("ZCD node minimum (V)")
    ax.set_title("False ZCD edges today: %d of %d corners;\nnone with the 1 nF (P-E1)" % (nfe, len(cases)), fontsize=8.5)
    ax = axs[1]
    fw = B["eft_firmware"]
    dut = sorted(fw["current_firmware"], key=float)
    err = [fw["current_firmware"][d]["burst"]["error_pct_of_full"] for d in dut]
    err2 = [fw["P_E2_level_qualified_50us"][d]["burst"]["error_pct_of_full"] for d in dut]
    x = np.arange(len(dut))
    ax.bar(x - 0.18, err, width=0.36, color=AS); ax.bar(x + 0.18, err2, width=0.36, color=WITH)
    for xi, e in zip(x, err):
        ax.text(xi - 0.18, e + 0.15 if e >= 0 else e - 0.15, "%+.1f" % e, ha="center", va="bottom" if e >= 0 else "top", fontsize=8, color=AS)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(dut); ax.set_xlabel("heater duty")
    ax.set_ylabel("power error during\nbursts (% of full)"); ax.set_ylim(-1, 5.6)
    ax.text(4.45, 5.4, "left bars: today\nright bars: with P-E2", fontsize=8, color=INK2, ha="right", va="top")
    ax.set_title("Firmware: bursts add a few %\nof power; P-E2 removes it", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    save(fig, "e02_eft_summary")


def chart_dips():
    dw = curve("dips_waves.json")
    keys = [k for k in dw if "worst" not in k]
    fig, axs = plt.subplots(3, 3, figsize=(W, 8.6), sharey="row", gridspec_kw=dict(hspace=0.12, wspace=0.08, left=0.085, right=0.985, top=0.87, bottom=0.09))
    xr = {0: (-20, 80), 1: (-20, 330), 2: (-20, 620)}
    for j, k in enumerate(keys):
        d = dw[k]
        for i, (sig, lim, lt) in enumerate((("V_bulk", 70, "HLK drop-out 70 V (assumed corner)"), ("V_5V", 3.35, "buck UVLO 3.35 V"),
                                           ("V_3V3", 2.43, "ESP32 brown-out 2.43 V"))):
            ax = axs[i, j]
            ax.plot(d["t_ms"], d[sig], color=AS, lw=1.4)
            wk = k + " | worst corner"
            if wk in dw:
                ax.plot(dw[wk]["t_ms"], dw[wk][sig], color=INK2, lw=0.6, ls=(0, (3, 2)), alpha=0.6)
            ax.axhline(lim, color=LIM, ls="--", lw=1.0)
            if j == 2:
                ax.text(xr[j][1] - 8, lim + (12 if i == 0 else 0.15), lt, fontsize=8, ha="right", va="bottom")
            ax.set_xlim(*xr[j])
            if i < 2:
                plt.setp(ax.get_xticklabels(), visible=False)
        axs[0, j].set_title(k.replace(" cycles", " cycles").replace(" / ", " residual, "), fontsize=8.5)
        axs[2, j].set_xlabel("time from dip start (ms)")
    axs[0, 0].set_ylabel("HLK bulk (V)"); axs[1, 0].set_ylabel("+5 V rail (V)"); axs[2, 0].set_ylabel("+3V3 rail (V)")
    axs[0, 0].set_ylim(0, 380); axs[1, 0].set_ylim(0, 5.8); axs[2, 0].set_ylim(0, 3.9)
    wk = [k for k in dw if "worst" in k][0]
    axs[2, 0].text(-15, 0.3, "dashed (40 % column): bulk 10 uF,\n90 V drop-out - the one corner\nof 18 that resets", fontsize=8, color=INK2)
    fig.suptitle("Dips (Table 13): with bulk >= 22 uF the 3V3 rail never moves (%.2f V); criterion C allows a reset anyway"
                 % min(dw[k]["min_3V3"] for k in keys), x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    fig.text(0.012, 0.925, "orange: bulk 22 uF (derived from the HLK datasheet), drop-out 70 V, 5.5 W load", fontsize=8, color=AS)
    save(fig, "d01_dips")


def chart_esd_cbar():
    eb = B["esd_barrier_vs_Cbar"]; cx = np.array(eb["Cbar_pF"])
    off = REPORT_ONLY["cbar_offset_pF"][0]
    fig, ax = plt.subplots(figsize=(W, 5.0), gridspec_kw=dict(left=0.085, right=0.975, top=0.78, bottom=0.12))
    rel = 2121.32; ok = 0.8 * rel; hlk = 3536
    ax.axhspan(rel, 4500, color=VERD["FAIL"][1], lw=0); ax.axhspan(ok, rel, color=VERD["MARGINAL"][1], lw=0); ax.axhspan(0, ok, color=VERD["PASS"][1], lw=0, alpha=0.7)
    ax.text(2300, 4380, "FAIL", fontsize=8, color=VERD["FAIL"][0], ha="right", va="top", fontweight="bold")
    ax.text(2300, (ok + rel) / 2, "MARGINAL (< 20 % margin)", fontsize=8, color=VERD["MARGINAL"][0], ha="right", va="center", fontweight="bold")
    ax.text(2300, ok - 80, "PASS", fontsize=8, color=VERD["PASS"][0], ha="right", va="top", fontweight="bold")
    ax.axhline(hlk, color=LIM, ls=":", lw=1.1); ax.text(2300, hlk + 40, "HLK isolation 2500 Vac = 3536 Vpk", fontsize=8, va="bottom", ha="right")
    ax.axhline(rel, color=LIM, ls="--", lw=1.1); ax.text(2300, rel + 40, "relay K1 coil-contact 1500 Vac = 2121 Vpk", fontsize=8, va="bottom", ha="right")
    cols = {"Cenv 10 pF": INK, "Cenv 30 pF": S5, "Cenv 100 pF": S3}
    for kk, ys in eb["curves"].items():
        ax.plot(cx, ys, "-o", color=cols[kk], ms=3, lw=1.5)
    cr = eb["crossing_Cbar_pF"]
    for kk in eb["curves"]:
        c1 = cr[kk + " | relay coil-contact 1500 Vac = 2121 Vpk"]; c2 = cr[kk + " | relay coil-contact 1500 Vac = 2121 Vpk | for PASS (>= 20 % margin)"]
        ax.plot([c1], [rel], "v", color=cols[kk], ms=6); ax.plot([c2], [ok], "v", color=cols[kk], ms=6)
    hd = [Line2D([], [], color=cols[k], marker="o", ms=3, lw=1.5, label="SELV to ground plane %s" % k.replace("Cenv ", "")) for k in eb["curves"]]
    hd.append(Line2D([], [], color=INK2, marker="v", ls="none", ms=6, label="crossing points (fail / pass thresholds)"))
    ax.legend(handles=hd, loc="lower left", fontsize=8, bbox_to_anchor=(0.0, 0.02))
    y1 = bv("ESD, proposal P-D1", "Barrier")
    ax.plot([1000 + 20], [y1["worst"]], marker="*", color=WITH, ms=11, ls="none")
    ax.text(1000, y1["worst"] + 380, "with Y1 1 nF (P-D1):\n%.0f V" % y1["worst"], fontsize=8, color=WITH, ha="center", va="bottom")
    ax.set_xscale("log"); ax.set_xlim(18, 2400); ax.set_ylim(0, 4500)
    ax.set_xlabel("total SELV-to-mains capacitance C_bar (pF) = LCR reading of HLK +Vout to AC + about %g pF" % off)
    ax.set_ylabel("barrier voltage after 4 kV contact (V)")
    from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
    tk = [20, 50, 70, 100, 140, 200, 500, 1000, 2000]
    ax.xaxis.set_major_locator(FixedLocator(tk)); ax.xaxis.set_major_formatter(FixedFormatter([str(t) for t in tk])); ax.xaxis.set_minor_locator(NullLocator())
    sec = ax.secondary_xaxis("top", functions=(lambda x: x - off, lambda x: x + off))
    tk2 = [15, 45, 65, 95, 135, 195, 495, 995, 1995]
    sec.xaxis.set_major_locator(FixedLocator(tk2)); sec.xaxis.set_major_formatter(FixedFormatter([str(t) for t in tk2])); sec.xaxis.set_minor_locator(NullLocator())
    sec.tick_params(labelsize=8)
    sec.set_xlabel("LCR-meter reading, HLK +Vout to AC pins (pF)", fontsize=8)
    fig.suptitle("ESD 4 kV contact on the thermocouple probe: the LCR reading decides the verdict",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    save(fig, "x01_esd_cbar")


def chart_esd_other():
    items = []
    for t, p, nm in (("ESD 4 kV contact", "D220", "TVS D220 current"), ("ESD 4 kV contact", "ADS1115", "ADS1115 input (voltage rule)"),
                     ("ESD 8 kV air / 4 kV contact, steel", "Barrier", "steel sheet: SELV barrier"), ("EFT 1 kV", "Barrier", "EFT: SELV barrier (comparison)")):
        r = bv(t, p)
        items.append((nm, r["worst"] / r["limit"] * 100, r["verdict"], "%s of %s %s  %s" % (_fmt(r["worst"]), _fmt(r["limit"]), r["unit"], r["verdict"])))
    g = bv("ESD 8 kV air, glass", "GT911")
    items.append(("glass over the touch panel\n(couples %.2f x the bare cover)" % g["worst"], None, "NOT SIMULABLE", ""))
    fig, ax = plt.subplots(figsize=(W, 3.0), gridspec_kw=dict(left=0.27, right=0.985, top=0.86, bottom=0.2))
    stress_bars(ax, items, "Other ESD points: ADS1115 input MARGINAL on the voltage rule only", xmax=140)
    save(fig, "x02_esd_other")


def _fmt(v):
    return ("%.3g" % v) if v < 100 else ("%.0f" % v)


def chart_re_mechanism():
    fig, ax = plt.subplots(figsize=(W, 4.6), gridspec_kw=dict(left=0.005, right=0.995, top=0.995, bottom=0.005))
    ax.set_xlim(0, 100); ax.set_ylim(0, 64); ax.axis("off")
    md = C["emission"]["mode"]
    gap = REPORT_ONLY["pcb_panel_gap_mm"][0]
    ax.text(1, 62, "How the board radiates (cross-section, not to scale): the display return current turns panel and PCB into an antenna",
            fontsize=8.5, fontweight="bold", va="center")
    ax.text(1, 58.6, "Model: thin-wire MoM of PCB, panel, FPC and cables; common-mode results about +-%g dB. Panel frame assumed tied to panel GND."
            % REPORT_ONLY["rc_uncertainty_dB"][0], fontsize=8, va="center", color=INK2)
    ax.text(45, 54.6, "Fixes (blue): bond the panel frame to PCB GND at about 19 points around the edge; 150 ohm ferrite on the FPC;",
            fontsize=8, ha="center", va="center", color=WITH)
    ax.text(45, 51.4, "RN1-RN7 33 -> 150 ohm (slower edges); %s +5V-GND at the J10 vias (removes the 498.5 MHz island resonance)" % REPORT_ONLY["j10_option_name"][0],
            fontsize=8, ha="center", va="center", color=WITH)
    ax.add_patch(mpatches.Rectangle((14, 42), 56, 6, fc="#DADADA", ec=INK, lw=1.0))
    ax.text(42, 45, "7-inch TFT panel: metal frame = panel GND", fontsize=8, ha="center", va="center")
    ax.add_patch(mpatches.Rectangle((16, 27), 52, 2.6, fc="#BFD7B5", ec=INK, lw=1.0))
    ax.text(36, 25.6, "PCB, In1 = GND plane", fontsize=8, ha="left", va="top")
    ax.add_patch(mpatches.Rectangle((19.4, 29.6), 1.2, 12.4, fc="white", ec=INK2, lw=0.8))
    ax.annotate("", xy=(23.5, 42), xytext=(23.5, 29.6), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
    ax.text(24.5, 37.5, "%g mm\nspacer gap" % gap, fontsize=8, va="center")
    for x in (36.5, 39.5):
        ax.add_patch(mpatches.Rectangle((x - 0.4, 29.6), 0.8, 12.4, fc=WITH, ec="none"))
    ax.text(35.2, 31.6, "bonding\ncontacts", fontsize=8, va="center", ha="right", color=WITH)
    ax.annotate("", xy=(45, 42), xytext=(45, 29.6), arrowprops=dict(arrowstyle="<->", color=AS, lw=1.6))
    ax.text(46.2, 38.6, "common-mode voltage:\npanel metal vs PCB GND", fontsize=8, va="center", color=AS)
    ax.text(46.2, 33.6, "resonance %.0f MHz,\nloaded Q about %.1f" % (md["f0_MHz"], md["Q_loaded_(unloaded 30/10/3)"]["10.0"]), fontsize=8, va="center", color=AS)
    ax.add_patch(mpatches.Rectangle((64.5, 29.6), 3.5, 1.6, fc=INK2, ec=INK, lw=0.8))
    ax.text(66.2, 25.6, "J10", fontsize=8, ha="center", va="top")
    t = np.linspace(-np.pi / 2, np.pi / 2, 60)
    fx = 68 + 9 * np.cos(t); fy = 37.5 + 8.2 * np.sin(t)
    ax.plot(np.r_[66.2, fx, 68], np.r_[30.4, fy, 45.7], color="#C9A227", lw=4.0, solid_capstyle="butt")
    ax.add_patch(mpatches.Rectangle((75.6, 35.0), 3.0, 5.0, fc=WITH, ec="none"))
    ax.text(80.0, 45.0, "FPC tail %.2f mm\n+ 20 mm in the panel" % REPORT_ONLY["fpc_tail_mm"][0], fontsize=8, va="center")
    ax.text(80.0, 37.5, "ferrite (proposed)", fontsize=8, va="center", color=WITH)
    ax.text(80.0, 30.0, "28 fast lines out;\nreturn crowds onto\n3 GND pins (3, 29, 36)\n+ VDD (pin 4)", fontsize=8, va="center")
    for x, nm in ((20, "mains cord"), (26, "thermocouple"), (32, "fan, heater")):
        ax.plot([x, x], [27, 2], color=INK, lw=1.4)
        ax.text(x + 0.9, 2.5, nm, fontsize=8, va="bottom", ha="left", rotation=90)
        ax.annotate("", xy=(x, 15.5), xytext=(x, 22.5), arrowprops=dict(arrowstyle="->", color=AS, lw=1.4))
    ax.text(38, 15.5, "The cables carry the common-mode current and radiate:\nat the PCLK harmonics they carry 25-36 dB more\ncurrent than the limit allows",
            fontsize=8, va="center", color=AS)
    save(fig, "r01_re_mechanism")


def chart_re_spectrum():
    e = C["emission"]
    fig, axs = plt.subplots(3, 1, figsize=(W, 8.6), sharex=True, gridspec_kw=dict(hspace=0.3, left=0.085, right=0.975, top=0.955, bottom=0.06))
    fl = np.geomspace(30e6, 1e9, 400)
    lim = C_COMMON.lim_far3m(fl)
    ttl = {"PCLK": "PCLK harmonics (33.3 MHz, always present): up to %.1f dB over the limit",
           "typical UI": "Typical UI content: up to %.1f dB over the limit",
           "worst pattern": "1-pixel stripes (not a normal operating mode): up to %.1f dB over the limit"}
    pend = []
    for ax, k in zip(axs, ("PCLK", "typical UI", "worst pattern")):
        rows = e["tables"][k]
        f = np.array([r["f_MHz"] for r in rows]); en = np.array([r["E_nom_Q10"] for r in rows])
        lo = np.array([r["E_low_Q3"] for r in rows]); hi = np.array([r["E_high_Q30_env"] for r in rows])
        ax.vlines(f, lo, hi, color=AS, lw=3.0, alpha=0.35)
        ax.plot(f, en, "o", color=AS, ms=3.5)
        ax.plot(fl / 1e6, lim, color=LIM, ls="--", lw=1.2)
        p, fb = combo(k)
        ax.plot([p["nominal"]["f_MHz"]], [p["nominal"]["E_nom_Q10"]], "s", color=WITH, ms=6)
        pend.append((ax, p["nominal"]))
        wr = e["worst_rows"][k]
        ax.set_title(ttl[k] % (-wr["margin_nom"]), fontsize=9.5)
        ax.set_xscale("log"); ax.set_xlim(30, 1000); ax.set_ylim(0, 100)
        ax.set_ylabel("E at 3 m (dBuV/m)")
    axs[-1].set_xlabel("frequency (MHz)")
    axs[-1].set_xticks([30, 50, 100, 200, 300, 500, 1000]); axs[-1].set_xticklabels(["30", "50", "100", "200", "300", "500", "1000"])
    pl = Placer(fig)
    for ax, p in pend:
        pl.place(ax, [(31, 42.0, "left", "bottom", 0, 3), (31, 42.0, "left", "top", 0, -3)], "Table 9 limit, FAR 3 m", fontsize=8)
        s = "all four changes (blue square): %.1f dBuV/m, %+.1f dB" % (p["E_nom_Q10"], p["margin_nom"])
        x, y = p["f_MHz"], p["E_nom_Q10"]
        pl.place(ax, [(x, y, "right", "center", -7, 0), (x, y, "right", "top", -6, -5), (x, y, "left", "top", 6, -5), (x, y, "right", "bottom", -6, 5),
                      (x, y, "center", "top", 0, -7), (x, y, "left", "center", 7, 0)], s, fontsize=8, color=WITH)
    pl.place(axs[0], [(990, 92, "right", "center"), (990, 8, "right", "center")],
             "dot: Q 10; bar: Q 3 to Q 30 + cable/barrier envelope; model +-%g dB" % REPORT_ONLY["rc_uncertainty_dB"][0], fontsize=8, color=INK2)
    save(fig, "r02_re_spectrum")


def chart_re_power():
    pb = C["emission"]["power_balance"]
    fig, axs = plt.subplots(2, 1, figsize=(W, 3.7), gridspec_kw=dict(hspace=0.75, left=0.11, right=0.975, top=0.92, bottom=0.12))
    for ax, src, ttl in zip(axs, ("24 data lines in phase", "PCLK"), ("24 data lines in phase", "PCLK")):
        rows = [r for r in pb if r["source"] == src]
        x = np.arange(len(rows))
        av = [r["P_avail_uW"] for r in rows]; dl = [max(r["P_in_Q10_uW"], 1e-4) for r in rows]
        ax.bar(x, av, width=0.75, color="white", edgecolor=INK2, lw=0.9)
        ax.bar(x, dl, width=0.45, color=AS)
        ax.set_yscale("log"); ax.set_ylim(1e-3, 1e5)
        ax.set_yticks([1e-3, 1e-1, 1e1, 1e3, 1e5]); ax.set_yticklabels(["0.001", "0.1", "10", "1000", "100000"])
        ax.set_xticks(x); ax.set_xticklabels(["%.0f" % r["f_MHz"] for r in rows], rotation=90, fontsize=8)
        ax.set_ylabel("power (uW)")
        worst = max(r["ratio_Q10_to_avail_dB"] for r in rows)
        ax.set_title("%s: delivered power always below what the drivers can supply (worst %.1f dB)" % (ttl, worst), fontsize=9)
        ax.grid(axis="x", visible=False)
        ax.text(len(rows) - 0.5, 2e4, "outline: available from the drivers\nfilled: delivered into the structure (Q 10)", fontsize=8, ha="right", va="center", color=INK2)
    axs[1].set_xlabel("harmonic frequency (MHz)")
    save(fig, "r03_re_power")


def chart_re_cables():
    cb = C["emission"]["cable_budget"]
    names = {"mains_cable": "mains cord", "heater": "heater lead", "fan": "fan lead", "tc": "thermocouple lead"}
    fig, ax = plt.subplots(figsize=(W, 3.1), gridspec_kw=dict(left=0.085, right=0.985, top=0.86, bottom=0.2))
    xt, xl = [], []
    x = 0
    for c, rows in cb.items():
        for r in rows:
            ax.plot([x - 0.3, x + 0.3], [r["I_at_limit_uA"]] * 2, color=LIM, lw=2.0)
            lo, hi = r["band_uA(Q3..Q30)"]
            ax.vlines(x, lo, hi, color=AS, lw=4, alpha=0.35)
            ax.plot([x], [r["I_est_PCLK_Q10_uA"]], "o", color=AS, ms=4)
            xt.append(x); xl.append("%.0f" % r["f_MHz"]); x += 1
        ax.text(x - 3, 1500, names[c], ha="center", fontsize=8, fontweight="bold")
        x += 1.2
    ax.set_yscale("log"); ax.set_ylim(0.3, 4000)
    ax.set_xticks(xt); ax.set_xticklabels(xl, fontsize=8); ax.set_xlabel("PCLK harmonic (MHz), per cable")
    ax.set_ylabel("common-mode current (uA)")
    ax.grid(axis="x", visible=False)
    ax.set_xlim(-0.8, x - 0.4)
    ax.set_title("Cable common-mode current, PCLK: estimated (dots, Q 3-30 bar) vs allowed at the limit (black dash)", fontsize=9.5)
    save(fig, "r04_re_cables")


def chart_re_ladder():
    e = C["emission"]; P = e["proposals"]; opt = REPORT_ONLY["j10_option_key"][0]
    capname = REPORT_ONLY["j10_option_name"][0]
    rows = [("as designed", None),
            ("panel frame bonded, 6 contacts", "bond_6pt"), ("panel frame bonded, 19 contacts", "bond_perimeter"),
            ("FPC ferrite 150 ohm alone", "ferrite_fpc_150"), ("RN1-RN7 150 ohm alone", "RN 150 ohm"),
            ("%s at the J10 vias alone" % capname, "J10 caps %s alone" % opt),
            ("19 contacts + ferrite", "bond_perimeter_ferrite"),
            ("19 contacts + RN 150 + %s" % capname, "@bond_perimeter + RN 150"),
            ("all four: 19 + ferrite + RN 150 + %s" % capname, "@bond_perimeter_ferrite + RN 150"),
            ("check: panel frame floating (as designed)", "frame_floating")]
    cols = ("PCLK", "typical UI", "worst pattern")
    fig, axs = plt.subplots(1, 3, figsize=(W, 4.6), sharey=True, gridspec_kw=dict(wspace=0.08, left=0.335, right=0.985, top=0.84, bottom=0.11))
    ys = np.arange(len(rows))[::-1]
    pend = []; marks = []
    for ax, c in zip(axs, cols):
        ax.axvspan(-70, 0, color=VERD["FAIL"][1], lw=0); ax.axvspan(0, 6, color=VERD["MARGINAL"][1], lw=0); ax.axvspan(6, 60, color=VERD["PASS"][1], lw=0, alpha=0.6)
        for y, (lab, key) in zip(ys, rows):
            fb = False
            if key is None:
                nom, up = e["worst_rows"][c]["margin_nom"], e["worst_rows_upper"][c]["margin_high"]
            else:
                if key.startswith("@"):
                    d, fb = combo(c, key[1:])
                else:
                    d = P[key].get(c)
                if not d:
                    pend.append((ax, [(-62, y, "left", "center")], "not computed", INK2))
                    continue
                nom, up = d["nominal"]["margin_nom"], d["upper"]["margin_high"]
            col = AS if key in (None, "frame_floating") else WITH
            ax.plot([nom, up], [y, y], color=col, lw=1.5)
            ax.plot([up], [y], marker="|", color=col, ms=7)
            ax.plot([nom], [y], marker="o" if col == AS else "s", color=col, ms=5)
            lab_ = "%+.1f" % nom + ("*" if fb else "")
            r_, l_ = max(nom, up), min(nom, up)
            pend.append((ax, [(r_, y, "left", "center", 6, 0), (l_, y, "right", "center", -6, 0), (r_, y, "left", "bottom", 4, 4),
                              (l_, y, "right", "bottom", -4, 4), (r_, y, "left", "top", 4, -4), (nom, y, "center", "bottom", 0, 6),
                              (nom, y, "right", "bottom", 0, 6), (nom, y, "center", "top", 0, -6), (nom, y, "right", "top", 0, -6)], lab_, col))
        ax.axvline(0, color=LIM, lw=1)
        ax.set_xlim(-64, 46); ax.set_xticks([-50, -25, 0, 25]); ax.set_title(c, fontsize=9)
        ax.set_xlabel("margin (dB)")
        ax.grid(False)
        ax.axhline(0.5, color=INK2, lw=0.8, ls=":")
    axs[0].set_yticks(ys); axs[0].set_yticklabels([r[0] for r in rows], fontsize=8); axs[0].tick_params(axis="y", length=0)
    fig.suptitle("Radiated emission margin, FAR 3 m (dot: nominal Q 10; whisker: worst upper end; model about +-10 dB)",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    fig.text(0.012, 0.93, "Only all four changes together pass PCLK with >= 6 dB at the upper end; 1-pixel stripes still fail.", fontsize=8, color=INK2)
    fig.text(0.012, 0.905, "* row computed by scope C with the earlier 2 x 1 nF (C ran the new capacitors for PCLK only).", fontsize=8, color=INK2)
    pl = Placer(fig)
    for ax, cands, s, col in pend:
        pl.place(ax, cands, s, fontsize=8, color=col)
    save(fig, "r05_re_ladder")


def chart_rf_immunity():
    inj = C["injected"]; ri = C["radiated_immunity"]
    crit = REPORT_ONLY["tc_criterion_degC"][0]; lm = REPORT_ONLY["display_logic_margin_V"][0]
    def worst(prefix, junction, key):
        return max(v[key] for k, v in inj.items() if isinstance(v, dict) and k.startswith(prefix) and ("junction " + junction) in k)
    rows = [("mains 3 V, grounded junction", worst("mains port", "grounded", "dT_worst_bound_degC"), worst("mains port", "grounded", "dT_realistic_degC"), "PASS"),
            ("mains 3 V, insulated junction", worst("mains port", "insulated", "dT_worst_bound_degC"), worst("mains port", "insulated", "dT_realistic_degC"), "PASS"),
            ("TC lead 1 V (N/A: lead is 1 m)", worst("TC lead", "grounded", "dT_worst_bound_degC"), worst("TC lead", "grounded", "dT_realistic_degC"), "N/A"),
            ("EFT burst (scope B)", None, bv("EFT TC lead", "TC reading")["worst"], "PASS")]
    fig, axs = plt.subplots(1, 2, figsize=(W, 4.6), gridspec_kw=dict(width_ratios=[1.6, 1], wspace=0.55, left=0.235, right=0.985, top=0.83, bottom=0.17))
    ax = axs[0]
    ys = np.arange(len(rows))[::-1]
    ax.axvspan(crit, 100, color=VERD["FAIL"][1], lw=0)
    pend = []
    for y, (lab, bnd, real, v) in zip(ys, rows):
        col = INK2 if v == "N/A" else AS
        if bnd is not None:
            ax.plot([real, bnd], [y, y], color=col, lw=1.5); ax.plot([bnd], [y], "|", color=col, ms=8)
            pend.append((ax, [(bnd, y, "right", "bottom", 0, 7), (bnd, y, "center", "bottom", 0, 7), (bnd, y, "left", "center", 9, 0), (bnd, y, "left", "bottom", 6, 7),
                              ((real * bnd) ** 0.5, y, "center", "bottom", 0, 7), (bnd, y, "right", "top", 0, -7)], "bound %.2g" % bnd, col))
        ax.plot([real], [y], "o", color=col, ms=5)
        pend.append((ax, [(real, y, "right", "center", -6, 0), (real, y, "center", "top", 0, -6)], "%.2g" % real, col))
    ax.axvline(crit, color=LIM, ls="--", lw=1.1)
    ax.set_xscale("log"); ax.set_xlim(1e-6, 100); ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=8); ax.tick_params(axis="y", length=0)
    ax.set_xticks([1e-5, 1e-3, 1e-1, 10]); ax.set_xticklabels(["0.00001", "0.001", "0.1", "10"])
    ax.set_xlabel("thermocouple reading error (degC);\ndashed line: 0.5 degC criterion (proposed)"); ax.grid(axis="y", visible=False)
    ax.set_title("Thermocouple: dot realistic, whisker worst-case\nbound. RF field 3 V/m: about 0 degC", fontsize=8.5)
    ax = axs[1]
    q10 = [ri["lossy Q 10 (nominal cables)"]["panel_input_noise_Vpk_max"], ri["lossy Q 10 + panel bonded 6 contacts"]["panel_input_noise_Vpk_max"],
           ri["lossy Q 10 + panel bonded 19 contacts"]["panel_input_noise_Vpk_max"]]
    ax.bar([0, 1, 2], q10, color=[AS, WITH, WITH], width=0.6)
    lo, hi = ri["lossy Q 3 (nominal cables)"]["panel_input_noise_Vpk_max"], ri["lossy Q 30 (nominal cables)"]["panel_input_noise_Vpk_max"]
    ax.vlines(0, lo, hi, color=INK, lw=1.2); ax.plot([-0.08, 0.08], [lo, lo], color=INK, lw=1.2); ax.plot([-0.08, 0.08], [hi, hi], color=INK, lw=1.2)
    ax.axhline(lm, color=LIM, ls="--", lw=1.1)
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["as\ndesigned", "6\ncontacts", "19\ncontacts"], fontsize=8); ax.set_ylim(0, 2.1)
    ax.set_ylabel("noise at the panel\ninputs, 3 V/m (V peak)")
    ax.set_title("Display inputs: FAIL risk\ntoday; bonding fixes it", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    pl = Placer(fig)
    for a, c, s, col in pend:
        pl.place(a, c, s, fontsize=8, color=col)
    for x, v in zip([0, 1, 2], q10):
        pl.place(ax, [(x, max(v, hi if x == 0 else v), "center", "bottom", 0, 4), (x + 0.32, v, "left", "bottom", 0, 3)], "%.2f V" % v, fontsize=8)
    xr = ax.get_xlim()[1]
    pl.place(ax, [(xr, lm, "right", "bottom", -2, 3), (xr, lm, "right", "top", -2, -3)], "logic margin %.2f V" % lm, fontsize=8)
    save(fig, "f01_rf_immunity")


def chart_y1():
    sb = A["A1_crosscheck_scopeB"]["selv_noise_bound"]; cy = C["cross_scope_conducted_Y1"]; tcy = C["injected"]["cross_scope_Y1_thermocouple"]
    fig, axs = plt.subplots(2, 2, figsize=(W, 8.6), gridspec_kw=dict(hspace=0.62, wspace=0.42, left=0.1, right=0.985, top=0.9, bottom=0.08))
    ax = axs[0, 0]
    e0 = bv("ESD 4 kV contact", "Barrier"); e1 = bv("ESD, proposal P-D1", "Barrier")
    ax.bar([0, 1], [e0["worst"], e1["worst"]], color=[AS, WITH], width=0.6)
    ax.axhline(e0["limit"], color=LIM, ls="--", lw=1.1); ax.text(1.45, e0["limit"] + 120, "relay 2121 V", fontsize=8, ha="right", va="bottom")
    for x, r in zip([0, 1], [e0, e1]):
        tag(ax, x, r["worst"] + 420, r["verdict"], text="%s %.0f V" % (r["verdict"], r["worst"]), fs=8)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["no Y1\n(C_bar 20 pF)", "Y1 1 nF"], fontsize=8); ax.set_ylim(0, 5000); ax.set_xlim(-0.5, 1.5)
    ax.set_ylabel("ESD barrier voltage (V)"); ax.grid(axis="x", visible=False)
    ax.set_title("Gain: ESD barrier\n3.98 kV -> 0.53 kV", fontsize=8.5)
    ax = axs[0, 1]
    styles = [("no Y1 (HLK primary-secondary 50 pF only)", INK, "no Y1"), ("Y1 470 pF", S3, "470 pF"), ("Y1 1 nF", WITH, "1 nF"), ("Y1 2.2 nF", S5, "2.2 nF")]
    for k, col, lab in styles:
        d = sb[k]; fq = sorted(float(x.replace("MHz", "")) for x in d)
        ax.plot(fq, [d["%gMHz" % f]["Vn_max_AV_dBuV"] for f in fq], "-o", color=col, ms=3)
        ax.text(0.15, d["0.15MHz"]["Vn_max_AV_dBuV"], lab, fontsize=8, color=col, va="center", ha="right",
                transform=__import__("matplotlib.transforms", fromlist=["x"]).offset_copy(ax.transData, fig=fig, x=-6, units="points"))
    for f, n in ((0.58, "buck"), (1.2, "boost")):
        ax.axvline(f, color=INK2, ls=":", lw=0.9)
        ax.text(f, 118, n, fontsize=8, color=INK2, va="top", ha="right" if n == "buck" else "left",
                transform=__import__("matplotlib.transforms", fromlist=["x"]).offset_copy(ax.transData, fig=fig, x=-4 if n == "buck" else 4, units="points"))
    ax.set_xscale("log"); ax.set_xlim(0.04, 60); ax.set_ylim(40, 120)
    ax.set_xticks([0.15, 0.5, 1, 5, 30]); ax.set_xticklabels(["0.15", "0.5", "1", "5", "30"])
    ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("SELV noise that reaches\nthe AV limit (dBuV)")
    ax.set_title("Cost: Y1 lets 25-35 dB less\nSELV noise through", fontsize=8.5)
    ax = axs[1, 0]
    src = cy["sources"]
    items = [("buck 0.58 MHz", src["buck SW 580 kHz"]), ("boost 1.2 MHz", src["boost SW 1.2 MHz"]), ("FPC 16.65 MHz", src["FPC panel-PCB source, worst pattern (16.65 MHz)"])]
    x = np.arange(len(items))
    ax.axhspan(-40, 0, color=VERD["FAIL"][1], lw=0); ax.axhspan(0, 6, color=VERD["MARGINAL"][1], lw=0)
    real = [d["worst_margin_realistic_dB"] for _, d in items]; bnd = [d["worst_margin_bound_dB"] for _, d in items]
    no = [d["margin_without_Y1_realistic_dB(+25..35)"] for _, d in items]
    ax.bar(x - 0.2, real, width=0.38, color=AS)
    for xi, (a, b) in zip(x, no):
        ax.add_patch(mpatches.Rectangle((xi + 0.01, a), 0.38, b - a, fc=WITH, ec="none", alpha=0.75))
    for xi, r, bd in zip(x, real, bnd):
        ax.text(xi - 0.2, r - 1.5, "%+.1f" % r, fontsize=8, ha="center", va="top", color=AS)
    ax.axhline(0, color=LIM, lw=1)
    ax.set_xticks(x); ax.set_xticklabels([i[0] for i in items], fontsize=8)
    ax.set_ylim(-35, 40); ax.set_ylabel("conducted AV margin (dB)")
    ax.text(2.45, 37, "left: with Y1 1 nF (realistic)\nright: without Y1 (+25 to 35 dB)", fontsize=8, ha="right", va="top", color=INK2)
    ax.set_title("Cost: conducted FAIL at the\nconverter frequencies with Y1", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    ax = axs[1, 1]
    vals = [0, 470, 1000, 2200]
    bg = [tcy["mains 3 V | junction grounded | barrier 50 pF | Y1 %d pF" % v]["dT_worst_bound_degC"] for v in vals]
    rg = [tcy["mains 3 V | junction grounded | barrier 50 pF | Y1 %d pF" % v]["dT_realistic_degC"] for v in vals]
    xs = np.arange(len(vals))
    ax.axhspan(REPORT_ONLY["tc_criterion_degC"][0], 100, color=VERD["FAIL"][1], lw=0)
    ax.plot(xs, bg, "-s", color=AS, ms=4); ax.plot(xs, rg, "-o", color=WITH, ms=4)
    for xi, a, b in zip(xs, bg, rg):
        if xi == 0:
            ax.text(xi - 0.1, a, "%.2g" % a, fontsize=8, color=AS, va="center", ha="right")
            ax.text(xi - 0.1, b, "%.2g" % b, fontsize=8, color=WITH, va="center", ha="right")
            continue
        ax.text(xi + 0.08, a * 1.5, "%.2g" % a, fontsize=8, color=AS, va="bottom")
        ax.text(xi + 0.08, b / 1.6, "%.2g" % b, fontsize=8, color=WITH, va="top")
    ax.axhline(REPORT_ONLY["tc_criterion_degC"][0], color=LIM, ls="--", lw=1.1)
    ax.text(3.5, 0.6, "0.5 degC", fontsize=8, va="bottom", ha="right")
    ax.set_yscale("log"); ax.set_ylim(1e-4, 100)
    ax.set_xticks(xs); ax.set_xticklabels(["no Y1", "470 pF", "1 nF", "2.2 nF"], fontsize=8); ax.set_xlim(-0.9, 3.6)
    ax.set_ylabel("TC error, mains 3 V (degC)")
    ax.text(3.5, 2e-4, "squares: worst-case bound\ncircles: realistic", fontsize=8, ha="right", va="bottom", color=INK2)
    ax.set_title("Cost: grounded TC probe error\nbound rises above 0.5 degC", fontsize=8.5)
    fig.suptitle("The Y1 capacitor (P-D1) trade-off: fit it only if the LCR measurement says the barrier is too small",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold", y=0.985)
    save(fig, "y01_y1_tradeoff")


def chart_pdn():
    pc = curve("pdn_curves.json")
    p5 = C["pdn"]["5V"]; opts = p5["J10_cap_options"]
    rec, rej = REPORT_ONLY["j10_option_name"][0], REPORT_ONLY["j10_rejected_name"][0]
    fig, axs = plt.subplots(3, 1, figsize=(W, 8.6), gridspec_kw=dict(hspace=0.45, left=0.085, right=0.975, top=0.955, bottom=0.065))
    an0 = p5["J10 via field (RGB B.Cu return)"]["anti_resonances"][0]
    specs = [("3V3", 0.33, "+3V3 plane at the IC pins: above the 0.33 ohm target from about 46 MHz"),
             ("5V", 0.5, "+5V island: %.0f ohm quarter-wave resonance at %.1f MHz; %s at J10 removes it" % (an0[1], an0[0], rec)),
             ("1V2", 1.0, "+1V2 core node: below 1 ohm up to about 170 MHz")]
    pend = []
    for ax, (rail, tgt, ttl) in zip(axs, specs):
        labs = []
        if rail == "5V":
            for lab, col in (("U30 VIN", S5), ("L12/C127 pi input", S3), ("J10 via field (RGB B.Cu return)", AS)):
                d = pc["5V"][lab]
                ax.loglog(d["f_MHz"], d["Z_ohm"], color=col, lw=1.2)
                labs.append(("J10 via field, no capacitors" if lab.startswith("J10") else lab, col))
            for name, col, ls, txt in ((rej, INK2, (0, (3, 2)), "J10 + %s (rejected)" % rej), (rec, WITH, "-", "J10 + %s (recommended)" % rec)):
                z = p5[opts[name]["zkey"]]
                ax.loglog(z["f_MHz"], np.abs(np.array(z["re"]) + 1j * np.array(z["im"])), color=col, lw=1.7, ls=ls)
                for fpk, zpk in opts[name]["peaks_J10"]:
                    if zpk > 2:
                        ax.plot([fpk], [zpk], "o", color=col, ms=4)
                labs.append((txt, col))
            pk = [q for q in opts[rej]["peaks_J10"] if q[0] < 300][0]
            pend.append((ax, [(pk[0], pk[1], "right", "center", -6, 0), (pk[0], pk[1], "left", "bottom", 5, 4)], "%.1f ohm at %.1f MHz" % (pk[1], pk[0]), INK2))
            ax.axvline(an0[0], color=INK2, ls=":", lw=0.9)
            pend.append((ax, [(an0[0], 900, "right", "top", -4, 0)], "%.1f MHz (PCLK h15 499.5)" % an0[0], INK2))
        else:
            for i, (lab, d) in enumerate(pc[rail].items()):
                col = [AS, S5, S3][i % 3]
                ax.loglog(d["f_MHz"], d["Z_ohm"], color=col, lw=1.2)
                labs.append((lab, col))
        ax.axhline(tgt, color=LIM, ls="--", lw=1.1)
        pend.append((ax, [(0.11, tgt, "left", "bottom", 0, 3), (0.11, tgt, "left", "top", 0, -3), (2.0, tgt, "left", "bottom", 0, 3)], "target %g ohm" % tgt, LIM))
        ax.set_xlim(0.1, 1500); ax.set_ylim(1e-3, 1e3)
        ax.set_ylabel("|Z| (ohm)"); ax.set_title(ttl, fontsize=9.5)
        ax.set_xticks([0.1, 1, 10, 100, 1000]); ax.set_xticklabels(["0.1", "1", "10", "100", "1000"])
        for i, (lab, col) in enumerate(labs):
            pend.append((ax, [(0.13, 400 / (3.6 ** i), "left", "center"), (2.0, 400 / (3.6 ** i), "left", "center")], lab, col))
    axs[-1].set_xlabel("frequency (MHz)")
    pl = Placer(fig)
    for ax, c, s, col in pend:
        pl.place(ax, c, s, fontsize=8, color=col)
    save(fig, "p01_pdn")


def board_axes(ax, alpha_cu=1.0):
    """kicad-cli render of the board (copy of the project) in board mm, about 60 % strength"""
    from PIL import Image
    meta = curve("board_meta.json")
    def mask(l):
        return 1 - np.asarray(Image.open(os.path.join(CURVES, "board_%s.png" % l)).convert("L"), float) / 255
    m0 = mask("F_Cu")
    img = np.ones(m0.shape + (3,)) * np.array([0.975, 0.975, 0.965])
    for l, c, a in (("B_Cu", (0.74, 0.78, 0.84), 0.45), ("F_Cu", (0.62, 0.68, 0.76), 0.75 * alpha_cu), ("F_Fab", (0.38, 0.38, 0.38), 0.6),
                    ("F_Silkscreen", (0.18, 0.18, 0.18), 0.8), ("Edge_Cuts", (0.05, 0.05, 0.05), 1.0)):
        k = mask(l)[..., None] * a
        img = img * (1 - k) + np.array(c) * k
    x0, x1, y0, y1 = meta["extent_mm"]
    ax.imshow(img, extent=(x0, x1, y1, y0), interpolation="antialiased", zorder=0)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0)
    ax.set_aspect("equal"); ax.axis("off")
    return meta["footprints"]


def chart_layout_audit():
    L = C["layout"]; pdn = C["pdn"]
    fig, ax = plt.subplots(figsize=(W, 5.15), gridspec_kw=dict(left=0.0, right=1.0, top=0.93, bottom=0.0))
    fp = board_axes(ax)
    def callout(x, y, num, col=AS):
        badge(ax, x, y, str(num), col, r=2.8, key="%s-%.1f-%.1f" % (num, x, y))
    # 1 RGB vias over the +5V island
    vias = [v for k, vl in L["via_details_rgb_8080"].items() if k.startswith("RGB") for v in vl]
    ax.plot([v["x"] for v in vias], [v["y"] for v in vias], "x", color=AS, ms=5, mew=1.4, zorder=6)
    callout(128.5, 98.5, 1)
    # 2 +5V island outline
    bb = L["plane_areas"]["In2_5V_bbox"]
    ax.add_patch(mpatches.Rectangle((bb[0], bb[2]), bb[1] - bb[0], bb[3] - bb[2], fill=False, ec=S5, lw=1.4, ls=(0, (4, 2)), zorder=5))
    callout(bb[0] + 4, bb[2] + 4, 2, col=S5)
    # 3 J10 via-field resonance
    ax.plot([150.0], [108.0], marker="*", color=AS, ms=13, mec="white", zorder=7)
    callout(144.5, 104.0, 3)
    # 4 largest stitching gap
    st = L["stitching"]
    ax.add_patch(mpatches.Circle(tuple(st["at"]), st["max_dist_In1_copper_to_gnd_via_mm"], fill=False, ec=AS, lw=1.4, zorder=6))
    callout(st["at"][0] - 9.5, st["at"][1] - 6.5, 4)
    # 5 In1 keep-outs
    vo = L["in1_voids"]
    for v in vo["merged_groups(>=2 members)"] + vo["unexplained_voids_gt_0.3mm2"]:
        r = math.sqrt(v["area_mm2"] / math.pi)
        ax.add_patch(mpatches.Circle((v["x"], v["y"]), r, fc=S4, ec=S4, alpha=0.45, lw=1, zorder=5))
    callout(84.0, 104.0, 5, col="#B07800")
    # 6 hot loops
    for ref in ("U30", "U11", "Y10"):
        f = fp[ref]
        ax.add_patch(mpatches.Circle((f["x"], f["y"]), 3.2, fill=False, ec=S3, lw=1.6, zorder=6))
    callout(fp["Y10"]["x"] - 7, fp["Y10"]["y"] - 6, 6, col=S3); callout(fp["U11"]["x"] + 8, fp["U11"]["y"] + 3, 6, col=S3)
    callout(fp["U30"]["x"] + 7.5, fp["U30"]["y"] + 5, 6, col=S3)
    # 7 U6 without local decoupling
    u6 = fp["U6"]
    ax.add_patch(mpatches.Circle((u6["x"], u6["y"]), 3.0, fill=False, ec=AS, lw=1.6, zorder=6))
    callout(u6["x"] + 5, u6["y"] - 4.5, 7)
    hl = L["hot_loops"]
    d8 = [L["nets"]["8080:D%d" % i]["F_within1mm_plane_edge_mm"] for i in (5, 6, 7) if "8080:D%d" % i in L["nets"]]
    notes = [
        "1  RGB B2/B3/PCLK/HSYNC/VSYNC/DE: 2 vias each (x); their B.Cu parts use the In2 +5V island as reference, nearest +5V capacitor %.0f-%.0f mm away"
        % (min(v["decap_dist_mm"] for v in vias), max(v["decap_dist_mm"] for v in vias)),
        "2  In2 +5V island (dashed);  3  J10 via field: %.0f ohm quarter-wave resonance at %.1f MHz (PCLK h15 = 499.5 MHz)"
        % (pdn["5V"]["J10 via field (RGB B.Cu return)"]["anti_resonances"][0][1], pdn["5V"]["J10 via field (RGB B.Cu return)"]["anti_resonances"][0][0]),
        "4  largest In1 copper-to-GND-via distance %.1f mm (λ/20 at 1 GHz in FR4 = %.2f mm); median via spacing %.1f mm"
        % (st["max_dist_In1_copper_to_gnd_via_mm"], st["lambda_over_20_FR4_mm"], st["nn_spacing_mm"]["median"]),
        "5  In1 keep-outs under L30 and L11 (%.0f and %.0f mm2), BUCK_SW and BL_SW run over them;  6  hot loops: buck output %.1f mm2, boost %.1f mm2, crystal %.1f mm2"
        % (vo["merged_groups(>=2 members)"][0]["area_mm2"], vo["unexplained_voids_gt_0.3mm2"][0]["area_mm2"], hl["buck output loop L30-C333-U30GND"]["planar_area_mm2"],
           hl["boost switching loop U11SW-D111-C125-U11GND"]["planar_area_mm2"], hl["crystal loop Y10-C110-C111"]["planar_area_mm2"]),
        "7  U6 (ZCD Schmitt trigger) has no local decoupling capacitor (nearest 55.7 mm).  Not on the map: 8080 D5-D7 run %.0f-%.0f mm within 1 mm of the In1 edge."
        % (min(d8), max(d8)) if d8 else "7  U6 (ZCD Schmitt trigger) has no local decoupling capacitor (nearest 55.7 mm)",
    ]
    fig.text(0.006, 0.985, "Layout audit of the current board (top view, kicad-cli render): seven places that matter for EMC",
             fontsize=9.5, fontweight="bold", va="top")
    save(fig, "p02_layout_map")
    with open(os.path.join(CH, "p02_layout_notes.json"), "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=1)
    return notes


CHANGES = [  # id, short name, kind, footprint refs (marker positions) or explicit (x, y)
    ("1", "800 V triac driver instead of MOC3052 (P-S1)", "hardware", ["U5"]),
    ("2", "RV2 -> 1.5KE440CA TVS across the triac (P-S4)", "hardware", ["RV2"]),
    ("3", "RV3: second TVR14431 LINE_FUSED-N (P-S2b)", "hardware", [(87.0, 29.5)]),
    ("4", "1 nF C0G on the ZCD node (P-E1)", "hardware", ["U6"]),
    ("5", "Y1 1 nF SELV GND-N, only if the LCR says so (P-D1)", "measure", ["PS1"]),
    ("6", "panel frame bonded to PCB GND, ~19 contacts", "hardware", []),
    ("7", "150 ohm flat ferrite on the TFT FPC", "hardware", ["J10"]),
    ("8", "RN1-RN7 33 -> 150 ohm", "hardware", ["RN1", "RN2", "RN3", "RN4", "RN5", "RN6", "RN7"]),
    ("9", "%s X7R +5V-GND at the J10 via field" % REPORT_ONLY["j10_option_name"][0], "hardware", [(150.0, 108.0)]),
]


def chart_changes_map():
    fig, ax = plt.subplots(figsize=(W, 4.75), gridspec_kw=dict(left=0.0, right=1.0, top=0.93, bottom=0.0))
    fp = board_axes(ax)
    capname = REPORT_ONLY["j10_option_name"][0]
    spec = {  # id: (anchor parts, badge position, label)
        "1": (["U5"], (112.0, 78.0), "U5: 800 V driver"),
        "2": (["RV2"], (136.0, 31.0), "RV2 -> TVS"),
        "3": ([(87.0, 29.5)], (74.0, 39.0), "RV3 new, LINE_FUSED"),
        "4": (["U6"], (153.0, 72.0), "1 nF at U6"),
        "5": (["PS1"], (160.0, 43.0), "Y1 near PS1 (if needed)"),
        "7": (["J10"], (170.0, 101.0), "ferrite on TFT FPC"),
        "8": (["RN1", "RN2", "RN3", "RN4", "RN5", "RN6", "RN7"], (114.0, 90.0), "RN1-RN7"),
        "9": ([(150.0, 108.0)], (138.0, 105.0), "%s at J10" % capname),
        "6": ([], (36.0, 106.0), "frame contacts (blue squares, illustrative)"),
    }
    R = 3.0
    labels = []
    for cid, (refs, (bxp, byp), lab) in spec.items():
        col = VERD["MEASURE"][0] if cid == "5" else WITH
        for r in refs:
            x, y = (fp[r]["x"], fp[r]["y"]) if isinstance(r, str) else r
            ax.plot([x], [y], "s" if cid == "8" else "o", color=col, ms=4.5, mec="white", mew=0.6, zorder=7)
            leader(ax, x, y, bxp, byp, R, col)
        badge(ax, bxp, byp, cid, col, r=R)
        labels.append((bxp, byp, lab, col))
    x0, x1, y0, y1 = 22.5, 181.5, 22.5, 116.5
    per = 2 * ((x1 - x0) + (y1 - y0)); n = 19
    for i in range(n):
        s = per * i / n
        if s < x1 - x0: px, py = x0 + s, y0
        elif s < (x1 - x0) + (y1 - y0): px, py = x1, y0 + s - (x1 - x0)
        elif s < 2 * (x1 - x0) + (y1 - y0): px, py = x1 - (s - (x1 - x0) - (y1 - y0)), y1
        else: px, py = x0, y1 - (s - 2 * (x1 - x0) - (y1 - y0))
        ax.add_patch(mpatches.Rectangle((px - 1.1, py - 1.1), 2.2, 2.2, fc=WITH, ec="white", lw=0.6, zorder=7))
    pl = Placer(fig)
    for bxp, byp, lab, col in labels:
        d = R * 72 / 25.4 * (W * 25.4 / (ax.get_xlim()[1] - ax.get_xlim()[0])) / 25.4 * 25.4 / 72 * 72 / 25.4  # badge radius in pt
        rp = R / (ax.get_xlim()[1] - ax.get_xlim()[0]) * W * 72 + 3
        pl.place(ax, [(bxp, byp, "right", "center", -rp, 0), (bxp, byp, "left", "center", rp, 0), (bxp, byp, "center", "bottom", 0, rp),
                      (bxp, byp, "center", "top", 0, -rp)], lab, fontsize=8, color=col, fontweight="bold", zorder=9,
                 bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92))
    fig.text(0.006, 0.985, "Where the hardware changes go (top view): blue = proposed, purple = only if the LCR measurement says so",
             fontsize=9.5, fontweight="bold", va="top")
    save(fig, "w01_changes_map")


def chart_changes_matrix():
    tests = ["conducted\nemission", "harmonics", "flicker", "surge", "EFT", "ESD", "radiated\nemission", "RF\nimmunity"]
    # cell: (state, word)  states: fix, help, cost, zero, alt   (sources in the comment of each row)
    rows = [
        ("1", "800 V triac driver", {3: ("fix", "FIX*")}),                                  # B §1 proposals
        ("2", "TVS across the triac", {3: ("fix", "FIX*")}),                                # B §1
        ("3", "RV3 on LINE_FUSED", {0: ("zero", "-0.1 dB"), 3: ("fix", "K1 FIX")}),         # A §9, B §1
        ("4", "1 nF on ZCD node", {1: ("zero", "<= 11 us"), 4: ("fix", "FIX"), 7: ("help", "helps")}),   # A §9 P-E1, B §2, C §5
        ("5", "Y1 1 nF (if needed)", {0: ("cost", "cost"), 4: ("help", "helps"), 5: ("fix", "FIX"), 6: ("zero", "~0"), 7: ("cost", "cost")}),  # A §9, B §4, C §5
        ("6", "panel bonding, 19", {6: ("fix", "FIX**"), 7: ("fix", "FIX")}),               # C §3, §4
        ("7", "FPC ferrite", {6: ("fix", "FIX**")}),
        ("8", "RN1-RN7 150 ohm", {6: ("fix", "FIX**")}),
        ("9", "%s at J10" % REPORT_ONLY["j10_option_name"][0], {6: ("fix", "FIX**")}),
        ("F1", "fire at window centre", {0: ("fix", "FIX"), 1: ("fix", "FIX")}),           # A A0/A1/A4
        ("F2", "1500-cycle frame", {2: ("fix", "FIX")}),                                    # A A5
        ("E2", "ZCD edge check 50 us", {4: ("help", "helps")}),                             # B §2 P-E2
        ("U1", "no 1-pixel stripes in UI", {6: ("help", "needed")}),                        # C §3
        ("M1", "insulated / guarded probe", {5: ("alt", "alt. to 5"), 7: ("help", "helps")}),  # B §4, C §5
        ("M2", "oven C_hc / C_ch limits", {0: ("help", "helps")}),                          # A §9 grid
    ]
    st = {"fix": (WITH, "white"), "help": ("#BBD7EE", INK), "cost": (AS, "white"), "zero": ("#E9E9E9", INK), "alt": ("#DCD9F2", INK)}
    fig, ax = plt.subplots(figsize=(W, 4.6), gridspec_kw=dict(left=0.005, right=0.995, top=0.9, bottom=0.12))
    nr, nc = len(rows), len(tests)
    ax.set_xlim(-3.15, nc); ax.set_ylim(nr, -1.1); ax.axis("off")
    for j, t in enumerate(tests):
        ax.text(j + 0.5, -0.55, t, ha="center", va="center", fontsize=8, fontweight="bold")
    for i, (cid, name, cells) in enumerate(rows):
        y = i + 0.5
        sep = cid.startswith("F") or cid.startswith("E") or cid.startswith("U") or cid.startswith("M")
        cc = mpatches.Circle((-2.95, y), 0.3, fc=VERD["MEASURE"][0] if cid == "5" else (WITH if not sep else INK2), ec="none"); cc.set_gid("badge-m%s" % cid)
        ax.add_patch(cc)
        ax.text(-2.95, y, cid, ha="center", va="center", fontsize=8, color="white", fontweight="bold").set_gid("badge-m%s" % cid)
        ax.text(-2.55, y, name, ha="left", va="center", fontsize=8)
        for j in range(nc):
            ax.add_patch(mpatches.Rectangle((j + 0.04, i + 0.06), 0.92, 0.88, fc="#FAFAFA", ec="#E4E4E4", lw=0.6))
            if j in cells:
                s, w_ = cells[j]
                fc, tc = st[s]
                ax.add_patch(mpatches.Rectangle((j + 0.04, i + 0.06), 0.92, 0.88, fc=fc, ec="white", lw=0.6))
                ax.text(j + 0.5, y, w_, ha="center", va="center", fontsize=8, color=tc, fontweight="bold" if s in ("fix", "cost") else "normal")
    ax.plot([-3.15, nc], [9, 9], color=INK2, lw=0.8)
    ax.text(-3.15, 9.0, "", fontsize=8)
    fig.text(0.006, 0.975, "Change x test: what each change fixes, helps or costs (blank = no effect expected or not simulated)",
             fontsize=9.5, fontweight="bold", va="top")
    fig.text(0.006, 0.075, "Rows 1-9 = hardware (numbers as on the board map); F = firmware; E2 = firmware edge check; U1 = user-interface rule; M = mechanical.",
             fontsize=8, va="center", color=INK2)
    fig.text(0.006, 0.035, "* 1 and 2 together (the driver alone stays MARGINAL).  ** 6-9 together pass PCLK with >= 6 dB; any subset falls short.",
             fontsize=8, va="center", color=INK2)
    save(fig, "w02_changes_matrix")


def chart_measure_first():
    eb = B["esd_barrier_vs_Cbar"]["crossing_Cbar_pF"]; off = REPORT_ONLY["cbar_offset_pF"][0]
    fp = C["emission"]["proposals"]["frame_floating"]; e = C["emission"]
    hb = ACON["M3_heater_off_HLK_bound"]
    fig, axs = plt.subplots(3, 1, figsize=(W, 7.0), gridspec_kw=dict(hspace=0.9, left=0.05, right=0.975, top=0.9, bottom=0.08))
    # 1 LCR
    ax = axs[0]
    for k, (yy, lab) in enumerate(((2, "SELV to plane 10 pF"), (1, "30 pF"), (0, "100 pF"))):
        cen = ["Cenv 10 pF", "Cenv 30 pF", "Cenv 100 pF"][k]
        a = eb[cen + " | relay coil-contact 1500 Vac = 2121 Vpk"] - off; b = eb[cen + " | relay coil-contact 1500 Vac = 2121 Vpk | for PASS (>= 20 % margin)"] - off
        ax.barh(yy, a, left=0, color=VERD["FAIL"][1], height=0.7, edgecolor="white")
        ax.barh(yy, b - a, left=a, color=VERD["MARGINAL"][1], height=0.7, edgecolor="white")
        ax.barh(yy, 300 - b, left=b, color=VERD["PASS"][1], height=0.7, edgecolor="white")
        ax.text(max(a, 0) / 2 if a > 30 else 2, yy, "FAIL", ha="center" if a > 30 else "left", va="center", fontsize=8, color=VERD["FAIL"][0], fontweight="bold")
        ax.text((a + b) / 2, yy, "MARGINAL", ha="center", va="center", fontsize=8, color=VERD["MARGINAL"][0], fontweight="bold")
        ax.text(b + 6, yy, "PASS from %.0f pF" % b, ha="left", va="center", fontsize=8, color=VERD["PASS"][0], fontweight="bold")
        ax.text(302, yy, lab, ha="left", va="center", fontsize=8)
    ax.set_xlim(0, 360); ax.set_ylim(-0.5, 2.5); ax.set_yticks([])
    ax.set_xticks([0, 50, 100, 150, 200, 250, 300])
    ax.set_xlabel("LCR-meter reading, HLK-10M05 +Vout to the AC pins (pF)")
    ax.set_title("1. LCR meter on the HLK-10M05 (unpowered): decides the ESD verdict and whether Y1 (change 5) is needed", fontsize=9)
    ax.grid(False)
    # 2 continuity
    ax = axs[1]
    ax.set_xlim(0, 100); ax.set_ylim(0, 10); ax.axis("off")
    ax.set_title("2. Ohmmeter: panel metal frame to FPC ground (pins 3, 29, 36): decides which radiated model applies", fontsize=9, loc="left")
    for x, ttl, vals, col in ((1, "frame connected (as modelled)", (e["worst_rows"]["PCLK"]["margin_nom"], e["worst_rows"]["typical UI"]["margin_nom"]), AS),
                              (51, "frame floating", (fp["PCLK"]["nominal"]["margin_nom"], fp["typical UI"]["nominal"]["margin_nom"]), S5)):
        ax.add_patch(mpatches.FancyBboxPatch((x, 0.8), 47, 7.6, boxstyle="round,pad=0.3", fc=VERD["FAIL"][1], ec=VERD["FAIL"][0], lw=0.8))
        ax.text(x + 1.5, 6.6, ttl, fontsize=8.5, fontweight="bold", va="center")
        ax.text(x + 1.5, 3.9, "radiated margin: PCLK %+.1f dB, typical UI %+.1f dB" % vals, fontsize=8, va="center")
        ax.text(x + 1.5, 1.9, "FAIL either way; changes 6-9 are needed in both cases", fontsize=8, va="center", color=VERD["FAIL"][0])
    # 3 conducted heater off
    ax = axs[2]
    need = REPORT_ONLY["hlk_needs_own_margin_dB"][0]
    ax.barh(0, need, color=VERD["FAIL"][1], height=0.7, edgecolor="white")
    ax.barh(0, 20 - need, left=need, color=VERD["PASS"][1], height=0.7, edgecolor="white")
    ax.text(need / 2, 0, "needs HLK filtering", ha="center", va="center", fontsize=8, color=VERD["FAIL"][0], fontweight="bold")
    ax.text(need + 0.4, 0, "PASS: the HLK has its own >= %.1f dB" % need, ha="left", va="center", fontsize=8, color=VERD["PASS"][0], fontweight="bold")
    ax.set_xlim(0, 20); ax.set_ylim(-0.6, 0.6); ax.set_yticks([])
    ax.set_xlabel("measured QP margin with the heater off, 1.2-15 MHz (dB), LISN pre-scan")
    ax.set_title("3. Conducted emission with the heater off: the board removes up to %.1f dB less than the HLK reference circuit" % -hb["DM_IL_extra_dB"]["min"], fontsize=9)
    ax.grid(False)
    fig.text(0.006, 0.975, "What to measure first: three cheap bench checks that settle the open verdicts", fontsize=9.5, fontweight="bold", va="top")
    save(fig, "w03_measure_first")


COVERAGE = {  # test -> states per column; source: the three report_section.md files (sections named in the caption of the page)
    "cols": ["board model", "limits / levels", "test method,\ngenerator", "HLK-10M05\ninside", "touch panel\n(GT911)", "ESP32\nmodule"],
    "rows": [
        ("Conducted emission", ["SIM", "READ", "PUBLIC", "BOUND", "-", "NO"]),
        ("Clicks (discontinuous)", ["SIM", "READ", "READ", "-", "-", "-"]),
        ("Harmonics", ["SIM", "READ", "PUBLIC", "BOUND", "-", "-"]),
        ("Flicker", ["SIM", "PUBLIC", "PUBLIC", "BOUND", "-", "-"]),
        ("Radiated emission", ["SIM", "READ", "PUBLIC", "-", "NO", "NO"]),
        ("Surge", ["SIM", "READ", "PUBLIC", "BOUND", "-", "-"]),
        ("EFT / burst", ["SIM", "READ", "PUBLIC", "BOUND", "NO", "NO"]),
        ("Voltage dips", ["SIM", "READ", "PUBLIC", "BOUND", "-", "-"]),
        ("ESD", ["SIM", "READ", "PUBLIC", "BOUND", "NO", "-"]),
        ("Injected RF", ["SIM", "READ", "PUBLIC", "BOUND", "NO", "-"]),
        ("Radiated RF field", ["SIM", "READ", "PUBLIC", "-", "NO", "NO"]),
        ("Radio (RED: EN 300 328, EN 301 489)", ["NO", "NO", "NO", "-", "-", "NO"]),
    ],
}


def chart_coverage():
    cs = {"SIM": ("simulated", WITH, "white"), "READ": ("read from your standard", "#BBD7EE", INK), "PUBLIC": ("public source, standard not on disk", VERD["MEASURE"][1], INK),
          "BOUND": ("black box: bound only", VERD["MARGINAL"][1], INK), "NO": ("not covered", VERD["NOT SIMULABLE"][1], INK), "-": ("not relevant", "white", INK2)}
    rows = COVERAGE["rows"]; cols = COVERAGE["cols"]
    fig, ax = plt.subplots(figsize=(W, 7.2), gridspec_kw=dict(left=0.005, right=0.995, top=0.83, bottom=0.11))
    nr, nc = len(rows), len(cols)
    ax.set_xlim(-2.7, nc); ax.set_ylim(nr, -1.1); ax.axis("off")
    for j, c in enumerate(cols):
        ax.text(j + 0.5, -0.55, c, ha="center", va="center", fontsize=8, fontweight="bold")
    for i, (t, sts) in enumerate(rows):
        ax.text(-2.65, i + 0.5, t, ha="left", va="center", fontsize=8)
        for j, s in enumerate(sts):
            lab, fc, tc = cs[s]
            ax.add_patch(mpatches.Rectangle((j + 0.04, i + 0.06), 0.92, 0.88, fc=fc, ec="#D0D0D0", lw=0.6))
            word = {"SIM": "simulated", "READ": "read", "PUBLIC": "public", "BOUND": "bound", "NO": "not covered", "-": ""}[s]
            ax.text(j + 0.5, i + 0.5, word, ha="center", va="center", fontsize=8, color=tc)
    fig.text(0.006, 0.975, "What the simulation covers, and what it could not", fontsize=9.5, fontweight="bold", va="top")
    fig.text(0.006, 0.93, "Public sources where the standard is not on disk: CISPR 16-1-1 and 16-1-2 (Schwarzbeck notes); IEC 61000-4-2, 4-4, 4-5, 4-11",
             fontsize=8, color=INK2, va="top")
    hd = [mpatches.Patch(fc=cs[k][1], ec="#BBBBBB", label=cs[k][0]) for k in ("SIM", "READ", "PUBLIC", "BOUND", "NO")]
    fig.legend(handles=hd, loc="lower left", ncol=5, fontsize=8, bbox_to_anchor=(0.0, 0.0), handlelength=1.4, columnspacing=1.0)
    fig.text(0.006, 0.9, "(IS 14700-4-x, TI SLVA711); IEC 61000-4-7 (IS 14700-4-7); IEC 61000-4-15 and the IEC 61000-3-3 limits (Keysight 5964-1917E);",
             fontsize=8, color=INK2, va="top")
    fig.text(0.006, 0.87, "IEC 61000-4-3 and 4-6 (public descriptions). Radio rules under RED are in no scope.", fontsize=8, color=INK2, va="top")
    save(fig, "w04_coverage")


def chart_rf_zcd():
    z = C["injected"]["ZCD"]; ln = C["injected"]["logic_nets"]; thr = REPORT_ONLY["zcd_toggle_threshold_V"][0]
    items = [("as designed, opto Cio 0.5 pF", z["Cio 0.5 pF"]["max_Vpk_at_U6_in"], AS),
             ("as designed, opto Cio 1.0 pF", z["Cio 1.0 pF"]["max_Vpk_at_U6_in"], AS),
             ("with 1 nF (P-E1), Cio 0.5 pF", z["Cio 0.5 pF + 1 nF C0G (scope B)"]["max_Vpk_at_U6_in"], WITH),
             ("with 1 nF (P-E1), Cio 1.0 pF", z["Cio 1.0 pF + 1 nF C0G (scope B)"]["max_Vpk_at_U6_in"], WITH),
             ("Y1 1 nF, no ZCD capacitor", z["Y1 1 nF, no ZCD cap (Cio 1 pF)"]["max_Vpk_at_U6_in"], S5),
             ("Y1 1 nF + ZCD 1 nF", z["Y1 1 nF + 1 nF C0G (Cio 1 pF)"]["max_Vpk_at_U6_in"], S5)]
    fig, ax = plt.subplots(figsize=(W, 3.4), gridspec_kw=dict(left=0.3, right=0.985, top=0.86, bottom=0.18))
    ys = np.arange(len(items))[::-1]
    for y, (lab, v, col) in zip(ys, items):
        ax.barh(y, v, color=col, height=0.55)
        ax.text(v * 1.25, y, "%.2g V" % v, va="center", fontsize=8)
    ax.axvline(thr, color=LIM, ls="--", lw=1.1); ax.text(thr / 1.08, len(items) - 0.5, "about 1 V needed to toggle U6 (assumed)", fontsize=8, ha="right", va="bottom")
    ax.set_xscale("log"); ax.set_xlim(1e-4, 3); ax.set_ylim(-0.6, len(items) - 0.05)
    ax.set_yticks(ys); ax.set_yticklabels([i[0] for i in items], fontsize=8); ax.tick_params(axis="y", length=0)
    ax.set_xlabel("peak RF voltage at the U6 input, mains 3 V injection 0.15-80 MHz (V)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Injected RF on the ZCD node: 14 dB margin today, about 55 dB with the 1 nF", fontsize=9.5)
    save(fig, "f02_rf_zcd")


def chart_hot_loops():
    hl = C["layout"]["hot_loops"]
    names = {"buck input loop C330-U30(VIN,GND)": "buck input, C330", "buck input loop C331-U30(VIN,GND)": "buck input, C331",
             "buck output loop L30-C333-U30GND": "buck output, L30-C333", "boost switching loop U11SW-D111-C125-U11GND": "boost switching, D111-C125",
             "boost input loop C124-L11-U11": "boost input, C124-L11", "crystal loop Y10-C110-C111": "crystal, Y10-C110-C111"}
    keys = list(names)
    fig, ax = plt.subplots(figsize=(W, 2.7), gridspec_kw=dict(left=0.27, right=0.985, top=0.86, bottom=0.18))
    ys = np.arange(len(keys))[::-1]
    pa = [hl[k]["planar_area_mm2"] for k in keys]; va = [hl[k]["vertical_area_if_return_in_In1_mm2"] for k in keys]
    ax.barh(ys + 0.18, pa, height=0.34, color=AS)
    ax.barh(ys - 0.18, va, height=0.34, color=INK2)
    for y, a, b in zip(ys, pa, va):
        ax.text(max(a, b) + 0.35, y, "%.2f / %.2f" % (a, b), va="center", fontsize=8)
    ax.set_yticks(ys); ax.set_yticklabels([names[k] for k in keys], fontsize=8); ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 15.5); ax.set_xlabel("loop area (mm2): orange = in the copper layer / grey = vertical, return in In1")
    ax.grid(axis="y", visible=False)
    ax.set_title("Hot loops of the converters and the crystal (layout audit)", fontsize=9.5)
    save(fig, "p03_hot_loops")


def ce_final():
    """A's final conducted model (A1_crosscheck_scopeB, baseline rows): worst line per statistic"""
    mc = A["A1_crosscheck_scopeB"]["monte_carlo"]
    out = {}
    for key, lab in (("V_on 10-40 V (as designed)", "as designed"), ("V_on 8-18 V (F1)", "F1")):
        b = mc[key]["baseline"]
        for det in ("QP", "AV"):
            ln = min(("L", "N"), key=lambda l: b["%s_%s" % (det, l)]["min"])
            out[(lab, det)] = dict(b["%s_%s" % (det, ln)], line=ln)
    out["n"] = mc["n"]
    return out


def combo(content, base="bond_perimeter_ferrite + RN 150"):
    """emission proposal row with the recommended J10 capacitors; falls back to the 2 x 1 nF run where C computed only PCLK"""
    P = C["emission"]["proposals"]
    k = "%s + J10 caps %s" % (base, REPORT_ONLY["j10_option_key"][0])
    if k in P and content in P[k]:
        return P[k][content], False
    return P["%s + 2x1nF" % base][content], True


def pdn_summary():
    """numbers for the caption and the change list, from C results.json"""
    p5 = C["pdn"]["5V"]; opts = p5["J10_cap_options"]
    rec, rej = REPORT_ONLY["j10_option_name"][0], REPORT_ONLY["j10_rejected_name"][0]
    pk = [q for q in opts[rej]["peaks_J10"] if q[0] < 300][0]
    und = [q[1] for n, o in opts.items() if isinstance(o, dict) and n != "none" and "ohm" not in n for q in o["peaks_J10"] if 700 < q[0] < 900]
    return {"rej_peak": pk, "rec_498": opts[rec]["Z_J10_at_MHz(caps 2.5 mm away)"]["498.5"], "none_498": opts["none"]["peaks_J10"][0][1],
            "rec_max_1_300": opts[rec]["max_Z_J10_1-300MHz"], "m824": (min(und), max(und))}


def badge(ax, x, y, num, col, r=3.0, fs=8, key=None):
    g = "badge-%s-%s" % (key or num, id(ax))
    c = mpatches.Circle((x, y), r, fc=col, ec="white", lw=1.0, zorder=8); c.set_gid(g); ax.add_patch(c)
    t = ax.text(x, y, num, ha="center", va="center", fontsize=fs, color="white", fontweight="bold", zorder=9); t.set_gid(g)
    return c


def leader(ax, x0, y0, x1, y1, r, col):
    """line from a part (x0, y0) to the edge of a badge of radius r at (x1, y1)"""
    L = math.hypot(x1 - x0, y1 - y0)
    if L <= r:
        return
    ax.plot([x0, x1 - (x1 - x0) * r / L], [y0, y1 - (y1 - y0) * r / L], color=col, lw=1.1, zorder=7)


ALL = {}
for _n, _f in list(globals().items()):
    if _n.startswith("chart_"):
        ALL[_n[6:]] = _f

if __name__ == "__main__":
    names = sys.argv[1:] or list(ALL)
    for n in names:
        ALL[n]()
    import common_style
    print("TEXT-vs-GRAPHICS OVERLAPS: %d" % len(common_style.OVERLAPS))
