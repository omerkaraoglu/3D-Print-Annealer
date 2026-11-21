"""Regenerate curve data that the scope folders do not store (read-only use of the engineers' scripts).

Writes only into report/curves/:
  surge_waves.json    B: sim_surge.run_case() for the worst triac case, as designed and with P-S4 / P-S2b + P-S4
  eft_waves.json      B: sim_eft.run() at the two worst ZCD corners, without and with the 1 nF of P-E1
  dips_waves.json     B: sim_dips.simulate() for the three Table 13 rows (22 uF / 70 V / 5.5 W, plus the one corner that resets)
  pdn_curves.json     C: c7_pdn.py executed with its save_section() and savefig() disabled; curves read from its axes
  board_*.png, board_meta.json   KiCad board layers rendered by kicad-cli from a COPY of the project (page coordinates = board mm)
Nothing in the scope folders, sim/emc, KiCad/ or Firmware/ is written.  Run: python -X utf8 regen_curves.py [surge eft dips pdn board]
"""
import json, os, sys, shutil, subprocess, tempfile
import numpy as np
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.abspath(os.path.join(HERE, ".."))
PROJ = os.path.abspath(os.path.join(TESTS, "..", "..", "..", ".."))
OUT = os.path.join(HERE, "curves"); os.makedirs(OUT, exist_ok=True)
B = os.path.join(TESTS, "B_immunity_transients"); C = os.path.join(TESTS, "C_rf")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
BOARD_DIR = os.path.join(PROJ, "KiCad", "3dFilamentDryer")


def dump(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o))
    print("wrote", name)


def thin(t, *ys, n=1500):
    """resample onto n uniform points (plotting only)."""
    tu = np.linspace(t[0], t[-1], n)
    return [tu.tolist()] + [np.interp(tu, t, y).tolist() for y in ys]


def surge():
    sys.path.insert(0, B); os.chdir(B)
    import sim_surge as ss
    out = {}
    base = dict(pol=+1, heater=False, relay_closed=False, mov="max", Lsat=5e-6, Isat=6.0)
    variants = {"as designed": {}, "P-S4 (RV2 -> 1.5KE440CA)": {"rv2": "TVS440"},
                "P-S2b + P-S4": {"rv2": "TVS440", "extra": ss.RV3("max")}}
    for name, kw in variants.items():
        m, tw, wv, ts = ss.run_case(**base, **kw)
        t = (tw - ts) * 1e6
        tt, vlf, vlfi, vt = thin(t, wv["vLF"], wv["vLFI"], wv["vT"])
        out[name] = {"t_us": tt, "V_LINE_FUSED": vlf, "V_LINE_FILT": vlfi, "V_triac": vt,
                     "peaks": {k: m[k] for k in ("V_LINE_FUSED_pk", "V_K1_open_contacts_pk", "V_LINE_FILT_pk", "V_triac_pk")}}
        print(name, out[name]["peaks"])
    out["case"] = "+1 kV at 90 deg, heater off, K1 open, varistors at max-voltage corner, L40 knee 6 A / 5 uH (sim_surge.run_case)"
    # K1's worst case is the soft-saturation corner (L40 knee 20 A / 20 uH); K1 contact = LINE_FUSED - fan side
    base20 = dict(base, Lsat=20e-6, Isat=20.0)
    for name, kw in (("as designed | knee 20 A", {}), ("P-S2b + P-S4 | knee 20 A", {"rv2": "TVS440", "extra": ss.RV3("max")})):
        r = None
        for tm in (200e-9, 100e-9, 50e-9, 20e-9):
            net, ts = ss.netlist(tmax=tm, **base20, **kw)
            try:
                r = ss.cm.run_netlist(net); break
            except Exception:
                continue
        m, tw, wv = ss.measure(r, ts, False)
        t = (tw - ts) * 1e6
        w = (r["time"] >= ts - 20e-6) & (r["time"] <= ts + 250e-6)
        vk1 = (r["v(lf)"] - r["v(fanh)"])[w]
        tt, vlf, vk = thin(t, wv["vLF"], vk1)
        out[name] = {"t_us": tt, "V_LINE_FUSED": vlf, "V_K1_contact": vk,
                     "peaks": {k: m[k] for k in ("V_LINE_FUSED_pk", "V_K1_open_contacts_pk", "V_LINE_FILT_pk", "V_triac_pk")}}
        print(name, out[name]["peaks"])
    dump("surge_waves.json", out)


def eft():
    sys.path.insert(0, B); os.chdir(B)
    import sim_eft as se
    out = {}
    corners = {"+ pulse, C_hlk 20 pF, C_sc/C_cg 50/150 pF, transistor off": dict(pol=+1, Chlk=20e-12, Csc=50e-12, Ccg=150e-12, q_on=False),
               "- pulse, C_hlk 20 pF, C_sc/C_cg 50/150 pF, transistor off": dict(pol=-1, Chlk=20e-12, Csc=50e-12, Ccg=150e-12, q_on=False)}
    for name, kw in corners.items():
        res = {}
        for lab, extra in (("as designed (8 pF node)", {}), ("P-E1 1 nF C0G", {"Czc": 1e-9})):
            m, t, w = se.run(**kw, **extra)
            sel = t <= 3e-6
            tt, vz = thin(t[sel] * 1e9, w["vzc"][sel], n=2500)
            res[lab] = {"t_ns": tt, "V_zcd": vz, "V_ZC_max": m["V_ZC_max"], "V_ZC_min": m["V_ZC_min"]}
            print(name, lab, round(m["V_ZC_max"], 3), round(m["V_ZC_min"], 3))
        out[name] = res
    dump("eft_waves.json", out)


def dips():
    sys.path.insert(0, B); os.chdir(B)
    import sim_dips as sd
    import common as cm
    out = {}
    for row in cm.STD["dips"]["rows"]:
        key = f"{row['residual_pct']} % / {row['cycles_50Hz']} cycles"
        s = sd.simulate(row["residual_pct"] / 100, row["cycles_50Hz"], Cb=22e-6, Voff=70.0, P5=5.5)
        tt, vb, v5, v3 = thin((s["t"] - 0.1) * 1e3, s["vb"], s["v5"], s["v3"], n=2500)
        out[key] = {"t_ms": tt, "V_bulk": vb, "V_5V": v5, "V_3V3": v3, "min_3V3": s["min_3V3"], "reset": s["brownout_reset"],
                    "corner": "bulk 22 uF, drop-out 70 V, 5.5 W"}
        if row["residual_pct"] == 40:
            s2 = sd.simulate(0.40, row["cycles_50Hz"], Cb=10e-6, Voff=90.0, P5=5.5)
            tt, vb, v5, v3 = thin((s2["t"] - 0.1) * 1e3, s2["vb"], s2["v5"], s2["v3"], n=2500)
            out[key + " | worst corner"] = {"t_ms": tt, "V_bulk": vb, "V_5V": v5, "V_3V3": v3, "min_3V3": s2["min_3V3"],
                                            "reset": s2["brownout_reset"], "corner": "bulk 10 uF, drop-out 90 V, 5.5 W"}
        print(key, s["min_3V3"], s["brownout_reset"])
    dump("dips_waves.json", out)


def pdn():
    """Execute c7_pdn.py unchanged, with its two side effects (results.json write, plot write) replaced by no-ops."""
    sys.path.insert(0, C); os.chdir(C)
    import c0_common
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.figure
    c0_common.save_section = lambda key, data: print("save_section suppressed:", key)
    orig = matplotlib.figure.Figure.savefig
    matplotlib.figure.Figure.savefig = lambda self, *a, **k: print("savefig suppressed")
    src = open(os.path.join(C, "c7_pdn.py"), encoding="utf-8").read()
    ns = {"__name__": "c7_pdn_readonly", "__file__": os.path.join(C, "c7_pdn.py")}
    exec(compile(src, "c7_pdn.py", "exec"), ns)
    matplotlib.figure.Figure.savefig = orig
    out = {}
    for ax, rail in zip(ns["axs"], ("3V3", "5V", "1V2")):
        out[rail] = {ln.get_label(): {"f_MHz": np.asarray(ln.get_xdata()).tolist(), "Z_ohm": np.asarray(ln.get_ydata()).tolist()}
                     for ln in ax.get_lines() if not ln.get_label().startswith("target") and not ln.get_label().startswith("_")}
    dump("pdn_curves.json", out)


def board():
    """Render the board with kicad-cli from a copy of the project; SVG page coordinates are KiCad mm."""
    import fitz
    with tempfile.TemporaryDirectory() as tmp:
        for f in os.listdir(BOARD_DIR):
            if f.endswith((".kicad_pcb", ".kicad_pro")):
                shutil.copy2(os.path.join(BOARD_DIR, f), tmp)
        pcb = os.path.join(tmp, "3dFilamentDryer.kicad_pcb")
        svgdir = os.path.join(tmp, "svg")
        subprocess.run([KICAD_CLI, "pcb", "export", "svg", "--mode-multi", "--layers", "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts,F.Fab",
                        "--page-size-mode", "1", "--exclude-drawing-sheet", "--black-and-white", "--drill-shape-opt", "1",
                        "-o", svgdir, pcb], check=True, capture_output=True)
        # board extent from the Edge.Cuts primitives (start/end/mid/center points) of the copy
        txt = open(pcb, encoding="utf-8").read()
        import re
        xs, ys = [], []
        for blk in re.findall(r"\((?:gr_line|gr_arc|gr_rect|gr_circle)\s(.*?)\(layer \"Edge\.Cuts\"\)", txt, flags=re.S):
            for x, y in re.findall(r"\((?:start|end|mid|center) ([-\d.]+) ([-\d.]+)\)", blk):
                xs.append(float(x)); ys.append(float(y))
        x0, x1, y0, y1 = min(xs) - 1.5, max(xs) + 1.5, min(ys) - 1.5, max(ys) + 1.5
        scale = 14.0                                             # px per mm (356 dpi)
        meta = {"extent_mm": [x0, x1, y0, y1], "px_per_mm": scale, "layers": []}
        for f in sorted(os.listdir(svgdir)):
            doc = fitz.open(os.path.join(svgdir, f))
            pg = doc[0]
            k = 72 / 25.4
            clip = fitz.Rect(x0 * k, y0 * k, x1 * k, y1 * k)
            pix = pg.get_pixmap(matrix=fitz.Matrix(scale / k, scale / k), clip=clip, alpha=False)
            layer = f.split("-")[-1].replace(".svg", "")
            pix.save(os.path.join(OUT, f"board_{layer}.png"))
            meta["layers"].append(layer)
            print("board layer", layer, pix.width, pix.height)
        # footprint positions (reference, x, y, side) parsed from the copy
        fps = {}
        for blk in txt.split("\n\t(footprint ")[1:]:
            m_at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
            m_ref = re.search(r"\(property \"Reference\" \"([^\"]+)\"", blk)
            m_layer = re.search(r"\n\t\t\(layer \"([FB])\.Cu\"\)", blk)
            m_val = re.search(r"\(property \"Value\" \"([^\"]*)\"", blk)
            if m_at and m_ref:
                fps[m_ref.group(1)] = {"x": float(m_at.group(1)), "y": float(m_at.group(2)), "side": m_layer.group(1) if m_layer else "?",
                                       "value": m_val.group(1) if m_val else ""}
        meta["footprints"] = fps
        dump("board_meta.json", meta)


if __name__ == "__main__":
    jobs = sys.argv[1:] or ["surge", "eft", "dips", "pdn", "board"]
    cwd = os.getcwd()
    for j in jobs:
        globals()[j]()
        os.chdir(cwd)
