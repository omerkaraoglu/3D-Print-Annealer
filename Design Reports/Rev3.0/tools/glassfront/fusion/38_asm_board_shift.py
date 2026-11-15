"""38 - stage 2, Part B: position the imported board and the panel (snapshot, as frame_v2 script 32):
  * board occurrence 'Rev3.0 PCB full (KiCad STEP)': translation (0, 0, board_dz) -> physical PCB back at Z 0
  * DS1 occurrence (the SAT070AT40D21 model 'TFT7...', LCM + CTP + both FPC tails with their folded U-loops and
    fingers, all RIGID solids): moved by ds1_dz = Z_PANEL_BACK - ds1_model_back (nominal -0.80) in model Z, so the
    panel back lands on Z_PANEL_BACK (-5.80) and the CTP front on Z_CTP_FRONT.
    TAILS: they move rigidly with the panel. In reality only the panel moves; the U-loops open up by 0.8 (U radius
    TFT 5.0 -> 5.4, CTP 5.55 -> 5.95, concept 3c) and the finger ends stay in J10 / J11. So in the model the legs
    attached to the panel are where they really are, the return legs / fingers are 0.8 too far forward (towards
    the glass) and sit 0.8 in front of their connectors; the loop bottoms keep their v2 y (in reality they rise by
    0.02-0.44, i.e. the model's y-clearance to the pocket bottom face is conservative).
The applied shifts are stored as attributes (gf/board_dz_applied, gf/ds1_dz_applied) so a re-run applies only the
difference when the parameters change. The occurrence positions are snapshots (not live expressions): re-run 38
after changing board_dz, sheet_t, g_bs or ds1_model_back."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def ds1_occ(board=None):
    """DS1 occurrence proxy in the ROOT context (top-most occurrence named TFT7... / ...SAT070...)"""
    hits = []
    ao = L.root().allOccurrences
    for i in range(ao.count):
        o = ao.item(i)
        if (o.name.startswith("TFT7") or "SAT070" in o.name) and L.BOARD_COMP in o.fullPathName:
            hits.append(o)
    hits.sort(key=lambda o: o.fullPathName.count("+"))
    if not hits:
        # fullPathName uses occurrence names, not component names: fall back to any TFT7 occurrence
        hits = [ao.item(i) for i in range(ao.count) if ao.item(i).name.startswith("TFT7")]
        hits.sort(key=lambda o: o.fullPathName.count("+"))
    if not hits:
        raise RuntimeError("DS1 occurrence not found")
    return hits[0]


def zmin(o):
    return min(L.bbox_mm(b)[4] for p, b in L.bodies_under(o))


def shift(o, key, want_mm):
    a = o.attributes.itemByName("gf", key)
    done = float(a.value) if a else 0.0
    d = want_mm - done
    if abs(d) > 1e-9:
        m = o.transform2
        t = m.translation
        t.z = t.z + d / 10.0
        m.translation = t
        o.transform2 = m
        o.attributes.add("gf", key, "%.6f" % want_mm)
    return done, d


def run(_context: str):
    L.check_doc()
    des = L.des()
    board = L.occ_by_comp(L.BOARD_COMP)
    pz0 = min(L.bbox_mm(b)[4] for p, b in L.bodies_under(board) if "TFT7" not in p)
    r1 = shift(board, "board_dz_applied", L.P("board_dz"))
    proxy = ds1_occ()
    z0 = zmin(proxy)
    r2 = shift(proxy, "ds1_dz_applied", L.P("ds1_dz"))   # Fusion: overrides only on the proxy from the root
    proxy = ds1_occ()
    z1 = zmin(proxy)
    if abs((z1 - z0) - r2[1]) > 1e-3:
        raise RuntimeError("DS1 moved %.4f in world Z, wanted %.4f" % (z1 - z0, r2[1]))
    if des.snapshots.hasPendingSnapshot:
        des.snapshots.add()
    bz = [(b.name, L.bbox_mm(b)[4:]) for p, b in L.bodies_under(proxy)]
    L.log("38 board %s, DS1 %s (%s) world zmin %.4f -> %.4f; DS1 bodies z %s" % (
        r1, r2, proxy.fullPathName, z0, z1, bz))
    print("board", r1, "DS1", r2, proxy.fullPathName, round(z0, 4), round(z1, 4), "DS1 z ranges", bz,
          "board occ z", round(board.transform2.translation.z * 10, 4), "board bodies zmin before", pz0)
