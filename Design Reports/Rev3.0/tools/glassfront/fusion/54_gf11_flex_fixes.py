"""54 - stage 3 (GF-1.1): fixes after the first GF-1.1 flex test (90, TAG gf11):
  * glass 2.0: 'Root fillets tube_sw_r - F5-F8 tube to step wall (rule)' failed - the vertical tube / step-wall
    junction is only Z_STEPWALL_BACK - Z_FLANGE_BACK = 1.0 high there, R1.2 does not fit; glass 1.1 (snap): the
    junction vanishes, the R1.2 rule took the merged tube-base edges and the R0.5 tube rule then failed.
    -> tube_sw_r = min(1.2; max(0.5; 0.75 x junction height)): 1.2 at glass 3.0 / 4.0, 0.75 at 2.0, 0.5 at 1.1
  * glass 4.0: the tube top lies 0.5 below the step-wall back, its R0.5 root fillet to the step wall reaches r 7.6
    from F5-F8 and the coring groove (r_out 7.7) clipped it (4 sharp concave edge pieces).
    -> core_r_out 7.5 (0.1 clear of that fillet: fast_off - s_ring - fillet_root - 0.1), groove 1.3 wide at the top
       / 1.185 at the floor, floor rounds core_floor_r 0.4 (flat floor 0.385; R0.5 would leave a 0.185 sliver)
Then checks glass 2.0 / 1.1 / 4.0 (health, unfilleted-root census) and returns to 3.0."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    d = L.check_doc()
    L.log("=== 54 start")
    L.set_param("tube_sw_r", "min(1.2 mm; max(0.5 mm; 0.75 * ( Z_STEPWALL_BACK - Z_FLANGE_BACK )))", "mm",
                "GF-1.1: F5-F8 tube to step-wall blend (item 6): 1.2 at glass 3.0 / 4.0, 0.75 at 2.0 (junction 1.0 "
                "high), 0.5 at the level snap (no junction)")
    L.set_param("core_r_out", "7.5 mm", "mm", "GF-1.1: coring groove outer radius at the tube top (0.1 clear of the "
                                            "R0.5 tube / step-wall fillet at glass 4.0; skin 1.5)")
    L.set_param("core_floor_r", "0.4 mm", "mm", "GF-1.1: coring groove floor rounds (groove 1.185 wide at the floor, "
                                              "flat 0.385)")
    ups = d.userParameters
    out = []
    for g in ("2.0 mm", "1.1 mm", "4.0 mm", "3.0 mm"):
        ups.itemByName("glass_t").expression = g
        d.computeAll()
        n, bad = L.timeline_health()
        roots = {}
        for grp, e, m, z, o in L.root_edges(0.9):
            roots[grp] = roots.get(grp, 0) + 1
        out.append((g, "healthy" if not bad else bad, round(L.body().volume, 4), L.body().faces.count,
                    round(L.P("tube_sw_r"), 3), roots))
    if abs(L.P("glass_t") - 3.0) > 1e-9:
        raise RuntimeError("glass_t not restored")
    L.log("54 %s" % out)
    for r in out:
        print(r)
