"""Stage 5 check, part 2 (python 3 + shapely): J5 geometry against the board and the frame documents (read only).

    python stage5_check.py export.json frame_v2_params.json out.json

  - zone connection: share of a ring just outside the pad (r 3.60 mm) and of the pad area covered by the GND fill on
    F.Cu / In1 / B.Cu (solid connection -> 100 %); anti-pad on In2 (radius of the 3V3 / +5V fill around the hole)
  - distances from the J5 copper (every layer) to: mains copper (net classes Mains / MainsHeater), any other-net copper,
    J20, BP16, holes, board edge; courtyard gaps
  - silkscreen: J5 designator and earth mark against mask openings, via holes, other silk, edge; ownership test
    (d_oth >= d_own + 0.30 and >= 2 d_own, silk_refdes rule)
  - frame side (frame v2 / GF-2.1 share the PCB seat): support ribs, shelf window, H8 boss, panel back; B-side copper,
    bare area (B.Mask opening 5.6) and screw head (ISO 7045 M3 pan head, dk 5.6, + 0.2 mm radial hole play: 3.2 hole, M3 shank >= 2.87, hole
    tolerance) against the rib contact faces (frame doc 1.2: ribs >= 1.0 mm from B.Cu pads)
  - lug side: M3 ring lug (ring 6.4, barrel 5.2 wide, 17 mm centre-to-end) at the chosen tongue direction against J20,
    the H8 PT-screw head (assumed dia 6.0) / washer keep-out and other-net bare copper; distance to the stud FH9
"""
import json
import math
import sys

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

X = json.load(open(sys.argv[1]))
FP = json.load(open(sys.argv[2], encoding="utf-8"))
J = X["j5"]
cx, cy = J["pos"]
C = Point(cx, cy)
PAD = C.buffer(3.5, 256)
R = {}
MAINS_NC = ("Mains", "MainsHeater")


def poly(pp):
    out = []
    for pts, holes in pp:
        if len(pts) >= 3:
            g = Polygon(pts, [h for h in holes if len(h) >= 3])
            out.append(g if g.is_valid else g.buffer(0))
    return unary_union(out) if out else Polygon()


cu = [dict(c, g=poly(c["poly"])) for c in X["cu"]]
# 1 zone connection / anti-pads
zc = {}
for ln in ("F.Cu", "In1.Cu", "B.Cu", "In2.Cu"):
    fills = unary_union([c["g"] for c in cu if c["layer"] == ln and c["kind"] == "zone" and c["net"] == "GND" and not c["teardrop"]])
    ring = [Point(cx + 3.6 * math.cos(a * math.pi / 90), cy + 3.6 * math.sin(a * math.pi / 90)) for a in range(180)]
    share = sum(1 for p in ring if fills.buffer(1e-4).contains(p)) / len(ring)
    inner = fills.intersection(PAD).area / PAD.area if not fills.is_empty else 0.0
    other = unary_union([c["g"] for c in cu if c["layer"] == ln and c["kind"] == "zone" and c["net"] not in ("GND", "")])
    anti = round(other.distance(C), 3) if not other.is_empty else None
    zc[ln] = dict(gnd_ring_r3p6_covered=round(share, 3), gnd_fill_over_pad=round(inner, 3), other_net_fill_from_centre=anti,
                  other_net_fill_gap_to_pad=None if anti is None else round(anti - 3.5, 3))
R["zone_connection"] = zc
# 2 distances
def nearest(pred, layers=("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"), target=PAD):
    best = (1e9, None)
    for c in cu:
        if c["layer"] in layers and pred(c) and not c["g"].is_empty:
            d = c["g"].distance(target)
            if d < best[0]:
                best = (d, "%s %s %s %s" % (c["layer"], c["kind"], c.get("ref", "") + ("." + c["num"] if c.get("num") else ""), c["net"]))
    return round(best[0], 3), best[1]


R["mains_copper"] = nearest(lambda c: c["nc"] in MAINS_NC)
R["other_net_copper_any_layer"] = nearest(lambda c: c["net"] not in ("GND",) and c.get("ref") != "J5")
R["other_net_copper_per_layer"] = {ln: nearest(lambda c: c["net"] not in ("GND",) and c.get("ref") != "J5", (ln,)) for ln in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")}
R["J20_pads"] = nearest(lambda c: c.get("ref") == "J20", ("F.Cu", "B.Cu"))
R["BP16_copper"] = nearest(lambda c: c.get("ref") == "BP16", ("B.Cu",))
bp16m = unary_union([poly(m["poly"]) for m in X["mask"] if m["ref"] == "BP16"])
R["BP16_bare_area_to_J5_pad"] = round(bp16m.distance(PAD), 3)
hole_j5 = C.buffer(1.6)
hd = sorted((Point(h[0], h[1]).buffer(h[2]).distance(hole_j5), h[3]) for h in X["holes"] if not h[3].startswith("pad J5"))
R["nearest_holes_edge_to_edge"] = [(round(d, 3), w) for d, w in hd[:3]]
edge = unary_union([poly([e]) for e in X["edge"]])
R["board_edge_to_pad"] = round(edge.distance(PAD), 3)
crt = {r: {k: poly(v) for k, v in d.items()} for r, d in X["crt"].items()}
for side in ("F.CrtYd", "B.CrtYd"):
    mine = crt["J5"][side]
    R["courtyard_gap_" + side] = sorted([(round(mine.distance(d[side]), 3), r) for r, d in crt.items() if r != "J5" and side in d])[:4]
# 3 silk
silkF = [dict(s, g=poly(s["poly"])) for s in X["silk"] if s["layer"] == "F.SilkS"]
ref = unary_union([s["g"] for s in silkF if s["ref"] == "J5" and "J5" in s["what"]])
mark = unary_union([s["g"] for s in silkF if s["ref"] == "J5" and "J5" not in s["what"]])
maskF = [(poly(m["poly"]), "%s.%s" % (m["ref"], m["num"])) for m in X["mask"] if m["layer"] == "F.Mask"]
vh = [(Point(h[0], h[1]).buffer(h[2]), h[3]) for h in X["holes"] if h[3].startswith("via")]
oth = [(s["g"], s["ref"] + " " + s["what"][:24]) for s in silkF if s["ref"] != "J5" and not s["g"].is_empty]
sil = {}
for name, g in (("designator J5", ref), ("earth mark", mark)):
    b = g.bounds
    sil[name] = dict(bbox=[round(v, 3) for v in b],
                     mask=min((round(m.distance(g), 3), w) for m, w in maskF),
                     via_hole=min((round(v.distance(g), 3), w) for v, w in vh),
                     other_silk=min((round(o.distance(g), 3), w) for o, w in oth),
                     edge=round(edge.boundary.distance(g), 3))
sil["designator_to_earth_mark"] = round(ref.distance(mark), 3)
d_own = ref.distance(crt["J5"]["F.CrtYd"])
d_oth = min((ref.distance(d["F.CrtYd"]), r) for r, d in crt.items() if r != "J5" and "F.CrtYd" in d)
sil["ownership"] = dict(d_own=round(d_own, 3), d_oth=(round(d_oth[0], 3), d_oth[1]),
                        ok=d_oth[0] >= d_own + 0.30 and d_oth[0] >= 2 * d_own)
m_oth = min((mark.distance(d["F.CrtYd"]), r) for r, d in crt.items() if r != "J5" and "F.CrtYd" in d)
sil["earth_mark_to_pad_mask"] = round(mark.distance(C.buffer(3.5 + J["mask_exp_F"])), 3)
sil["earth_mark_to_other_courtyard"] = (round(m_oth[0], 3), m_oth[1])
R["silk"] = sil
# 4 frame side (KiCad abs in the frame documents -> local = abs - 20)
ribs = [(r["rib"], box(r["x0"] - 20, r["y0"] - 20, r["x1"] - 20, r["y1"] - 20)) for r in FP["support_ribs"]["per_rib"]]
fr = {}
bareB = unary_union([poly(m["poly"]) for m in X["mask"] if m["ref"] == "J5" and m["layer"] == "B.Mask"]).intersection(PAD)
fr["J5 bare back area (B.Mask opening within the copper): equivalent dia"] = round(2 * math.sqrt(bareB.area / math.pi), 3)
for name, g in (("B copper dia 7.0 (masked rim 5.6-7.0)", PAD), ("B bare area (mask opening)", bareB),
                ("screw head dk 5.6 centred", C.buffer(2.8)), ("screw head dk 5.6 + 0.2 radial hole play", C.buffer(3.0))):
    fr[name] = sorted((round(rb.distance(g), 3), "rib %d" % n) for n, rb in ribs)[:2]
win = box(2.62, 1.6, 162.32, 96.4)
fr["shelf window edge (local x 2.62 / y 96.4) to B copper"] = round(win.exterior.distance(PAD), 3)
fr["shelf window edge to screw head dk 5.6 + play"] = round(win.exterior.distance(C.buffer(3.0)), 3)
fr["H8 boss dia 8.0 (-4.8, 89.0) to B copper"] = round(Point(-4.8, 89.0).buffer(4.0).distance(PAD), 3)
fr["H7 boss dia 8.0 (10.0, 103.8) to B copper"] = round(Point(10.0, 103.8).buffer(4.0).distance(PAD), 3)
lv = FP["derived_levels_mm"]
fr["Z levels"] = dict(PCB_back=lv["Z_PCB"], shelf_back=lv["Z_SHELF_BACK"], Formex_back=lv["Z_SEAT"], panel_back_v2=lv["Z_PANEL_BACK"],
                      panel_back_GF21_nominal=-5.80, panel_back_GF21_min=-5.08)
fr["screw head height 2.4 -> gap to Formex / panel back (v2)"] = (round(2.4 - 2.4 + (-lv["Z_SEAT"] - 2.4), 2), round(-lv["Z_PANEL_BACK"] - 2.4, 2))
fh9 = [s for s in FP["stud_holes"] if s["name"] == "FH9"][0]
F9 = (fh9["x_abs"] - 20, fh9["y_abs_down"] - 20)
fr["FH9 (local)"] = F9
fr["J5 centre to FH9 centre"] = round(math.dist((cx, cy), F9), 2)
R["frame"] = fr
# 5 lug on the F side
J20c = crt["J20"]["F.CrtYd"]
H8head = Point(-4.8, 89.0).buffer(3.0)
H8wash = Point(-4.8, 89.0).buffer(4.7)
bareF = [(m, w) for m, w in maskF if not w.startswith("J5.")]
TH = 150
lug = {}
for ring_d, tw, L in ((6.4, 4.5, 15.0), (6.4, 5.2, 17.0)):
    g = translate(rotate(Point(0, 0).buffer(ring_d / 2).union(box(0, -tw / 2, L, tw / 2)), TH, origin=(0, 0)), cx, cy)
    bare = translate(rotate(Point(0, 0).buffer(ring_d / 2).union(box(0, -tw / 2, 6.0, tw / 2)), TH, origin=(0, 0)), cx, cy)
    lug["ring %.1f / barrel %.1f / %.0f mm" % (ring_d, tw, L)] = dict(
        J20_courtyard=round(g.distance(J20c), 2), H8_head_dia6=round(g.distance(H8head), 2), H8_washer_keepout=round(g.distance(H8wash), 2),
        bare_metal_to_other_net_bare_copper=min((round(m.distance(bare), 2), w) for m, w in bareF),
        mains_copper=nearest(lambda c: c["nc"] in MAINS_NC, ("F.Cu",), g))
d = (math.cos(math.radians(TH)), math.sin(math.radians(TH)))
lug["tongue direction deg (KiCad, y down)"] = TH
ax = LineString([(cx, cy), (cx + 30 * d[0], cy + 30 * d[1])]).intersection(edge)
first = min((g for g in getattr(ax, "geoms", [ax]) if not g.is_empty), key=lambda g: g.distance(C), default=None)
lug["board edge crossed at (local), distance from J5 centre"] = None if first is None else (
    [round(v, 2) for v in first.interpolate(first.project(C)).coords[0]], round(first.distance(C), 2))
R["lug"] = lug
R["j5"] = J
json.dump(R, open(sys.argv[3], "w"), indent=1)
print(json.dumps(R, indent=1))
