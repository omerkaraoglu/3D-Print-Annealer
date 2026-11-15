"""Stage 3 (GF-1.1): run the INDEPENDENT verification toolchain's thick-section (and optionally thin-wall) check on a
frame STEP without touching tools/glassfront/verify: its modules are imported read-only (vcommon, mould_check) and
every output is redirected (--out / --img) to the folder given.
  <cqenv>\\Scripts\\python.exe gf11_thickness_check.py --frame f.step --out DIR --img DIR [--thin] [--list 4.0]
mould_check.thick_sections is called unchanged (voxel 0.2, 3D EDT, sphere dia = 2 x EDT) but with its `limit`
argument set to --list (default 4.0) so that the clusters thicker than that are listed: the verdict uses 5.0
(spots > 5.0), the report takes the top five clusters. Writes DIR\\thickness_check.json and DIR\\Thickness_map.png."""
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
    t0 = time.time()
    fr, G = ctx.frame, ctx.G
    res = {"frame": ctx.frame_path, "frame_info": getattr(ctx, "frame_info", None), "list_limit": lim}
    t = M.thick_sections(fr, G, ctx.imgdir, limit=lim)
    res["max_sphere_dia"] = t["max_sphere_dia"]
    res["spots_over_5.0"] = [s for s in t["spots_over_limit"] if s["max_sphere_dia"] > M.THICK_LIMIT]
    res["top5"] = t["spots_over_limit"][:5]
    res["thick_raw"] = t
    if "--thin" in argv:
        res["thin"] = M.thin_probe(fr, G)
    res["seconds"] = round(time.time() - t0, 1)
    p = os.path.join(ctx.outdir, "thickness_check.json")
    json.dump(res, open(p, "w"), indent=1, default=str)
    print("max sphere dia", res["max_sphere_dia"], "spots > 5.0:", len(res["spots_over_5.0"]))
    for s in res["top5"]:
        print("   top", s["max_sphere_dia"], s["at_abs"], s.get("what"))
    if "thin" in res:
        th = res["thin"]
        print("thin walls (non-lip):", [w for w in th["thin_walls"] if not w.get("what")][:10])
        print("thin gaps:", th["thin_gaps"][:10])
        print("v-notches:", [(v["at"], v["width_max"], v["class"]) for v in th.get("v_notches", [])][:12])
    print(p, res["seconds"], "s")


if __name__ == "__main__":
    main()
