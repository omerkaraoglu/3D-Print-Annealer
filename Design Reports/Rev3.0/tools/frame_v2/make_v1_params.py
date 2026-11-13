"""Write v1_params.json: the v1 carrier frame described in the v2 params-JSON format, so that the v2
toolchain (build_v2.py --v1) can be regression-tested on the v1 STEP.

  <venv>/Scripts/python.exe make_v1_params.py [path/to/v1/frame.py]

Reads the v1 parameter module (../frame/frame.py, imported by path; it is not modified) and the v1
build summary (../frame/out/summary.json) and writes ./v1_params.json. Only needed again if v1 changes;
the JSON is kept next to the scripts, so the v2 tools do not depend on the v1 folder at run time.
"""
import importlib.util
import json
import sys
sys.dont_write_bytecode = True
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1_DIR = os.path.normpath(os.path.join(HERE, "..", "frame"))


def load_v1(path):
    sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location("frame_v1", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv):
    F = load_v1(argv[0] if argv else os.path.join(V1_DIR, "frame.py"))
    summ = json.load(open(os.path.join(V1_DIR, "out", "summary.json")))
    t = math.tan(math.radians(F.DRAFT))

    def p(name, value, unit, comment):
        return {"name": name, "value": value, "unit": unit, "comment": comment}

    params = [
        # board / panel facts (not frame design choices, but the tools need them)
        p("PCB_T", F.PCB_T, "mm", "board thickness"),
        p("PANEL", list(F.PANEL), "mm", "panel outline x0, x1, y0, y1 (KiCad abs, y down)"),
        p("PANEL_T", F.PANEL_T, "mm", "LCM 3.34 + CTP stack 1.98"),
        p("PANEL_T_TOL", F.PANEL_T_TOL, "mm", "LCM thickness tolerance (+-)"),
        p("STANDOFF", F.STANDOFF, "mm", "PCB back -> panel back"),
        p("VA", list(F.VA), "mm", "cover view area x0, x1, y0, y1 (abs)"),
        p("AA", list(F.AA), "mm", "active area x0, x1, y0, y1 (abs)"),
        # sheet, gasket, oven sheet
        p("SHEET_T", F.SHEET_T, "mm", "Formex-type insulating sheet"),
        p("SHEET_INSET", F.SHEET_INSET, "mm", "sheet = panel outline - 2 x inset"),
        p("SHEET_R", F.SHEET_R, "mm", "sheet corner radius"),
        p("GASKET_T", F.GASKET_T, "mm", "closed-cell silicone sponge, nominal"),
        p("GASKET_COMP", F.GASKET_COMP, "-", "design compression (fraction)"),
        p("GASKET_IN_MARGIN", F.GASKET_IN_MARGIN, "mm", "gasket inner edge = VA + this per side"),
        p("GASKET_OUT_INSET", F.GASKET_OUT_INSET, "mm", "gasket outer edge = panel outline - this per side"),
        p("OVEN_SHEET_T", F.OVEN_SHEET_T, "mm", "steel front sheet"),
        p("CUTOUT_MARGIN", F.CUTOUT_MARGIN, "mm", "sheet window = VA + this per side"),
        p("CUTOUT_R", F.CUTOUT_R, "mm", "sheet window corner radius"),
        # moulding rules / frame
        p("WALL", F.WALL, "mm", "nominal wall"),
        p("RIB_T", F.RIB_T, "mm", "rib thickness"),
        p("DRAFT", F.DRAFT, "deg", "draft along the pull"),
        p("DRAFT_LOC", F.DRAFT_LOC, "deg", "draft of the panel locating faces and pegs"),
        p("FRAME_R", F.FRAME_R, "mm", "body outer corner radius"),
        p("POCKET_CLR", F.POCKET_CLR, "mm", "panel to pocket wall per side"),
        p("LEADIN", F.LEADIN, "mm", "45 deg lead-in at the pocket mouth"),
        p("SEAT_W", F.SEAT_W, "mm", "shelf reach inside the panel outline"),
        p("PCB_RIM_W", F.PCB_RIM_W, "mm", "PCB support ribs reach inside the panel outline"),
        p("SHELF_T", F.SHELF_T, "mm", "shelf thickness"),
        p("PAD_CLR", F.PAD_CLR, "mm", "PCB support >= this from any B.Cu pad"),
        p("SCREW_D", F.SCREW_D, "mm", "ST2.9 thread-forming screw"),
        p("PILOT_D", F.PILOT_D, "mm", "boss pilot hole"),
        p("BOSS_OD", F.BOSS_OD, "mm", "PCB boss OD at the top"),
        p("CBORE_D", F.CBORE_D, "mm", "relief at the pilot mouth"),
        p("CBORE_H", F.CBORE_H, "mm", "relief depth"),
        p("TROUGH_R", F.TROUGH_R, "mm", "tail-pocket inner corner radius"),
        p("LOOP_CLR", F.LOOP_CLR, "mm", "clearance around the FPC loop envelopes"),
        p("LOOP_Z", list(F.LOOP_Z), "mm", "Z range of the FPC loops"),
        # mounting (v1: eight feet, no flange)
        p("STUD_HOLE_D", F.FOOT_HOLE, "mm", "M4 stud clearance hole (v1 FOOT_HOLE)"),
        p("STUD_OD", F.FOOT_OD, "mm", "stud tube OD at the top (v1 FOOT_OD)"),
        p("STUD_H", F.FOOT_H, "mm", "v1: tube height above the feet plane (v1 FOOT_H)"),
        p("STUD_PAD_W", F.FOOT_PAD_W, "mm", "v1 foot pad plate width"),
        p("STUD_RIB_T", 0.0, "mm", "v1 has no radial rib (pad plate merges into the wall)"),
        p("FLANGE_W", 0.0, "mm", "v1 has no perimeter flange (feet pads only)"),
        p("FLANGE_T", F.WALL, "mm", "v1 foot pad plate thickness"),
        p("PEG_D", F.PEG_D, "mm", "locating peg dia"),
        p("PEG_H", F.PEG_H, "mm", "locating peg height"),
        p("PEG_SLOT", 0.0, "mm", "v1: both peg holes in the sheet round (no slot)"),
        p("STUD_SPEC", "PEM FH-M4-15", "", "v1 stud part number (alt. ISO 13918 weld stud M4x15)"),
        # derived plan geometry
        p("OUTER", list(F.OUTER), "mm", "body outline at Z_FRONT x0, x1, y0, y1 (abs)"),
        p("POCKET", list(F.POCKET), "mm", "panel pocket x0, x1, y0, y1 (abs)"),
        p("TROUGH", [F.TR_X0, F.TR_X1, F.TR_Y0, F.TR_Y1], "mm", "tail pocket x0, x1, y0, y1 (abs)"),
    ]
    levels = [
        p("Z_PCB", F.Z_PCB, "mm", "PCB back = boss tops = rib tops = wall top"),
        p("Z_SHELF_BACK", F.Z_SHELF_BACK, "mm", "shelf back face"),
        p("Z_SEAT", F.Z_SEAT, "mm", "shelf front face = Formex sheet back"),
        p("Z_PANEL_BACK", F.Z_PANEL_BACK, "mm", "panel back"),
        p("Z_GLASS", F.Z_GLASS, "mm", "cover glass front"),
        p("Z_FRONT", F.Z_FRONT, "mm", "feet plane = oven sheet inner face (v2: flange front)"),
        p("Z_FLANGE_BACK", F.Z_FRONT + F.WALL, "mm", "v1: foot pad plate back face"),
        p("Z_STUD_TOP", F.Z_FRONT + F.FOOT_H, "mm", "stud tube top = washer / nut seat"),
        p("Z_TROUGH_TOP", F.Z_TROUGH_TOP, "mm", "tail-pocket wall top (outside the board)"),
    ]
    feet = [{"name": k, "x": v[0], "y": v[1]} for k, v in F.FEET.items()]
    holes = [{"name": k, "x": v[0], "y": v[1]} for k, v in F.HOLES.items()]
    pegs = [{"name": k, "x": v[0], "y": v[1]} for k, v in F.PEG_POS.items()] if F.PEGS else []
    fr = summ["frame"]
    out = {
        "schema": "rev3-frame-params/1",
        "part": "Rev3.0 OVEN CONTROLLER carrier frame v1 (CadQuery, eight feet)",
        "source": "generated by make_v1_params.py from tools/frame/frame.py + tools/frame/out/summary.json",
        "units": {"length": "mm", "angle": "deg"},
        "coordinate_frame": "X = KiCad abs x, Y = -(KiCad abs y), Z = 0 at the physical PCB back, pull = Z; "
                            "all plan values in this file are KiCad abs (x, y down)",
        "parameters": params,
        "levels": levels,
        "stud_holes": feet,
        "pcb_holes": holes,
        "pegs": pegs,
        "body": {"volume_cm3": fr["volume_cm3"], "mass_g": fr["mass_g_1.36"], "bbox_model": fr["bbox"],
                 "support_ribs": fr["support_ribs"], "boss_base_d": summ["levels"]["boss_base_d"],
                 "stud_tube_base_d": F.FOOT_OD + 2 * F.FOOT_H * t},
        "checks": {"fit_min_component_mm": summ["fit"]["closest_components"][0]["min_dist"],
                   "slivers": len(summ["fit"]["slivers"]["slivers"]),
                   "faces": summ["fit"]["slivers"]["faces"]},
    }
    dst = os.path.join(HERE, "v1_params.json")
    json.dump(out, open(dst, "w"), indent=1)
    print("wrote", dst)


if __name__ == "__main__":
    main(sys.argv[1:])
