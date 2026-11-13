"""Build everything for the Rev3.0 carrier frame.

  <venv>\\Scripts\\python.exe build.py [--dump] [--no-render]

  --dump       re-read the board with KiCad's Python first (dump_board.py -> out/board_geom.json)
  --no-render  skip PNG renders / sections / drawing

Steps: (1) optional board dump, (2) board STEP export with every 3D model (kicad-cli, read-only),
(3) frame + Formex sheet + gasket, (4) Rev3.0_Frame.step/.stl, (5) Rev3.0_Assembly.step,
(6) fit check, (7) hand calculations, (8) renders + sections + 2D drawing + sheet DXF, (9) out/summary.json.
Outputs: <project>/Mechanical/Rev3.0_Frame/. The .kicad_pcb is never written.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadquery as cq

import frame as F
import fitcheck as FC
import calc as CALC

ROOT = os.path.normpath(os.path.join(HERE, r"..\..\..\.."))
PCB = os.path.join(ROOT, r"KiCad\3dFilamentDryer\3dFilamentDryer.kicad_pcb")
OUTDIR = os.path.join(ROOT, r"Mechanical\Rev3.0_Frame")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
KICAD_PY = r"C:\Program Files\KiCad\10.0\bin\python.exe"
TMP = os.environ.get("FRAME_TMP", os.path.join(tempfile.gettempdir(), "rev3_frame"))

COL_FRAME = (0.62, 0.64, 0.68)
COL_SHEET = (0.93, 0.92, 0.80)
COL_GASKET = (0.80, 0.30, 0.20)
COL_OVEN = (0.78, 0.80, 0.82)


def log(*a):
    print(*a, flush=True)


def colour(ref, part):
    p = part.lower()
    if ref == "PCB":
        return (0.10, 0.42, 0.20)
    if ref == "DS1":
        if "tail" in p:
            return (0.85, 0.55, 0.10)
        if "finger" in p:
            return (0.85, 0.68, 0.25)
        if "va" in p:
            return (0.05, 0.07, 0.12)
        if "cover" in p or "sensor" in p:
            return (0.70, 0.82, 0.88)
        return (0.45, 0.47, 0.50)
    if ref.startswith("HS"):
        return (0.12, 0.12, 0.14)
    if ref.startswith(("PS", "K", "U", "Q")):
        return (0.15, 0.15, 0.17)
    if ref.startswith(("C40", "L")):
        return (0.30, 0.30, 0.33)
    if ref.startswith(("J3", "J4", "R1")) and "Wire" in part:
        return (0.6, 0.15, 0.15)
    return (0.55, 0.55, 0.58)


def export_board_step(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [KICAD_CLI, "pcb", "export", "step", "--subst-models", "--user-origin", "0x0mm", "-f", "-o", path, PCB]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(path):
        raise RuntimeError("kicad-cli failed: " + r.stdout + r.stderr)
    return path


def write_assembly(board_step, extra, path):
    """Board STEP (KiCad export coordinates, colours and names kept) + extra parts moved by -BOARD_DZ."""
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorSurf
    from OCP.TDF import TDF_LabelSequence
    from OCP.TDataStd import TDataStd_Name
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    doc = FC.read_doc(board_step)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    labs = TDF_LabelSequence(); st.GetFreeShapes(labs)
    top = labs.Value(1)
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, -FC.BOARD_DZ))
    loc = TopLoc_Location(tr)
    for name, shp, rgb in extra:
        s = shp.val() if isinstance(shp, cq.Workplane) else shp
        lab = st.AddShape(s.wrapped, False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        ct.SetColor(lab, Quantity_Color(*rgb, Quantity_TOC_RGB), XCAFDoc_ColorSurf)
        comp = st.AddComponent(top, lab, loc)
        TDataStd_Name.Set_s(comp, TCollection_ExtendedString(name))
    TDataStd_Name.Set_s(top, TCollection_ExtendedString("Rev3.0_Assembly"))
    st.UpdateAssemblies()
    w = STEPCAFControl_Writer()
    w.SetColorMode(True); w.SetNameMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    w.Write(path)
    return path


def renders(frame, sheet, gasket, oven, items):
    import render as R
    import sections as SEC
    out = {}
    fpart = [("frame", frame, COL_FRAME, 1.0)]
    asm = [("frame", frame, COL_FRAME, 1.0), ("sheet", sheet, COL_SHEET, 1.0), ("gasket", gasket, COL_GASKET, 1.0)]
    for ref, part, s in items:
        asm.append(("%s:%s" % (ref, part), s, colour(ref, part), 1.0))
    jobs = [
        ("Frame_iso_front", fpart, "iso_front", "Carrier frame - iso, oven-front side (feet plane, panel pocket)"),
        ("Frame_iso_back", fpart, "iso_back", "Carrier frame - iso, component side (bosses, PCB support ribs, tail pocket)"),
        ("Frame_front", fpart, "front", "Carrier frame - front view (from in front of the oven)"),
        ("Frame_back", fpart, "back", "Carrier frame - back view (component side)"),
        ("Assembly_iso_front", asm, "iso_front", "Assembly - iso, oven-front side (glass, gasket, frame)"),
        ("Assembly_iso_back", asm, "iso_back", "Assembly - iso, component side"),
        ("Assembly_front", asm, "front", "Assembly - front view"),
        ("Assembly_back", asm, "back", "Assembly - back view (component side)"),
        ("Assembly_side", asm, "side", "Assembly - side view from the right (+X); oven front at the left"),
    ]
    for fn, parts, view, title in jobs:
        p = os.path.join(OUTDIR, fn + ".png")
        R.render(parts, p, view=view, title=title, size=(2000, 1400))
        out[fn] = p
        log("  render", fn)

    # sections (2D, filled)
    sec_parts = [("frame PA6-GF30", frame, COL_FRAME), ("Formex sheet", sheet, (0.85, 0.80, 0.30)),
                 ("gasket (compressed)", gasket, COL_GASKET), ("oven front sheet (patch)", oven, COL_OVEN)]
    grp = {}
    for ref, part, s in items:
        lab = "PCB" if ref == "PCB" else ("panel: tails" if (ref == "DS1" and "tail" in part.lower()) else
                                          ("panel" if ref == "DS1" else "components"))
        grp.setdefault(lab, []).append(s)
    cols = {"PCB": (0.10, 0.42, 0.20), "panel": (0.45, 0.55, 0.65), "panel: tails": (0.90, 0.55, 0.10),
            "components": (0.30, 0.30, 0.33)}
    for lab, ss in grp.items():
        sec_parts.append((lab, cq.Compound.makeCompound(ss), cols[lab]))
    hv = lambda x, y, z: (-y, z)            # horizontal = board y (abs, down = right), vertical = Z
    zf, z0 = F.Z_FRONT, F.Z_PCB
    # A: through H1 and H7 (x = 30)
    xA = F.HOLES["H1"][0]
    pA = os.path.join(OUTDIR, "Section_A_ear_bosses_x%.0f.png" % xA)
    SEC.section(sec_parts, "x", xA, pA, hv,
                "Section A-A at board x = %.1f through the ear bosses H1 (top) and H7 (bottom); left = top edge, "
                "down = oven front" % xA,
                xlim=(4, 160), ylim=(-16, 26),
                dims=[((14.2, zf), (14.2, z0), 9.5, "%.2f" % (z0 - zf), False),
                      ((24.0, F.Z_PANEL_BACK), (24.0, z0), 25.0, "%.2f stand-off" % (z0 - F.Z_PANEL_BACK), False),
                      ((30.0, F.Z_GLASS), (30.0, F.Z_PANEL_BACK), 31.0, "%.2f panel" % F.PANEL_T, False),
                      ((10.2, 3.5), (18.2, 3.5), 4.5, "boss %.1f" % F.BOSS_OD, True)],
                insets=[((6, 30), (-14, 6), [0.02, 0.50, 0.30, 0.48]), ((112, 132), (-14, 6), [0.68, 0.50, 0.30, 0.48])],
                figsize=(18, 8))
    out["Section_A"] = pA
    # B: through the TFT tail loop (x = 125)
    xB = 125.0
    pB = os.path.join(OUTDIR, "Section_B_tail_pocket_x%.0f.png" % xB)
    SEC.section(sec_parts, "x", xB, pB, hv,
                "Section B-B at board x = %.0f through the TFT tail U-loop and the tail pocket (front open to the "
                "oven sheet, back open for assembly)" % xB,
                xlim=(100, 158), ylim=(-16, 10),
                dims=[((F.LOOPS["TFT"][2], -5), (F.TR_Y1, -5), -6.5, "%.1f" % (F.TR_Y1 - F.LOOPS["TFT"][2]), True),
                      ((150, F.LOOP_Z[1]), (150, F.Z_TROUGH_TOP), 151, "%.1f" % F.LOOP_CLR, False),
                      ((150, F.Z_FRONT), (150, F.LOOP_Z[0]), 152.5, "%.2f to the sheet" % (F.LOOP_Z[0] - F.Z_FRONT), False)],
                figsize=(16, 7))
    out["Section_B"] = pB
    # C: plan section in the gasket mid-plane (feet plane + 0.35), front view
    zC = F.Z_FRONT + F.GASKET_T * (1 - F.GASKET_COMP) / 2
    xc, yc = (F.PX0 + F.PX1) / 2, (F.PY0 + F.PY1) / 2
    pC = os.path.join(OUTDIR, "Section_C_gasket_feet_plane.png")
    SEC.section(sec_parts, "z", zC, pC, lambda x, y, z: (-(x - xc), y + yc),
                "Section C-C in the gasket mid-plane Z = %.2f (feet plane + %.2f), seen from the oven front: "
                "feet, frame front, gasket ring, glass" % (zC, zC - F.Z_FRONT),
                figsize=(16, 12))
    out["Section_C"] = pC
    # D: through foot F2 with the oven sheet (x = F2)
    xD = F.FEET["F2"][0]
    pD = os.path.join(OUTDIR, "Section_D_foot_F2_x%.1f.png" % xD)
    SEC.section(sec_parts, "x", xD, pD, hv,
                "Section D-D at board x = %.1f through foot F2 (M4 stud), the gasket and the glass" % xD,
                xlim=(2, 40), ylim=(-15, 6), figsize=(14, 7),
                dims=[((12.0, F.Z_FRONT), (12.0, F.Z_FRONT + F.FOOT_H), 18.5, "foot %.1f" % F.FOOT_H, False),
                      ((24, F.Z_FRONT), (24, F.Z_GLASS), 26, "gasket %.2f" % (F.Z_GLASS - F.Z_FRONT), False)])
    out["Section_D"] = pD
    return out


def main(argv):
    t0 = time.time()
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    if "--dump" in argv or not os.path.exists(F.BOARD_GEOM):
        log("[1] dump_board.py (KiCad Python, read-only copy)")
        subprocess.run([KICAD_PY, os.path.join(HERE, "dump_board.py")], check=True)
    log("[2] board STEP export")
    board_step = export_board_step(os.path.join(TMP, "board_full.step"))
    log("[3] frame")
    frame, ribs, skipped = F.build_frame(log=log)
    sheet, gasket, oven = F.build_sheet(), F.build_gasket(), F.build_oven_sheet()
    log("[4] Rev3.0_Frame.step / .stl")
    cq.exporters.export(frame, os.path.join(OUTDIR, "Rev3.0_Frame.step"))
    cq.exporters.export(frame, os.path.join(OUTDIR, "Rev3.0_Frame.stl"), tolerance=0.02, angularTolerance=0.1)
    re = cq.importers.importStep(os.path.join(OUTDIR, "Rev3.0_Frame.step")).val()
    log("    re-import: valid=%s volume=%.1f" % (re.isValid(), re.Volume()))
    log("[5] Rev3.0_Assembly.step")
    write_assembly(board_step, [("Carrier frame PA6-GF30", frame, COL_FRAME),
                                ("Insulating sheet Formex 0.4", sheet, COL_SHEET),
                                ("Gasket silicone sponge (compressed)", gasket, COL_GASKET)],
                   os.path.join(OUTDIR, "Rev3.0_Assembly.step"))
    log("[6] fit check")
    fit, items = FC.run(board_step, frame, ribs, sheet, gasket, log=log)
    fit["slivers"] = FC.sliver_report(frame)
    log("    sliver faces: %d of %d" % (len(fit["slivers"]["slivers"]), fit["slivers"]["faces"]))
    fit["oven_sheet_vs_frame_overlap_mm3"] = round(FC.common_vol(frame.val(), oven.val()), 4)
    log("[7] calculations")
    calc = CALC.run()
    out = {}
    if "--no-render" not in argv:
        log("[8] renders, sections, drawing")
        out = renders(frame, sheet, gasket, oven, items)
        import drawing as D
        D.draw(frame, os.path.join(OUTDIR, "Rev3.0_Frame_Drawing.png"),
               os.path.join(OUTDIR, "Rev3.0_FrontSheet_Pattern.dxf"))
    fv = frame.val()
    bb = fv.BoundingBox()
    summ = {"frame": {"valid": fv.isValid(), "volume_cm3": round(fv.Volume() / 1000, 2),
                      "mass_g_1.36": round(fv.Volume() / 1000 * 1.36, 1),
                      "bbox": [round(v, 2) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)],
                      "size": [round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)],
                      "support_ribs": len(ribs), "skipped_ribs": skipped},
            "levels": F.summary(), "fit": fit, "calc": calc, "files": out, "seconds": round(time.time() - t0)}
    json.dump(summ, open(os.path.join(HERE, "out", "summary.json"), "w"), indent=1, default=str)
    log("done in %.0f s" % (time.time() - t0))
    return summ


if __name__ == "__main__":
    main(sys.argv[1:])
