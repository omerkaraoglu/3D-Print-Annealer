"""Off-screen VTK renders of the frame / assembly (PNG), incl. section views.

render(parts, fname, view=..., clip=None)
  parts: list of (label, cq.Shape or Workplane, rgb, opacity)
  view : "iso_front", "iso_back", "front", "back", "side", "top" or a dict(pos=, focal=, up=)
  clip : (origin, normal) - plane section: everything on the +normal side is removed and the
         cut faces are drawn (each part is intersected with a half-space box, so the cut faces are
         real solid faces).
Frame: X = board x, Y = -board y, Z = +component side (PCB back at 0), -Z = towards the oven sheet.
"""
import os

import vtk
import cadquery as cq

OUT = None


def _poly(shape, tol=0.05):
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    return s.toVtkPolyData(tol, 0.2, True)


def _halfspace(origin, normal, size=2000.0):
    """Big box occupying the side of the plane opposite to `normal` (the side that is kept)."""
    o = cq.Vector(*origin)
    n = cq.Vector(*normal).normalized()
    # a box centred size/2 behind the plane
    c = o - n * (size / 2)
    pl = cq.Plane(origin=c.toTuple(), normal=n.toTuple())
    return cq.Workplane(pl).rect(size, size).extrude(size / 2, both=True).val()


def cut_part(shape, clip):
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    if clip is None:
        return s
    hs = _halfspace(*clip)
    try:
        r = s.intersect(hs)
        return r if r.Faces() else None
    except Exception:
        return None


VIEWS = {  # cam = direction from the target to the camera
    "iso_front": dict(cam=(-0.55, 0.45, -1.0), up=(0, 1, 0)),   # oven-front side, from upper left
    "iso_back": dict(cam=(-0.55, 0.45, 1.0), up=(0, 1, 0)),     # component side, from upper left
    "front": dict(cam=(0, 0, -1), up=(0, 1, 0)),                # looking at the glass (X mirrored)
    "back": dict(cam=(0, 0, 1), up=(0, 1, 0)),                  # looking at the component side
    "side": dict(cam=(1, 0, 0), up=(0, 1, 0)),                  # from the right (+X)
    "bottom": dict(cam=(0, -1, 0), up=(0, 0, 1)),               # from below the bottom edge
}


def render(parts, fname, view="iso_front", clip=None, size=(1800, 1200), title=None, zoom=1.0,
           focal=None, parallel=True, edges=True):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for lbl, shp, rgb, op in parts:
        s = cut_part(shp, clip)
        if s is None:
            continue
        pd = _poly(s)
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
        if edges and op > 0.9:
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
    win.AddRenderer(ren)
    win.SetSize(*size)
    cam = ren.GetActiveCamera()
    v = VIEWS[view] if isinstance(view, str) else view
    ren.ResetCamera()
    fp = focal or cam.GetFocalPoint()
    d = cam.GetDistance()
    dx, dy, dz = v["cam"]
    cam.SetFocalPoint(*fp)
    cam.SetPosition(fp[0] + dx * d, fp[1] + dy * d, fp[2] + dz * d)
    cam.SetViewUp(*v["up"])
    if parallel:
        cam.ParallelProjectionOn()
    ren.ResetCamera()
    if focal:
        cam.SetFocalPoint(*focal)
        cam.SetPosition(focal[0] + dx * d, focal[1] + dy * d, focal[2] + dz * d)
    cam.Zoom(zoom)
    ren.ResetCameraClippingRange()
    kit = vtk.vtkLightKit(); kit.AddLightsToRenderer(ren)
    if title:
        ta = vtk.vtkTextActor(); ta.SetInput(title)
        tp = ta.GetTextProperty(); tp.SetFontSize(22); tp.SetColor(0.1, 0.1, 0.1)
        ta.SetDisplayPosition(15, size[1] - 40)
        ren.AddActor2D(ta)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(fname); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    win.Finalize()
    return fname
