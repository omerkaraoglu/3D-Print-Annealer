"""72 - stage 4 (GF-2.0): flex test 71 failed only at glass 1.1 (level snap), with two rule fillets:
  * 'Root fillets R0.5 - floors over the bridge and the flange plate (rule)': at the snap the lowered floor
    (flange back) and the land-plate back are one plane, so 68's floor cut only removes the GF-1.1 cell fillets above
    the floor and the new fillets would have to continue them through a 1 deg cut end -> General modeling error.
    FIX: new level Z_FLOOR_LOW = min(Z_FLANGE_BACK; Z_LANDPLATE_BACK - 2 x fillet_root): the floor behind the bridge
    is the flange back (glass 2.0 / 3.0 / 4.0, unchanged) but never less than 1.0 below the land-plate back, so the
    step and the topology are the same at every glass_t. Only the snapped glass-1.1 variant changes: floors over the
    flange at Z -8.92 (flange 1.6 under the cells / tail pocket) instead of flat -7.92 (2.6).
    Floor cut extent -> Z_PCB - Z_FLOOR_LOW; new hidden plane 'Z_FLOOR_LOW plane'; the sketches 'Cell ribs over the
    flange plate' and 'Divider rib (over the flange plate)' redefined onto it (outline offsets and extents re-based,
    rib front ends 0.5 inside the step-wall back face at that level).
  * 'Root fillets R0.5 - outer wall to the flange plate (rule)': at the snap the flange back merges with the land-plate
    back, the rule finds no edge. FIX: deleted; the GF-1.1 rule 'Root fillets R0.5 - wall + step wall to plates
    (rule)' is re-created at its timeline position as BETWEEN ['Land plate + step wall (back)', 'Flange plate'] AND
    ['Flange plate', 'Outer wall block', 'Tail wall block'] (GF-1.1: first list without 'Flange plate'), which takes
    the outer wall on the flange plate in every state.
Refuses to run twice (Z_FLOOR_LOW exists)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

N_W = "Root fillets R0.5 - wall + step wall to plates (rule)"
N_R1 = "Root fillets R0.5 - outer wall to the flange plate (rule)"
SK_RIBS = "Cell ribs over the flange plate sketch"
SK_DIV = "Divider rib (over the flange plate) sketch"
OLD_FRONT = "glass_y1 + s_ring - rib_bury"
NEW_FRONT = "glass_y1 + s_ring_b - ( Z_FLOOR_LOW - Z_FLANGE_FRONT ) * tan(draft) - rib_bury"


def health(tag, res):
    n, bad = L.timeline_health()
    res[tag] = bad
    L.log("72 %s: timeline %d unhealthy %s; %s" % (tag, n, bad, L.body_stats()))
    if bad:
        raise RuntimeError("72 unhealthy after %s: %s" % (tag, bad))


def set_extent(name, expr, direction, tl):
    f = L.feature(name)
    taper = f.taperAngleOne.expression
    f.timelineObject.rollTo(True)
    ok = f.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI(expr)), direction, L.VI(taper))
    tl.moveToEnd()
    if not ok:
        raise RuntimeError("extent " + name)


def rebase_sketch(name, plane, tl):
    sk = L.comp().sketches.itemByName(name)
    sk.timelineObject.rollTo(True)
    if not sk.redefine(plane):
        raise RuntimeError("redefine " + name)
    k = 0
    for j in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(j)
        e = dm.parameter.expression
        e2 = e.replace(OLD_FRONT, NEW_FRONT).replace("Z_FLANGE_BACK", "Z_FLOOR_LOW")
        if e2 != e:
            dm.parameter.expression = e2
            k += 1
    tl.moveToEnd()
    return k


def run(_context: str):
    d = L.check_doc()
    L.log("=== 72 start")
    ups = d.userParameters
    if ups.itemByName("Z_FLOOR_LOW") is not None:
        raise RuntimeError("72 already applied")
    tl = d.timeline
    res = {}
    L.set_param("Z_FLOOR_LOW", "min(Z_FLANGE_BACK; Z_LANDPLATE_BACK - 2 * fillet_root)", "mm",
                "GF-2.0: floor behind the bridge (cells + tail pocket beyond the step-wall back) = the flange back, but "
                "at least 2 x fillet_root below the land-plate back so the floor always steps (one topology at every "
                "glass_t); differs from Z_FLANGE_BACK only at the level snap (glass 1.1: -8.92, flange 1.6 there)")
    # 1 R1 out, W re-created with Flange plate in the first list
    L.feature(N_R1).deleteMe()
    w = L.feature(N_W)
    nxt = tl.item(w.timelineObject.index + 1)
    w.deleteMe()
    nxt.rollTo(True)
    f = L.rule_fillet(N_W, "between", ["Land plate + step wall (back)", "Flange plate"],
                      ["Flange plate", "Outer wall block", "Tail wall block"])
    res["W_faces"] = f.faces.count
    tl.moveToEnd()
    d.computeAll()
    health("W", res)
    # 2 plane + rebased sketches + extents
    sk = L.comp().sketches.itemByName(SK_RIBS)
    sk.timelineObject.rollTo(True)
    pl = L.offset_plane("Z_FLOOR_LOW plane", "Z_FLOOR_LOW")
    pl.isLightBulbOn = False
    tl.moveToEnd()
    res["ribs_dims"] = rebase_sketch(SK_RIBS, pl, tl)
    res["div_dims"] = rebase_sketch(SK_DIV, pl, tl)
    set_extent("Floor over the flange plate (cells + tail pocket)", "Z_PCB - Z_FLOOR_LOW",
               adsk.fusion.ExtentDirections.NegativeExtentDirection, tl)
    set_extent("Cell ribs over the flange plate", "Z_CELL_RIB_TOP - Z_FLOOR_LOW",
               adsk.fusion.ExtentDirections.PositiveExtentDirection, tl)
    set_extent("Divider rib (over the flange plate)", "Z_TROUGH_TOP - Z_FLOOR_LOW",
               adsk.fusion.ExtentDirections.PositiveExtentDirection, tl)
    d.computeAll()
    health("rebase", res)
    res["Z_FLOOR_LOW"] = round(L.P("Z_FLOOR_LOW"), 4)
    res["frame"] = L.body_dict()
    L.dump(res, "gf20/72_snap_fix.json")
    L.log("72 %s" % res)
    print(res)
