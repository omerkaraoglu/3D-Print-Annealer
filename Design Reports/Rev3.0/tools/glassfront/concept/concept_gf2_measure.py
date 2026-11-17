"""GF-2.0 concept (equal borders) - measurements from the models in the repo. READ-ONLY on every input.

Run with the CadQuery environment (python -B, no byte-code written anywhere):
    <cqenv>\\Scripts\\python.exe -B concept_gf2_measure.py
Writes (this folder only):
    concept_gf2_measured.json   numbers + section polylines used by concept_gf2_calc.py
    concept_gf2_measure_out.txt run log

Inputs (read only):
    Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step      GF-1.1 frame (verified STEP, sha256 47742d2f...)
    <TEMP>/gf_verify/board_full.step                                  kicad-cli export used by the GF-1.1 verification
                                                                      (board + 145 models incl. DS1 with its folded tails)
    Design Reports/Rev3.0/tools/frame_v2/out/board_geom.json          Edge.Cuts outline, courtyards
    Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json        GF-1.1 master
The helpers come from tools/glassfront/verify/vcommon.py (imported, not modified).

Coordinates: X = KiCad abs x, model Y = -(abs y), Z = 0 at the PCB back, -Z to the front. Everything reported in
abs (x, y down). The DS1 model sits at the v2 stand-off (panel back Z -5.0); it is moved by Z_PANEL_BACK - (-5.0) =
-0.80 like the GF-1.1 verification does (tails moved rigidly with the panel = the panel-side legs; the connector legs
of the real tails stay at J10/J11, see the calc).
"""
import sys
sys.dont_write_bytecode = True
import json
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.normpath(os.path.join(HERE, "..", "verify"))
sys.path.insert(0, VERIFY)
import vcommon as C            # noqa: E402  (read-only helpers)
import numpy as np             # noqa: E402

OUT_JSON = os.path.join(HERE, "concept_gf2_measured.json")
OUT_TXT = os.path.join(HERE, "concept_gf2_measure_out.txt")
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def r3(v):
    return None if v is None else round(float(v), 3)


def bb_abs(shape):
    b = shape.BoundingBox()
    return {"x": [r3(b.xmin), r3(b.xmax)], "y": [r3(-b.ymax), r3(-b.ymin)], "z": [r3(b.zmin), r3(b.zmax)]}


def section_x(shape, x):
    """section by the plane X = x -> list of loops [(y_abs, Z)...]"""
    sec = C.plane_section(shape, "x", x)
    out = []
    if sec is None:
        return out
    for f in sec.Faces():
        for l in C.face_loops_3d(f, 0.01):
            out.append([[r3(-p[1]), r3(p[2])] for p in l])
    return out


def section_y(shape, y_abs):
    """section by the plane y = y_abs -> loops [(x, Z)...]"""
    sec = C.plane_section(shape, "y", -y_abs)
    out = []
    if sec is None:
        return out
    for f in sec.Faces():
        for l in C.face_loops_3d(f, 0.01):
            out.append([[r3(p[0]), r3(p[2])] for p in l])
    return out


def section_z(shape, z):
    sec = C.plane_section(shape, "z", z)
    out = []
    if sec is None:
        return out
    for f in sec.Faces():
        for l in C.face_loops_abs(f, 0.01):
            out.append([[r3(p[0]), r3(p[1])] for p in l])
    return out


res = {"about": "GF-2.0 concept measurements (concept_gf2_measure.py)", "date": time.strftime("%Y-%m-%d %H:%M")}
G = C.GF()
L = G.L
res["params_revision"] = G.revision
panel_dz = L["Z_PANEL_BACK"] - C.V2_PANEL_BACK
res["panel_dz"] = r3(panel_dz)

# ------------------------------------------------------------------------------------------- frame GF-1.1
t0 = time.time()
frame, finfo = C.load_solid(C.GF_STEP)
res["frame_step"] = {k: finfo[k] for k in ("file", "sha256", "volume_mm3", "valid", "bbox_abs")}
log("frame STEP read %.1f s, sha256 %s..., volume %.1f mm3" % (time.time() - t0, finfo["sha256"][:12], finfo["volume_mm3"]))
SECX = {}
for x in (30.0, 60.0, 80.0, 103.85, 140.0, 175.0):
    SECX[str(x)] = [l for l in section_x(frame, x) if max(p[0] for p in l) > 100.0]
    ys = [p[0] for l in SECX[str(x)] for p in l]
    log("  frame section x %.2f: %d loops, y extent %.2f .. %.2f" % (x, len(SECX[str(x)]), min(ys), max(ys)))
res["frame_sections_x"] = SECX


def y_hits(loops, z, ymin=100.0):
    """y values where the section boundary crosses Z = z (bottom zone)"""
    hits = []
    for l in loops:
        a = np.array(l)
        b = np.roll(a, -1, axis=0)
        for p, q in zip(a, b):
            if (p[1] - z) * (q[1] - z) < 0 or (abs(p[1] - z) < 1e-9 and abs(q[1] - z) > 1e-9):
                t = (z - p[1]) / (q[1] - p[1])
                y = p[0] + t * (q[0] - p[0])
                if y >= ymin:
                    hits.append(round(float(y), 3))
    return sorted(set(hits))


def z_hits(loops, y):
    hits = []
    for l in loops:
        a = np.array(l)
        b = np.roll(a, -1, axis=0)
        for p, q in zip(a, b):
            if (p[0] - y) * (q[0] - y) < 0:
                t = (y - p[0]) / (q[0] - p[0])
                hits.append(round(float(p[1] + t * (q[1] - p[1])), 3))
    return sorted(set(hits))


probe = {}
for x in ("60.0", "103.85", "140.0"):
    lp = SECX[x]
    probe[x] = {"y_crossings_at_Z": {str(z): y_hits(lp, z) for z in (-12.0, -10.0, -9.0, -7.0, -5.0, -3.0, -1.0, 1.0, 3.0)},
                "Z_crossings_at_y": {str(y): z_hits(lp, y) for y in (118.5, 119.5, 125.0, 140.0, 149.0, 152.0, 160.0, 174.0)}}
    log("  x %s: y crossings at Z -10 %s, at Z -3 %s, at Z +1 %s" % (x, probe[x]["y_crossings_at_Z"]["-10.0"],
                                                                     probe[x]["y_crossings_at_Z"]["-3.0"], probe[x]["y_crossings_at_Z"]["1.0"]))
res["frame_probe"] = probe
SECZ = {}
for z in (-11.0, -9.0, -6.0, -1.0, 2.0):
    loops = section_z(frame, z)
    SECZ[str(z)] = [l for l in loops if max(p[1] for p in l) > 110.0]
res["frame_sections_z_bottom"] = SECZ
log("  plan sections (bottom zone) at Z", list(SECZ))

# ------------------------------------------------------------------------------------------- board + DS1
t0 = time.time()
bstep = C.board_step()
items = C.board_items(bstep, panel_dz=panel_dz)
res["board_step"] = C.file_id(bstep)
res["board_step"].pop("mtime", None)
log("board STEP %s read %.1f s, %d items" % (bstep, time.time() - t0, len(items)))

pcb = [s for r, p, s in items if r == "PCB"]
pcb_bb = [bb_abs(s) for s in pcb]
res["pcb_bbox"] = pcb_bb
log("  PCB bbox", pcb_bb)
# PCB bottom edge between the ears: section of the PCB at x 103.85 / 60
pcb_edge = {}
for x in (45.0, 60.0, 103.85, 140.0, 160.0):
    ys = [p[0] for s in pcb for l in section_x(s, x) for p in l]
    zs = [p[1] for s in pcb for l in section_x(s, x) for p in l]
    pcb_edge[str(x)] = {"y_max": r3(max(ys)) if ys else None, "Z": [r3(min(zs)), r3(max(zs))] if zs else None}
res["pcb_bottom_edge"] = pcb_edge
log("  PCB bottom edge (y max at x):", {k: v["y_max"] for k, v in pcb_edge.items()}, "Z", pcb_edge["103.85"]["Z"])

tails = {}
for r, p, s in items:
    if r != "DS1":
        continue
    b = bb_abs(s)
    if p.startswith(("tft_tail", "ctp_tail")):
        d = {"bbox": b}
        # exit cross-section just outside the panel edge (y 119.0)
        for yy in (119.2, 120.0, 122.0, 125.0, 130.0):
            loops = section_y(s, yy)
            if loops:
                xs = [q[0] for l in loops for q in l]
                zs = [q[1] for l in loops for q in l]
                d["sec_y%.1f" % yy] = {"x": [r3(min(xs)), r3(max(xs))], "Z": [r3(min(zs)), r3(max(zs))], "n_loops": len(loops)}
        # side profile at a mid x of the tail
        xm = {"tft": 103.85, "ctp": 60.0}[p[:3]]
        d["profile_x"] = xm
        d["profile"] = section_x(s, xm)
        tails[p] = d
        log("  DS1 %-10s bbox x %s y %s z %s; exit (y 119.2) x %s Z %s" % (p, b["x"], b["y"], b["z"],
                                                                          d.get("sec_y119.2", {}).get("x"), d.get("sec_y119.2", {}).get("Z")))
    elif p.startswith(("tft_fingers", "ctp_fingers")):
        tails[p] = {"bbox": b}
        log("  DS1 %-10s bbox x %s y %s z %s" % (p, b["x"], b["y"], b["z"]))
    else:
        tails.setdefault("_panel_parts", {})[p] = b
res["ds1"] = tails
pp = tails.get("_panel_parts", {})
for k, b in pp.items():
    log("  DS1 panel part %-12s x %s y %s z %s" % (k, b["x"], b["y"], b["z"]))

# components near the bottom edge (y > 100) and their Z extent (back-side protrusions are Z < 0)
comps = []
for r, p, s in items:
    if r in ("PCB", "DS1"):
        continue
    b = bb_abs(s)
    if b["y"][1] > 100.0 and b["x"][1] > 30.0 and b["x"][0] < 175.0:
        comps.append({"ref": r, "part": p, "bbox": b})
comps.sort(key=lambda c: c["bbox"]["z"][0])
res["components_bottom_zone"] = comps
back = [c for c in comps if c["bbox"]["z"][0] < -0.01]
log("  components with y > 100 in x 30..175: %d; reaching in front of the PCB back (Z < 0): %d" % (len(comps), len(back)))
for c in back:
    log("    %-6s z %s y %s x %s" % (c["ref"], c["bbox"]["z"], c["bbox"]["y"], c["bbox"]["x"]))
for ref in ("J10", "J11"):
    for c in comps:
        if c["ref"] == ref:
            log("  %s bbox x %s y %s z %s" % (ref, c["bbox"]["x"], c["bbox"]["y"], c["bbox"]["z"]))

bg = C.board_geom()
res["board_outline_bottom"] = [[r3(x), r3(y)] for x, y in bg["outline"][0] if y > 112.0]
res["courtyards"] = {f["ref"]: f["crtyd"] for f in bg["fps"] if f["ref"] in ("J10", "J11", "J20", "J2", "H6", "H7")}

json.dump(res, open(OUT_JSON, "w"), indent=1)
open(OUT_TXT, "w").write("\n".join(LOG) + "\n")
log("wrote", os.path.basename(OUT_JSON), os.path.basename(OUT_TXT))
