"""Earthed case, step 1: nominal / all-worst corner for the earthing and SELV variants, and the fix candidates.
Writes results.json sections 'nominal_and_corners' and 'fix_candidates'. Runs in ~3-4 min (foreground)."""
import sys, time, json
import numpy as np
import earthed_model as em
from ecommon import save

FIXES = {
    "none": {},
    "heater-lead CMC 2x1.8 mH 6 A": {"fix_heater_cmc": em.CMC_6A},
    "A1-lead inductor 100 uH 5 A (2nd RC1415U-101K)": {"fix_lead_L": {"L": 100e-6, "Cw": 10e-12, "Rp": 30e3}},
    "A1-lead inductor 47 uH 5 A": {"fix_lead_L": {"L": 47e-6, "Cw": 8e-12, "Rp": 20e3}},
    "Y 2x2.2 nF to PCB PE (no CMC)": {"fix_y": {"C": 2.2e-9, "esl": 8e-9, "L_pe_wire": 0.2e-6}},
    "Y 2x4.7 nF to PCB PE (no CMC)": {"fix_y": {"C": 4.7e-9, "esl": 8e-9, "L_pe_wire": 0.2e-6}},
    "input CMC 2x1.8 mH 6 A + Y 2x2.2 nF": {"fix_in_cmc": em.CMC_6A, "fix_y": {"C": 2.2e-9, "esl": 8e-9, "L_pe_wire": 0.2e-6}},
    "input CMC 2x1.8 mH 6 A, no Y": {"fix_in_cmc": em.CMC_6A},
}
# damped A1-lead inductor: the plain 100 uH resonates with C_hc near 0.5 MHz; a parallel resistor ~ sqrt(L/C_hc) damps it
FIXES_DAMPED = {
    "A1-lead 100 uH || 220 ohm": {"fix_lead_L": {"L": 100e-6, "Cw": 10e-12, "Rp": 220.0}},
    "A1-lead 100 uH || 330 ohm": {"fix_lead_L": {"L": 100e-6, "Cw": 10e-12, "Rp": 330.0}},
    "A1-lead 100 uH || 470 ohm": {"fix_lead_L": {"L": 100e-6, "Cw": 10e-12, "Rp": 470.0}},
    "A1-lead 220 uH || 680 ohm": {"fix_lead_L": {"L": 220e-6, "Cw": 12e-12, "Rp": 680.0}},
    "heater-lead CMC 2x1.8 mH, each winding || 1 kohm": {"fix_heater_cmc": dict(em.CMC_6A, Rp=1e3)},
}


# two RC1415U-101K in series in the A1 lead (200 uH, same part and footprint as L40)
FIXES_200 = {
    "A1-lead 2x RC1415U-101K (200 uH), core loss only": {"fix_lead_L": {"L": 200e-6, "Cw": 6e-12, "Rp": 60e3}},
    "A1-lead 2x RC1415U-101K (200 uH) || 1 kohm": {"fix_lead_L": {"L": 200e-6, "Cw": 6e-12, "Rp": 1000.0}},
    "A1-lead 2x RC1415U-101K (200 uH) || 680 ohm": {"fix_lead_L": {"L": 200e-6, "Cw": 6e-12, "Rp": 680.0}},
}
ALL = {**FIXES, **FIXES_DAMPED, **FIXES_200}
CHOSEN = "A1-lead 2x RC1415U-101K (200 uH), core loss only"
CORNERS = (("today V_on 20 V", {"V_on": 20.0}), ("F1 V_on 15 V", {"V_on": 15.0}),
           ("today all-worst (V_on 40 V)", dict(em.WORST)), ("F1 all-worst (V_on 18 V)", dict(em.WORST, V_on=18.0)))


def _job(args):
    lab, mods, tl, tm = args
    P = dict(em.EARTHED); P.update(mods); P.update(tm)
    return f"{lab} | {tl}", em.evalP(P)


def run_parallel(fixdict, section):
    from concurrent.futures import ProcessPoolExecutor
    import os
    jobs = [(lab, mods, tl, tm) for lab, mods in fixdict.items() for tl, tm in CORNERS]
    with ProcessPoolExecutor(max_workers=min(len(jobs), (os.cpu_count() or 4) - 2)) as ex:
        res = dict(ex.map(_job, jobs))
    save(section, res)
    for k, m in res.items():
        print(k.ljust(70), " ".join(f"{a}:{b['margin_dB']}@{b['f_MHz']}" for a, b in m.items()))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "200":
        run_parallel(FIXES_200, "fix_candidates_200uH")
        return
    t0 = time.time()
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "cases"):
        res = {}
        for lab, mods in (("unearthed reference (original model, C_ch 50 pF)", dict(earthed=False, C_ch=50e-12, selv="floating", C_RV2=120e-12, RV3=False, C_fanframe=1e-15)),
                          ("earthed, SELV insulated junction", {}), ("earthed, SELV grounded junction", {"selv": "grounded"}),
                          ("earthed, SELV bonded at board", {"selv": "bonded"})):
            for tl, tm in (("today V_on 20 V", {"V_on": 20.0}), ("F1 V_on 15 V", {"V_on": 15.0}),
                           ("today all-worst (V_on 40 V)", dict(em.WORST)), ("F1 all-worst (V_on 18 V)", dict(em.WORST, V_on=18.0))):
                P = dict(em.EARTHED); P.update(mods); P.update(tm)
                res[f"{lab} | {tl}"] = em.evalP(P)
        save("nominal_and_corners", res)
        print("cases", time.time() - t0, flush=True)
    if which in ("all", "fixes", "damped"):
        res = {}
        for lab, mods in (FIXES_DAMPED if which == "damped" else FIXES).items():
            for tl, tm in (("today V_on 20 V", {"V_on": 20.0}), ("F1 V_on 15 V", {"V_on": 15.0}),
                           ("today all-worst (V_on 40 V)", dict(em.WORST)), ("F1 all-worst (V_on 18 V)", dict(em.WORST, V_on=18.0))):
                P = dict(em.EARTHED); P.update(mods); P.update(tm)
                res[f"{lab} | {tl}"] = em.evalP(P)
        save("fix_candidates_damped" if which == "damped" else "fix_candidates", res)
        print("fixes", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
