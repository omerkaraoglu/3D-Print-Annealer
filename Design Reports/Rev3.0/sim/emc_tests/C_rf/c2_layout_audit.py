"""C_rf step 2 - layout / return-path audit of the CURRENT routed board (task 4, and the geometry for tasks 1-3).

Input : geom.json from c1_export_geom.py (KiCad 10 export of a copy of KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb,
        zones as saved = KiCad's own fill).
Method: the filled copper of In1 (GND), In2 (3V3 plane, +5V island) and the board outline are rasterised at 0.05 mm
        (PIL); every fast/sensitive net is sampled every 0.1 mm along its real tracks (segments and arcs) and the copper
        under it is read from the raster. Voids in the In1 fill are labelled (scipy.ndimage) and attributed to the
        vias/pads inside them (merged anti-pads = slots). Distances use exact Euclidean distance transforms.
Output: results.json["layout"], plots/layout_*.png
"""
import json, math, collections
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *

G = json.load(open(GEOM))
RES = 0.05
ol = G["outline"][0]["outline"]
X0, Y0 = min(p[0] for p in ol) - 1, min(p[1] for p in ol) - 1
X1, Y1 = max(p[0] for p in ol) + 1, max(p[1] for p in ol) + 1
W, H = int((X1 - X0) / RES) + 1, int((Y1 - Y0) / RES) + 1
TC = "/Thermocouple front end (K-type, ADS1115)/"


def raster(polys):
    img = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(img)
    for p in polys:
        d.polygon([((x - X0) / RES, (y - Y0) / RES) for x, y in p["outline"]], fill=1)
        for h in p.get("holes", []):
            d.polygon([((x - X0) / RES, (y - Y0) / RES) for x, y in h], fill=0)
    return np.array(img, dtype=bool)


def zone(name, layer):
    for z in G["zones"]:
        if z["name"] == name:
            return z["fills"][layer]
    raise KeyError(name)


board = raster(G["outline"])
in1 = raster(zone("GND plane", "In1.Cu"))
in2_33 = raster(zone("3V3 plane", "In2.Cu"))
in2_5 = raster(zone("5V island", "In2.Cu"))
fgnd = raster(zone("GND top pour", "F.Cu"))
bgnd = raster(zone("GND bottom pour", "B.Cu"))
pix_area = RES * RES


def ij(x, y):
    return (np.clip(((np.asarray(y) - Y0) / RES).round().astype(int), 0, H - 1),
            np.clip(((np.asarray(x) - X0) / RES).round().astype(int), 0, W - 1))


# --- distance maps --------------------------------------------------------------------------------------------
d_edge = ndimage.distance_transform_edt(board) * RES                       # distance to the board edge
# plane edge: close small anti-pads (r <= 0.9 mm) first, so "edge" means the outer plane boundary or a real void
close_r = int(0.9 / RES)
yy, xx = np.ogrid[-close_r:close_r + 1, -close_r:close_r + 1]
disk = (xx ** 2 + yy ** 2) <= close_r ** 2
in1_closed = ndimage.binary_closing(in1, structure=disk)
d_in1_edge = ndimage.distance_transform_edt(in1_closed) * RES


# --- track sampling --------------------------------------------------------------------------------------------
def arc_points(t, step):
    (x1, y1), (xm, ym), (x2, y2) = (t["x1"], t["y1"]), (t["xm"], t["ym"]), (t["x2"], t["y2"])
    ax, ay, bx, by, cx, cy = x1, y1, xm, ym, x2, y2
    dd = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(dd) < 1e-9:
        n = max(2, int(t["len"] / step) + 1)
        return np.linspace(x1, x2, n), np.linspace(y1, y2, n)
    ux = ((ax ** 2 + ay ** 2) * (by - cy) + (bx ** 2 + by ** 2) * (cy - ay) + (cx ** 2 + cy ** 2) * (ay - by)) / dd
    uy = ((ax ** 2 + ay ** 2) * (cx - bx) + (bx ** 2 + by ** 2) * (ax - cx) + (cx ** 2 + cy ** 2) * (bx - ax)) / dd
    r = math.hypot(ax - ux, ay - uy)
    a1, am, a2 = (math.atan2(p[1] - uy, p[0] - ux) for p in ((ax, ay), (bx, by), (cx, cy)))
    # choose direction through the mid point
    def norm(a): return a % (2 * math.pi)
    span = norm(a2 - a1)
    if norm(am - a1) > span:
        span = span - 2 * math.pi
    n = max(2, int(abs(span) * r / step) + 1)
    a = a1 + np.linspace(0, span, n)
    return ux + r * np.cos(a), uy + r * np.sin(a)


def samples(net, step=0.1):
    out = []
    for t in G["tracks"]:
        if t["net"] != net:
            continue
        if t["kind"] == "arc":
            xs, ys = arc_points(t, step)
        else:
            n = max(2, int(t["len"] / step) + 1)
            xs, ys = np.linspace(t["x1"], t["x2"], n), np.linspace(t["y1"], t["y2"], n)
        out.append((t["layer"], t["w"], xs, ys, t["len"]))
    return out


GVIAS = np.array([(v["x"], v["y"], v["d"]) for v in G["vias"] if v["net"] == "GND"])
GPADS_THT = np.array([(p["x"], p["y"], max(p["sx"], p["sy"])) for p in G["pads"] if p["net"] == "GND" and p["tht"]])
SIGVIAS = [v for v in G["vias"] if v["net"] != "GND"]
PADS = G["pads"]
FP = {f["ref"]: f for f in G["footprints"]}


def pad(ref, num):
    for p in PADS:
        if p["ref"] == ref and p["num"] == str(num):
            return p
    raise KeyError((ref, num))


# decoupling capacitors: two-pad parts with one pad on GND and the other on a supply net
SUPPLY_NETS = ("+3V3", "+5V", "+1V2", "/Display/TFT_VDD", "/Display/TP_VDD", "/Display/BL_VIN", "/Display/VLED_P", "/Display/VLED_N")
CAPS = collections.defaultdict(list)
for ref in {p["ref"] for p in PADS if p["ref"].startswith("C")}:
    ps = [p for p in PADS if p["ref"] == ref]
    if len(ps) == 2 and any(p["net"] == "GND" for p in ps):
        other = [p for p in ps if p["net"] != "GND"][0]
        CAPS[other["net"]].append((ref, other["x"], other["y"], FP[ref]["value"]))

FAST = {}
RGB = [c + str(i) for c in "RGB" for i in range(8)] + ["PCLK", "HSYNC", "VSYNC", "DE"]
for s in RGB:
    FAST["RGB:" + s] = ["/Display/%s_T" % s, "/Display/%s" % s]
for i in range(8):
    FAST["8080:D%d" % i] = ["LCD_D%d" % i, "/Display/SSD_D%d" % i]
for s in ("WR", "DC", "CS", "RST"):
    FAST["8080:" + s] = ["LCD_" + s, "/Display/SSD_" + s]
FAST.update({"XTAL_IN": ["/Display/XTAL_IN"], "XTAL_OUT": ["/Display/XTAL_OUT"], "BUCK_SW": ["/Power/BUCK_SW"],
             "BL_SW": ["/Display/BL_SW"], "BL_PWM": ["/Display/BL_PWM"], "I2C_SDA": ["I2C_SDA"], "I2C_SCL": ["I2C_SCL"],
             "TP_INT": ["TP_INT"], "LCD_RST(J11 part)": [], "ZCD": ["/ZCD"], "TRIG": ["/TRIG"], "EN": ["/EN", "Net-(Q3-C)"],
             "TC_P": [TC + "TC_P", TC + "TCF_P"], "TC_N": [TC + "TC_N", TC + "TCF_N"], "ADC_RDY": ["ADC_RDY"],
             "VLED_P": ["/Display/VLED_P"], "VLED_N": ["/Display/VLED_N"]})
nets_present = set(G["nets"])
for k in list(FAST):
    FAST[k] = [n for n in FAST[k] if n in nets_present]
    if not FAST[k]:
        del FAST[k]


def net_audit(nets):
    rec = {"length_mm": 0.0, "layers_mm": collections.defaultdict(float), "vias": 0, "segments": []}
    over_void_mm = 0.0; void_pts = []; ref = collections.defaultdict(float); min_edge = 1e9; near_plane_edge_mm = 0.0
    min_plane_edge = 1e9; split_cross = 0; edge_lt = collections.defaultdict(float)
    myvias = [v for v in G["vias"] if v["net"] in nets]
    rec["vias"] = len(myvias)
    for net in nets:
        for layer, w, xs, ys, L in samples(net):
            rec["length_mm"] += L; rec["layers_mm"][layer] += L
            I, J = ij(xs, ys)
            dl = L / max(1, len(xs) - 1)
            de = d_edge[I, J]; min_edge = min(min_edge, float(de.min()))
            for thr in (3.0, 5.0):
                edge_lt[thr] += float((de < thr).sum() * dl)
            near_own = np.zeros(len(xs), bool)
            for v in myvias:
                near_own |= np.hypot(xs - v["x"], ys - v["y"]) < 0.75
            if layer == "F.Cu":
                ok = in1[I, J]
                bad = (~ok) & (~near_own)
                over_void_mm += float(bad.sum() * dl)
                if bad.any():
                    void_pts += list(zip(xs[bad][::5].round(2), ys[bad][::5].round(2)))
                ref["In1 GND"] += float(ok.sum() * dl)
                pe = d_in1_edge[I, J]
                min_plane_edge = min(min_plane_edge, float(pe[~near_own].min()) if (~near_own).any() else 1e9)
                near_plane_edge_mm += float(((pe < 1.0) & ~near_own).sum() * dl)   # within 1 mm (5 h) of a plane edge
            elif layer == "B.Cu":
                r33, r5 = in2_33[I, J], in2_5[I, J]
                lab = np.where(r33, 1, np.where(r5, 2, 0))
                lab_eff = lab[~near_own] if (~near_own).any() else lab
                for code, name in ((1, "In2 +3V3"), (2, "In2 +5V island"), (0, "no In2 copper")):
                    ref[name] += float((lab_eff == code).sum() * dl)
                nz = lab_eff[lab_eff != 0]                      # ignore the 0.4-0.5 mm split gap itself
                if len(nz) > 1:
                    split_cross += int((nz[1:] != nz[:-1]).sum())
    rec["layers_mm"] = dict(rec["layers_mm"])
    rec["reference_mm"] = dict(ref)
    rec["F.Cu_over_In1_void_mm"] = over_void_mm
    rec["F.Cu_void_points"] = void_pts[:10]
    rec["F.Cu_within_1mm_of_In1_plane_edge_mm"] = near_plane_edge_mm
    rec["min_dist_to_In1_plane_edge_mm"] = min_plane_edge if min_plane_edge < 1e8 else None
    rec["In2_split_crossings_on_B.Cu"] = split_cross
    rec["min_board_edge_mm"] = min_edge if min_edge < 1e8 else None
    rec["len_within_3mm_of_edge_mm"] = edge_lt[3.0]
    rec["len_within_5mm_of_edge_mm"] = edge_lt[5.0]
    vrec = []
    for v in myvias:
        dg = np.hypot(GVIAS[:, 0] - v["x"], GVIAS[:, 1] - v["y"])
        k = int(np.argmin(dg))
        e2e = dg[k] - v["d"] / 2 - GVIAS[k, 2] / 2
        # reference after the via: In2 net under the via position (B.Cu side), and nearest cap to that In2 net
        ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)          # the via's own anti-pad is a hole: look on a 1.0 mm ring
        I, J = ij(v["x"] + 1.0 * np.cos(ang), v["y"] + 1.0 * np.sin(ang))
        n33, n5 = int(in2_33[I, J].sum()), int(in2_5[I, J].sum())
        in2net = "none" if n33 + n5 == 0 else ("+3V3" if n33 >= n5 else "+5V") + ("" if min(n33, n5) == 0 else " (at split)")
        cap_d = None; cap_ref = None
        key = in2net.split(" ")[0]
        if key in CAPS:
            ds = [(math.hypot(c[1] - v["x"], c[2] - v["y"]), c[0]) for c in CAPS[key]]
            cap_d, cap_ref = min(ds)
        vrec.append({"net": v["net"], "x": v["x"], "y": v["y"], "gnd_via_cc_mm": float(dg[k]), "gnd_via_edge_mm": float(e2e),
                     "In2_net_below": in2net, "nearest_decap_on_In2_net": cap_ref, "decap_dist_mm": cap_d})
    rec["via_detail"] = vrec
    return rec


audit = {k: net_audit(v) for k, v in FAST.items()}

# --- In1 void analysis (anti-pads and merged slots) ----------------------------------------------------------
sel = board & ndimage.binary_dilation(in1_closed, iterations=int(2.0 / RES))        # SELV plane region (+2 mm)
voids, nv = ndimage.label(sel & ~in1)
objs = ndimage.find_objects(voids)
allv = [(v["x"], v["y"], v["net"], v["d"]) for v in G["vias"]] + [(p["x"], p["y"], p["ref"] + "." + p["num"] + ":" + p["net"], max(p["sx"], p["sy"])) for p in PADS if p["tht"]]
vI, vJ = ij([a[0] for a in allv], [a[1] for a in allv])
lab_at = voids[vI, vJ]
void_list = []
for k, sl in enumerate(objs, start=1):
    if sl is None:
        continue
    m = voids[sl] == k
    area = m.sum() * pix_area
    if area > 400:          # the mains band / outside region, not a hole in the plane
        continue
    ext = (math.hypot((sl[0].stop - sl[0].start), (sl[1].stop - sl[1].start))) * RES
    members = [allv[i] for i in np.where(lab_at == k)[0]]
    cy = (sl[0].start + sl[0].stop) / 2 * RES + Y0; cx = (sl[1].start + sl[1].stop) / 2 * RES + X0
    void_list.append({"x": round(cx, 2), "y": round(cy, 2), "area_mm2": round(area, 3), "extent_mm": round(ext, 2),
                      "n_members": len(members), "members": [str(m_[2])[-28:] for m_ in members][:8]})
merged = [v for v in void_list if v["n_members"] >= 2]
long_voids = [v for v in void_list if v["extent_mm"] > 2.2]
unexplained = [v for v in void_list if v["n_members"] == 0 and v["area_mm2"] > 0.3]

# which fast nets pass over merged / long voids (F.Cu samples within the void bbox)
def nets_over(vd):
    hits = []
    for k, nets in FAST.items():
        for net in nets:
            for layer, w, xs, ys, L in samples(net, 0.1):
                if layer != "F.Cu":
                    continue
                I, J = ij(xs, ys)
                lab = voids[I, J]
                kk = voids[ij(vd["x"], vd["y"])]
                if kk and np.any(lab == kk):
                    hits.append(k)
    return sorted(set(hits))
for v in merged + long_voids:
    v["fast_nets_over_it"] = nets_over(v)

# --- stitching: GND via spacing --------------------------------------------------------------------------------
pts = np.vstack([GVIAS[:, :2], GPADS_THT[:, :2]]) if len(GPADS_THT) else GVIAS[:, :2]
from scipy.spatial import cKDTree
tree = cKDTree(pts)
dnn, _ = cKDTree(GVIAS[:, :2]).query(GVIAS[:, :2], k=2)
nn = dnn[:, 1]
# largest distance from any In1 copper pixel (SELV) to the nearest GND via / GND THT pad
ys_, xs_ = np.nonzero(in1[::4, ::4])
P = np.c_[xs_ * 4 * RES + X0, ys_ * 4 * RES + Y0]
dmin, _ = tree.query(P)
k = int(np.argmax(dmin))
# edge fence: points on the outline that lie next to In1 copper -> distance to nearest GND via
olp = np.array(ol)
seg = []
for a, b_ in zip(olp, np.roll(olp, -1, axis=0)):
    n = max(1, int(np.hypot(*(b_ - a)) / 0.5))
    seg.append(np.c_[np.linspace(a[0], b_[0], n, endpoint=False), np.linspace(a[1], b_[1], n, endpoint=False)])
seg = np.vstack(seg)
I, J = ij(seg[:, 0], seg[:, 1])
near_in1 = ndimage.binary_dilation(in1, iterations=int(1.5 / RES))[I, J]
de_fence, _ = tree.query(seg[near_in1])
lam_1g_air = C0 / 1e9 * 1e3
lam_1g_fr4 = lam_1g_air / math.sqrt(4.4)
stitch = {"gnd_vias": int(len(GVIAS)), "vias_total": len(G["vias"]), "nn_spacing_mm": {"median": float(np.median(nn)), "p95": float(np.percentile(nn, 95)), "max": float(nn.max())},
          "max_dist_In1_copper_to_gnd_via_mm": float(dmin[k]), "at": [round(float(P[k, 0]), 2), round(float(P[k, 1]), 2)],
          "edge_fence_max_dist_to_gnd_via_mm": float(de_fence.max()), "edge_fence_p95_mm": float(np.percentile(de_fence, 95)),
          "lambda_1GHz_air_mm": lam_1g_air, "lambda_over_20_air_mm": lam_1g_air / 20, "lambda_over_20_FR4_mm": lam_1g_fr4 / 20}

# --- plane areas -----------------------------------------------------------------------------------------------
areas = {"In1_GND_mm2": float(in1.sum() * pix_area), "In2_3V3_mm2": float(in2_33.sum() * pix_area), "In2_5V_mm2": float(in2_5.sum() * pix_area),
         "board_mm2": float(board.sum() * pix_area), "F_GND_pour_mm2": float(fgnd.sum() * pix_area), "B_GND_pour_mm2": float(bgnd.sum() * pix_area)}
for nm, msk in (("In2_3V3", in2_33), ("In2_5V", in2_5)):
    ys_, xs_ = np.nonzero(msk)
    areas[nm + "_bbox"] = [round(xs_.min() * RES + X0, 2), round(xs_.max() * RES + X0, 2), round(ys_.min() * RES + Y0, 2), round(ys_.max() * RES + Y0, 2)]
ys_, xs_ = np.nonzero(in1)
areas["In1_bbox"] = [round(xs_.min() * RES + X0, 2), round(xs_.max() * RES + X0, 2), round(ys_.min() * RES + Y0, 2), round(ys_.max() * RES + Y0, 2)]
areas["In1_over_In2_3V3_overlap_mm2"] = float((in1 & in2_33).sum() * pix_area)
areas["In1_over_In2_5V_overlap_mm2"] = float((in1 & in2_5).sum() * pix_area)


# --- copper area of noisy nets ---------------------------------------------------------------------------------
def poly_area(pts_):
    if len(pts_) < 3:
        return 0.0
    a = np.array(pts_)
    return 0.5 * abs(np.dot(a[:, 0], np.roll(a[:, 1], 1)) - np.dot(a[:, 1], np.roll(a[:, 0], 1)))
cu_area = {}
for net in ("/Power/BUCK_SW", "/Display/BL_SW", "/Display/XTAL_IN", "/Display/XTAL_OUT", "/Display/PCLK_T", "/Display/PCLK"):
    a_tr = sum(t["len"] * t["w"] for t in G["tracks"] if t["net"] == net)
    a_pad = sum(poly_area(p["poly"]) for p in PADS if p["net"] == net)
    a_zone = sum(poly_area(pp["outline"]) for z in G["zones"] if z["net"] == net for L, fl in z["fills"].items() for pp in fl)
    cu_area[net] = {"tracks_mm2": a_tr, "pads_mm2": a_pad, "zones_teardrops_mm2": a_zone, "total_mm2": a_tr + a_pad + a_zone}


# --- hot loops from pad centres (planar F.Cu part) -------------------------------------------------------------
def loop_area(seq):
    pts_ = [(pad(r, n)["x"], pad(r, n)["y"]) for r, n in seq]
    per = sum(math.hypot(pts_[i][0] - pts_[i - 1][0], pts_[i][1] - pts_[i - 1][1]) for i in range(len(pts_)))
    return poly_area(pts_), per, pts_
loops = {}
for name, seq in {
        "buck input loop C330-U30(VIN,GND)": [("C330", 1), ("U30", 3), ("U30", 1), ("C330", 2)],
        "buck input loop C331-U30(VIN,GND)": [("C331", 1), ("U30", 3), ("U30", 1), ("C331", 2)],
        "buck output loop L30-C333-U30GND": [("U30", 2), ("L30", 1), ("L30", 2), ("C333", 1), ("C333", 2), ("U30", 1)],
        "boost switching loop U11SW-D111-C125-U11GND": [("U11", 1), ("D111", 2), ("D111", 1), ("C125", 1), ("C125", 2), ("U11", 2)],
        "boost input loop C124-L11-U11": [("C124", 1), ("L11", 1), ("L11", 2), ("U11", 1), ("U11", 2), ("C124", 2)],
        "crystal loop Y10-C110-C111": [("Y10", 1), ("C110", 1), ("C110", 2), ("C111", 2), ("C111", 1), ("Y10", 3)]}.items():
    a, per, pts_ = loop_area(seq)
    loops[name] = {"planar_area_mm2": a, "perimeter_mm": per, "vertical_area_if_return_in_In1_mm2": per * 0.2175,
                   "pads": [(r + "." + str(n)) for r, n in seq]}


# --- decoupling: per IC supply pin, nearest cap (same net) and an inductance estimate ---------------------------
# L_mount = 2 * L_via(0.2 mm F.Cu->In1, 0.6/0.3 via: ~0.06 nH each) + trace L' * distance (microstrip 0.25 mm over 0.2 mm:
# L' = Z0*sqrt(eeff)/c with Z0=59 ohm, eeff=3.3 -> 0.36 nH/mm) + package ESL (0402 0.35 nH, 0603 0.45, 0805 0.6 nH; assumed,
# typical MLCC vendor data) - the cap and pin each reach In1 through their own GND via (spreading inductance in the plane,
# L_sp = mu0*h/(2 pi) ln(d/r_via) with h = 0.2175 mm).
def via_L(h_mm, r_mm=0.15, pitch_mm=1.0):
    return MU0 * h_mm * 1e-3 / (2 * math.pi) * math.log(pitch_mm / r_mm) * 1e9 if h_mm > 0 else 0.0
ESL = {"0402": 0.35, "0603": 0.45, "0805": 0.6, "1206": 0.8}
def size_of(ref):
    fp = FP[ref]["fpid"]
    for k in ESL:
        if k in fp:
            return k
    return "0805"
decap = {}
for ic, pins in {"U10 SSD1963 (3V3)": ("U10", "+3V3"), "U10 SSD1963 (1V2)": ("U10", "+1V2"), "U3 ESP32 (3V3)": ("U3", "+3V3"),
                 "U20 ADS1115 (3V3)": ("U20", "+3V3"), "U30 TPS562201 (VIN 5V)": ("U30", "+5V"), "U31 LD1117 (out 1V2)": ("U31", "+1V2"),
                 "U11 MIC2288 (VIN)": ("U11", "/Display/BL_VIN"), "U6 74AHC1G14 (3V3)": ("U6", "+3V3"), "J10 TFT_VDD": ("J10", "/Display/TFT_VDD"),
                 "J11 TP_VDD": ("J11", "/Display/TP_VDD")}.items():
    ref, net = pins
    pps = [p for p in PADS if p["ref"] == ref and p["net"] == net]
    rows = []
    for p in pps:
        if net not in CAPS:
            continue
        ds = sorted((math.hypot(c[1] - p["x"], c[2] - p["y"]), c[0], c[3]) for c in CAPS[net])
        d, cref, val = ds[0]
        Ltr = 0.36 * d * 1.2                               # 1.2 = routing detour factor (assumed)
        Lv = 2 * via_L(0.2175)
        Lesl = ESL[size_of(cref)]
        rows.append({"pin": p["num"], "cap": cref, "value": val, "dist_mm": round(d, 2), "L_trace_nH": round(Ltr, 2), "L_vias_nH": round(Lv, 3),
                     "ESL_nH": Lesl, "L_loop_nH": round(Ltr + Lv + Lesl, 2)})
    decap[ic] = rows

# --- summaries for the report ----------------------------------------------------------------------------------
summary = {}
for k, r in audit.items():
    vias = r["via_detail"]
    summary[k] = {"len_mm": round(r["length_mm"], 1), "layers": rnd(r["layers_mm"], 1), "vias": r["vias"],
                  "ref_mm": rnd(r["reference_mm"], 1), "F_over_void_mm": round(r["F.Cu_over_In1_void_mm"], 2),
                  "F_within1mm_plane_edge_mm": round(r["F.Cu_within_1mm_of_In1_plane_edge_mm"], 1),
                  "In2_split_crossings": r["In2_split_crossings_on_B.Cu"], "min_board_edge_mm": rnd(r["min_board_edge_mm"], 2),
                  "len_within_5mm_edge": round(r["len_within_5mm_of_edge_mm"], 1),
                  "worst_gnd_return_via_edge_mm": round(max([v["gnd_via_edge_mm"] for v in vias]), 2) if vias else None,
                  "via_In2_net": sorted(set(v["In2_net_below"] for v in vias)),
                  "worst_decap_dist_mm_for_In2_ref_change": round(max([v["decap_dist_mm"] or 0 for v in vias]), 1) if vias else None}

rgb = {k: v for k, v in summary.items() if k.startswith("RGB:")}
res = {
    "source_board": "KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb (md5 82cfd2615aa8e4511e89f13eb2a7eb6c, 2026-11-13 17:17), exported from a copy",
    "counts": {"tracks_items": len(G["tracks"]), "segments": sum(1 for t in G["tracks"] if t["kind"] == "seg"),
               "arcs": sum(1 for t in G["tracks"] if t["kind"] == "arc"), "vias": len(G["vias"]), "gnd_vias": int(len(GVIAS)),
               "signal_and_power_vias": len(SIGVIAS), "teardrop_zones": sum(1 for z in G["zones"] if z["priority"] == 30000),
               "footprints": len(G["footprints"])},
    "stackup_assumed_from_spec_12_1": "F.Cu / 0.2 mm prepreg er 4.4 / In1 GND / 1.0 mm core / In2 3V3 + 5V island / 0.2 mm prepreg / B.Cu, 35 um Cu",
    "plane_areas": rnd(areas, 1),
    "nets": summary,
    "rgb_length_range_mm": [min(v["len_mm"] for v in rgb.values()), max(v["len_mm"] for v in rgb.values())],
    "in1_voids": {"total_voids": len(void_list), "merged_groups(>=2 members)": merged, "voids_extent_gt_2.2mm": long_voids,
                  "unexplained_voids_gt_0.3mm2": unexplained[:20]},
    "stitching": rnd(stitch, 2),
    "noisy_copper_area": rnd(cu_area, 2),
    "hot_loops": rnd(loops, 2),
    "decoupling": decap,
    "caps_by_net": {k: [c[0] + " " + c[3] for c in v] for k, v in CAPS.items()},
    "via_details_rgb_8080": {k: rnd(audit[k]["via_detail"], 2) for k in audit if audit[k]["via_detail"] and (k.startswith("RGB") or k.startswith("8080"))},
}
save_section("layout", res)

# --- plots ---------------------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 7.5))
img = np.zeros((H, W, 3))
img[board] = (0.93, 0.93, 0.93)
img[in2_33 & ~in1] = (0.6, 0.75, 1.0)
img[in2_5] = (1.0, 0.8, 0.5)
img[in1] = img[in1] * 0.5 + np.array([0.45, 0.85, 0.45]) * 0.5
ax.imshow(img, extent=(X0, X0 + W * RES, Y0 + H * RES, Y0), interpolation="nearest")
cols = {"F.Cu": "r", "B.Cu": "b"}
for k, nets in FAST.items():
    for net in nets:
        for layer, w, xs, ys, L in samples(net, 0.3):
            ax.plot(xs, ys, cols.get(layer, "k"), lw=0.5)
ax.plot(GVIAS[:, 0], GVIAS[:, 1], ".", ms=1.2, color="k")
for v in merged + long_voids:
    ax.plot(v["x"], v["y"], "mo", mfc="none", ms=9)
ax.set_title("Rev3.0 board: In1 GND (green), In2 3V3 (blue, where no In1), In2 +5V island (orange);\nfast nets F.Cu red / B.Cu blue; GND vias black; merged In1 voids magenta")
ax.set_xlabel("x / mm (KiCad page)"); ax.set_ylabel("y / mm")
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "layout_planes_fastnets.png"), dpi=170)
print(json.dumps({"counts": res["counts"], "rgb_len": res["rgb_length_range_mm"], "stitch": res["stitching"], "voids": {"n": len(void_list), "merged": merged, "long": long_voids[:5]},
                  "loops": res["hot_loops"], "areas": res["plane_areas"]}, indent=1, default=str)[:6000])
