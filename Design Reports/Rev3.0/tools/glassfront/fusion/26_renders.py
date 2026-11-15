"""26 - frame screenshots (orthographic, camera set by script, 1600 x 1200) to Mechanical/Rev3.0_GlassFront/renders/
Fusion_FrameGF_<name>.png. Model Y up = top of the board; front = -Z (oven / glass side), so the front view is the
mirror of the KiCad view (front-view u = -(x - 103.85), as the master JSON).
Section views use a temporary SECTION ANALYSIS on the root XZ plane offset to the cut position (no timeline change);
each analysis is deleted right after its screenshot.
Expects: final model."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

R = os.path.join(L.MECH, "renders")
VIEWS = [
    ("front", dict(eye_dir=(0, 0, -1))),
    ("back", dict(eye_dir=(0, 0, 1))),
    ("iso_front", dict(eye_dir=(0.55, 0.45, -1.0))),
    ("iso_back", dict(eye_dir=(0.5, 0.45, 1.0))),
    ("closeup_corner_F1_lip_seat_ring_pad_slot", dict(eye_dir=(-0.55, 0.6, -1.0), target_mm=(7.0, -4.0, -12.8),
                                                      fit=False, extent_mm=36)),
    ("closeup_land_pip_P1", dict(eye_dir=(0.35, -0.55, -1.0), target_mm=(58.48, -12.0, -11.6), fit=False,
                                 extent_mm=16)),
    ("closeup_chin_tail_pocket_front", dict(eye_dir=(0.25, -0.5, -1.0), target_mm=(103.85, -134.0, -10.0),
                                            fit=False, extent_mm=175)),
    ("closeup_tail_pocket_back", dict(eye_dir=(0.25, -0.55, 1.0), target_mm=(103.0, -136.0, -3.0), fit=False,
                                      extent_mm=150)),
    ("closeup_corner_F1_back_tube_rib", dict(eye_dir=(-0.6, 0.55, 1.0), target_mm=(8.0, -4.0, -9.0), fit=False,
                                             extent_mm=34)),
]
# sections: (name, plane offset along the root XZ plane normal (+Y) in mm, camera). The analysis removes the
# +Y side (above the cut), so the camera looks from +Y (eye_dir (0, 1, 0)); first run used (0, -1, 0) = no cut visible.
SECTIONS = [
    ("section_left_edge_y82.085_F8", -82.085, dict(eye_dir=(0, 1, 0), up=(0, 0, 1), target_mm=(8.5, -82.085, -9.0),
                                                   fit=False, extent_mm=34)),
    ("section_right_edge_y60", -60.0, dict(eye_dir=(0, 1, 0), up=(0, 0, 1), target_mm=(196.0, -60.0, -9.0),
                                           fit=False, extent_mm=34)),
]


def grid_off():
    """UI preference only (not the design): select 'Grid Off' in the Layout Grid list control (the v2 attempt toggled
    the wrong item); the layout grid lies in the Z 0 plane and otherwise covers every back view of the frame."""
    cd = L.app().userInterface.commandDefinitions.itemById("ViewLayoutGridOnCommand")
    lc = adsk.core.ListControlDefinition.cast(cd.controlDefinition)
    for i in range(lc.listItems.count):
        if lc.listItems.item(i).name == "Grid Off":
            lc.listItems.item(i).isSelected = True


def run(_context: str):
    L.check_doc()
    os.makedirs(R, exist_ok=True)
    grid_off()
    out = []
    for name, kw in VIEWS:
        out.append((name, L.shot(os.path.join(R, "Fusion_FrameGF_%s.png" % name), **kw)))
    sas = L.des().analyses.sectionAnalyses
    for name, off, kw in SECTIONS:
        si = sas.createInput(L.root().xZConstructionPlane, off / 10.0)
        si.isHatchShown = True
        sa = sas.add(si)
        out.append((name, L.shot(os.path.join(R, "Fusion_FrameGF_%s.png" % name), **kw)))
        sa.deleteMe()
    L.show_iso()
    L.log("26 renders %s" % out)
    print(out)
