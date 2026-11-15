"""65 - stage 3, lead round 3: save + Fusion archive ONLY. The frame is frozen (verified STEP sha256 47742d2f...): the
frame STEP / STL are NOT exported. The assembly STEP is not re-exported either because only bodies of the hidden
variants changed (R4 rivets, S8 spacers); the script checks that those occurrences are hidden and that the frame
fingerprint equals the one recorded by 64 (round3_hardware.json) before saving."""
import importlib
import json
import os
import sys

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

DEFAULTS = {"glass_t": 3.0, "t_sheet": 1.0, "t_opt": 0.3, "t_bond": 1.0, "t_gap": 1.0, "stud_fl_d": 5.5,
            "stud_fl_k": 0.7, "cb_w": 7.4, "cb_l": 9.0}
HIDDEN = ["Rivets R4 F1-F4 (hidden)", "Washers, nuts, spacers S8 F5-F8 (hidden)"]
MSG = ("GF-1.1 round 3 (hardware only, frame frozen): R4 large-flange rivet head dia 14 (DIN 7337 K14, k 1.6), S8 shim "
       "DIN 988 7 x 13 x 1.0")


def run(_context: str):
    d = L.check_doc()
    for k, v in DEFAULTS.items():
        if abs(L.P(k) - v) > 1e-9:
            raise RuntimeError("%s = %r not %r" % (k, L.P(k), v))
    n, bad = L.timeline_health()
    if bad or d.analyses.sectionAnalyses.count or d.snapshots.hasPendingSnapshot:
        raise RuntimeError("not clean")
    p64 = os.path.join(L.GF_DIR, "64_gf11_round3_hardware.py")
    ns = {"__name__": "gf_64_lib", "__file__": p64}
    exec(compile(open(p64, encoding="utf-8").read(), p64, "exec"), ns)
    ref = json.load(open(os.path.join(L.SCR, "gf11", "round3_hardware.json")))["frame_fingerprint (unchanged)"]
    now = ns["fingerprint"](L.body())
    if now != ref:
        raise RuntimeError("frame fingerprint differs: %s vs %s" % (now, ref))
    vis = {cn: L.occ_by_comp(cn).isLightBulbOn for cn in HIDDEN}
    if any(vis.values()):
        raise RuntimeError("variant occurrence visible: %s" % vis)
    ok, ver = L.save_version(MSG)
    em = d.exportManager
    pf = os.path.join(L.MECH, "Rev3.0_GlassFront.f3d")
    f3d = em.execute(em.createFusionArchiveExportOptions(pf))
    L.log("65 saved %s (log version %s); f3d %s %d bytes; frame fingerprint %s; hidden %s" %
          (ok, ver, f3d, os.path.getsize(pf), now, vis))
    print("saved", ok, ver, "f3d", f3d, os.path.getsize(pf), vis)
