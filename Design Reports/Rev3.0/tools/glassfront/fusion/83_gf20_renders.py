"""83 - stage 4 (GF-2.0) screenshots to Mechanical/Rev3.0_GlassFront/renders/ (orthographic, 1600 x 1200). Module global
GROUP (runner) = 'frame' | 'gf20' | 'asm' | 'asm_nopcb' (the last needs the board children hidden first by 44 with
SHOW = False and restored with SHOW = True). Every temporary state is restored (visibility, appearances, exploded
transforms via revertPendingSnapshot, section analyses deleted); nothing enters the timeline.
  frame      Fusion_FrameGF_<view>.png  (frame alone, black as moulded; 26's set with the GF-2.0 positions)
  gf20       Fusion_GF20_<view>.png     (frame light grey for legibility, tails orange): front, back, bottom edge with
             the bridge and the tail route from the back and from the front (glass hidden), sections x 103.85 (TFT
             tail), x 60.0 (CTP tail), x 150.0 (TFT wide part), x 79.92 (divider rib), assembly front S4 and R4
  asm        Fusion_Assembly_<view>.png (43's set: iso / front / R4 / exploded / sections, GF-2.0 names)
  asm_nopcb  Fusion_Assembly_back_no_PCB.png, ..._iso_back_no_PCB.png"""
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
GROUP = globals().get("GROUP") or "frame"
PFX = "Fusion_%s_" % (globals().get("PREFIX") or "GF20")   # stage 5: PREFIX = "GF21"
S4_COMPS = ["Weld studs S4 F1-F4", "Washers + nyloc nuts S4 F1-F4"]
LOOK = {("Frame GF", "Frame GF"): "Plastic - Matte (White)", ("Formex sheet", "Formex sheet"): "Plastic - Matte (Green)",
        ("Glass", "Glass"): "Glass - Light Color (Blue)"}


def cam_shot(path, eye_dir, target=None, extent=None, up=(0, 1, 0), w=1600, h=1200):
    vp = L.app().activeViewport
    cam = vp.camera
    cam.isSmoothTransition = False
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    t = adsk.core.Point3D.create(*(v / 10.0 for v in (target or (L.P("gc_x"), -L.P("gc_y"), -6.0))))
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
    L.log("83 shot %s -> %s" % (path, ok))
    return ok


def occ(name):
    return L.occ_by_comp(name)


def all_vis():
    r = L.root()
    return {r.occurrences.item(i).component.name: r.occurrences.item(i).isLightBulbOn for i in range(r.occurrences.count)}


def set_vis(d):
    old = {}
    for n, v in d.items():
        o = occ(n)
        old[n] = o.isLightBulbOn
        o.isLightBulbOn = v
    return old


def only(names):
    return set_vis({n: (n in names) for n in all_vis()})


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


def sheet_bodies():
    c = occ("Oven sheet").component
    return L.body_in(c, "Oven sheet S4/S8 (no holes)"), L.body_in(c, "Oven sheet R4 (rivet holes)")


def section(path, plane, off_mm, eye, up, target, extent, transform=None):
    sas = L.des().analyses.sectionAnalyses
    si = sas.createInput(plane, off_mm / 10.0)
    if transform is not None:
        si.transform = transform
    si.isHatchShown = True
    sa = sas.add(si)
    ok = cam_shot(path, eye, target, extent, up)
    sa.deleteMe()
    return ok


def r4_on():
    s4, r4 = sheet_bodies()
    old = set_vis({"Rivets R4 F1-F4 (hidden)": True, S4_COMPS[0]: False, S4_COMPS[1]: False})
    s4.isLightBulbOn, r4.isLightBulbOn = False, True
    return old


def r4_off(old):
    s4, r4 = sheet_bodies()
    s4.isLightBulbOn, r4.isLightBulbOn = True, False
    set_vis(old)


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


def frame_group(out):
    old = only([L.COMP_NAME])
    f1x, f1y, p1x, p1y = L.P("f1_x"), L.P("f1_y"), L.P("pip1_x"), L.P("pip1_y")
    views = [("front", (0, 0, -1), None, None, (0, 1, 0)), ("back", (0, 0, 1), None, None, (0, 1, 0)),
             ("iso_front", (0.55, 0.45, -1.0), None, None, (0, 1, 0)), ("iso_back", (0.5, 0.45, 1.0), None, None, (0, 1, 0)),
             ("closeup_corner_F1_lip_seat_ring_pad_slot", (-0.55, 0.6, -1.0), (f1x + 4.89, -(f1y + 4.83), -12.8), 36, (0, 1, 0)),
             ("closeup_land_pip_P1", (0.35, -0.55, -1.0), (p1x, -(p1y - 1.07), -11.6), 16, (0, 1, 0)),
             ("closeup_bridge_tail_pocket_front", (0.25, -0.5, -1.0), (103.85, -128.0, -10.0), 175, (0, 1, 0)),
             ("closeup_tail_pocket_back", (0.25, -0.55, 1.0), (103.0, -136.0, -3.0), 150, (0, 1, 0)),
             ("closeup_corner_F1_back_tube_rib", (-0.6, 0.55, 1.0), (f1x + 5.89, -(f1y + 4.83), -9.0), 34, (0, 1, 0))]
    for name, eye, tgt, ext, up in views:
        out.append((name, cam_shot(os.path.join(R, "Fusion_FrameGF_%s.png" % name), eye, tgt, ext, up)))
    gy = L.P("gc_y")
    for name, off, tgt in (("section_left_edge_y%.2f" % gy, -gy, (3.5, -gy, -9.0)),
                           ("section_right_edge_y60", -60.0, (200.5, -60.0, -9.0))):
        out.append((name, section(os.path.join(R, "Fusion_FrameGF_%s.png" % name), L.root().xZConstructionPlane, off,
                                  (0, 1, 0), (0, 0, 1), tgt, 34)))
    set_vis(old)


def gf20_group(out):
    looks = swap_looks(LOOK)
    try:
        old = only([L.COMP_NAME])
        out.append(("front", cam_shot(os.path.join(R, PFX + "front.png"), (0, 0, -1))))
        out.append(("back", cam_shot(os.path.join(R, PFX + "back.png"), (0, 0, 1))))
        set_vis(old)
        old = set_vis({"Glass": False, "Optical bond": False, "Bead": False, "Oven sheet": False, "VHB tape strips": False,
                       S4_COMPS[0]: False, S4_COMPS[1]: False, A.TAIL_COMP: True})
        out.append(("bottom_edge_bridge_tails_back", cam_shot(os.path.join(R, PFX + "bottom_edge_bridge_tails_back.png"),
                                                              (0.3, -0.75, 1.0), (103.85, -133.0, -4.0), 70)))
        out.append(("bottom_edge_bridge_tails_front", cam_shot(os.path.join(R, PFX + "bottom_edge_bridge_tails_front.png"),
                                                               (0.3, -0.65, -1.0), (103.85, -124.0, -9.0), 70)))
        out.append(("bottom_edge_bridge_nose_closeup", cam_shot(os.path.join(R, PFX + "bottom_edge_bridge_nose_closeup.png"),
                                                                (0.6, -0.55, 0.8), (72.0, -123.0, -7.0), 22)))
        set_vis(old)
        old = set_vis({A.TAIL_COMP: True})
        yz = L.root().yZConstructionPlane
        for name, x in (("section_x103.85_TFT_tail", 103.85), ("section_x60.0_CTP_tail", 60.0),
                        ("section_x150.0_TFT_wide_part", 150.0), ("section_x79.92_divider_rib", 79.92)):
            out.append((name, section(os.path.join(R, PFX + "%s.png" % name), yz, x, (1, 0, 0), (0, 0, 1),
                                      (x, -131.0, -5.0), 46)))
        set_vis(old)
    finally:
        restore_looks(looks)
    out.append(("assembly_front_S4", cam_shot(os.path.join(R, PFX + "assembly_front_S4.png"), (0, 0, -1))))
    old = r4_on()
    out.append(("assembly_front_R4", cam_shot(os.path.join(R, PFX + "assembly_front_R4.png"), (0, 0, -1))))
    r4_off(old)


def asm_group(out):
    des = L.des()
    f = lambda n: os.path.join(R, "Fusion_Assembly_%s.png" % n)
    out.append(("iso_front", cam_shot(f("iso_front"), (0.55, 0.45, -1.0))))
    out.append(("iso_back", cam_shot(f("iso_back"), (0.5, 0.45, 1.0))))
    out.append(("front", cam_shot(f("front"), (0, 0, -1))))
    old = r4_on()
    out.append(("front_R4", cam_shot(f("front_R4"), (0, 0, -1))))
    out.append(("front_R4_closeup_F1", cam_shot(f("front_R4_closeup_F1"), (-0.35, 0.3, -1.0),
                                                (L.P("f1_x") + 5.89, -(L.P("f1_y") + 4.83), -14.4), 40)))
    r4_off(old)
    moves = [("Oven sheet", -170), (S4_COMPS[0], -170), ("VHB tape strips", -140), ("Glass", -110), ("Optical bond", -88),
             ("Bead", -66), ("Formex sheet", -22), (L.BOARD_COMP, 45), (A.TAIL_COMP, -44), (S4_COMPS[1], 80)]
    for n, dz in moves:
        move_z(occ(n), dz)
    move_z(ds1_proxy(), -44 - 45)
    out.append(("exploded", cam_shot(f("exploded"), (1.0, 0.42, -0.42))))
    out.append(("exploded_back", cam_shot(f("exploded_back"), (1.0, 0.55, 0.75))))
    if des.snapshots.hasPendingSnapshot:
        des.snapshots.revertPendingSnapshot()
    looks = swap_looks(LOOK)
    try:
        gy = L.P("gc_y")
        out.append(("section_side_edge_y%.2f" % gy, section(f("section_side_edge_y%.2f" % gy), L.root().xZConstructionPlane,
                                                            -gy, (0, 1, 0), (0, 0, 1), (1.5, -gy, -6.5), 42)))
        out.append(("section_bridge_x103.85", section(f("section_bridge_x103.85"), L.root().yZConstructionPlane,
                                                      L.P("gc_x"), (1, 0, 0), (0, 0, 1), (L.P("gc_x"), -131.0, -5.0), 46)))
        ux, uy = L.P("f1_ux"), -L.P("f1_uy")
        th = math.atan2(uy, ux)
        m = adsk.core.Matrix3D.create()
        m.setToRotation(th, adsk.core.Vector3D.create(0, 0, 1), adsk.core.Point3D.create(0, 0, 0))
        fx, fy = L.P("f1_x"), -L.P("f1_y")
        m.translation = adsk.core.Vector3D.create(fx / 10.0, fy / 10.0, 0)
        n = (-math.sin(th), math.cos(th), 0)
        out.append(("section_corner_F1_slot_axis", section(f("section_corner_F1_slot_axis"), L.root().xZConstructionPlane,
                                                           0.0, n, (0, 0, 1), (fx + 12 * ux, fy + 12 * uy, -7.5), 44, m)))
    finally:
        restore_looks(looks)


def asm_nopcb_group(out):
    f = lambda n: os.path.join(R, "Fusion_Assembly_%s.png" % n)
    out.append(("back_no_PCB", cam_shot(f("back_no_PCB"), (0, 0, 1))))
    out.append(("iso_back_no_PCB", cam_shot(f("iso_back_no_PCB"), (0.5, 0.45, 1.0))))


def run(_context: str):
    L.check_doc()
    os.makedirs(R, exist_ok=True)
    p26 = os.path.join(L.GF_DIR, "26_renders.py")
    ns = {"__name__": "gf_26"}
    exec(compile(open(p26, encoding="utf-8").read(), p26, "exec"), ns)
    ns["grid_off"]()
    vis0 = all_vis()
    out = []
    try:
        {"frame": frame_group, "gf20": gf20_group, "asm": asm_group, "asm_nopcb": asm_nopcb_group}[GROUP](out)
    finally:
        set_vis(vis0)
        if L.des().snapshots.hasPendingSnapshot:
            L.des().snapshots.revertPendingSnapshot()
    L.show_iso()
    L.log("83 %s %s" % (GROUP, out))
    print(GROUP, out, "pending snapshot", L.des().snapshots.hasPendingSnapshot)
