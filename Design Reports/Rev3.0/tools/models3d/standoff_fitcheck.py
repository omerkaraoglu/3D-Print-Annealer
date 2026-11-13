"""Display stand-off fit check (round 2): panel STANDOFF mm off the PCB back.

  * reads out/board_fps.json (dump_board_fps.py, KiCad Python, read-only copy of the board)
  * for every F-side through-hole part: the lowest point of its 3D model below the PCB back
    (lead / pin protrusion) and the clearance left to the panel back (STANDOFF - protrusion)
  * renders (MODELS3D_RENDER_DIR): bottom-edge front view, gap section over the whole board,
    side view of the whole board, side sections through the J10 and J11 folds
  * writes out/standoff_clearance.json
Model frame = the display model's frame (tft7_sat070at40d21.py): z 0 = PCB back, PCB z -1.6..0,
panel back z = STANDOFF, component side towards -z.  J10/J11 are drawn at the positions the
model is built for (t.J10 / t.J11); a warning is printed if the board has them elsewhere.
"""
import json, math, os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cadquery as cq
from common import HERE, OUT_DIR, box, render_ortho
import tft7_sat070at40d21 as t

KI3D = r"C:\Program Files\KiCad\10.0\share\kicad\3dmodels"
PRJ = os.path.normpath(os.path.join(HERE, r"..\..\..\..\KiCad\3dFilamentDryer"))
MAINS = ("LINE", "NEUT", "PSU_L", "ZCD_", "AC/", "Q1-", "C4-Pad1", "R3-Pad1")


def model_file(f):
    fn = f.replace("${KICAD10_3DMODEL_DIR}", KI3D).replace("${KICAD9_3DMODEL_DIR}", KI3D).replace("${KIPRJMOD}", PRJ)
    return os.path.normpath(fn)


def place(shape, x, y, rot):
    """Component model (footprint frame, z up from the PCB top) -> display model frame."""
    X0, Y0 = t.abs_to_model(x, y)
    return (shape.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
            .rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 180)
            .translate(cq.Vector(X0, Y0, -t.PCB_T)))


def main():
    d = json.load(open(os.path.join(OUT_DIR, "board_fps.json")))
    T = d["thickness"]
    m = t.build()
    parts = list(m.shapes())
    x0, y0, x1, y1 = t.BOARD
    (a, b), (c_, e) = t.abs_to_model(x0, y0), t.abs_to_model(x1, y1)
    parts.append(("pcb", box(min(a, c_), max(a, c_), min(b, e), max(b, e), -T, 0).val(), "green"))
    px0, px1 = t.CX - t.L_OUT / 2, t.CX + t.L_OUT / 2
    py0, py1 = t.CY - t.H_OUT / 2, t.CY + t.H_OUT / 2
    rows, warn = [], []
    for f in d["fps"]:
        x, y = f["x"], f["y"]
        if f["ref"] in ("J10", "J11"):
            want = {"J10": t.J10, "J11": t.J11}[f["ref"]]
            if math.hypot(x - want[0], y - want[1]) > 0.005:
                warn.append("%s is on the board at (%.2f, %.2f); model built for (%.2f, %.2f)" % (f["ref"], x, y, *want))
            x, y = want
        tht = [p for p in f["pads"] if p["tht"]]
        if f["side"] != "F" or not f["models"] or not (tht or f["ref"] in ("J10", "J11")):
            continue
        fn = model_file(f["models"][0]["file"])
        if not os.path.exists(fn):
            warn.append("%s: model missing %s" % (f["ref"], fn))
            continue
        shp = cq.importers.importStep(fn).val()
        gap = box(-200, 200, -200, 200, 0, 50).val()          # everything past the PCB back, display frame
        for s in shp.Solids():
            ps = place(s, x, y, f["rot"])
            if ps.BoundingBox().zmax > 1e-3:                    # pokes out of the PCB back: red part in the gap
                parts.append((f["ref"] + " protrusion", ps.intersect(gap), "wire_red"))
                ps = ps.cut(gap)
            parts.append((f["ref"], ps, "film_grey"))
        if not tht:
            continue
        prot = max(0.0, -shp.BoundingBox().zmin - T)
        inside = all(px0 <= p["x"] <= px1 and py0 <= p["y"] <= py1 for p in tht)
        nets = sorted({p["net"] for p in tht})
        mains = any(any(k in n for k in MAINS) for n in nets)
        rows.append({"ref": f["ref"], "x": round(x, 2), "y": round(y, 2), "model": os.path.basename(fn),
                     "protrusion_below_back": round(prot, 2), "clearance_to_panel": round(t.STANDOFF - prot, 2),
                     "under_panel": inside, "mains": mains, "nets": nets})
    rows.sort(key=lambda r: -r["protrusion_below_back"])
    res = {"standoff": t.STANDOFF, "pcb_t": T, "panel_back_z": t.STANDOFF, "rows": rows, "warnings": warn,
           "geo": m.geo}
    ye = -t.H_OUT / 2
    zt = t.STANDOFF + t.T_LCM + t.T_PU + t.T_SENSOR + t.T_OCA + t.T_COVER
    deep = max(g["loop_bottom_below_board_edge"] for g in m.geo.values())
    hl = [(0.0, "PCB back z 0", "-"), (-T, "PCB top", "-"), (t.STANDOFF, "panel back z %.1f" % t.STANDOFF, "--")]
    png = {}
    png["front_bottom_edge"] = render_ortho(
        parts, "front", "R2_front_bottom_edge", clip=(-90, 90, ye - deep - 2, ye + 20, -T - 4, zt + 0.5), hlines=hl,
        width_in=16, title="Bottom edge, front view (looking +Y): PCB, %.1f mm gap, panel, folded tails" % t.STANDOFF)
    png["front_gap_section"] = render_ortho(
        parts, "front", "R2_front_gap_section", clip=(-90, 90, -60, 60, -T - 0.01, zt + 0.5), hlines=hl, width_in=16,
        title="Whole board, z PCB top..cover only (front view): lead protrusions (red) in the %.1f mm gap" % t.STANDOFF)
    png["side_full"] = render_ortho(
        parts, "side", "R2_side_full", clip=(-90, 90, ye - deep - 2, 60, -30, zt + 0.5), hlines=hl, width_in=16,
        title="Side view (looking -X), whole board: parts, PCB, gap, panel, tail loops")
    for name, conn in (("J10", t.J10), ("J11", t.J11)):
        X, _ = t.abs_to_model(*conn)
        g = m.geo["tft" if name == "J10" else "ctp"]
        png["side_fold_" + name] = render_ortho(
            parts, "side", "R2_side_fold_" + name,
            clip=(X - 3, X + 3, ye - g["loop_bottom_below_board_edge"] - 2, ye + 14, -T - 6, zt + 0.5),
            hlines=hl, vlines=[(ye, "board / panel bottom edge", ":")], width_in=12,
            title="%s fold, section X %.1f +-3 (side view): gap %.1f, bend r %.2f, loop %.2f below the edge"
                  % (name, X, t.STANDOFF, g["bend_r"], g["loop_bottom_below_board_edge"]))
    res["png"] = png
    json.dump(res, open(os.path.join(OUT_DIR, "standoff_clearance.json"), "w"), indent=1)
    print("stand-off %.2f mm; lead protrusion below the PCB back (3D models):" % t.STANDOFF)
    for r in rows:
        print("  %-4s %5.2f  clear %5.2f  %s%s  %s" % (r["ref"], r["protrusion_below_back"], r["clearance_to_panel"],
                                                     "under panel" if r["under_panel"] else "outside",
                                                     ", MAINS" if r["mains"] else "", r["model"]))
    for w in warn:
        print("WARNING:", w)
    for k, v in png.items():
        print("  png", k, v)


if __name__ == "__main__":
    main()
