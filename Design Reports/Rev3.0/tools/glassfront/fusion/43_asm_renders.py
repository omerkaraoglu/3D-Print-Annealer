"""43 - stage 2, Part D: assembly screenshots (orthographic, 1600 x 1200) to Mechanical/Rev3.0_GlassFront/renders/
Fusion_Assembly_<name>.png. Front = -Z (oven side); a front view is the mirror of the KiCad top view.
Run with WHICH = a list of view names (module global, default all except 'back_no_PCB', which needs the board
children hidden first by 44_asm_board_visibility.py SHOW=False and restored afterwards with SHOW=True).
Temporary states (all restored at the end of each view, nothing enters the timeline):
  * visibility of components / the sheet bodies (variant views)
  * exploded view: occurrence transforms moved along Z, then Snapshots.revertPendingSnapshot()
  * sections: a temporary SECTION ANALYSIS (hatch on) on the root XZ / YZ plane, optionally re-positioned by its
    transform (corner section along the F1 slot axis); deleted right after the screenshot
  * section appearances: SECTION_LOOK swaps the black parts to contrasting appearances for legibility, restored
    afterwards (frame light grey, bead red, tape yellow, print black, glass light blue, Formex green)."""
import importlib
import math
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)

R = os.path.join(L.MECH, "renders")
WHICH = ["iso_front", "iso_back", "front", "front_R4", "exploded", "section_side_edge_y82", "section_chin_x103.85",
         "section_corner_F1_slot_axis"]
S4_COMPS = ["Weld studs S4 F1-F4", "Washers + nyloc nuts S4 F1-F4"]
SECTION_LOOK = {("Frame GF", "Frame GF"): "Plastic - Matte (White)",
                ("Formex sheet", "Formex sheet"): "Plastic - Matte (Green)",
                ("Glass", "Glass"): "Glass - Light Color (Blue)"}


def cam_shot(path, eye_dir, target=None, extent=None, up=(0, 1, 0), w=1600, h=1200):
    vp = L.app().activeViewport
    cam = vp.camera
    cam.isSmoothTransition = False
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    t = adsk.core.Point3D.create(*(v / 10.0 for v in (target or (103.85, -82.0, -6.0))))
    n = math.sqrt(sum(c * c for c in eye_dir))
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
    ok = vp.saveAsImageFile(path, w, h)
    L.log("43 shot %s -> %s" % (path, ok))
    return ok


def occ(name):
    return L.occ_by_comp(name)


def set_vis(d):
    old = {}
    for n, v in d.items():
        o = occ(n)
        old[n] = o.isLightBulbOn
        o.isLightBulbOn = v
    return old


def sheet_bodies():
    c = occ("Oven sheet").component
    return L.body_in(c, "Oven sheet S4/S8 (no holes)"), L.body_in(c, "Oven sheet R4 (rivet holes)")


def ds1_proxy():
    ao = L.root().allOccurrences
    hits = [ao.item(i) for i in range(ao.count) if ao.item(i).name.startswith("TFT7")]
    hits.sort(key=lambda o: o.fullPathName.count("+"))
    return hits[0]


def move_z(o, dz):
    m = o.transform2
    t = m.translation
    t.z = t.z + dz / 10.0
    m.translation = t
    o.transform2 = m


def swap_looks(look):
    old = {}
    for (cn, bn), ap in look.items():
        b = L.body_in(occ(cn).component, bn)
        old[(cn, bn)] = b.appearance
        b.appearance = L.appearance(ap)
    return old


def restore_looks(old):
    for (cn, bn), ap in old.items():
        L.body_in(occ(cn).component, bn).appearance = ap


def section_shot(name, plane, off_mm, eye, up, target, extent, transform=None):
    sas = L.des().analyses.sectionAnalyses
    si = sas.createInput(plane, off_mm / 10.0)
    if transform is not None:
        si.transform = transform
    si.isHatchShown = True
    sa = sas.add(si)
    ok = cam_shot(os.path.join(R, "Fusion_Assembly_%s.png" % name), eye, target, extent, up)
    sa.deleteMe()
    return ok


def run(_context: str):
    L.check_doc()
    os.makedirs(R, exist_ok=True)
    p26 = os.path.join(L.GF_DIR, "26_renders.py")
    ns = {"__name__": "gf_26"}
    exec(compile(open(p26, encoding="utf-8").read(), p26, "exec"), ns)
    ns["grid_off"]()
    des = L.des()
    out = []
    TG = (103.85, -82.0, -6.0)
    for name in WHICH:
        f = os.path.join(R, "Fusion_Assembly_%s.png" % name)
        if name == "iso_front":
            out.append((name, cam_shot(f, (0.55, 0.45, -1.0))))
        elif name == "iso_back":
            out.append((name, cam_shot(f, (0.5, 0.45, 1.0))))
        elif name == "front":
            out.append((name, cam_shot(f, (0, 0, -1))))
        elif name == "back_no_PCB":
            out.append((name, cam_shot(f, (0, 0, 1))))
        elif name == "front_R4":
            s4, r4 = sheet_bodies()
            old = set_vis({"Rivets R4 F1-F4 (hidden)": True, S4_COMPS[0]: False, S4_COMPS[1]: False})
            s4.isLightBulbOn, r4.isLightBulbOn = False, True
            out.append((name, cam_shot(f, (0, 0, -1))))
            out.append((name + "_closeup_F1", cam_shot(os.path.join(R, "Fusion_Assembly_front_R4_closeup_F1.png"),
                                                       (-0.35, 0.3, -1.0), (8.0, -4.0, -14.4), 40)))
            s4.isLightBulbOn, r4.isLightBulbOn = True, False
            set_vis(old)
        elif name == "exploded":
            moves = [("Oven sheet", -170), (S4_COMPS[0], -170), ("VHB tape strips", -140), ("Glass", -110),
                     ("Optical bond", -88), ("Bead", -66), ("Formex sheet", -22), (L.BOARD_COMP, 45),
                     (S4_COMPS[1], 80)]
            for n, dz in moves:
                move_z(occ(n), dz)
            move_z(ds1_proxy(), -44 - 45)          # panel: -44 in the world (it rides on the board occurrence)
            out.append((name, cam_shot(f, (1.0, 0.42, -0.42))))
            out.append((name + "_back", cam_shot(os.path.join(R, "Fusion_Assembly_exploded_back.png"),
                                                 (1.0, 0.55, 0.75))))
            if des.snapshots.hasPendingSnapshot:
                des.snapshots.revertPendingSnapshot()
        elif name.startswith("section"):
            old = swap_looks(SECTION_LOOK)
            if name == "section_side_edge_y82":
                out.append((name, section_shot(name, L.root().xZConstructionPlane, -L.P("gc_y"), (0, 1, 0), (0, 0, 1),
                                               (6.0, -L.P("gc_y"), -6.5), 42)))
            elif name == "section_chin_x103.85":
                out.append((name, section_shot(name, L.root().yZConstructionPlane, L.P("gc_x"), (1, 0, 0), (0, 0, 1),
                                               (L.P("gc_x"), -136.0, -5.0), 62)))
            elif name == "section_corner_F1_slot_axis":
                ux, uy = L.P("f1_ux"), -L.P("f1_uy")              # model frame (Y up)
                th = math.atan2(uy, ux)
                m = adsk.core.Matrix3D.create()
                m.setToRotation(th, adsk.core.Vector3D.create(0, 0, 1), adsk.core.Point3D.create(0, 0, 0))
                fx, fy = L.P("f1_x"), -L.P("f1_y")
                m.translation = adsk.core.Vector3D.create(fx / 10.0, fy / 10.0, 0)
                n = (-math.sin(th), math.cos(th), 0)
                tgt = (fx + 12 * ux, fy + 12 * uy, -7.5)
                out.append((name, section_shot(name, L.root().xZConstructionPlane, 0.0, n, (0, 0, 1), tgt, 44, m)))
            restore_looks(old)
    L.show_iso()
    L.log("43 renders %s" % out)
    print(out, "pending snapshot", des.snapshots.hasPendingSnapshot)
