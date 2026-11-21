"""Earthed case Monte Carlo (120 draws, paired across configurations), one configuration per call so each run
finishes in a few minutes:  python -X utf8 run_mc.py <config> [n]
configs: earthed_today, earthed_F1, fix_today, fix_F1  (fix = fixes.CHOSEN)
Parameters as in the scope-A Monte Carlo (V_on 10-40 V today / 8-18 V F1, t_f, heater L, L40/C40/C1 tolerances and
parasitics, trace scale, C_hc 100-1000 pF, mains Z, cord coupling, L40 Rp, L1 core loss) plus PE bond 0.1-3 uH,
insulated-junction C 20-200 pF, fan frame C 50-300 pF. Writes results.json section 'mc_<config>'."""
import os, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import earthed_model as em
import fixes
from ecommon import save


def draws(n, seed=20261121):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append({"u_von": rng.uniform(), "t_f": 10 ** rng.uniform(np.log10(0.2e-6), np.log10(2e-6)),
                    "L_heater": 10 ** rng.uniform(-6, np.log10(20e-6)), "ESL40": rng.uniform(10e-9, 30e-9), "Cp40": rng.uniform(3e-12, 20e-12),
                    "L40": 100e-6 * rng.uniform(0.9, 1.1), "C40": 1e-6 * rng.uniform(0.9, 1.1), "C1": 100e-9 * rng.uniform(0.8, 1.2),
                    "trace_scale": rng.uniform(0.5, 1.5), "C_hc": 10 ** rng.uniform(-10, -9),
                    "Rm": rng.uniform(0.1, 1.0), "Lm": rng.uniform(0, 1.5e-3), "k_cord": rng.uniform(0.6, 0.85), "k_pe": rng.uniform(0.6, 0.85),
                    "Rp40": 10 ** rng.uniform(np.log10(5e3), np.log10(100e3)), "Rp_cmc": 10 ** rng.uniform(np.log10(5e3), np.log10(50e3)),
                    "L_bond": 10 ** rng.uniform(-7, np.log10(3e-6)), "C_jn": 10 ** rng.uniform(np.log10(20e-12), np.log10(200e-12)),
                    "C_fanframe": rng.uniform(50e-12, 300e-12)})
    return out


def job(args):
    d, von, mods = args
    P = dict(em.EARTHED); P.update(mods); P.update({k: v for k, v in d.items() if k != "u_von"})
    P["V_on"] = von[0] + d["u_von"] * (von[1] - von[0])
    return em.evalP(P)


def summarise(rows):
    s = {}
    for k in rows[0]:
        m = np.array([r[k]["margin_dB"] for r in rows])
        s[k] = {"min": round(float(m.min()), 1), "p5": round(float(np.percentile(m, 5)), 1), "median": round(float(np.median(m)), 1),
                "f_MHz_at_min": rows[int(np.argmin(m))][k]["f_MHz"], "n_below_6dB": int((m < 6).sum()), "n_below_0dB": int((m < 0).sum())}
    return s


def main():
    cfg = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    von = (8.0, 18.0) if cfg.endswith("F1") else (10.0, 40.0)
    mods = fixes.ALL[fixes.CHOSEN] if cfg.startswith("fix") else {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        rows = list(ex.map(job, [(d, von, mods) for d in draws(n)], chunksize=2))
    out = {"config": cfg, "fix": fixes.CHOSEN if cfg.startswith("fix") else None, "V_on_range": von, "n": n,
           "summary": summarise(rows), "rows": rows, "runtime_s": round(time.time() - t0, 1)}
    save(f"mc_{cfg}", out)
    print(cfg, out["summary"], out["runtime_s"])


if __name__ == "__main__":
    main()
