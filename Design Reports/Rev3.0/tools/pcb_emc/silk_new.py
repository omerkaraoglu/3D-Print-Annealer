"""Designators for new / moved parts only, by the silk_refdes method (tools/silk_refdes/refdes_place.py: same obstacle
raster, candidate generator, ownership test and parameters); every other designator stays where it is and is an
obstacle (its ink box + clr_label 0.25 mm).

    python silk_new.py geom.json REF1,REF2,... out.json

geom.json from tools/silk_refdes/refdes_geom.py (KiCad python) of the current board. Writes the chosen candidate per
ref (absolute mm): style, angle, text centre, rect, d_own, d_oth. Parts with no clean candidate are reported (they
would need a legend map; none expected here)."""
import json
import sys

sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/silk_refdes")
import refdes_place as RP  # noqa: E402

geom, refs, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
G = json.load(open(geom, encoding="utf-8"))
STY = G["styles"]


def style_of(h, w):
    best = min(STY, key=lambda k: abs(STY[k][0] - h) + abs(STY[k][1] - w))
    return best


# existing designators of all other parts as silk obstacles (grown by clr_label - clr_silk)
grow = RP.P["clr_label"] - RP.P["clr_silk"]
nobs = 0
for fp in G["fps"]:
    r = fp["ref"]
    rn = fp.get("refnow")
    if r in refs or r in RP.SKIP or not rn or not rn["visible"] or rn["layer"] != "F.Silkscreen":
        continue
    st = style_of(rn["h"], rn["w"])
    ang = "90" if round(rn["ang"]) % 180 == 90 else "0"
    ib = G["ink"][r][st][ang]
    x, y = rn["pos"]
    x0, y0, x1, y1 = x + ib[0] - grow, y + ib[1] - grow, x + ib[2] + grow, y + ib[3] + grow
    G["silk"].append({"cls": "REF", "text": r, "uuid": "", "poly": [[[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]]]})
    nobs += 1
grid = RP.Grid()
forb, cyforb = RP.build_obstacles(G, grid)
forbS = grid.integral(forb)
parts_l = [RP.Part(f) for f in G["fps"] if f["ref"] not in RP.SKIP]
parts = {p.ref: p for p in parts_l}
res = {}
placed = []
for r in refs:
    p = parts[r]
    cs = RP.gen_candidates(p, G, grid, forbS, RP.neighbours(parts_l, p), extra_rects=placed)
    ok = [c for c in cs if all(RP.rect_dist(c.rect, q) >= RP.P["clr_label"] for q in placed)]
    if not ok:
        res[r] = None
        print(r, "NO candidate")
        continue
    c = ok[0]
    placed.append(c.rect)
    res[r] = dict(style=c.style, ang=c.ang, side=c.side, gap=c.gap, off=c.off, rect=c.rect,
                  centre=((c.rect[0] + c.rect[2]) / 2, (c.rect[1] + c.rect[3]) / 2), size=STY[c.style],
                  d_own=c.d_own, d_oth=c.d_oth, cost=c.cost, n_cands=len(cs))
    print("%-5s %s %3d side %s gap %.2f off %.2f centre (%.3f, %.3f) d_own %.2f d_oth %.2f cands %d" % (
        r, c.style, c.ang, c.side, c.gap, c.off, res[r]["centre"][0], res[r]["centre"][1], c.d_own, c.d_oth, len(cs)))
json.dump(res, open(out, "w"), indent=1)
print("other designators as obstacles:", nobs)
