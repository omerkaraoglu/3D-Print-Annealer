"""Off-screen VTK renders of the frame STEP and of the independently built assembly (v2 render conventions).

  <venv>\\Scripts\\python.exe render_gf.py [--frame f.step] [--img dir]

Frame_front / Frame_back / Frame_iso_front / Frame_iso_back; Assembly_iso_front / Assembly_iso_back /
Assembly_front / Assembly_side (frame, glass, bead, VHB strips, Formex, S4 studs + washers + nuts, oven sheet
translucent, the board with every model and DS1 moved with the panel). Output: Mechanical/Rev3.0_GlassFront/renders/verify/
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtk
import cadquery as cq

import vcommon as C

COL = {"frame": (0.30, 0.31, 0.34), "glass": (0.10, 0.16, 0.22), "bead": (0.85, 0.15, 0.12), "tape": (0.95, 0.75, 0.10),
       "formex": (0.93, 0.92, 0.80), "hw": (0.75, 0.72, 0.62), "sheet": (0.80, 0.81, 0.84), "loca": (0.6, 0.85, 0.95)}
SIZE = (2000, 1400)
FIT_MARGIN = 1.04
TESS_FINE = (0.01, 0.08)
TESS_COARSE = (0.05, 0.2)
VIEWS = {"iso_front": dict(cam=(-0.55, 0.45, -1.0), up=(0, 1, 0)), "iso_back": dict(cam=(-0.55, 0.45, 1.0), up=(0, 1, 0)),
         "front": dict(cam=(0, 0, -1), up=(0, 1, 0)), "back": dict(cam=(0, 0, 1), up=(0, 1, 0)),
         "side": dict(cam=(1, 0, 0), up=(0, 1, 0)), "iso_low": dict(cam=(-0.35, -0.85, -0.6), up=(0, 0, -1))}
_PD = {}


def board_colour(ref, part):
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
    if ref.startswith(("HS", "PS", "K", "U", "Q")):
        return (0.15, 0.15, 0.17)
    return (0.55, 0.55, 0.58)


def _poly(shape, tess):
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    k = (id(s.wrapped), tess)
    if k not in _PD:
        _PD[k] = (s, s.toVtkPolyData(tess[0], tess[1], True))
    return _PD[k][1]


def _fit_camera(ren, actors, v, size):
    import numpy as np
    corners = []
    for a in actors:
        b = a.GetBounds()
        corners += [(x, y, z) for x in b[0:2] for y in b[2:4] for z in b[4:6]]
    P = np.array(corners)
    c = (P.min(axis=0) + P.max(axis=0)) / 2
    d = np.array(v["cam"], float); d /= np.linalg.norm(d)
    up = np.array(v["up"], float); up = up - up.dot(d) * d; up /= np.linalg.norm(up)
    right = np.cross(up, d)
    hu = np.abs((P - c).dot(up)).max()
    hr = np.abs((P - c).dot(right)).max()
    dist = 3 * np.linalg.norm(P.max(axis=0) - P.min(axis=0)) + 1
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*c); cam.SetPosition(*(c + d * dist)); cam.SetViewUp(*up)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(max(hu, hr * size[1] / size[0]) * FIT_MARGIN + 0.03 * hu)
    ren.ResetCameraClippingRange()


def render(parts, fname, view, title=None, size=SIZE, zoom=1.0):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.SetUseDepthPeeling(1); ren.SetMaximumNumberOfPeels(8)
    actors = []
    for lbl, shp, rgb, op in parts:
        pd = _poly(shp, TESS_FINE if lbl.startswith(("frame", "hw")) else TESS_COARSE)
        m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
        a = vtk.vtkActor(); a.SetMapper(m)
        p = a.GetProperty(); p.SetColor(*rgb); p.SetOpacity(op); p.SetAmbient(0.25); p.SetDiffuse(0.75); p.SetSpecular(0.15)
        ren.AddActor(a); actors.append(a)
        if op > 0.9 and lbl.startswith(("frame", "glass", "hw")):
            fe = vtk.vtkFeatureEdges(); fe.SetInputData(pd)
            fe.BoundaryEdgesOn(); fe.FeatureEdgesOn(); fe.SetFeatureAngle(35); fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff()
            em = vtk.vtkPolyDataMapper(); em.SetInputConnection(fe.GetOutputPort()); em.ScalarVisibilityOff()
            ea = vtk.vtkActor(); ea.SetMapper(em); ea.GetProperty().SetColor(0.85, 0.85, 0.85) if lbl.startswith("frame") else \
                ea.GetProperty().SetColor(0.15, 0.15, 0.15)
            ea.GetProperty().SetLineWidth(1.0)
            ren.AddActor(ea)
    win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.SetAlphaBitPlanes(1); win.SetMultiSamples(0)
    win.AddRenderer(ren); win.SetSize(*size)
    _fit_camera(ren, actors, VIEWS[view], size)
    if zoom != 1.0:
        ren.GetActiveCamera().Zoom(zoom); ren.ResetCameraClippingRange()
    kit = vtk.vtkLightKit(); kit.AddLightsToRenderer(ren)
    if title:
        ta = vtk.vtkTextActor(); ta.SetInput(title)
        tp = ta.GetTextProperty(); tp.SetFontSize(24); tp.SetColor(0.1, 0.1, 0.1)
        ta.SetDisplayPosition(15, size[1] - 42); ren.AddViewProp(ta)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(fname); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    win.Finalize()
    return fname


DRAFT_CLASSES = [("flagged < 0.25 deg (no draft)", (0.90, 0.10, 0.10)), ("0.25-0.75 deg (0.5 deg locating faces)", (0.98, 0.60, 0.10)),
                 ("0.75-1.25 deg (1 deg rule)", (0.20, 0.70, 0.30)), ("1.25-10 deg", (0.10, 0.65, 0.75)),
                 ("> 10 deg (chamfers, rounds, cones)", (0.25, 0.35, 0.85)), ("horizontal / fillet blends", (0.80, 0.80, 0.82))]


def _draft_class(d, flagged):
    if flagged:
        return 0
    if d is None:
        return 5
    if d < 0.25:
        return 0
    if d < 0.75:
        return 1
    if d < 1.25:
        return 2
    if d < 10.0:
        return 3
    return 4


def draft_map(ctx, per_face, size=(2600, 1300)):
    """two orthographic views of the frame (front = from -Z, back = from +Z), every face coloured by its draft class
    (mould_check.draft per_face: plane angle / cone semi-angle / sampled minimum for other surfaces)"""
    fr = ctx.frame
    faces = fr.Faces()
    app = vtk.vtkAppendPolyData()
    for fi, d, k, flg in per_face:
        pd = faces[fi].toVtkPolyData(0.02, 0.2, True)
        cls = _draft_class(d, flg)
        arr = vtk.vtkUnsignedCharArray(); arr.SetNumberOfComponents(3); arr.SetName("col")
        rgb = [int(255 * c) for c in DRAFT_CLASSES[cls][1]]
        for _ in range(pd.GetNumberOfCells()):
            arr.InsertNextTuple3(*rgb)
        pd.GetCellData().SetScalars(arr)
        app.AddInputData(pd)
    app.Update()
    win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.SetSize(*size)
    for k_, (view, vp) in enumerate((("iso_front", (0.0, 0.0, 0.5, 1.0)), ("iso_back", (0.5, 0.0, 1.0, 1.0)))):
        ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1); ren.SetViewport(*vp)
        m = vtk.vtkPolyDataMapper(); m.SetInputConnection(app.GetOutputPort()); m.SetScalarModeToUseCellData()
        a = vtk.vtkActor(); a.SetMapper(m); a.GetProperty().SetAmbient(0.35); a.GetProperty().SetDiffuse(0.7)
        ren.AddActor(a)
        win.AddRenderer(ren)
        _fit_camera(ren, [a], VIEWS[view], (size[0] // 2, size[1]))
        kit = vtk.vtkLightKit(); kit.AddLightsToRenderer(ren)
        ta = vtk.vtkTextActor(); ta.SetInput("Draft map %s - %s (%s); face colour = draft against the pull Z" % (
            str(ctx.G.revision).split(" ")[0], view.replace("_", " "), "front side, -Z" if view == "iso_front" else "back side, +Z"))
        ta.GetTextProperty().SetFontSize(24); ta.GetTextProperty().SetColor(0.1, 0.1, 0.1)
        ta.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport(); ta.SetPosition(0.02, 0.95)
        ren.AddViewProp(ta)
        if k_ == 0:
            for j, (lab, rgb) in enumerate(DRAFT_CLASSES):
                n = sum(1 for fi, d, kk, flg in per_face if _draft_class(d, flg) == j)
                t = vtk.vtkTextActor(); t.SetInput("%s: %d faces" % (lab, n))
                t.GetTextProperty().SetFontSize(22); t.GetTextProperty().SetColor(*rgb); t.GetTextProperty().BoldOn()
                t.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport(); t.SetPosition(0.02, 0.02 + 0.03 * (len(DRAFT_CLASSES) - j))
                ren.AddViewProp(t)
    win.Render()
    fname = os.path.join(ctx.imgdir, "Draft_map_%s.png" % str(ctx.G.revision).split(" ")[0])
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(fname); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    win.Finalize()
    return fname


def run(ctx, log=C.log):
    import fit_check as F
    os.makedirs(ctx.imgdir, exist_ok=True)
    G = ctx.G
    import tails_gf2 as TG
    A = F.build(G)
    hw = F.hardware(G, "S4")
    tag = "glass-front frame %s (STEP %s, sha %s)" % (G.revision.split(" ")[0], ctx.frame_info["mtime"], ctx.frame_info["sha256"][:10])
    fpart = [("frame", ctx.frame, COL["frame"], 1.0)]
    tails = []
    if G.tail_route:
        for n in ("TFT", "CTP"):
            tails += [("tail %s" % lab, s, (0.90, 0.55, 0.10), 1.0) for lab, s, _ in TG.tail_solids(G, n)]
    asm = [("frame", ctx.frame, COL["frame"], 1.0), ("glass", A["glass"], COL["glass"], 0.55), ("bead", A["bead"], COL["bead"], 1.0),
           ("formex", A["formex"], COL["formex"], 1.0)]
    asm += [("tape", A[k], COL["tape"], 1.0) for k in ("tape_top", "tape_bottom", "tape_left", "tape_right")]
    asm += [("hw " + k, s, COL["hw"], 1.0) for k, s in hw.items()]
    asm += tails
    for ref, part, s in ctx.items:
        if G.tail_route and ref == "DS1" and part.startswith(C.PANEL_TAIL_PARTS):
            continue            # GF-2.0: the DS1 model still carries the GF-1.1 tail route; replaced by the tails built here
        asm.append(("%s:%s" % (ref, part), s, board_colour(ref, part), 1.0))
    asm_sheet = asm + [("sheet", A["sheet"], COL["sheet"], 0.35)]
    rv = G.revision.split(" ")[0]
    jobs = [("Frame_front", fpart, "front", "Frame - front view (as seen from the oven front): " + tag),
            ("Frame_back", fpart, "back", "Frame - back view (component side): " + tag),
            ("Frame_iso_front", fpart, "iso_front", "Frame - iso, front side (lip, seat ring, pads, flange, recess, pips): " + tag),
            ("Frame_iso_back", fpart, "iso_back", "Frame - iso, back side (tubes, ribs, bosses, cells, tail pocket, bridge, divider rib): " + tag),
            ("Assembly_iso_front", asm_sheet, "iso_front", "Independent assembly from the params - iso front (sheet translucent, glass translucent, bead red, VHB yellow)"),
            ("Assembly_iso_back", asm_sheet, "iso_back", "Independent assembly - iso back (S4 studs, washers, nuts; PCB with every model; %s tails built here)" % rv),
            ("Assembly_front", asm_sheet, "front", "Independent assembly - front view through the translucent sheet and glass"),
            ("Assembly_side", asm_sheet, "side", "Independent assembly - side view from +X (oven front sheet at the right, PCB components at the left)")]
    if G.gf2:
        clip = C.box(30.0, 176.0, -153.0, -112.0, -16.0, 6.0)
        fz = C.common_shape(ctx.frame, clip)
        near = [(lab, C.common_shape(s, clip), col, op) for lab, s, col, op in asm
                if lab.startswith(("glass", "bead", "PCB", "J10", "J11", "DS1:lcm", "DS1:sensor", "DS1:cover", "formex"))]
        near = [p for p in near if p[1].Solids()]
        close = [("frame", fz, COL["frame"], 1.0)] + tails + near
        jobs += [("Bridge_tails_closeup_iso_back", close, "iso_back",
                  "Bottom zone x 30-176 (clipped): bridge, nose, divider rib, tail pocket; TFT / CTP tails on the %s route (built here), PCB, J10 / J11" % rv),
                 ("Bridge_tails_closeup_iso_low", close, "iso_low",
                  "Bottom zone from below the panel edge: bend-gap slot, bridge, tails folded back over the R1.5 nose")]
    out = {}
    for fn, parts, view, title in jobs:
        p = os.path.join(ctx.imgdir, fn + ".png")
        render(parts, p, view, title)
        out[fn] = p
        log("  render", fn)
    return out


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    _ = ctx.frame
    run(ctx)
