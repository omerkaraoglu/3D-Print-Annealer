"""Off-screen renders and section geometry for the GF-2.1 overview PDF (CadQuery / OCP / VTK).

    <cq-venv>\\Scripts\\python.exe -B render_overview.py            # everything
    <cq-venv>\\Scripts\\python.exe -B render_overview.py parts hero  # only some jobs

Reads (never writes) Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Assembly.step and writes into
Mechanical/Rev3.0_GlassFront/renders/overview/:
  <name>.png       shaded render, light background
  <name>_id.png    flat-colour id buffer of the same view (one colour per part key, used by the PDF builder to
                   put balloons and labels on free background next to what they point at)
  <name>.json      view record: id colours -> part keys, pixel boxes, projected anchor points
  sections.json    planar sections of the assembly (polygons per body, h / Z in mm) for the vector section figures

Every body is taken from the assembly STEP as Fusion exported it (GF-2.1, Fusion version 19); the only things
done here are grouping the bodies into BOM items, moving whole bodies for exploded views, colouring and cutting.
"""
import json
import os
import sys
import time

sys.dont_write_bytecode = True
import numpy as np
import vtk
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_SOLID, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Trsf, gp_Vec

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
ASM = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_Assembly.step")
OUT = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "renders", "overview")
MASTER = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
DRAFT = os.path.join(ROOT, "Design Reports", "Rev3.0", "tools", "glassfront", "drawings", "drafting_choices.json")

# ----------------------------------------------------------------------------------------------- loading
def _name(lab):
    a = TDataStd_Name()
    return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else "?"


def load_assembly(path=ASM):
    """[(path, leaf name, TopoDS_Solid in model coordinates)] for every solid instance of the STEP"""
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    r = STEPCAFControl_Reader(); r.SetNameMode(True); r.SetColorMode(True)
    if r.ReadFile(path) != IFSelect_RetDone:
        raise SystemExit("cannot read " + path)
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    out = []

    def walk(lab, loc, pth):
        if st.IsAssembly_s(lab):
            comps = TDF_LabelSequence(); st.GetComponents_s(lab, comps)
            for i in range(1, comps.Length() + 1):
                c = comps.Value(i)
                ref = TDF_Label(); st.GetReferredShape_s(c, ref)
                walk(ref, loc.Multiplied(st.GetLocation_s(c)), pth + [_name(c)])
        else:
            shp = st.GetShape_s(lab).Moved(loc)
            ex = TopExp_Explorer(shp, TopAbs_SOLID)
            while ex.More():
                out.append(("/".join(pth), _name(lab), ex.Current()))
                ex.Next()
    top = TDF_LabelSequence(); st.GetFreeShapes(top)
    for i in range(1, top.Length() + 1):
        walk(top.Value(i), TopLoc_Location(), [_name(top.Value(i))])
    return out


def bbox(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b)
    return b.Get()


# BOM item keys (the PDF uses the same keys; numbers and names live in overview_content.json)
def classify(pth, name, s):
    """-> (key, sub) for one solid of the assembly STEP"""
    p = pth
    if "Frame GF" in p:
        return "frame", "frame"
    if "/Glass:" in p:
        z0, z1 = bbox(s)[2], bbox(s)[5]
        return "glass", ("print" if (z1 - z0) < 0.1 else "glass")
    if "Optical bond" in p:
        return "loca", "loca"
    if "Formex" in p:
        return "formex", "formex"
    if "/Bead:" in p:
        return "bead", "bead"
    if "VHB" in p:
        return "tape", "tape"
    if "Oven sheet" in p:
        return "sheet", "sheet"
    if "Weld studs" in p:
        return "stud", "stud"
    if "Washers + nyloc" in p:
        z0, z1 = bbox(s)[2], bbox(s)[5]
        return ("washer", "washer") if (z1 - z0) < 1.5 else ("nut", "nut")
    if "Tails GF-2.0" in p:
        return "panel", "tail"
    if "TFT7_SAT070AT40D21" in p:
        return "panel", name.split("_")[0] if "_" in name else name
    if "PCB full" in p:
        if p.endswith("3dFilamentDryer_PCB:1") or "3dFilamentDryer_PCB" in p.split("/")[-1]:
            return "pcb", "board"
        return "pcb", "component:" + p.split("/")[3] if len(p.split("/")) > 3 else "component"
    return "other", name


# ----------------------------------------------------------------------------------------------- colours
COL = {
    "frame": (0.30, 0.31, 0.34), "glass": (0.80, 0.88, 0.92), "print": (0.04, 0.04, 0.05), "loca": (0.55, 0.85, 0.95),
    "formex": (0.93, 0.91, 0.80), "bead": (0.80, 0.18, 0.14), "tape": (0.96, 0.72, 0.16), "sheet": (0.80, 0.81, 0.83),
    "stud": (0.80, 0.62, 0.42), "washer": (0.78, 0.79, 0.81), "nut": (0.74, 0.75, 0.78), "tail": (0.88, 0.58, 0.14),
    "lcm": (0.62, 0.63, 0.66), "pu": (0.08, 0.08, 0.09), "sensor": (0.55, 0.70, 0.80), "cover": (0.05, 0.05, 0.06),
    "board": (0.10, 0.42, 0.22),
}
OPA = {"glass": 0.30, "loca": 0.55}


def colour(key, sub):
    if key == "panel":
        for k in ("tail", "lcm", "pu", "sensor", "cover"):
            if sub.startswith(k):
                return COL[k]
        return COL["lcm"]
    if key == "pcb":
        if sub == "board":
            return COL["board"]
        ref = sub.split(":")[-1]
        if ref.startswith(("Heatsink", "TO-220", "Relay", "Converter", "LQFP", "ESP32")):
            return (0.22, 0.22, 0.25)
        if ref.startswith(("C_Rect", "RV_", "L_Radial")):
            return (0.25, 0.32, 0.55)
        if ref.startswith(("TerminalBlock",)):
            return (0.20, 0.55, 0.30)
        if ref.startswith(("Connfly", "KLS")):
            return (0.90, 0.86, 0.74)
        if ref.startswith(("Fuse",)):
            return (0.75, 0.75, 0.78)
        return (0.55, 0.55, 0.58)
    return COL.get(sub, COL.get(key, (0.6, 0.6, 0.6)))


# ----------------------------------------------------------------------------------------------- tessellation
_PD = {}


def polydata(s, fine=False):
    """triangle mesh from OCC's own face triangulation (cq.Shape.tessellate), normals split at 35 deg so that
    flat faces stay flat and edges stay crisp (the IVtk path left a stray fan on the 0.02 print layer)"""
    k = (id(s), fine)
    if k not in _PD:
        tol = (0.01, 0.1) if fine else (0.05, 0.25)
        v, tris = cq.Shape.cast(s).tessellate(tol[0], tol[1])
        pts = vtk.vtkPoints()
        for p in v:
            pts.InsertNextPoint(p.x, p.y, p.z)
        cells = vtk.vtkCellArray()
        for a, b, c in tris:
            cells.InsertNextCell(3); cells.InsertCellPoint(a); cells.InsertCellPoint(b); cells.InsertCellPoint(c)
        pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
        nf = vtk.vtkPolyDataNormals(); nf.SetInputData(pd); nf.SetFeatureAngle(35); nf.SplittingOn()
        nf.ConsistencyOn(); nf.AutoOrientNormalsOff(); nf.Update()
        _PD[k] = nf.GetOutput()
    return _PD[k]


def moved(pd, off):
    if not any(off):
        return pd
    t = vtk.vtkTransform(); t.Translate(*off)
    f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(t); f.SetInputData(pd); f.Update()
    return f.GetOutput()


# ----------------------------------------------------------------------------------------------- render
VIEWS = {
    "iso_front": ((-0.55, 0.45, -1.0), (0, 1, 0)),
    "iso_front_low": ((-0.65, -0.30, -1.0), (0, 1, 0)),
    "iso_back": ((-0.55, 0.45, 1.0), (0, 1, 0)),
    "iso_back_r": ((0.60, 0.50, 1.0), (0, 1, 0)),
    "front": ((0, 0, -1), (0, 1, 0)),
    "back": ((0, 0, 1), (0, 1, 0)),
    "explode": ((-1.25, 0.50, -0.72), (0, 1, 0)),
    "explode_back": ((-1.0, 0.55, 0.80), (0, 1, 0)),
    "j2": ((-0.60, -1.0, 0.32), (0, 0, 1)),
    "stud": ((-0.8, 0.6, 0.9), (0, 1, 0)),
    "gauge": ((-0.55, -0.9, 0.75), (0, 0, 1)),
}
BG = (1.0, 1.0, 1.0)


def _camera(ren, pts, view, size, margin):
    d = np.array(VIEWS[view][0], float); d /= np.linalg.norm(d)
    up = np.array(VIEWS[view][1], float); up = up - up.dot(d) * d; up /= np.linalg.norm(up)
    right = np.cross(up, d)
    P = np.asarray(pts)
    c = (P.min(axis=0) + P.max(axis=0)) / 2
    hu = np.abs((P - c).dot(up)).max()
    hr = np.abs((P - c).dot(right)).max()
    # centre the projected extents (not the 3D box centre) so the picture fills the frame evenly
    cu = ((P - c).dot(up).max() + (P - c).dot(up).min()) / 2
    cr = ((P - c).dot(right).max() + (P - c).dot(right).min()) / 2
    c = c + up * cu + right * cr
    hu = np.abs((P - c).dot(up)).max(); hr = np.abs((P - c).dot(right)).max()
    dist = 3 * np.linalg.norm(P.max(axis=0) - P.min(axis=0)) + 10
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*c); cam.SetPosition(*(c + d * dist)); cam.SetViewUp(*up)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(max(hu, hr * size[1] / size[0]) * margin)
    ren.ResetCameraClippingRange()


def render(name, items, view, size=(1800, 1300), margin=1.06, edges=True, anchors=None, ssao=False):
    """items: [(key, sub, solid, offset(3), rgb or None, opacity or None)]; anchors: {label: (x, y, z)} model points
    (already offset) projected to pixel coordinates in the record"""
    os.makedirs(OUT, exist_ok=True)
    keys = []
    for it in items:
        if it[0] not in keys:
            keys.append(it[0])
    idcol = {k: ((37 * (i + 1)) % 256, (91 * (i + 3)) % 256, (157 * (i + 5)) % 256) for i, k in enumerate(keys)}
    pts = []
    pds = []
    for key, sub, s, off, rgb, op in items:
        pd = moved(polydata(s, fine=key in ("frame", "stud", "washer", "nut", "glass")), off)
        b = pd.GetBounds()
        pts += [(x, y, z) for x in b[0:2] for y in b[2:4] for z in b[4:6]]
        pds.append((key, sub, pd, rgb or colour(key, sub), op if op is not None else OPA.get(sub, 1.0)))

    def build(id_pass):
        ren = vtk.vtkRenderer(); ren.SetBackground(*BG)
        if not id_pass:
            ren.SetUseDepthPeeling(1); ren.SetMaximumNumberOfPeels(12); ren.SetOcclusionRatio(0.0)
        for key, sub, pd, rgb, op in pds:
            m = vtk.vtkPolyDataMapper(); m.SetInputData(pd); m.ScalarVisibilityOff()
            a = vtk.vtkActor(); a.SetMapper(m); p = a.GetProperty()
            if id_pass:
                # every body is opaque in the id buffer: a key owns the pixels where it is the front-most body
                c = idcol[key]
                p.SetColor(c[0] / 255, c[1] / 255, c[2] / 255); p.LightingOff(); p.SetAmbient(1); p.SetDiffuse(0)
                p.SetInterpolationToFlat()
            else:
                p.SetColor(*rgb); p.SetOpacity(op); p.SetAmbient(0.22); p.SetDiffuse(0.78)
                p.SetSpecular(0.35 if sub in ("glass", "stud", "washer", "nut", "print") else 0.12)
                p.SetSpecularPower(40)
            ren.AddActor(a)
            if edges and not id_pass and op > 0.9 and key in ("frame", "stud", "washer", "nut", "sheet"):
                fe = vtk.vtkFeatureEdges(); fe.SetInputData(pd)
                fe.BoundaryEdgesOn(); fe.FeatureEdgesOn(); fe.SetFeatureAngle(40); fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff()
                em = vtk.vtkPolyDataMapper(); em.SetInputConnection(fe.GetOutputPort()); em.ScalarVisibilityOff()
                ea = vtk.vtkActor(); ea.SetMapper(em)
                ea.GetProperty().SetColor(*((0.55, 0.56, 0.60) if key == "frame" else (0.35, 0.35, 0.38)))
                ea.GetProperty().SetLineWidth(1.2); ea.GetProperty().LightingOff()
                ren.AddActor(ea)
        win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.SetMultiSamples(0)
        win.AddRenderer(ren); win.SetSize(*size)
        _camera(ren, pts, view, size, margin)
        if not id_pass:
            kit = vtk.vtkLightKit(); kit.SetKeyLightIntensity(1.0); kit.SetKeyToFillRatio(2.2); kit.AddLightsToRenderer(ren)
            ren.SetUseFXAA(True)
            if ssao:
                ren.SetUseSSAO(True); ren.SetSSAORadius(4.0); ren.SetSSAOKernelSize(64)
        win.Render()
        return win, ren

    rec = {"name": name, "view": view, "size": list(size), "keys": {}, "anchors": {}}
    for id_pass in (False, True):
        win, ren = build(id_pass)
        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.SetInputBufferTypeToRGB(); w2i.Update()
        wr = vtk.vtkPNGWriter(); wr.SetFileName(os.path.join(OUT, name + ("_id.png" if id_pass else ".png")))
        wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
        if not id_pass and anchors:
            co = vtk.vtkCoordinate(); co.SetCoordinateSystemToWorld()
            for lab, p in anchors.items():
                co.SetValue(*p)
                x, y = co.GetComputedDoubleDisplayValue(ren)
                rec["anchors"][lab] = [round(x, 1), round(size[1] - y, 1)]
        win.Finalize()
    for k, c in idcol.items():
        rec["keys"][k] = list(c)
    json.dump(rec, open(os.path.join(OUT, name + ".json"), "w"), indent=1)
    print("  wrote", name, flush=True)
    return rec


# ----------------------------------------------------------------------------------------------- sections
def _edge_pts(e, defl=0.003):
    c = BRepAdaptor_Curve(e)
    d = GCPnts_QuasiUniformDeflection(c, defl)
    if not d.IsDone() or d.NbPoints() < 2:
        p0, p1 = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
        return np.array([[p0.X(), p0.Y(), p0.Z()], [p1.X(), p1.Y(), p1.Z()]])
    return np.array([[d.Value(i).X(), d.Value(i).Y(), d.Value(i).Z()] for i in range(1, d.NbPoints() + 1)])


def _wire_loop(w):
    ex = BRepTools_WireExplorer(w)
    out = []
    while ex.More():
        e = ex.Current()
        p = _edge_pts(e)
        if e.Orientation() == TopAbs_REVERSED:
            p = p[::-1]
        out.append(p if not out else p[1:])
        ex.Next()
    return np.vstack(out) if out else np.zeros((0, 3))


def section(solids, axis, value, window):
    """planar section of every solid whose box crosses the plane and the window
    axis 'x': plane x = value, h = model -Y = abs y; axis 'y': plane model Y = -value (abs y = value), h = abs x
    window = (h0, h1, z0, z1); returns [{key, sub, loops: [[[h, z]...] outer, holes...]}]"""
    res = []
    for key, sub, s in solids:
        b = bbox(s)
        lo, hi = (b[0], b[3]) if axis == "x" else (b[1], b[4])
        pv = value if axis == "x" else -value
        if pv < lo - 1e-6 or pv > hi + 1e-6:
            continue
        hb = (-b[4], -b[1]) if axis == "x" else (b[0], b[3])
        if hb[1] < window[0] or hb[0] > window[1] or b[5] < window[2] or b[2] > window[3]:
            continue
        n = (1, 0, 0) if axis == "x" else (0, 1, 0)
        p = (pv, 0, 0) if axis == "x" else (0, pv, 0)
        face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*p), gp_Dir(*n)), -3000, 3000, -3000, 3000).Face()
        op = BRepAlgoAPI_Common(s, face); op.Build()
        if not op.IsDone():
            continue
        r = cq.Shape.cast(op.Shape())
        for f in r.Faces():
            loops = []
            for w in [f.outerWire()] + list(f.innerWires()):
                L = _wire_loop(w.wrapped)
                if len(L) < 3:
                    continue
                hz = np.column_stack([-L[:, 1], L[:, 2]]) if axis == "x" else np.column_stack([L[:, 0], L[:, 2]])
                loops.append([[round(a, 4), round(c, 4)] for a, c in hz])
            if loops:
                res.append({"key": key, "sub": sub, "loops": loops})
    return res


# ----------------------------------------------------------------------------------------------- jobs
def main(jobs):
    t0 = time.time()
    raw = load_assembly()
    S = [(classify(p, n, s)[0], classify(p, n, s)[1], s) for p, n, s in raw]
    os.makedirs(OUT, exist_ok=True)
    census = {}
    for k, sub, s in S:
        census.setdefault(k, 0); census[k] += 1
    print("solids:", len(S), census, "%.1fs" % (time.time() - t0), flush=True)
    json.dump({"step": os.path.relpath(ASM, ROOT).replace("\\", "/"), "solid_instances": len(S), "by_item": census,
               "bodies": [{"path": p, "name": n, "item": classify(p, n, s)[0], "sub": classify(p, n, s)[1]}
                          for p, n, s in raw]},
              open(os.path.join(OUT, "assembly_census.json"), "w"), indent=0)

    def sel(*keys, sub=None, excl=()):
        return [(k, sb, s) for k, sb, s in S if k in keys and (sub is None or sb.startswith(sub)) and not sb.startswith(excl)]

    def items(lst, off=(0, 0, 0), rgb=None, op=None):
        return [(k, sb, s, off, rgb, op) for k, sb, s in lst]

    if "parts" in jobs or "all" in jobs:
        jobs_parts = [
            ("part_panel", sel("panel"), "iso_front_low"),
            ("part_loca", sel("loca"), "iso_front"),
            ("part_frame_front", sel("frame"), "iso_front"),
            ("part_frame_back", sel("frame"), "iso_back"),
            ("part_bead", sel("bead"), "iso_front"),
            ("part_tape", sel("tape"), "iso_front"),
            ("part_formex", sel("formex"), "iso_front"),
            ("part_sheet", sel("sheet") + sel("stud"), "iso_back"),
            ("part_pcb", sel("pcb"), "iso_back_r"),
        ]
        for name, lst, view in jobs_parts:
            render(name, items(lst), view, size=(1500, 1100), margin=1.04)
        # the glass alone: clear glass, black print on its inner face
        render("part_glass", items(sel("glass", sub="glass"), rgb=(0.86, 0.91, 0.94), op=0.25) +
               items(sel("glass", sub="print"), rgb=(0.0, 0.0, 0.0)), "iso_front", size=(1500, 1100), margin=1.04)
        # one fastener of each kind, alone (F1 = the top-left one in KiCad coordinates)
        for name, key in (("part_stud", "stud"), ("part_washer", "washer"), ("part_nut", "nut")):
            lst = sel(key)
            lst = sorted(lst, key=lambda t: (bbox(t[2])[0] + bbox(t[2])[3], -(bbox(t[2])[1] + bbox(t[2])[4])))[:1]
            render(name, items(lst), "stud", size=(1100, 1100), margin=1.15)

    if "hero" in jobs or "all" in jobs:
        # the hero shows the finished front: dark glass, no tinted LOCA, display off. Display off: the window reads
        # grey-black against the black print (design doc 2.1), so the panel's view area is a little lighter
        hero = items(sel("sheet", "stud", "tape", "bead", "formex", "frame", "washer", "nut", "pcb")) + \
            items(sel("panel", excl=("cover",))) + items(sel("panel", sub="cover"), rgb=(0.17, 0.18, 0.20)) + \
            items(sel("glass", sub="glass"), rgb=(0.12, 0.13, 0.15), op=0.22) + \
            items(sel("glass", sub="print"), rgb=(0.0, 0.0, 0.0))
        render("hero_front", hero, "iso_front_low", size=(2400, 1500), margin=0.98)

    if "explode" in jobs or "all" in jobs:
        # front (-Z) to back (+Z); each group moved as a whole along Z
        order = [("sheet", -215), ("stud", -215), ("tape", -160), ("glass", -112), ("loca", -76), ("panel", -40), ("bead", 6),
                 ("formex", 40), ("frame", 86), ("washer", 146), ("nut", 172), ("pcb", 232)]
        it = []
        anchors = {}
        for key, dz in order:
            lst = sel(key)
            it += items(lst, off=(0, 0, dz))
        # anchors: one representative point per item (model coords + offset); the builder snaps to the visible part
        def anchor(key, x, yabs, z, dz):
            anchors[key] = (x, -yabs, z + dz)
        d = dict(order)
        anchor("sheet", 230.0, 40.0, -14.42, d["sheet"])
        anchor("stud", 210.59, -5.83, -3.0, d["stud"])
        anchor("tape", 209.5, 60.0, -12.42, d["tape"])
        anchor("glass", 199.59, 30.0, -14.42, d["glass"])
        anchor("loca", 184.9, 40.0, -11.42, d["loca"])
        anchor("panel", 184.9, 50.0, -9.0, d["panel"])
        anchor("bead", 198.69, 60.0, -11.42, d["bead"])
        anchor("formex", 184.4, 60.0, -5.0, d["formex"])
        anchor("frame", 103.85, -10.0, -12.42, d["frame"])   # middle of the frame's top bar, clear of the Formex
        anchor("washer", 210.59, -5.83, -7.42, d["washer"])
        anchor("nut", 210.59, -5.83, -4.0, d["nut"])
        anchor("pcb", 190.0, 60.0, 1.55, d["pcb"])
        render("exploded", it, "explode", size=(3200, 1900), margin=1.02, anchors=anchors)

    if "steps" in jobs or "all" in jobs:
        # station 1: optical bond (glass face 2 up in the picture = seen from the back), LOCA, panel
        it = items(sel("glass")) + items(sel("loca"), off=(0, 0, 14)) + items(sel("panel", excl=("tail",)), off=(0, 0, 34))
        render("step1_bond", it, "iso_back", size=(1500, 1050), margin=1.03)
        # station 2: frame + Formex (Formex lifted out of its seat, seen from the front)
        it = items(sel("frame")) + items(sel("formex"), off=(0, 0, -40))
        render("step2_frame_prep", it, "iso_front", size=(1500, 1050), margin=1.03)
        # station 3 (J2) is rendered in the "tools" job, on the J2 plate
        # station 4: tape strips on the flange (module from the front, tape liner side); finished-look glass
        it = items(sel("glass", sub="glass"), rgb=(0.12, 0.13, 0.15), op=0.22) + \
            items(sel("glass", sub="print"), rgb=(0.0, 0.0, 0.0)) + items(sel("panel", excl=("cover",))) + \
            items(sel("panel", sub="cover"), rgb=(0.17, 0.18, 0.20)) + items(sel("bead")) + items(sel("formex")) + \
            items(sel("frame")) + items(sel("tape"), off=(0, 0, -12))
        render("step4_tape", it, "iso_front", size=(1500, 1050), margin=1.03)
        # station 5: PCB on the bosses (from the back)
        it = items(sel("glass", "loca", "panel", "bead", "formex", "frame", "tape")) + items(sel("pcb"), off=(0, 0, 45))
        render("step5_pcb", it, "iso_back", size=(1500, 1050), margin=1.03)
        # station 6: mounting into the sheet from behind, then washers + nuts
        it = items(sel("sheet", "stud")) + items(sel("glass", "loca", "panel", "bead", "formex", "frame", "tape", "pcb"),
                                               off=(0, 0, 60)) + items(sel("washer"), off=(0, 0, 100)) + \
            items(sel("nut"), off=(0, 0, 118))
        render("step6_mount", it, "iso_back", size=(1500, 1050), margin=1.03)

    if "tools" in jobs or "all" in jobs:
        # simple solids built from the drawing values (GF-D30 / GF-D21 via drafting_choices.json) and the master
        # fastener positions - illustrations of the tools, not CAD of record
        dc = {i["name"]: i["value"] for i in json.load(open(DRAFT, encoding="utf-8"))["items"]}
        M = json.load(open(MASTER, encoding="utf-8"))
        gl = [r for r in M["plan_rectangles"] if r["name"] == "glass"][0]
        fl = [r for r in M["plan_rectangles"] if r["name"] == "flange"][0]
        xc, yc = (gl["x0"] + gl["x1"]) / 2, (gl["y0"] + gl["y1"]) / 2
        zf = -14.42  # flush plane = J2 working face (master derived level Z_GLASS_FRONT at glass_t 3.0)
        L, Wd, Tp = dc["j2_plate"]
        plate = cq.Workplane("XY").box(L, Wd, Tp).translate((xc, -yc, zf - Tp / 2)).edges("|Z").fillet(6).val().wrapped
        pins = []
        for f in M["fasteners"]["positions"]:
            pins.append(cq.Workplane("XY").circle(dc["j2_pin_d"] / 2).extrude(dc["j2_pin_proud"])
                        .translate((f["x_abs"], -f["y_abs_down"], zf)).val().wrapped)
        th = dc["j2_tail_holder"]
        post_y = fl["y1"] + th["post_offset"]
        post = cq.Workplane("XY").circle(th["post_d"] / 2).extrude(th["post_h"]).translate((xc, -post_y, zf)).val().wrapped
        jig = [("jig", "plate", plate, (0, 0, 0), (0.80, 0.82, 0.85), 1.0)]
        jig += [("jig", "pin", p, (0, 0, 0), (0.62, 0.63, 0.66), 1.0) for p in pins]
        jig += [("jig", "post", post, (0, 0, 0), (0.62, 0.63, 0.66), 1.0)]
        render("tool_j2", jig, "j2", size=(1500, 1050), margin=1.03)
        it = jig + items(sel("glass")) + items(sel("loca")) + items(sel("panel")) + \
            items(sel("bead"), off=(0, 0, 55)) + items(sel("formex"), off=(0, 0, 55)) + items(sel("frame"), off=(0, 0, 55))
        render("step3_j2", it, "j2", size=(1500, 1050), margin=1.03)
        # tail fold gauge GF-D21: base block + two end pads; R1.5 nose on the recess face's top edge
        g = dc["tg_gauge"]
        gb = [d for d in M["driving_parameters"] if d["name"] == "g_bend"][0]["value"]
        nose = [d for d in M["driving_parameters"] if d["name"] == "bend_nose_R"][0]["value"]
        span = (lambda r: r["x1"] - r["x0"])([r for r in M["plan_rectangles"] if r["name"] == "bend_gap_slot"][0])
        tot = span + 2 * g["pad_len"]
        hgt = 3.2  # GF-D21 / design doc 2.2.5: gauge height 3.2 = bridge back above the CTP front
        base = cq.Workplane("XY").box(tot, g["depth"], hgt, centered=False).translate((0, gb, 0))
        pads = cq.Workplane("XY").box(g["pad_len"], gb, hgt, centered=False).union(
            cq.Workplane("XY").box(g["pad_len"], gb, hgt, centered=False).translate((tot - g["pad_len"], 0, 0)))
        body = base.union(pads)
        body = body.edges(cq.selectors.BoxSelector((g["pad_len"] + 0.5, gb - 0.2, hgt - 0.2),
                                                   (tot - g["pad_len"] - 0.5, gb + 0.2, hgt + 0.2))).fillet(nose)
        render("tool_gauge", [("gauge", "gauge", body.val().wrapped, (0, 0, 0), (0.18, 0.19, 0.21), 1.0)],
               "gauge", size=(1500, 900), margin=1.05)

    if "sections" in jobs or "all" in jobs:
        cut = [(k, sb, s) for k, sb, s in S]
        sec = {
            "side_edge_y66.83": {"axis": "y", "value": 66.83, "window": [-16.5, 30.0, -16.0, 6.0]},
            "corner_F1_y-5.83": {"axis": "y", "value": -5.83, "window": [-16.5, 12.0, -16.0, 6.0]},
            "bottom_x60": {"axis": "x", "value": 60.0, "window": [108.0, 152.5, -16.0, 6.0]},
            "bottom_x103.85": {"axis": "x", "value": 103.85, "window": [108.0, 152.5, -16.0, 6.0]},
        }
        out = {}
        for nm, spec in sec.items():
            out[nm] = dict(spec, polys=section(cut, spec["axis"], spec["value"], spec["window"]))
            print("  section", nm, len(out[nm]["polys"]), flush=True)
        json.dump(out, open(os.path.join(OUT, "sections.json"), "w"))
    print("done %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main(sys.argv[1:] or ["all"])
