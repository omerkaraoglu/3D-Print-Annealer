"""C_rf step 4 - SPICE (ngspice 46, KiCad 10 dll) of every fast chain with its ROUTED lengths -> current spectra.

RGB/sync chain (per line, lengths from results.json["layout"] = c2 extraction):
  SSD1963 LCD output  (Rout, tr: NOT given in the SSD1963 datasheet Rev 1.1 - Table 12-1 PDF p.80 lists only VOH >= 0.8 VDDIO /
                       VOL <= 0.2 VDDIO, Table 13 timing uses CL = 0 pF for the LCD interface -> ASSUMED Rout 30 ohm (swept 20..50),
                       tr = tf = 1.5 ns (swept 1.0..2.5 ns))
  -> trace U10..RN (the <net>_T net, F.Cu over In1, 4 sections) -> 33 ohm array RN1..RN7 (Royalohm 4D02WGJ0330TCE, 0402x4:
     ESL 0.4 nH assumed) -> trace RN..J10 (4 sections, incl. the via / B.Cu stub where present) -> J10 + via 1.5 nH (assumed)
  -> FPC tail 67.65 mm (spec 12.9) + 20 mm panel-internal routing (assumed), 4 sections -> panel input 5 pF (assumed 3..10)
  Board trace Z0: isolated microstrip 57.3 ohm / eeff 3.22 (Hammerstad, c3); all lines in phase: parallel-plate per-line
  72 ohm / er 4.4. FPC per-line mode from c3: all 24 data in phase L' = 4.14 nH/mm, alone (PCLK) 0.67 nH/mm, eeff 1.6
  (polyimide, assumed) -> Z0 = L'*v.
Patterns (SSD1963 -> panel, PCLK 33.30 MHz from the firmware, Display_SSD1963.h: PLL 100 MHz, FPR 0x0553F7):
  worst  : 1-pixel vertical stripes -> every data bit toggles every pixel, 24 lines in phase, square wave PCLK/2
  typical: UI content -> modelled in c6 statistically (toggle probability per pixel), uses the single-line transfer computed here
8080 bus (ESP32 -> 33 ohm at the ESP32 -> trace -> SSD1963 input 5 pF): WR strobe 15 MHz continuous during a full-screen
  redraw (spec 5: 10-20 MHz), data worst toggle at WR/2; ESP32 GPIO Rout 30 ohm / tr 2 ns (ASSUMED; ESP32 datasheet not in the
  project's Datasheets folder).
Validation: (1) PULSE into 100 ohm vs the analytic trapezoid Fourier series; (2) matched-line delay/amplitude.
Outputs: results.json["spice_chain"], plots/spice_*.png
"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *
from c3_inductance2d import hammerstad

import subprocess, tempfile, itertools
from concurrent.futures import ThreadPoolExecutor
_cnt = itertools.count()


class _NG:
    """every netlist runs in a fresh python process (spice_worker.py); vector names as in ngspice_helper"""
    @staticmethod
    def run_netlist(net):
        k = next(_cnt)
        d = tempfile.mkdtemp(dir=WORK)
        cir, npz = os.path.join(d, "n.cir"), os.path.join(d, "o.npz")
        open(cir, "w", encoding="utf-8").write(net)
        for attempt, (old, new) in enumerate(((None, None), (" 0 20p", " 0 20p uic"), (" 20p ", " 13p "))):
            if old:                                  # ngspice occasionally stalls on the ideal-L / T-line mix: retry variants
                net2 = net.replace(old, new) if old in net else net + ""
                if attempt == 2:
                    net2 = net.replace(".tran 20p", ".tran 13p").replace(" 0 20p", " 0 13p")
                open(cir, "w", encoding="utf-8").write(net2)
            try:
                subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "spice_worker.py"), cir, npz], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
                break
            except subprocess.TimeoutExpired:
                continue
        z = np.load(npz)
        v = {}
        for key in z.files:
            a = z[key]
            v[key] = a
            if key.endswith("_branch"):
                v[key[:-7] + "#branch"] = a
            if key.startswith("v_") and key.endswith("_"):
                v["v(" + key[2:-1] + ")"] = a
        return v


ng = _NG()
POOL = ThreadPoolExecutor(max_workers=6)
LAY = load_results()["layout"]["nets"]
I2D = load_results()["inductance2d"]
PCLK = 33.30e6
NPER_RUN, STEP = 12, "20p"        # 12 periods, 20 ps step (checked against 40 periods / 10 ps below)
VDD = 3.3
Z_ISO, EEFF_ISO = hammerstad(0.25, 0.2, 4.4, 0.035)
Z_EVEN, ER_PP = 72.0, 4.4
PS_MM = lambda eeff: math.sqrt(eeff) / C0 * 1e-3 * 1e12          # ps per mm
L_FPC_EVEN = I2D["fpc_tft"]["all 24 data in phase, returns GND 3/29/36 + VDD 4"]["loop_L_nH_per_mm_per_line"] * 1e-6
L_FPC_ISO = I2D["fpc_tft"]["PCLK (pin 30) alone, returns GND + VDD"]["loop_L_nH_per_mm_per_line"] * 1e-6
EEFF_FPC = 1.6
V_FPC = C0 / math.sqrt(EEFF_FPC)
FPC_LEN = 67.65 + 20.0


def ladder(tag, n1, n2, Z, td, ncell=3):
    """lossless line as an LC ladder (ngspice's ideal T element stalls with ps delays next to small C/L);
    cell delay td/ncell -> cut-off ncell/(pi*td) > 6 GHz for every section here. Half-C at both ends (pi cells)."""
    L = Z * td / ncell
    C = td / (ncell * Z)
    out, a = [], n1
    out.append(f"C{tag}s {n1} 0 {C / 2}")
    for k in range(ncell):
        b = n2 if k == ncell - 1 else f"{tag}m{k}"
        out.append(f"L{tag}_{k} {a} {b} {L}")
        out.append(f"C{tag}_{k} {b} 0 {C if k < ncell - 1 else C / 2}")
        a = b
    return out


def chain_netlist(L1, L2, period, duty, tr, Rout, Zb, ps_mm, Zf, Cin, Rs=33.0, nsec=4, tstop=None):
    tstop = tstop or NPER_RUN * period
    pw = duty * period - tr
    s = ["chain", f"V1 drv 0 PULSE(0 {VDD} 1n {tr} {tr} {pw} {period})", f"Rout drv n0 {Rout}"]
    # segment 1 (U10 -> RN), probes = 0V sources between sections
    nodes = []
    k = 0
    def line(prefix, length_mm, Z, td_per_mm, start):
        nonlocal k
        cur = start
        for i in range(nsec):
            nxt = f"{prefix}{i+1}"
            s.append(f"Vp{prefix}{i} {cur} {cur}x 0")
            s.extend(ladder(f"{prefix}{i}", f"{cur}x", nxt, Z, length_mm / nsec * td_per_mm * 1e-12))
            cur = nxt
        s.append(f"Vp{prefix}{nsec} {cur} {cur}e 0")
        return cur + "e"
    e1 = line("a", L1, Zb, ps_mm, "n0")
    s.append(f"Rrn {e1} rn1 {Rs}")
    s.append(f"Lrn rn1 rn2 0.4n")
    e2 = line("b", L2, Zb, ps_mm, "rn2")
    s.append(f"Lcon {e2} j10 1.5n")
    e3 = line("c", FPC_LEN, Zf, 1e12 / V_FPC * 1e-3, "j10")
    s.append(f"Cin {e3} 0 {Cin}p")
    s.append(f"Rin {e3} 0 250k")
    s.append(f".tran {STEP} {tstop} 0 {STEP}")
    s.append(".end")
    return "\n".join(s) + "\n"


def harmonics(t, y, period, nharm, nper=4):
    """Exact harmonic phasors (peak) from the last nper periods (steady state), rectangular window."""
    T = nper * period
    m = t >= t[-1] - T
    tu = np.linspace(t[-1] - T, t[-1], 4096 * nper, endpoint=False)
    yu = np.interp(tu, t[m], y[m])
    Y = np.fft.rfft(yu) / len(yu) * 2
    return Y[nper * np.arange(1, nharm + 1)]


def run_chain(L1, L2, period, duty, tr, Rout, Zb, ps_mm, Zf, Cin, nharm):
    v = ng.run_netlist(chain_netlist(L1, L2, period, duty, tr, Rout, Zb, ps_mm, Zf, Cin))
    t = np.real(v["time"])
    res = {}
    for pre, L in (("a", L1), ("b", L2), ("c", FPC_LEN)):
        ph = [harmonics(t, np.real(v[f"vp{pre}{i}#branch"]), period, nharm) for i in range(5)]
        ph = np.array(ph)                            # (5 probes, nharm)
        # current moment of the segment: trapezoid integral of the complex current along the length (A*m)
        mom = np.trapezoid(ph, dx=L / 4 * 1e-3, axis=0)
        res[pre] = {"I_start": ph[0], "I_end": ph[-1], "moment_Am": mom, "I_avg": mom / (L * 1e-3)}
    res["v_in"] = harmonics(t, np.real(v["v(ce)"]) if "v(ce)" in v else np.real(v["v(c4e)"]), period, nharm)
    res["t"] = t; res["v_end"] = np.real(v["v(c4e)"]); res["i_drv"] = np.real(v["vpa0#branch"])
    res["V_oc"] = harmonics(t, np.real(v["v(drv)"]), period, nharm)        # open-circuit driver harmonic phasors (same time origin)
    return res


out = {"assumptions": {"SSD1963_Rout_ohm": "30 (20..50) assumed - not in the SSD1963 datasheet", "SSD1963_tr_ns": "1.5 (1.0..2.5) assumed",
                       "RN_ESL_nH": 0.4, "J10_plus_via_nH": 1.5, "FPC_length_mm": FPC_LEN, "FPC_eeff": EEFF_FPC, "panel_Cin_pF": "5 (3..10) assumed",
                       "Z_board_isolated_ohm": Z_ISO, "eeff_board": EEFF_ISO, "Z_board_in_phase_ohm": Z_EVEN,
                       "Z_fpc_in_phase_ohm": L_FPC_EVEN * V_FPC, "Z_fpc_isolated_ohm": L_FPC_ISO * V_FPC,
                       "ESP32_Rout_ohm": "30 assumed", "ESP32_tr_ns": "2.0 assumed", "f_WR_MHz": "15 (10..20) assumed from spec 5"}}

# ---------------- validation 1: trapezoid into 100 ohm -------------------------------------------------------------
per, tr = 60e-9, 1.5e-9
net = f"val\nV1 a 0 PULSE(0 1 1n {tr} {tr} {per/2 - tr} {per})\nR1 a 0 100\n.tran 10p {30*per} 0 10p\n.end\n"
v = ng.run_netlist(net)
t = np.real(v["time"]); y = np.real(v["v(a)"]) / 100
H = harmonics(t, y, per, 15)
n = np.arange(1, 16)
d = 0.5
ana = 2 * 0.01 * d * np.abs(np.sinc(n * d) * np.sinc(n * tr / per))          # Ott eq: 2 A d sinc(pi n d) sinc(pi n tr/T)
val = [{"n": int(k), "spice_mA": float(abs(H[k - 1]) * 1e3), "analytic_mA": float(ana[k - 1] * 1e3)} for k in (1, 3, 5, 7, 9, 11, 13, 15)]
out["validation_trapezoid"] = rnd(val, 4)
out["validation_trapezoid_max_err_dB"] = float(max(abs(20 * math.log10(r["spice_mA"] / r["analytic_mA"])) for r in val))

# ---------------- numerical check: 12 periods / 20 ps vs 40 periods / 10 ps on B7 (in-phase mode) ----------------------
_G = json.load(open(GEOM)); _LEN = {}
for _t in _G["tracks"]:
    _LEN[_t["net"]] = _LEN.get(_t["net"], 0.0) + _t["len"]
_a, _b = _LEN["/Display/B7_T"], _LEN["/Display/B7"]
_r1 = run_chain(_a, _b, 2 / PCLK, 0.5, 1.5e-9, 30, Z_EVEN, PS_MM(ER_PP), L_FPC_EVEN * V_FPC, 5, 61)
NPER_RUN, STEP = 40, "10p"
_r2 = run_chain(_a, _b, 2 / PCLK, 0.5, 1.5e-9, 30, Z_EVEN, PS_MM(ER_PP), L_FPC_EVEN * V_FPC, 5, 61)
NPER_RUN, STEP = 12, "20p"
_odd = np.arange(0, 61, 2)
out["numerical_check_fpc_moment_max_dev_dB_odd_harmonics"] = float(np.max(np.abs(dB(_r1["c"]["moment_Am"][_odd]) - dB(_r2["c"]["moment_Am"][_odd]))))

# ---------------- RGB: every data line, worst pattern (in phase, PCLK/2 square) ---------------------------------------
NH = 61                                    # harmonics of 16.65 MHz up to ~1015 MHz
per_d = 2 / PCLK
f_d = np.arange(1, NH + 1) / per_d
data_names = [c + str(i) for c in "RGB" for i in range(8)]


def lens(nm):
    a = LAY["RGB:" + nm]
    L = a["len_mm"]
    # split total into U10->RN (the _T net) and RN->J10 from the layout section of results.json
    return L


# per-net split from the raw layout export (lengths of <net>_T and <net>)
G = json.load(open(GEOM))
LEN = {}
for tr_ in G["tracks"]:
    LEN[tr_["net"]] = LEN.get(tr_["net"], 0.0) + tr_["len"]


def L12(nm):
    return LEN["/Display/%s_T" % nm], LEN["/Display/%s" % nm]


def sweep_case(Rout, trr, Cin, label):
    tot = {"a": 0, "b": 0, "c": 0, "Ic_start": 0, "V_oc": 0}
    per_line = {}
    futs = {nm: POOL.submit(run_chain, *L12(nm), per_d, 0.5, trr, Rout, Z_EVEN, PS_MM(ER_PP), L_FPC_EVEN * V_FPC, Cin, NH) for nm in data_names}
    for nm in data_names:
        r = futs[nm].result()
        for k in ("a", "b", "c"):
            tot[k] = tot[k] + r[k]["moment_Am"]
        tot["Ic_start"] = tot["Ic_start"] + r["c"]["I_start"]
        tot["V_oc"] = r["V_oc"]
        per_line[nm] = r
    return tot, per_line


cases = {}
nominal, per_line = sweep_case(30, 1.5e-9, 5, "nominal")
cases["nominal Rout30 tr1.5 Cin5"] = nominal
for (R, trr, C, lab) in ((20, 1.0e-9, 10, "fast Rout20 tr1.0 Cin10"), (50, 2.5e-9, 3, "slow Rout50 tr2.5 Cin3")):
    cases[lab], _ = sweep_case(R, trr, C, lab)

# single data line (isolated mode, for typical content) and PCLK (always toggling, 33.3 MHz square)
L1, L2 = L12("G3")
single = run_chain(L1, L2, per_d, 0.5, 1.5e-9, 30, Z_ISO, PS_MM(EEFF_ISO), L_FPC_ISO * V_FPC, 5, NH)
L1, L2 = L12("PCLK")
NHc = 30
pclk = run_chain(L1, L2, 1 / PCLK, 0.5, 1.5e-9, 30, Z_ISO, PS_MM(EEFF_ISO), L_FPC_ISO * V_FPC, 5, NHc)
f_c = np.arange(1, NHc + 1) * PCLK
pclk_fast = run_chain(L1, L2, 1 / PCLK, 0.5, 1.0e-9, 20, Z_ISO, PS_MM(EEFF_ISO), L_FPC_ISO * V_FPC, 10, NHc)
# PCLK duty is not exactly 50 %: SSD1963 LSHIFT from the fractional divider - a 48 % duty puts even harmonics in (sensitivity)
pclk_48 = run_chain(L1, L2, 1 / PCLK, 0.48, 1.5e-9, 30, Z_ISO, PS_MM(EEFF_ISO), L_FPC_ISO * V_FPC, 5, NHc)

# ---------------- 8080 bus ---------------------------------------------------------------------------------------------
fwr = 15e6
G_L = {k: v["len_mm"] for k, v in LAY.items() if k.startswith("8080:")}


def bus_netlist(L, period, tr, Rout=30, Cin=5):
    s = ["bus", f"V1 drv 0 PULSE(0 {VDD} 1n {tr} {tr} {period/2 - tr} {period})", f"Rout drv n0 {Rout}", "Rs n0 n1 33"]
    cur = "n1"
    for i in range(4):
        s.append(f"Vpa{i} {cur} {cur}x 0"); s.extend(ladder(f"a{i}", f"{cur}x", f"a{i+1}", Z_ISO, L / 4 * PS_MM(EEFF_ISO) * 1e-12)); cur = f"a{i+1}"
    s.append(f"Vpa4 {cur} {cur}e 0"); s.append(f"Cin {cur}e 0 {Cin}p"); s.append(f".tran {STEP} {NPER_RUN * period} 0 {STEP}"); s.append(".end")
    return "\n".join(s) + "\n"


def run_bus(L, period, nh):
    v = ng.run_netlist(bus_netlist(L, period, 2e-9))
    t = np.real(v["time"])
    ph = np.array([harmonics(t, np.real(v[f"vpa{i}#branch"]), period, nh, nper=4) for i in range(5)])
    return np.trapezoid(ph, dx=L / 4 * 1e-3, axis=0), ph[0]
wr_mom, wr_I = run_bus(G_L["8080:WR"], 1 / fwr, 66)
f_wr = np.arange(1, 67) * fwr
bus_mom = 0
for fu in [POOL.submit(run_bus, G_L["8080:D%d" % i], 2 / fwr, 133) for i in range(8)]:
    m_, _ = fu.result()
    bus_mom = bus_mom + m_
f_bus = np.arange(1, 134) * fwr / 2

# ---------------- save ------------------------------------------------------------------------------------------------
def pack(f, d):
    return {"f_MHz": (f / 1e6).round(3).tolist(), **{k: [[float(abs(x)), float(np.angle(x))] for x in v] for k, v in d.items()}}
out["rgb_worst_in_phase"] = {lab: pack(f_d, {"board_seg1_moment_Am": c["a"], "board_seg2_moment_Am": c["b"], "fpc_moment_Am": c["c"],
                                             "I_into_fpc_A": c["Ic_start"], "V_oc_V": c["V_oc"]}) for lab, c in cases.items()}
out["rgb_single_line_isolated"] = pack(f_d, {"board_seg1_moment_Am": single["a"]["moment_Am"], "board_seg2_moment_Am": single["b"]["moment_Am"],
                                             "fpc_moment_Am": single["c"]["moment_Am"], "I_into_fpc_A": single["c"]["I_start"], "I_drv_A": single["a"]["I_start"], "V_oc_V": single["V_oc"]})
for lab, r in (("pclk", pclk), ("pclk_fast", pclk_fast), ("pclk_duty48", pclk_48)):
    out[lab] = pack(f_c, {"board_seg1_moment_Am": r["a"]["moment_Am"], "board_seg2_moment_Am": r["b"]["moment_Am"],
                          "fpc_moment_Am": r["c"]["moment_Am"], "I_into_fpc_A": r["c"]["I_start"], "I_drv_A": r["a"]["I_start"], "V_oc_V": r["V_oc"]})
out["bus_8080_WR"] = pack(f_wr, {"moment_Am": wr_mom, "I_drv_A": wr_I})
out["bus_8080_data8_in_phase"] = pack(f_bus, {"moment_Am": bus_mom})
# summary table of currents at selected harmonics
summ = {}
for lab, f, arr in (("RGB 24 in phase: current into FPC (sum)", f_d, cases["nominal Rout30 tr1.5 Cin5"]["Ic_start"]),
                    ("PCLK: current into FPC", f_c, pclk["c"]["I_start"]), ("PCLK: driver current", f_c, pclk["a"]["I_start"])):
    summ[lab] = {f"{ff/1e6:.0f}MHz": round(float(abs(a)) * 1e3, 3) for ff, a in zip(f, arr) if ff < 1.05e9 and (round(ff / 16.65e6) % 3 == 0 or ff < 120e6)}
out["summary_mA"] = summ
save_section("spice_chain", out)

# ---------------- plots ---------------------------------------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
r = per_line["B7"]
m = r["t"] > r["t"][-1] - 3 * per_d
ax[0].plot((r["t"][m] - r["t"][m][0]) * 1e9, r["v_end"][m], label="panel input (end of FPC), B7")
ax[0].set_xlabel("ns"); ax[0].set_ylabel("V"); ax[0].set_title("Worst pattern, 24 lines in phase: B7 at the panel input"); ax[0].grid(alpha=.3)
ax[0].axhline(0.7 * VDD, color="k", ls=":", label="VIH 0.7 VDD (panel DS p.6)"); ax[0].axhline(0.3 * VDD, color="k", ls="--", label="VIL 0.3 VDD"); ax[0].legend(fontsize=7)
for lab, c in cases.items():
    ax[1].semilogy(f_d / 1e6, np.abs(c["Ic_start"]) * 1e3, "o-", ms=2, label="sum of 24 data lines into FPC, " + lab)
ax[1].semilogy(f_c / 1e6, np.abs(pclk["c"]["I_start"]) * 1e3, "s-", ms=3, label="PCLK into FPC")
ax[1].set_xlabel("MHz"); ax[1].set_ylabel("harmonic current, mA peak"); ax[1].set_title("Current entering the TFT FPC at J10 (SPICE)")
ax[1].grid(True, which="both", alpha=.3); ax[1].legend(fontsize=7); ax[1].set_xlim(0, 1000)
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "spice_rgb_chain.png"), dpi=150)
print(json.dumps({"num": out["numerical_check_fpc_moment_max_dev_dB_odd_harmonics"], "val": out["validation_trapezoid_max_err_dB"], "summ": summ, "assump": out["assumptions"]}, indent=1, default=str))
