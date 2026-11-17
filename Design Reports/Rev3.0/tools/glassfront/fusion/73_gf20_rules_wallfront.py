"""73 - stage 4 (GF-2.0), corrections after 72:
  (a) 72 re-created 'Root fillets R0.5 - wall + step wall to plates (rule)' with 'Flange plate' in BOTH lists; Fusion
      then drops the step wall <-> flange back edges (a face in both sets counts as set 1): 13 roots were left sharp
      (census). The R1 failure at the snap in flex test 71 was a cascade of the R2 failure, not its own. So:
      the rule W is re-created with its GF-1.1 lists (BETWEEN ['Land plate + step wall (back)'] AND ['Flange plate',
      'Outer wall block', 'Tail wall block']) and 'Root fillets R0.5 - outer wall to the flange plate (rule)'
      (BETWEEN ['Flange plate'] AND ['Outer wall block']) is re-created at the end of the late block, before the tubes.
  (b) 'Outer wall block' starts at Z_WALL_FRONT = min(Z_LAND; Z_FLANGE_BACK - 0.5 mm) instead of the flange front
      (67): at glass 3.0 / 2.0 / 1.1 that is Z_LAND (the GF-1.1 sketch level, outline identical) and its front face
      lies inside the flange plate; at glass 4.0 it reaches 0.5 into the flange plate. 67's choice made the block's
      front face coplanar with the flange front, so Fusion attributed the parting-plane face to the wall block.
      New hidden plane 'Z_WALL_FRONT plane'; sketch redefined, dims Z_FLANGE_FRONT -> Z_WALL_FRONT, extent
      Z_PCB - Z_WALL_FRONT.
Refuses to run twice (Z_WALL_FRONT exists)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

N_W = "Root fillets R0.5 - wall + step wall to plates (rule)"
N_R1 = "Root fillets R0.5 - outer wall to the flange plate (rule)"


def health(tag, res):
    n, bad = L.timeline_health()
    res[tag] = bad
    L.log("73 %s: timeline %d unhealthy %s; %s" % (tag, n, bad, L.body_stats()))
    if bad:
        raise RuntimeError("73 unhealthy after %s: %s" % (tag, bad))


def run(_context: str):
    d = L.check_doc()
    L.log("=== 73 start")
    ups = d.userParameters
    if ups.itemByName("Z_WALL_FRONT") is not None:
        raise RuntimeError("73 already applied")
    tl = d.timeline
    res = {}
    # (a) rule W with the GF-1.1 lists, R1 back at the end of the late block
    w = L.feature(N_W)
    nxt = tl.item(w.timelineObject.index + 1)
    w.deleteMe()
    nxt.rollTo(True)
    f = L.rule_fillet(N_W, "between", ["Land plate + step wall (back)"], ["Flange plate", "Outer wall block",
                                                                          "Tail wall block"])
    res["W_faces"] = f.faces.count
    tl.moveToEnd()
    d.computeAll()
    health("W", res)
    L.comp().sketches.itemByName("Fastener tubes F1-F4 sketch").timelineObject.rollTo(True)
    f = L.rule_fillet(N_R1, "between", ["Flange plate"], ["Outer wall block"])
    res["R1_faces"] = f.faces.count
    tl.moveToEnd()
    d.computeAll()
    health("R1", res)
    # (b) outer wall block front level
    L.set_param("Z_WALL_FRONT", "min(Z_LAND; Z_FLANGE_BACK - 0.5 mm)", "mm",
                "GF-2.0: front of the outer wall block = Z_LAND (GF-1.1), but at least 0.5 into the flange plate where "
                "the flange back lies in front of the land (glass 4.0): the walls below the board edge stand on the "
                "flange plate")
    sk = L.comp().sketches.itemByName("Outer wall block sketch")
    sk.timelineObject.rollTo(True)
    pl = L.offset_plane("Z_WALL_FRONT plane", "Z_WALL_FRONT")
    pl.isLightBulbOn = False
    if not sk.redefine(pl):
        raise RuntimeError("redefine")
    k = 0
    for j in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(j)
        e = dm.parameter.expression
        if "Z_FLANGE_FRONT" in e:
            dm.parameter.expression = e.replace("Z_FLANGE_FRONT", "Z_WALL_FRONT")
            k += 1
    if k != 8:
        raise RuntimeError("outer wall dims %d" % k)
    tl.moveToEnd()
    ow = L.feature("Outer wall block")
    ow.timelineObject.rollTo(True)
    ok = ow.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("Z_PCB - Z_WALL_FRONT")),
                             adsk.fusion.ExtentDirections.PositiveExtentDirection, L.VI(L.shrink()))
    tl.moveToEnd()
    if not ok:
        raise RuntimeError("outer wall extent")
    d.computeAll()
    health("wall front", res)
    roots = {}
    for g, e, m, z, o in L.root_edges(0.9):
        roots[g] = roots.get(g, 0) + 1
    res["roots"] = roots
    res["Z_WALL_FRONT"] = round(L.P("Z_WALL_FRONT"), 4)
    res["frame"] = L.body_dict()
    L.dump(res, "gf20/73_rules_wallfront.json")
    L.log("73 %s" % res)
    print(res)
