"""Stage 4 (GF-2.0): gf11_thickness_check.py for the GF-2.0 frame. The INDEPENDENT verification toolchain's
thick-section and thin-wall checks (tools/glassfront/verify: vcommon, mould_check - imported read-only, unchanged;
outputs redirected) on a frame STEP, with the GF-2.0 master params.
  <cqenv>\\Scripts\\python.exe -B gf20_thickness_check.py --frame f.step --out DIR --img DIR [--thin] [--list 4.0]
Only adaptation: the toolchain's thin probe still asks for the F5-F8 counterbore floor (GF-1.1 item, removed at GF-2.0);
G.cb_floor_z is wrapped so that F5-F8 return the F1-F4 floor level (it only places two extra probe planes). Its fixed
vertical probe sections (e.g. 'chin x 103.85 (bottom)', 'F5 slot axis') are kept as they are: at GF-2.0 they cut the
bridge / tail pocket and the top border. Writes DIR\\thickness_check.json and DIR\\Thickness_map.png."""
import json
import os
import sys
import time

sys.dont_write_bytecode = True
VER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verify"))
sys.path.insert(0, VER)

import vcommon as C                     # noqa: E402
import mould_check as M                 # noqa: E402


def main():
    argv = sys.argv[1:]
    lim = float(argv[argv.index("--list") + 1]) if "--list" in argv else 4.0
    ctx = C.Context(argv)
    G = ctx.G
    orig = G.cb_floor_z
    G.cb_floor_z = lambda n: orig("F1") if n in ("F5", "F6", "F7", "F8") else orig(n)
    t0 = time.time()
    fr = ctx.frame
    res = {"frame": ctx.frame_path, "frame_info": getattr(ctx, "frame_info", None), "params": G.path,
           "params_revision": G.revision, "list_limit": lim}
    t = M.thick_sections(fr, G, ctx.imgdir, limit=lim)
    res["max_sphere_dia"] = t["max_sphere_dia"]
    res["spots_over_5.0"] = [s for s in t["spots_over_limit"] if s["max_sphere_dia"] > M.THICK_LIMIT]
    res["top5"] = t["spots_over_limit"][:5]
    res["top_local"] = t.get("top_spots")
    res["thick_raw"] = t
    if "--thin" in argv:
        if "--thin-min" in argv:
            M.THIN_MIN = float(argv[argv.index("--thin-min") + 1])      # brief: list walls < 1.2 (toolchain 1.0)
        res["thin_min_mm"] = M.THIN_MIN
        res["thin"] = M.thin_probe(fr, G)
        # GF-2.0 extra probes: between the flange back and the land-plate back (step face, rib feet, cell ribs),
        # vertical sections through the divider rib, the CTP compartment and across the pocket floor / cells
        import numpy as np
        extra = []
        for name, z in (("GF-2.0 floors / step / rib feet Z -9.0", -9.0), ("GF-2.0 bridge back Z -8.3", -8.3)):
            sec = C.plane_section(fr, "z", z)
            if sec is not None:
                loops = [C.face_loops_abs(f, 0.002) for f in sec.Faces()]
                extra.append(M._thin_eval(G, {"kind": "plan", "name": name, "z": z}, loops, "x, y_abs"))
        for name, axis, val, lim in (("GF-2.0 divider rib x 79.92", "x", 79.92, (110, 152)),
                                     ("GF-2.0 CTP compartment x 60", "x", 60.0, (110, 152)),
                                     ("GF-2.0 across the pocket / cells y 138", "y", 138.0, (10, 200))):
            sec = C.plane_section(fr, axis, -val if axis == "y" else val)
            if sec is None:
                continue
            loops = []
            for f in sec.Faces():
                ll = []
                for l in C.face_loops_3d(f, 0.002):
                    h = -l[:, 1] if axis == "x" else l[:, 0]
                    ll.append(np.column_stack([h, l[:, 2]]))
                if np.max(ll[0][:, 0]) < lim[0] or np.min(ll[0][:, 0]) > lim[1]:
                    continue
                loops.append(ll)
            if loops:
                extra.append(M._thin_eval(G, {"kind": "vertical", "name": name, "z": None}, loops,
                                          "y_abs, Z" if axis == "x" else "x, Z"))
        res["thin_extra_gf20"] = extra
        res["thin_extra_walls"] = [dict(r, plane=p["name"]) for p in extra for r in p["slots_or_walls"]]
    res["seconds"] = round(time.time() - t0, 1)
    p = os.path.join(ctx.outdir, "thickness_check.json")
    json.dump(res, open(p, "w"), indent=1, default=str)
    print("max sphere dia", res["max_sphere_dia"], "spots > 5.0:", len(res["spots_over_5.0"]))
    for s in res["top5"]:
        print("   top", s["max_sphere_dia"], s["at_abs"], s.get("what"))
    if "thin" in res:
        th = res["thin"]
        print("thin walls (all):", [(w.get("plane"), w.get("class"), w.get("width_min", w.get("w_min")), w.get("at"),
                                     w.get("what")) for w in th["thin_walls"]][:40])
        print("thin gaps:", th["thin_gaps"][:10])
        print("not by design:", th["not_by_design"][:20])
        print("knife edges:", th["steel_knife_edges"][:10])
        print("extra GF-2.0 probes:", [(w.get("plane"), w.get("class"), w.get("at"), w.get("what")) for w in res["thin_extra_walls"]][:30])
    print(p, res["seconds"], "s")


if __name__ == "__main__":
    main()
