"""Off-screen VTK renders of the frame (from its STEP) and of the assembly (PNG) - v1 render.py conventions.

  <venv>/Scripts/python.exe render_v2.py [--v1] [--frame f.step] [--params p.json] [--board b.step]

Frame_front / Frame_back / Frame_iso_front / Frame_iso_back, Assembly_iso_front / iso_back / front / back / side
with the board (every 3D model), the panel, the Formex sheet, the gasket (red), the M4 studs and the oven-sheet
patch (grey, translucent, with the window, stud and peg holes). Output: <Mechanical>/Rev3.0_Frame/renders_v2/
(--v1: renders_v2/v1_regression/). Views: cam = direction from the target to the camera, as v1:
  iso_front (-0.55, 0.45, -1) oven-front side from upper left; iso_back (-0.55, 0.45, 1) component side;
  front (0, 0, -1) looking at the glass (X mirrored); back (0, 0, 1); side (1, 0, 0) from the right (+X).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtk
import cadquery as cq

import common_v2 as C

COL_FRAME = (0.62, 0.64, 0.68)
COL_SHEET = (0.93, 0.92, 0.80)
COL_GASKET = (0.85, 0.15, 0.12)
COL_OVEN = (0.70, 0.72, 0.75)
COL_STUD = (0.55, 0.50, 0.40)
OVEN_OPACITY = 0.45
SIZE = (2000, 1400)
FIT_MARGIN = 1.04       # parallel scale = projected half-extent of all parts x this (nothing cropped)
TESS_FINE = (0.01, 0.08)      # frame (and studs): linear / angular tessellation tolerance - round tubes and slots
TESS_COARSE = (0.05, 0.2)     # board items

VIEWS = {  # cam = direction from the target to the camera
    "iso_front": dict(cam=(-0.55, 0.45, -1.0), up=(0, 1, 0)),
    "iso_back": dict(cam=(-0.55, 0.45, 1.0), up=(0, 1, 0)),
    "front": dict(cam=(0, 0, -1), up=(0, 1, 0)),
    "back": dict(cam=(0, 0, 1), up=(0, 1, 0)),
    "side": dict(cam=(1, 0, 0), up=(0, 1, 0)),
}
_PD = {}


def colour(ref, part):
    """v1 build.py colours"""
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


def _poly(shape, tess=TESS_COARSE):
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    k = (id(s.wrapped), tess)
    if k not in _PD:
        _PD[k] = (s, s.toVtkPolyData(tess[0], tess[1], True))
    return _PD[k][1]


def _fit_camera(ren, actors, v, size):
    """parallel camera along v['cam'] whose scale fits the projected bounds of every actor (no crop, no waste)"""
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
    cam.SetFocalPoint(*c)
    cam.SetPosition(*(c + d * dist))
    cam.SetViewUp(*up)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(max(hu, hr * size[1] / size[0]) * FIT_MARGIN + 0.03 * hu)   # + room for the title
    ren.ResetCameraClippingRange()


def render(parts, fname, view="iso_front", size=SIZE, title=None, zoom=1.0, parallel=True, edges=True):
    """parts: [(label, shape, rgb, opacity)]"""
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.SetUseDepthPeeling(1)
    ren.SetMaximumNumberOfPeels(8)
    actors = []
    for lbl, shp, rgb, op in parts:
        pd = _poly(shp, TESS_FINE if lbl in ("frame", "stud") else TESS_COARSE)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        a = vtk.vtkActor()
        a.SetMapper(m)
        p = a.GetProperty()
        p.SetColor(*rgb)
        p.SetOpacity(op)
        p.SetAmbient(0.25)
        p.SetDiffuse(0.75)
        p.SetSpecular(0.1)
        ren.AddActor(a)
        actors.append(a)
        if edges and (op > 0.9 or lbl.startswith("oven")):
            fe = vtk.vtkFeatureEdges()
            fe.SetInputData(pd)
            fe.BoundaryEdgesOn(); fe.FeatureEdgesOn(); fe.SetFeatureAngle(35)
            fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff()
            em = vtk.vtkPolyDataMapper(); em.SetInputConnection(fe.GetOutputPort()); em.ScalarVisibilityOff()
            ea = vtk.vtkActor(); ea.SetMapper(em)
            ea.GetProperty().SetColor(0.15, 0.15, 0.15); ea.GetProperty().SetLineWidth(1.0)
            ren.AddActor(ea)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetAlphaBitPlanes(1)
    win.SetMultiSamples(0)
    win.AddRenderer(ren)
    win.SetSize(*size)
    v = VIEWS[view]
    _fit_camera(ren, actors, v, size)
    if zoom != 1.0:
        ren.GetActiveCamera().Zoom(zoom)
        ren.ResetCameraClippingRange()
    kit = vtk.vtkLightKit(); kit.AddLightsToRenderer(ren)
    if title:
        ta = vtk.vtkTextActor(); ta.SetInput(title)
        tp = ta.GetTextProperty(); tp.SetFontSize(22); tp.SetColor(0.1, 0.1, 0.1)
        ta.SetDisplayPosition(15, size[1] - 40)
        ren.AddViewProp(ta)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(fname); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    win.Finalize()
    return fname


def run(ctx, log=C.log):
    os.makedirs(ctx.imgdir, exist_ok=True)
    aux = ctx.aux
    tag = "v2" if not ctx.v1 else "v1 (regression run of the v2 toolchain)"
    fpart = [("frame", ctx.frame, COL_FRAME, 1.0)]
    asm = [("frame", ctx.frame, COL_FRAME, 1.0), ("sheet", aux["sheet"], COL_SHEET, 1.0),
           ("gasket", aux["gasket"], COL_GASKET, 1.0)]
    asm += [("stud", s, COL_STUD, 1.0) for s in aux["studs"]]
    for ref, part, s in ctx.items:
        asm.append(("%s:%s" % (ref, part), s, colour(ref, part), 1.0))
    asm_oven = asm + [("oven sheet", aux["oven"], COL_OVEN, OVEN_OPACITY)]
    jobs = [
        ("Frame_iso_front", fpart, "iso_front", "Carrier frame %s - iso, oven-front side (flange face, panel pocket)" % tag),
        ("Frame_iso_back", fpart, "iso_back", "Carrier frame %s - iso, component side (bosses, ribs, stud tubes)" % tag),
        ("Frame_front", fpart, "front", "Carrier frame %s - front view (from in front of the oven)" % tag),
        ("Frame_back", fpart, "back", "Carrier frame %s - back view (component side)" % tag),
        ("Assembly_iso_front", asm_oven, "iso_front",
         "Assembly %s - iso, oven-front side (oven sheet translucent, gasket red)" % tag),
        ("Assembly_iso_back", asm_oven, "iso_back", "Assembly %s - iso, component side (studs, oven sheet)" % tag),
        ("Assembly_front", asm_oven, "front", "Assembly %s - front view through the translucent oven sheet" % tag),
        ("Assembly_back", asm_oven, "back", "Assembly %s - back view (component side)" % tag),
        ("Assembly_side", asm_oven, "side", "Assembly %s - side view from the right (+X); oven front at the left" % tag),
    ]
    out = {}
    for fn, parts, view, title in jobs:
        p = os.path.join(ctx.imgdir, fn + ".png")
        render(parts, p, view=view, title=title)
        out[fn] = p
        log("  render", fn)
    return out


if __name__ == "__main__":
    run(C.Context(sys.argv[1:]))
