"""C_rf step 4b - re-simulate the RGB/PCLK chain with the proposed series-resistor values (RN1..RN7 33 ohm -> 100/150/220 ohm)
and check the signal integrity at the panel input (edge, levels, settling within the 30 ns PCLK period).
Faster transient (12 periods, 20 ps); the 33 ohm case is re-run as a numerical check against c4 (40 periods, 10 ps).
Panel timing: the SAT070AT40D21 datasheet gives VIH 0.7 VDD / VIL 0.3 VDD (p.6); its setup/hold table was not extracted -
a 10-90 % edge <= 5 ns (1/6 of the 30 ns period) is used as the SI acceptance (ASSUMED, to be checked on the panel sheet)."""
import json, math
import numpy as np
from c0_common import *
src = open(os.path.join(HERE, "c4_spice_chain.py"), encoding="utf-8").read().split('out = {"assumptions"')[0]
exec(src)
_G = json.load(open(GEOM)); LEN = {}
for _t in _G["tracks"]:
    LEN[_t["net"]] = LEN.get(_t["net"], 0.0) + _t["len"]
L12 = lambda nm: (LEN["/Display/%s_T" % nm], LEN["/Display/%s" % nm])
data_names = [c + str(i) for c in "RGB" for i in range(8)]
NH, NHc = 61, 30
per_d = 2 / PCLK
f_d = np.arange(1, NH + 1) / per_d
f_c = np.arange(1, NHc + 1) * PCLK
pack = lambda f, d: {"f_MHz": (f / 1e6).round(3).tolist(), **{k: [[float(abs(x)), float(np.angle(x))] for x in v] for k, v in d.items()}}


def run_fast(L1, L2, period, Rs, Zb, ps, Zf, nh, tr=1.5e-9, Rout=30, Cin=5):
    n = chain_netlist(L1, L2, period, 0.5, tr, Rout, Zb, ps, Zf, Cin, Rs=Rs, tstop=12 * period)
    n = n.replace(".tran 10p", ".tran 20p").replace(" 0 10p\n", " 0 20p\n")
    v = ng.run_netlist(n)
    t = np.real(v["time"])
    res = {}
    for pre, L in (("a", L1), ("b", L2), ("c", FPC_LEN)):
        ph = np.array([harmonics(t, np.real(v[f"vp{pre}{i}#branch"]), period, nh, nper=4) for i in range(5)])
        res[pre] = np.trapezoid(ph, dx=L / 4 * 1e-3, axis=0)
    res["Ic0"] = harmonics(t, np.real(v["vpc0#branch"]), period, nh, nper=4)
    res["V_oc"] = harmonics(t, np.real(v["v(drv)"]), period, nh, nper=4)
    ve = np.real(v["v(c4e)"])
    m = t > t[-1] - 2 * period
    tt, vv = t[m], ve[m]
    # 10-90 % rise time of the first rising edge in the window
    lo, hi = 0.1 * VDD, 0.9 * VDD
    i0 = np.argmax((vv[:-1] < lo) & (vv[1:] >= lo)) if np.any((vv[:-1] < lo) & (vv[1:] >= lo)) else 0
    i1 = i0 + np.argmax(vv[i0:] >= hi)
    res["tr_10_90_ns"] = float((tt[i1] - tt[i0]) * 1e9)
    res["vmax"], res["vmin"] = float(vv.max()), float(vv.min())
    return res


SCd = load_results()["spice_chain"]
L1, L2 = L12("PCLK")
chk = {}
for Rs in (33, 100, 150, 220):
    r = run_fast(L1, L2, 1 / PCLK, Rs, Z_ISO, PS_MM(EEFF_ISO), L_FPC_ISO * V_FPC, NHc)
    key = "pclk" if Rs == 33 else f"pclk_rs{Rs}"
    pack_ = {"board_seg1_moment_Am": r["a"], "board_seg2_moment_Am": r["b"], "fpc_moment_Am": r["c"], "I_into_fpc_A": r["Ic0"], "V_oc_V": r["V_oc"]}
    if Rs == 33:
        ref = np.array(SCd["pclk"]["fpc_moment_Am"])[:, 0]
        chk["fast_vs_c4_fpc_moment_max_dev_dB_first10"] = float(np.max(np.abs(dB(np.abs(r["c"][:10])) - dB(ref[:10]))))
    else:
        SCd[key] = pack(f_c, pack_)
    chk[f"PCLK Rs={Rs}: panel-input edge 10-90 % ns / Vmax / Vmin"] = [round(r["tr_10_90_ns"], 2), round(r["vmax"], 2), round(r["vmin"], 2)]
# worst pattern with the larger resistors (24 lines)
for Rs in (100, 150):
    tot = {"a": 0, "b": 0, "c": 0, "Ic": 0, "V_oc": 0}
    for nm in data_names:
        a1, a2 = L12(nm)
        r = run_fast(a1, a2, per_d, Rs, Z_EVEN, PS_MM(ER_PP), L_FPC_EVEN * V_FPC, NH)
        for k in "abc":
            tot[k] = tot[k] + r[k]
        tot["Ic"] = tot["Ic"] + r["Ic0"]
        tot["V_oc"] = r["V_oc"]
    SCd["rgb_worst_in_phase"][f"Rs{Rs} Rout30 tr1.5 Cin5"] = pack(f_d, {"board_seg1_moment_Am": tot["a"], "board_seg2_moment_Am": tot["b"],
                                                                      "fpc_moment_Am": tot["c"], "I_into_fpc_A": tot["Ic"], "V_oc_V": tot["V_oc"]})
    chk[f"data B7 Rs={Rs}: edge ns / Vmax / Vmin (in-phase mode)"] = [round(r["tr_10_90_ns"], 2), round(r["vmax"], 2), round(r["vmin"], 2)]
SCd["proposal_SI_check"] = chk
save_section("spice_chain", SCd)
print(json.dumps(chk, indent=1))
