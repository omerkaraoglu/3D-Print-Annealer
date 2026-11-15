"""diag (stage 2) - viewport screenshots to %TEMP%\\rev3_glassfront\\peek_<name>.png (camera only, no design change).
VIEWS: (name, eye direction, target model mm or None = fit all, view extent mm or None = fit)."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

VIEWS = [("asm_iso_back", (0.5, 0.45, 1.0), None, None),
         ("asm_chin_back", (0.25, -0.55, 1.0), (103.0, -136.0, -3.0), 150)]


def cam_shot(path, eye_dir, target=None, extent=None, up=(0, 1, 0), w=1600, h=1200):
    vp = L.app().activeViewport
    cam = vp.camera
    cam.isSmoothTransition = False
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    t = adsk.core.Point3D.create(*(v / 10.0 for v in (target or (103.85, -82.0, -6.0))))
    n = sum(c * c for c in eye_dir) ** 0.5
    cam.target = t
    cam.eye = adsk.core.Point3D.create(t.x + eye_dir[0] / n * 80, t.y + eye_dir[1] / n * 80, t.z + eye_dir[2] / n * 80)
    cam.upVector = adsk.core.Vector3D.create(*up)
    cam.isFitView = target is None
    vp.camera = cam
    vp.refresh()
    if target is None:
        vp.fit()
    else:
        cam = vp.camera
        cam.viewExtents = extent / 10.0
        vp.camera = cam
        vp.refresh()
    return vp.saveAsImageFile(path, w, h)


def run(_context: str):
    L.check_doc()
    out = []
    for name, e, t, x in VIEWS:
        out.append((name, cam_shot(os.path.join(L.SCR, "peek_%s.png" % name), e, t, x)))
    print(out)
