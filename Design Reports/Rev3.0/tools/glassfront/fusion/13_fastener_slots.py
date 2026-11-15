"""13 - radial stadium slots F1-F8 (master JSON fasteners.slot, cad_rules): slot_w x slot_l AT THE FLANGE FRONT, long
axis = (fN_ux, fN_uy) = unit vector from the fastener towards the glass centre, 0.5 deg draft wider to the back.
Sketch 'Fastener slots F1-F8' on the Z_FLANGE_FRONT plane: per slot two half circles (radius slot_w / 2) round
A, B = fN -/+ (slot_l - slot_w) / 2 * u and two tangent lines; A and B dimensioned by expressions -> FULLY
PARAMETRIC (moves with glass / border / fast_off / slot_* edits; v2 needed a re-run there).
  'Fastener slots F1-F8 (back)'           cut +Z from the flange front through the tube top (+1), draft_loc widening
  'Fastener slots F1-F4 (through the pads)' the same F1-F4 profiles cut -Z through the corner pads (t_gap + 1),
                                          draft_loc narrowing to the front (one continuous taper: the B-side pin
                                          shuts off on the A half at the pad top)
Made after all fillets (v2 practice: slot edges are convex, no fillet needed).
Expects: 12 done."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

H = "( slot_l - slot_w ) / 2"


def run(_context: str):
    L.check_doc()
    L.log("=== 13 start")
    b = L.body()
    sk = L.new_sketch("Fastener slots F1-F8", "Z_FLANGE_FRONT plane")
    sk.isComputeDeferred = False          # tangency + equal solved live (as in diag_stadium_probe)
    for k in range(1, 9):
        ax = "f%d_x - %s * f%d_ux" % (k, H, k)
        ay = "f%d_y - %s * f%d_uy" % (k, H, k)
        bx = "f%d_x + %s * f%d_ux" % (k, H, k)
        by = "f%d_y + %s * f%d_uy" % (k, H, k)
        L.stadium(sk, ax, ay, bx, by, "slot_w / 2")
    pr = L.solve(sk, 8)
    uc = L.under_constrained(sk)
    if uc:
        raise RuntimeError("slot sketch: %d curves not fully constrained" % uc)
    L.extrude(pr, "cut", "Z_TUBE_TOP - Z_FLANGE_FRONT + 1 mm", +1, L.grow("draft_loc"),
              "Fastener slots F1-F8 (back)", b)
    pads = [(L.P("f%d_x" % k), L.P("f%d_y" % k)) for k in (1, 2, 3, 4)]
    pr4 = L.pick_profiles(sk, lambda a, bb: any(abs((bb[0] + bb[1]) / 2 - x) < 1 and abs((bb[2] + bb[3]) / 2 - y) < 1
                                               for x, y in pads))
    if pr4.count != 4:
        raise RuntimeError("pad slot profiles %d" % pr4.count)
    L.extrude(pr4, "cut", "t_gap + 1 mm", -1, L.shrink("draft_loc"), "Fastener slots F1-F4 (through the pads)", b)
    # check: slot size and axis at the flange front from the sketch geometry
    chk = []
    for k in range(1, 9):
        ux, uy = L.P("f%d_ux" % k), L.P("f%d_uy" % k)
        chk.append(("F%d" % k, round(math.degrees(math.atan2(uy, ux)), 3)))
    n, bad = L.timeline_health()
    L.log("13 slot axes %s; %s; timeline %d unhealthy %s" % (chk, L.body_stats(), n, bad))
    print(chk, L.body_stats(), n, bad)
