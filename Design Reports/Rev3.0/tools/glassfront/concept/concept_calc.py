"""Rev3.0 glass-front controller - concept calculations, rev GF-1.0 (study 2026-11-15 + lead amendments A1-A8).

Plain Python 3 (math + json only). Run from this folder:
    C:\\Users\\lenovo\\AppData\\Local\\Programs\\Python\\Python311\\python.exe concept_calc.py > concept_calc_out.txt
Writes:
    concept_params.json                                     (flat list, this folder)
    <repo>/Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json   (frozen master for CAD / drawings)
Reads (read-only): Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2_params.json, Design Reports/Rev3.0/tools/frame_v2/out/board_geom.json

Coordinates as frame v2: X = KiCad abs x, y = KiCad abs y (down), Z = 0 at the physical PCB back, -Z to the front.
Front view: u = -(x - xc), v = yc - y about the glass centre.  ASSUMED = engineering assumption (concept.md sec. 9).
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
V2JSON = os.path.join(ROOT, "Mechanical", "Rev3.0_Frame", "Rev3.0_Frame_v2_params.json")
BOARD = os.path.join(ROOT, "Design Reports", "Rev3.0", "tools", "frame_v2", "out", "board_geom.json")
MASTER = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
PARAMS = []


def prm(name, value, unit, note, group):
    PARAMS.append({"name": name, "value": round(value, 4) if isinstance(value, float) else value,
                   "unit": unit, "group": group, "note": note})
    return value


def r4(v):
    return round(v, 4) if isinstance(v, float) else v


def hdr(t):
    print("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


def stack(items):
    return sum(abs(t) for _, t in items), math.sqrt(sum(t * t for _, t in items))


def show_stack(title, items, nominal=0.0, quiet=False):
    wc, rss = stack(items)
    print(f"  {title}: nominal {nominal:+.3f}  WC +-{wc:.3f}  RSS +-{rss:.3f}  -> WC [{nominal-wc:+.3f}, {nominal+wc:+.3f}]  RSS [{nominal-rss:+.3f}, {nominal+rss:+.3f}]")
    if not quiet:
        for n, t in items:
            print(f"      +-{t:.3f}  {n}")
    return wc, rss


# =============================================================================================
# 1. INPUTS
# =============================================================================================
v2 = json.load(open(V2JSON))
V2P = {p["name"]: p["value"] for p in v2["user_parameters"]}
V2 = dict(panel_x0=V2P["panel_x0"], panel_x1=V2P["panel_x1"], panel_y0=V2P["panel_y0"], panel_y1=V2P["panel_y1"],
          Z_SEAT=V2P["Z_SEAT"], Z_SHELF_BACK=V2P["Z_SHELF_BACK"], Z_FORMEX_FRONT=V2P["Z_PANEL_BACK"], formex_t=V2P["sheet_t"],
          panel_t=V2P["panel_t"], standoff=V2P["standoff"], loop_clr=V2P["loop_clr"], Z_TROUGH_TOP=V2P["Z_TROUGH_TOP"],
          tr_x0=V2P["tr_x0"], tr_x1=V2P["tr_x1"], wall=V2P["wall"], seat_w=V2P["seat_w"],
          loop_ctp=(V2P["loop_ctp_x0"], V2P["loop_ctp_x1"], V2P["loop_ctp_y1"]),
          loop_tft=(V2P["loop_tft_x0"], V2P["loop_tft_x1"], V2P["loop_tft_y1"]))
HOLES = {f"H{i}": (V2P[f"h{i}_x"], V2P[f"h{i}_y"]) for i in range(1, 10)}
DS = dict(L=164.90, H=100.00, lcm_tol=0.30, ctp_tol=0.10,
          AA_fv=(4.03, 4.87, 154.08, 85.92), BEZEL_fv=(2.70, 3.75, 156.80, 89.10), VA_fv=(3.53, 4.23, 155.08, 86.92),
          tail_exit_above_back={"TFT": 2.6, "CTP": 3.9}, tail_t=0.30)
board = json.load(open(BOARD))
OUTLINE = board["outline"][0]                                   # outer board outline incl. ears (abs)
FPS = {f["ref"]: f for f in board["fps"]}


def fv_to_abs(r):
    l, t, w, h = r
    x1 = V2["panel_x1"] - l
    return (x1 - w, x1, V2["panel_y0"] + t, V2["panel_y0"] + t + h)


AA, VA, BZ = fv_to_abs(DS["AA_fv"]), fv_to_abs(DS["VA_fv"]), fv_to_abs(DS["BEZEL_fv"])
assert all(abs(a - b) < 0.006 for a, b in zip(VA, (V2P["va_x0"], V2P["va_x1"], V2P["va_y0"], V2P["va_y1"]))), VA

E_G, NU_G, ALPHA_G, RHO_G = 70000.0, 0.22, 9e-6, 2.5e-3
E_F, NU_F = 3500.0, 0.35
ALPHA_F = {"flow 30": 30e-6, "design 50": 50e-6, "bound 70": 70e-6}
ALPHA_S = 12e-6
# glass options: thickness -> (type, thickness tol, characteristic bending strength MPa)  [R2 sec.1, EN 12150, ASSUMED CS]
GLASS = {1.1: ("chemically strengthened (aluminosilicate or soda-lime)", 0.10, 250.0),
         2.0: ("chemically strengthened soda-lime", 0.20, 250.0),
         3.0: ("thermally tempered (CS if the supplier cannot temper < 3.2)", 0.20, 120.0),
         4.0: ("thermally tempered", 0.20, 120.0)}
TG_LIST = sorted(GLASS)

# =============================================================================================
# 2. DRIVING PARAMETERS (frozen GF-1.0)
# =============================================================================================
D = "driving"
glass_t = prm("glass_t", 3.0, "mm", "glass thickness, DRIVING; design valid for 1.1 / 2.0 / 3.0 / 4.0 (sec. 3 table)", D)
t_opt = prm("t_opt", 0.30, "mm", "optical bond glass -> CTP lens (LOCA / silicone gel, hard stops 0.30 +-0.03; R1 sec.3.3)", D)
t_bond = prm("t_bond", 1.0, "mm", "glass -> land bond line, elastic gap-filling bead, nominal (set by the flush jig)", D)
t_sheet = prm("t_sheet", 1.0, "mm", "oven front sheet, steel (0.8-1.5); lip height above the seat ring = t_sheet", D)
t_gap = prm("t_gap", 1.0, "mm", "flange front -> sheet back between hard stops (seat ring + corner pads); VHB 1.1 or foam 1.5 lives here", D)
g_bs = prm("g_bs", 0.8, "mm", "panel back -> Formex air gap, nominal (back-stop)", D)
print_inset = prm("print_inset", 0.30, "mm", "print window = AA inset by this per side; ALTERNATIVE AA + 0.25 (R1 sec.3.3 step 7) = -0.25", D)
B = prm("border", 14.0, "mm", "window edge -> glass edge, top / left / right (A1)", D)
glass_y1 = prm("glass_y1", 154.00, "mm", "glass bottom edge, abs y (A1; chin)", D)
R_glass = prm("R_glass", 6.0, "mm", "glass corner radius (R2: >= 3)", D)
g2 = prm("g2", 0.40, "mm", "gap glass edge -> lip inner face at 20 C", D)
lip_w = prm("lip_w", 1.00, "mm", "lip width (root)", D)
g1 = prm("g1", 0.40, "mm", "gap lip outer face -> sheet cut-out edge at 20 C", D)
seat_w = prm("seat_ring_w", 1.50, "mm", "sheet-seat ring width outside the lip (s 1.4 .. 2.9)", D)
pocket_clr = prm("pocket_clr", 0.80, "mm", "panel outline -> clearance pocket wall, per side", D)
bead_w = prm("bead_w", 4.0, "mm", "glass->frame bead width after squeeze (A1)", D)
bead_edge = prm("bead_edge", 0.9, "mm", "bead outer edge inside the glass edge (A1: >= 0.9)", D)
bead_pocket_min = prm("bead_pocket_min", 1.0, "mm", "min distance bead inner edge -> pocket face (A1)", D)
fast_off = prm("fast_off", 11.0, "mm", "fastener centre outside the glass edge, in x and y (corners) / in the normal direction (mid-sides)", D)
fl_beyond = prm("flange_beyond_glass", 21.0, "mm", "flange outline = glass + this (pad/tube R9 + 1 mm beyond the fastener)", D)
fl_R = prm("flange_R", 10.0, "mm", "flange outer corner radius (centre = corner fastener)", D)
fl_t = prm("flange_t", 2.5, "mm", "flange thickness = wall (v2)", D)
slot_w = prm("slot_w", 5.4, "mm", "fastener stadium slot width (A4 asked 5.0; 5.4 needed for a dia-4.8 rivet, sec. 11)", D)
slot_l = prm("slot_l", 7.0, "mm", "fastener stadium slot length, long axis towards the glass centre (A4 asked 6.5)", D)
pad_d = prm("pad_d", 18.0, "mm", "corner pad dia (front, top at Z_SHEET_BACK) and fastener tube top dia (back)", D)
tube_h = prm("tube_h", 2.5, "mm", "fastener tube height above the flange back (washer / rivet seat)", D)
pip_d = prm("pip_d", 1.5, "mm", "stand-off pip dia at the base (A2), 1 deg draft", D)
pip_h = prm("pip_h", 0.50, "mm", "stand-off pip height above the land (A2), +-0.05", D)
vhb_w = prm("tape_w", 12.0, "mm", "VHB strip width (standard 12 mm roll, 3M 5952 class, 1.1 thick) (A3)", D)
tape_margin = prm("tape_margin", 1.0, "mm", "min flat flange face beyond each tape edge (A3)", D)
trough_R = prm("trough_R", 1.5, "mm", "tail-pocket bottom inner corner radius (keeps 1.5 to the TFT loop corner)", D)
s_fl = fast_off  # fastener line offset

# =============================================================================================
# 3. LEVELS as functions of the driving parameters, for the four glass thicknesses
# =============================================================================================
hdr("3. LEVELS (Z = 0 at the PCB back, -Z to the front). PCB side (Z >= -5.0) = v2")
EXPR = [  # name, expression, note
    ("Z_TROUGH_TOP", "4.05 (v2)", "tail-pocket walls / bottom beam top, outside the board only"),
    ("Z_PCB", "0 (v2)", "PCB back = boss / support-rib / pocket-wall tops"),
    ("Z_SHELF_BACK", "-2.10 (v2)", "shelf back"),
    ("Z_SEAT", "-4.60 (v2)", "shelf front = Formex back (Formex PSA-bonded)"),
    ("Z_FORMEX_FRONT", "Z_SEAT - 0.40", "Formex front (= v2 panel back)"),
    ("Z_PANEL_BACK", "Z_FORMEX_FRONT - g_bs", "panel back, nominal (floats with the tolerances, sec. 4c)"),
    ("Z_CTP_FRONT", "Z_PANEL_BACK - panel_t", "CTP cover-lens front (panel_t 5.32)"),
    ("Z_GLASS_BACK", "Z_CTP_FRONT - t_opt", "glass printed face"),
    ("Z_GLASS_FRONT", "Z_GLASS_BACK - glass_t", "FLUSH PLANE = lip top = sheet front"),
    ("Z_SHEET_BACK", "Z_GLASS_FRONT + t_sheet", "sheet back = seat-ring top = corner-pad tops = parting plane"),
    ("Z_FLANGE_FRONT", "Z_SHEET_BACK + t_gap", "flange front face (tape / gasket on it)"),
    ("Z_FLANGE_BACK", "Z_FLANGE_FRONT + flange_t; = Z_STEPWALL_BACK if within 0.5 of Z_LANDPLATE_BACK (level snap)", "flange back"),
    ("Z_LAND", "Z_GLASS_BACK + t_bond", "glass land = recess floor (bead, pips)"),
    ("Z_PIP_TOP", "Z_LAND - pip_h", "stand-off pip tops"),
    ("Z_LANDPLATE_BACK", "Z_LAND + wall", "land-plate back (corner-cell floors, PCB-boss bases)"),
    ("Z_STEPWALL_BACK", "max(Z_FLANGE_BACK, Z_LANDPLATE_BACK); snap both to it if they differ < 0.5", "back of the step wall"),
    ("Z_TUBE_TOP", "Z_FLANGE_BACK + tube_h", "fastener tube top = washer / rivet seat"),
    ("Z_TAIL_TFT_EXIT", "Z_PANEL_BACK - 2.6", "TFT tail centre at the panel edge (panel model, estimated)"),
    ("Z_TAIL_CTP_EXIT", "Z_PANEL_BACK - 3.9", "CTP tail centre at the panel edge (estimated)"),
    ("Z_LOOP_FRONT", "Z_TAIL_CTP_EXIT - 0.15", "front-most point of the tail loops"),
]


def levels(tg, topt=None):
    topt = t_opt if topt is None else topt
    Z = {"Z_TROUGH_TOP": V2["Z_TROUGH_TOP"], "Z_PCB": 0.0, "Z_SHELF_BACK": V2["Z_SHELF_BACK"], "Z_SEAT": V2["Z_SEAT"]}
    Z["Z_FORMEX_FRONT"] = Z["Z_SEAT"] - V2["formex_t"]
    Z["Z_PANEL_BACK"] = Z["Z_FORMEX_FRONT"] - g_bs
    Z["Z_CTP_FRONT"] = Z["Z_PANEL_BACK"] - V2["panel_t"]
    Z["Z_GLASS_BACK"] = Z["Z_CTP_FRONT"] - topt
    Z["Z_GLASS_FRONT"] = Z["Z_GLASS_BACK"] - tg
    Z["Z_SHEET_BACK"] = Z["Z_GLASS_FRONT"] + t_sheet
    Z["Z_FLANGE_FRONT"] = Z["Z_SHEET_BACK"] + t_gap
    Z["Z_FLANGE_BACK"] = Z["Z_FLANGE_FRONT"] + fl_t
    Z["Z_LAND"] = Z["Z_GLASS_BACK"] + t_bond
    Z["Z_PIP_TOP"] = Z["Z_LAND"] - pip_h
    Z["Z_LANDPLATE_BACK"] = Z["Z_LAND"] + V2["wall"]
    Z["Z_STEPWALL_BACK"] = max(Z["Z_FLANGE_BACK"], Z["Z_LANDPLATE_BACK"])
    if abs(Z["Z_FLANGE_BACK"] - Z["Z_LANDPLATE_BACK"]) < 0.5:          # level snap (CAD rule): no 0.1 step faces
        Z["Z_FLANGE_BACK"] = Z["Z_LANDPLATE_BACK"] = Z["Z_STEPWALL_BACK"]
    Z["Z_TUBE_TOP"] = Z["Z_FLANGE_BACK"] + tube_h
    Z["Z_TAIL_TFT_EXIT"] = Z["Z_PANEL_BACK"] - DS["tail_exit_above_back"]["TFT"]
    Z["Z_TAIL_CTP_EXIT"] = Z["Z_PANEL_BACK"] - DS["tail_exit_above_back"]["CTP"]
    Z["Z_LOOP_FRONT"] = Z["Z_TAIL_CTP_EXIT"] - DS["tail_t"] / 2
    return Z


LV = {tg: levels(tg) for tg in TG_LIST}
print(f"  {'level':18s}" + "".join(f"{'t='+str(tg):>10s}" for tg in TG_LIST) + "   expression")
for n, ex, note in EXPR:
    print(f"  {n:18s}" + "".join(f"{LV[tg][n]:+10.2f}" for tg in TG_LIST) + f"   {ex}")
for tg in TG_LIST:
    Z = LV[tg]
    d_back = Z["Z_LANDPLATE_BACK"] - (Z["Z_FLANGE_FRONT"] + fl_t)
    d_front = Z["Z_LAND"] - Z["Z_FLANGE_FRONT"]
    print(f"  t {tg}: land {d_front:+.2f} behind the flange front; flange back (unsnapped) vs land-plate back {d_back:+.2f}"
          f"{'  -> SNAP (< 0.5): flange back to ' + format(Z['Z_STEPWALL_BACK'], '+.2f') + ' (flange ' + format(Z['Z_FLANGE_BACK']-Z['Z_FLANGE_FRONT'], '.2f') + ')' if abs(d_back) < 0.5 else ''}"
          f"; step wall {Z['Z_STEPWALL_BACK']-Z['Z_SHEET_BACK']:.2f} tall; frame depth behind the sheet back {V2['Z_TROUGH_TOP']-Z['Z_SHEET_BACK']:.2f}")
Z = LV[glass_t]
for n, ex, note in EXPR:
    prm(n, Z[n], "mm", f"{note} [= {ex}] (glass_t {glass_t})", "level")

# =============================================================================================
# 4. PLAN GEOMETRY (independent of glass_t)
# =============================================================================================
hdr("4. PLAN GEOMETRY (KiCad abs, y down)")
P = "plan"
mVA = (AA[0] - VA[0], VA[1] - AA[1], AA[2] - VA[2], VA[3] - AA[3])
W = (AA[0] + print_inset, AA[1] - print_inset, AA[2] + print_inset, AA[3] - print_inset)
wc_x, wc_y = (W[0] + W[1]) / 2, (W[2] + W[3]) / 2
print(f"  AA x {AA[0]:.2f}-{AA[1]:.2f} y {AA[2]:.2f}-{AA[3]:.2f}; VA margin outside AA (L/R/T/B) {mVA[0]:.2f} {mVA[1]:.2f} {mVA[2]:.2f} {mVA[3]:.2f}")
print(f"  WINDOW x {W[0]:.2f}-{W[1]:.2f}  y {W[2]:.2f}-{W[3]:.2f}  ({W[1]-W[0]:.2f} x {W[3]-W[2]:.2f}), centre ({wc_x:.2f}, {wc_y:.2f})")
GL = (W[0] - B, W[1] + B, W[2] - B, glass_y1)
gW, gH = GL[1] - GL[0], GL[3] - GL[2]
gc = ((GL[0] + GL[1]) / 2, (GL[2] + GL[3]) / 2)
chin = GL[3] - W[3]
tp_bottom = max(V2["loop_ctp"][2], V2["loop_tft"][2]) + V2["loop_clr"]
POCKET = (V2["panel_x0"] - pocket_clr, V2["panel_x1"] + pocket_clr, V2["panel_y0"] - pocket_clr, V2["panel_y1"] + pocket_clr)
print(f"  GLASS x {GL[0]:.2f}-{GL[1]:.2f}  y {GL[2]:.2f}-{GL[3]:.2f}  ({gW:.2f} x {gH:.2f}), centre ({gc[0]:.3f}, {gc[1]:.3f}); chin border {chin:.2f}")
LANDS = {"abs left (front-view right)": POCKET[0] - GL[0], "abs right (front-view left)": GL[1] - POCKET[1],
         "top": POCKET[2] - GL[2], "bottom (over the tail-pocket bottom beam)": GL[3] - tp_bottom}
for k, v in LANDS.items():
    inner = v - bead_edge - bead_w
    print(f"  land {k:42s} {v:5.2f}  bead {bead_edge:.1f}..{bead_edge+bead_w:.1f} inside the edge -> {inner:.2f} to the pocket face "
          f"({'OK' if v >= 6.0 - 1e-9 and inner >= bead_pocket_min - 1e-9 else 'FAIL'})")
land_min = min(LANDS.values())


def ring(off, R0):
    return (GL[0] - off, GL[1] + off, GL[2] - off, GL[3] + off), R0 + off


RECTS = [("AA", AA, 0.0, "display active area (DS)"), ("VA_CTP", VA, None, "CTP cover-lens view window (v2 va_*)"),
         ("print_window", W, 0.5, "print window = AA - print_inset per side, corner R0.5"),
         ("glass", GL, R_glass, "glass outline, +-0.2"),
         ("lip_in", *ring(g2, R_glass), "lip inner face = glass recess wall, at the lip top"),
         ("lip_out", *ring(g2 + lip_w, R_glass), "lip outer face"),
         ("seat_ring_out", *ring(g2 + lip_w + seat_w, R_glass), "sheet-seat ring outer edge (ring = lip_out .. this)"),
         ("cut", *ring(g2 + lip_w + g1, R_glass), "SHEET CUT-OUT, laser, +-0.1"),
         ("tape_in", *ring(g2 + lip_w + seat_w + tape_margin, R_glass), "tape strips inner edge (straight strips)"),
         ("tape_out", *ring(g2 + lip_w + seat_w + tape_margin + vhb_w, R_glass), "tape strips outer edge"),
         ("fastener_line", *ring(fast_off, 0.0), "fastener centre lines"),
         ("flange", *ring(fl_beyond, 0.0), "flange outline (corner radius flange_R, centred on F1-F4)"),
         ("pocket", POCKET, 0.5, "clearance pocket = panel + pocket_clr"),
         ("tail_pocket", (V2["tr_x0"], V2["tr_x1"], V2["panel_y1"], tp_bottom), trough_R, "tail pocket (bottom face moved from v2 151.2)")]
RECTS = [(n, r, (fl_R if n == "flange" else None if n in ("fastener_line", "tape_in", "tape_out") else R), note) for n, r, R, note in RECTS]
for n, r, R, note in RECTS:
    print(f"  {n:15s} x {r[0]:7.2f}-{r[1]:7.2f}  y {r[2]:7.2f}-{r[3]:7.2f}  ({r[1]-r[0]:6.2f} x {r[3]-r[2]:6.2f})  R {R if R is not None else '-'}   {note}")
    for i, s in enumerate(("x0", "x1", "y0", "y1")):
        prm(f"{n}_{s}", r[i], "mm", note, P)
    if R is not None and n != "flange":
        prm(f"{n}_R", R, "mm", note + " - corner radius", P)
s_tape0 = g2 + lip_w + seat_w + tape_margin
s_tape1 = s_tape0 + vhb_w
logo = (gc[0], (W[3] + GL[3]) / 2, 100.0, 20.0)
print(f"  logo zone centre ({logo[0]:.2f}, {logo[1]:.3f}) {logo[2]} x {logo[3]}; {logo[1]-logo[3]/2-W[3]:.2f} from the window (R2 >= 1)")
print(f"  overall at the sheet (flange) {gW+2*fl_beyond:.2f} x {gH+2*fl_beyond:.2f}; visible module (cut-out) {gW+2*(g2+lip_w+g1):.2f} x {gH+2*(g2+lip_w+g1):.2f}")
c = (V2["tr_x1"] - trough_R, tp_bottom - trough_R)
print(f"  tail-pocket bottom y {tp_bottom:.2f}, R{trough_R}: TFT loop corner -> arc {trough_R - math.hypot(V2['loop_tft'][1]-c[0], V2['loop_tft'][2]-c[1]):.2f} (>= 1.5)")
# pips: 8, on the bead centre line, 2 per side at +-1/4 of the side length
s_bead = -(bead_edge + bead_w / 2)
PIPS = []
for fx in (-0.25, 0.25):
    PIPS += [(gc[0] + fx * gW, GL[2] - s_bead), (gc[0] + fx * gW, GL[3] + s_bead)]
for fy in (-0.25, 0.25):
    PIPS += [(GL[0] - s_bead, gc[1] + fy * gH), (GL[1] + s_bead, gc[1] + fy * gH)]
for i, (x, y) in enumerate(PIPS, 1):
    print(f"  pip P{i} ({x:7.2f}, {y:7.2f})")


# =============================================================================================
# 4a. FASTENERS F1-F8 and their clearances
# =============================================================================================
def seg_d(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1e-12)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def poly_d(p, pts):
    return min(seg_d(p, pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def rect_d(p, r):
    dx = max(r[0] - p[0], 0.0, p[0] - r[1]); dy = max(r[2] - p[1], 0.0, p[1] - r[3])
    return math.hypot(dx, dy)


def rrect_d(p, r, R):
    return rect_d(p, (r[0] + R, r[1] - R, r[2] + R, r[3] - R)) - R


hdr("4a. FASTENERS (F1-F4 corners, used by S4/R4/S8; F5-F8 mid-sides, optional, used by S8)")
FL = (GL[0] - fast_off, GL[1] + fast_off, GL[2] - fast_off, GL[3] + fast_off)
FA = {"F1": (FL[0], FL[2]), "F2": (FL[1], FL[2]), "F3": (FL[1], FL[3]), "F4": (FL[0], FL[3]),
      "F5": (gc[0], FL[2]), "F6": (FL[1], gc[1]), "F7": (gc[0], FL[3]), "F8": (FL[0], gc[1])}
J20, J2 = FPS["J20"]["crtyd"], FPS["J2"]["crtyd"]
corr = {"J20 wires (exit -x)": (-1e3, J20[2], J20[1] - 2.0, J20[3] + 2.0), "J2 cable (exit -x)": (-1e3, J2[2], J2[1] - 2.0, J2[3] + 2.0)}
loops = [(V2["loop_ctp"][0], V2["loop_ctp"][1], V2["panel_y1"], V2["loop_ctp"][2]), (V2["loop_tft"][0], V2["loop_tft"][1], V2["panel_y1"], V2["loop_tft"][2])]
cut_r = [r for n, r, R, _ in RECTS if n == "cut"][0]
cut_R = R_glass + g2 + lip_w + g1
FTAB = []
print(f"  J20 courtyard {J20}, J2 courtyard {J2}")
print(f"  {'':4s} {'x':>7s} {'y':>7s} {'axis deg':>8s} {'r_c':>6s} {'outline':>7s} {'ear hole':>9s} {'J20/J2':>7s} {'tails':>6s} {'boss gap':>8s} {'cut edge':>8s} {'flange':>6s}")
for n, (x, y) in FA.items():
    ux, uy = gc[0] - x, gc[1] - y
    L_ = math.hypot(ux, uy)
    ang = math.degrees(math.atan2(uy, ux))
    d_out = poly_d((x, y), OUTLINE)
    hn, hd = min(((h, math.hypot(x - hx, y - hy)) for h, (hx, hy) in HOLES.items()), key=lambda t: t[1])
    d_wire = min(rect_d((x, y), r) for r in corr.values())
    d_tail = min([rect_d((x, y), r) for r in loops] + [rect_d((x, y), (V2["tr_x0"], V2["tr_x1"], V2["panel_y1"], tp_bottom))])
    d_boss = hd - pad_d / 2 - 4.0
    d_cut = rrect_d((x, y), cut_r, cut_R)
    d_fl = (fl_beyond - fast_off) if n in ("F5", "F6", "F7", "F8") else fl_R
    ok = d_out >= 6.5 and hd >= 11.0 and d_boss > 0 and d_cut >= 8.0
    FTAB.append(dict(name=n, x_abs=r4(x), y_abs_down=r4(y), slot_axis=[r4(ux / L_), r4(uy / L_)], slot_axis_deg=r4(ang),
                     r_from_glass_centre=r4(L_), d_board_outline_incl_ears=r4(d_out), nearest_ear_hole=hn, d_ear_hole=r4(hd),
                     d_J20_J2_wire_corridor=r4(d_wire), d_tail_pocket_or_loops=r4(d_tail), d_pcb_boss_edge_from_tube=r4(d_boss),
                     d_cut_out_edge=r4(d_cut), d_tube_edge_to_flange_edge=r4(d_fl - pad_d / 2),
                     front_view_u=r4(-(x - gc[0])), front_view_v=r4(gc[1] - y),
                     used_by="S4, R4, S8" if n in ("F1", "F2", "F3", "F4") else "S8 only (optional position, tube + slot always moulded)",
                     front_pad="moulded pad dia 18, top Z_SHEET_BACK" if n in ("F1", "F2", "F3", "F4") else "none moulded; S8 adds a 1.0 spacer washer (DIN 9021 M4) as hard stop"))
    print(f"  {n:4s} {x:7.2f} {y:7.2f} {ang:8.2f} {L_:6.1f} {d_out:7.2f} {hn:>3s} {hd:5.2f} {d_wire:7.1f} {d_tail:6.1f} {d_boss:8.1f} {d_cut:8.2f} {d_fl-pad_d/2:6.2f}  {'OK' if ok else 'CHECK'}")
print("  rules: outline >= 6.5 and ear hole >= 11.0 (v2 dia-12 socket rule), tube (R9) clear of PCB bosses (R4), >= 8.0 to the cut-out (R2 sheet rule)")

# =============================================================================================
# 4b. PRINT WINDOW vs ACTIVE AREA
# =============================================================================================
hdr("4b. PRINT WINDOW vs AA (per side)")
pitch = ((AA[1] - AA[0]) / 800, (AA[3] - AA[2]) / 480)
for lab, inset in (("print_inset 0.30 (frozen)", print_inset), ("alternative AA + 0.25 (R1)", -0.25)):
    for k, items in (("active alignment", [("fixture + operator", 0.08), ("print edge", 0.03), ("LOCA lamination shift", 0.05)]),
                     ("passive alignment", [("print -> glass edge", 0.15), ("glass outline/2", 0.10), ("LCM outline -> AA (ASSUMED)", 0.20),
                                            ("LCM centring", 0.15), ("jig", 0.05), ("lamination shift", 0.05)])):
        wc, rss = stack(items)
        for nm, dl in (("RSS", rss), ("WC", wc)):
            lo, hi = -inset - dl, -inset + dl
            print(f"  {lab:27s} {k:17s} {nm} +-{dl:.2f}: window edge {lo:+.2f}..{hi:+.2f} from AA; covers <= {max(-lo,0)/pitch[1]:.1f} px; "
                  f"black matrix shown {max(hi,0):.2f}; CTP print shown {max(hi-min(mVA),0):.2f}")

# =============================================================================================
# 4c. Z TOLERANCES per glass thickness: flushness, bond line, pips, back-stop gap
# =============================================================================================
hdr("4c. FLUSHNESS, BOND LINE, PIPS AND BACK-STOP GAP (jig: glass front and lip top on one flat plate)")
show_stack("glass front vs lip top", [("plate flatness", 0.02), ("glass bow residual", 0.05), ("cure shrinkage", 0.02), ("spring-back", 0.02)])
show_stack("lip top vs sheet front", [("lip above seat ring (one tool half)", 0.03), ("sheet EN 10131 normal", 0.08), ("sheet seating on the ring", 0.03)])
show_stack("lip top vs sheet front, sheet +-0.05", [("lip", 0.03), ("sheet restricted", 0.05), ("seating", 0.03)], quiet=True)
show_stack("glass front vs sheet front", [("plate", 0.02), ("bow", 0.05), ("shrinkage", 0.02), ("spring-back", 0.02), ("lip", 0.03), ("sheet", 0.08), ("seating", 0.03)], quiet=True)
show_stack("glass front vs lip top, fixed-thickness tape instead (3.0 +-0.2)", [("glass", 0.20), ("tape", 0.05), ("land vs lip", 0.05), ("bow", 0.05)], quiet=True)
TOLZ = {}
for tg in TG_LIST:
    gtol = GLASS[tg][1]
    bl = stack([("glass thickness", gtol), ("land vs lip top", 0.05), ("plate/jig", 0.02)])
    bond_min_local = t_bond - bl[0] - 0.05
    pip_clear = bond_min_local - (pip_h + 0.05)
    gb = stack([("glass", gtol), ("LOCA 0.30 +-0.03", 0.03), ("LCM", DS["lcm_tol"]), ("CTP", DS["ctp_tol"]), ("flush plane vs shelf", 0.05), ("Formex", 0.04)])
    TOLZ[tg] = dict(glass_tol=gtol, bond_wc=(t_bond - bl[0], t_bond + bl[0]), bond_rss=(t_bond - bl[1], t_bond + bl[1]),
                    pip_clear_wc=pip_clear, gbs_wc=(g_bs - gb[0], g_bs + gb[0]), gbs_rss=(g_bs - gb[1], g_bs + gb[1]))
    print(f"  glass {tg} (+-{gtol}): bond line WC {t_bond-bl[0]:.2f}-{t_bond+bl[0]:.2f} (RSS {t_bond-bl[1]:.2f}-{t_bond+bl[1]:.2f}); "
          f"pip top {pip_h:.2f}+0.05 -> min clearance to the glass {pip_clear:+.2f} ({'never touches' if pip_clear > 0 else 'CAN TOUCH'}); "
          f"back-stop gap WC {g_bs-gb[0]:.2f}-{g_bs+gb[0]:.2f}, RSS {g_bs-gb[1]:.2f}-{g_bs+gb[1]:.2f}")
    assert pip_clear > 0 and g_bs - gb[0] > 0
print(f"  CTP tail front -> glass back {LV[3.0]['Z_LOOP_FRONT']-LV[3.0]['Z_GLASS_BACK']:.2f} (all thicknesses); tails are not in front of any frame feature (chin)")
for nm, zx, zr in (("TFT", 2.6, -2.4), ("CTP", 3.9, -2.2)):
    r0, rn = (V2["standoff"] + zx - zr) / 2, (5.0 + g_bs + zx - zr) / 2
    print(f"  {nm}: stand-off 5.00 -> {5.0+g_bs:.2f}: U radius {r0:.2f} -> {rn:.2f}, loop bottom moves {(rn-r0)*(1-math.pi/2):+.2f} (up)")

# =============================================================================================
# 5. THERMAL
# =============================================================================================
hdr("5. THERMAL (assembled at 20 C): gaps, bead and tape shear, slot float")
half_g = (gW / 2, gH / 2)
half_lo = (gW / 2 + g2 + lip_w, gH / 2 + g2 + lip_w)
tol_g2 = stack([("glass +-0.2 /2", 0.10), ("lip ring +-0.1 /2", 0.05), ("centring shims", 0.05)])
tol_g1 = stack([("cut-out +-0.1 /2", 0.05), ("lip ring +-0.1 /2", 0.05), ("centring shims", 0.05)])
print(f"  per-side tolerance: g2 RSS {tol_g2[1]:.3f} / WC {tol_g2[0]:.3f}; g1 RSS {tol_g1[1]:.3f} / WC {tol_g1[0]:.3f}")
for an, af in ALPHA_F.items():
    for tn, (dtf, dts) in {"-20 C": (-40, -40), "+70 frame / +50 sheet": (50, 30)}.items():
        d2 = min((af - ALPHA_G) * dtf * h for h in half_g)
        d1 = min(-(af * dtf - ALPHA_S * dts) * h for h in half_lo)
        print(f"  frame {an:9s} {tn:22s}: g2 {g2+d2:5.2f} (RSS min {g2+d2-tol_g2[1]:+.2f}, WC {g2+d2-tol_g2[0]:+.2f}) | g1 {g1+d1:5.2f} (RSS min {g1+d1-tol_g1[1]:+.2f}, WC {g1+d1-tol_g1[0]:+.2f})")
bead_rect = (gW - 2 * (bead_edge + bead_w / 2), gH - 2 * (bead_edge + bead_w / 2))
r_bead = math.hypot(bead_rect[0] / 2, bead_rect[1] / 2)
for an, af in ALPHA_F.items():
    dl = (af - ALPHA_G) * 50 * r_bead
    print(f"  bead (corner r {r_bead:.1f}) frame {an:9s} +70 C: {dl:.3f} mm -> {dl/t_bond*100:4.1f} % at t 1.0, {dl/TOLZ[3.0]['bond_wc'][0]*100:4.1f} % at the 3.0-glass min bond line")
r_tape = math.hypot(gW / 2 + s_tape1, gH / 2 + s_tape1)
for an, af in ALPHA_F.items():
    dl = (af * 50 - ALPHA_S * 30) * r_tape
    print(f"  tape (outer corner r {r_tape:.1f}) frame {an:9s} +70/+50 C: {dl:.3f} mm -> {dl/t_gap*100:4.1f} % shear (VHB)")
fl_along = (slot_l - 4.0) / 2 - 0.20 - 0.15
fl_across = (slot_w - 4.0) / 2 - 0.20 - 0.15
rmax = max(f["r_from_glass_centre"] for f in FTAB)
print(f"  slot {slot_w} x {slot_l} on M4: float along {(slot_l-4)/2:.2f} - stud position 0.20 - centring 0.15 = {fl_along:.2f}; across {fl_across:.2f}")
for an, af in ALPHA_F.items():
    print(f"   frame {an:9s}: radial move at r {rmax:.1f} = {(af-ALPHA_S)*50*rmax:.3f} mm along the slot -> {'OK' if (af-ALPHA_S)*50*rmax < fl_along else 'BEARS'}")

# =============================================================================================
# 6. JOINTS
# =============================================================================================
hdr("6. JOINTS: bead, LOCA, tape, slot + washer, rivet")
m_glass = {tg: (gW * gH - (4 - math.pi) * R_glass ** 2) * tg * RHO_G for tg in TG_LIST}
m_panel, m_frame, m_rest = 200.0, 105.0, 290.0
A_bead = 2 * (bead_rect[0] + bead_rect[1]) * bead_w
A_tape = 2 * ((gW + 2) + (gH + 2)) * vhb_w
print(f"  glass mass {', '.join(f'{tg}: {m:.0f} g' for tg, m in m_glass.items())}; frame ~{m_frame:.0f} g (est., ~77 cm3); panel {m_panel:.0f}; PCB etc. {m_rest:.0f}")
print(f"  bead area {A_bead:.0f} mm2 (was 1846); dead load glass 3.0 + panel {((m_glass[3.0]+m_panel)*9.81e-3):.2f} N -> {((m_glass[3.0]+m_panel)*9.81e-3)/A_bead*1e3:.2f} kPa; "
      f"250 N pull -> {250/A_bead:.3f} MPa mean")
print(f"  tape: 4 straight strips {vhb_w:.0f} wide, top/bottom {gW+2:.2f} long, sides {gH+2:.2f} long, area {A_tape:.0f} mm2; "
      f"module dead load {(m_glass[3.0]+m_panel+m_frame+m_rest)*9.81e-3:.2f} N -> {(m_glass[3.0]+m_panel+m_frame+m_rest)*9.81e-3/A_tape*1e3:.2f} kPa")
print(f"  strip ends {tape_margin:.1f} from the corner pads (pad R{pad_d/2:.0f} at s {fast_off}): end at s {fast_off-pad_d/2-tape_margin:+.1f} beyond the glass edge line; "
      f"corner gap sealed with a dab of the bead adhesive (4 places)")
wash = {"DIN 9021 M4 (stud)": (4.3, 12.0, 1.0, 4.0), "DIN 9021 M5 (rivet backing)": (5.3, 15.0, 1.2, 4.8)}
for wn, (di, do, th, sd) in wash.items():
    off_al = (slot_l - sd) / 2
    far = slot_l / 2 + off_al
    side = slot_w / 2 + (slot_w - sd) / 2
    A_b = math.pi * do ** 2 / 4 - (slot_w * (slot_l - slot_w) + math.pi * slot_w ** 2 / 4)
    print(f"  {wn:28s}: shaft offset up to {off_al:.2f} along; washer R{do/2:.1f} vs slot far end {far:.2f} -> rim {do/2-far:.2f}; "
          f"across rim {do/2-side:.2f}; on the R{pad_d/2:.0f} tube top: washer edge {do/2+off_al:.2f} ({'inside' if do/2+off_al <= pad_d/2 else 'OVERHANGS'}); bearing {A_b:.0f} mm2")
print(f"  stud M4 nyloc 0.6 Nm ~500 N -> {500/(math.pi*36-(slot_w*(slot_l-slot_w)+math.pi*slot_w**2/4)):.1f} MPa (creep 15)")
for tg in TG_LIST:
    flt = LV[tg]["Z_FLANGE_BACK"] - LV[tg]["Z_FLANGE_FRONT"]
    grip = t_sheet + t_gap + flt + tube_h + 1.2
    stud = t_gap + flt + tube_h + 1.0 + 5.0 + 1.5
    print(f"  glass {tg}: rivet grip (sheet + gap/pad + flange {flt:.2f} + tube + washer 1.2) = {grip:.2f} mm; stud length above the sheet back >= {stud:.2f} -> M4 x 16")
for nm, (a, b) in (("lead's 5.0 x 6.5", (5.0, 6.5)), ("frozen 5.4 x 7.0", (5.4, 7.0))):
    print(f"  slot {nm}: dia-4.8 rivet across clearance {(a-4.8)/2:.2f}/side vs frame-to-sheet location RSS "
          f"{math.sqrt(0.1**2+0.05**2+0.05**2):.2f} and GESIPA tri-fold hole 5.1-5.4 (R2); M4 stud float along {(b-4)/2-0.35:.2f}, across {(a-4)/2-0.35:.2f}")

# =============================================================================================
# 7. PUSH STIFFNESS - grillage (glass strips + frame ring on the glass edge + corner links + supports)
# =============================================================================================
hdr("7. PUSH ON THE GLASS - grillage (panel, LOCA and PCB stiffness NOT counted; frame E 3500 MPa; VHB E 1 MPa)")
D_fl = E_F * fl_t ** 3 / (12 * (1 - NU_F ** 2))
I_link = 2 * 109.8          # corner flange + tube + rib, ASSUMED 2 x v2 T-section


def ring_section(Zl):
    s_pf = -land_min
    rects = [("lip", g2, g2 + lip_w, Zl["Z_GLASS_FRONT"], Zl["Z_SHEET_BACK"]),
             ("step wall + seat ring", g2, g2 + 2.5, Zl["Z_SHEET_BACK"], Zl["Z_STEPWALL_BACK"]),
             ("flange", g2 + 2.5, fl_beyond, Zl["Z_FLANGE_FRONT"], Zl["Z_STEPWALL_BACK"] if abs(Zl["Z_LANDPLATE_BACK"] - Zl["Z_FLANGE_BACK"]) < 0.5 else Zl["Z_FLANGE_BACK"]),
             ("land plate", s_pf, g2, Zl["Z_LAND"], Zl["Z_LANDPLATE_BACK"]),
             ("pocket wall", s_pf, s_pf + 2.5, Zl["Z_LANDPLATE_BACK"], 0.0),
             ("shelf", s_pf - (V2["seat_w"] + pocket_clr), s_pf, V2["Z_SEAT"], V2["Z_SHELF_BACK"])]
    A = sum((r[2] - r[1]) * (r[4] - r[3]) for r in rects)
    zc = sum((r[2] - r[1]) * (r[4] - r[3]) * (r[3] + r[4]) / 2 for r in rects) / A
    I = sum((r[2] - r[1]) * (r[4] - r[3]) ** 3 / 12 + (r[2] - r[1]) * (r[4] - r[3]) * ((r[3] + r[4]) / 2 - zc) ** 2 for r in rects)
    J = sum(max(r[2] - r[1], r[4] - r[3]) * min(r[2] - r[1], r[4] - r[3]) ** 3 / 3 for r in rects)
    c = max(abs(Zl["Z_GLASS_FRONT"] - zc), abs(zc))
    return dict(A=A, zc=zc, I=I, J=J, c=c, rects=rects)


SEC = {tg: ring_section(LV[tg]) for tg in TG_LIST}
for tg in TG_LIST:
    s = SEC[tg]
    print(f"  ring section, glass {tg}: A {s['A']:.1f} mm2, centroid Z {s['zc']:+.2f}, I {s['I']:.0f} mm4, J {s['J']:.0f} mm4 (v2 713)")


def band_shares(a, b, L):
    a1, b1 = min(a, L), min(b, L)
    s0 = (b1 - b1 ** 2 / (2 * L)) - (a1 - a1 ** 2 / (2 * L))
    return s0, (b - a) - s0          # mm of band width carried by the glass-edge line / by the fastener line


SH0, SH1 = band_shares(s_tape0, s_tape1, fast_off)
print(f"  tape band s {s_tape0:.1f}..{s_tape1:.1f}: {SH0:.2f} mm to the glass-edge line, {SH1:.2f} mm to the fastener line")


def band_solve(Ab, rhs, n, bw):
    Ab = [row[:] for row in Ab]
    rhs = [r[:] for r in rhs]
    for i in range(n):
        rowi = Ab[i]; piv = rowi[0]; lim = min(bw, n - 1 - i)
        for k in range(1, lim + 1):
            f = rowi[k] / piv
            if f == 0.0:
                continue
            rowj = Ab[i + k]
            for m in range(k, lim + 1):
                rowj[m - k] -= f * rowi[m]
            for r in rhs:
                r[i + k] -= f * r[i]
    out = []
    for r in rhs:
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            s = r[i]; row = Ab[i]
            for k in range(1, min(bw, n - 1 - i) + 1):
                s -= row[k] * x[i + k]
            x[i] = s / row[0]
        out.append(x)
    return out


def beam_k(EI, GJ, L):
    k = [[0.0] * 6 for _ in range(6)]
    b = [[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L], [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]]
    idx = [0, 1, 3, 4]
    for i in range(4):
        for j in range(4):
            k[idx[i]][idx[j]] = EI / L ** 3 * b[i][j]
    k[2][2] = k[5][5] = GJ / L
    k[2][5] = k[5][2] = -GJ / L
    return k


def tmat(c, s):
    T = [[0.0] * 6 for _ in range(6)]
    for o in (0, 3):
        T[o][o] = 1.0
        T[o + 1][o + 1], T[o + 1][o + 2] = c, s
        T[o + 2][o + 1], T[o + 2][o + 2] = -s, c
    return T


def grillage(t_g, supports, vhb=False, line_q=0.0, loads=(), E_vhb=1.0):
    """Glass GL on a frame ring along its edges, corner links to the fastener corners, supports = stiff springs at fasteners.
    vhb: tension/compression springs along the tape band; line_q: foam-gasket line load (N/mm, pushes the frame back)."""
    gx0, gx1, gy0, gy1 = GL
    sec = SEC[t_g]
    I_ring, J_ring = sec["I"], sec["J"]
    D_g = E_G * t_g ** 3 / (12 * (1 - NU_G ** 2))
    fx0, fx1, fy0, fy1 = FL
    xs = sorted({fx0, fx1, gx0, gx1} | {gx0 + gW * i / 16 for i in range(17)})
    ys = sorted({fy0, fy1, gy0, gy1} | {gy0 + gH * i / 12 for i in range(13)} | {wc_y, gc[1], logo[1], V2["panel_y1"]})
    xs = [x for i, x in enumerate(xs) if i == 0 or x - xs[i - 1] > 1.5]
    ys = [y for i, y in enumerate(ys) if i == 0 or y - ys[i - 1] > 1.5]
    nx, ny = len(xs), len(ys)
    nid = lambda ix, iy: ix * ny + iy
    n = 3 * nx * ny; bw = 3 * (ny + 1) + 2
    Ab = [[0.0] * (bw + 1) for _ in range(n)]
    elems = []

    def add_el(p, q, EI_g, EI_r, GJ, kind):
        (x1, y1), (x2, y2) = (xs[p // ny], ys[p % ny]), (xs[q // ny], ys[q % ny])
        Ln = math.hypot(x2 - x1, y2 - y1); c, s = (x2 - x1) / Ln, (y2 - y1) / Ln
        kl = beam_k(EI_g + EI_r, GJ, Ln); T = tmat(c, s)
        kg = [[sum(T[a][i] * kl[a][b] * T[b][j] for a in range(6) for b in range(6)) for j in range(6)] for i in range(6)]
        dofs = [3 * p, 3 * p + 1, 3 * p + 2, 3 * q, 3 * q + 1, 3 * q + 2]
        for i in range(6):
            for j in range(6):
                if dofs[j] >= dofs[i]:
                    Ab[dofs[i]][dofs[j] - dofs[i]] += kg[i][j]
        elems.append((dofs, kl, T, EI_g, EI_r, kind))

    def trib(lines, i):
        lo = lines[i] - (lines[i] - lines[i - 1]) / 2 if i > 0 else lines[i]
        hi = lines[i] + (lines[i + 1] - lines[i]) / 2 if i < len(lines) - 1 else lines[i]
        return lo, hi

    for ix in range(nx):
        for iy in range(ny):
            for horiz in (True, False):
                if (horiz and ix == nx - 1) or ((not horiz) and iy == ny - 1):
                    continue
                p = nid(ix, iy); q = nid(ix + 1, iy) if horiz else nid(ix, iy + 1)
                if horiz:
                    xm, ym = (xs[ix] + xs[ix + 1]) / 2, ys[iy]; lo, hi = trib(ys, iy); inside = gx0 - 1e-9 <= xm <= gx1 + 1e-9
                    glo, ghi = gy0, gy1; on_edge = abs(ym - gy0) < 1e-6 or abs(ym - gy1) < 1e-6
                else:
                    xm, ym = xs[ix], (ys[iy] + ys[iy + 1]) / 2; lo, hi = trib(xs, ix); inside = gy0 - 1e-9 <= ym <= gy1 + 1e-9
                    glo, ghi = gx0, gx1; on_edge = abs(xm - gx0) < 1e-6 or abs(xm - gx1) < 1e-6
                bg = max(0.0, min(hi, ghi) - max(lo, glo)) if inside else 0.0
                bf = (hi - lo) - bg
                EI_r = E_F * I_ring if (inside and on_edge) else 0.0
                GJ = D_g * (1 - NU_G) * bg + D_fl * (1 - NU_F) * bf + (E_F / (2 * (1 + NU_F)) * J_ring if EI_r else 0.0)
                add_el(p, q, D_g * bg, EI_r + D_fl * bf, GJ, "glass" if bg > 0 else "flange")
    for (cx, cy), (gxc, gyc) in zip(((fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)), ((gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1))):
        p = nid(xs.index(cx), ys.index(cy)); q = nid(xs.index(gxc), ys.index(gyc))
        add_el(min(p, q), max(p, q), 0.0, E_F * I_link, E_F / (2 * (1 + NU_F)) * 60.0, "link")
    sup = []
    for (sx, sy) in supports:
        ix = min(range(nx), key=lambda i: abs(xs[i] - sx)); iy = min(range(ny), key=lambda i: abs(ys[i] - sy))
        p = nid(ix, iy); sup.append(p); Ab[3 * p][0] += 2.0e4
    band = {}
    for ix in range(nx):
        for iy in range(ny):
            x, y = xs[ix], ys[iy]; lx = trib(xs, ix); ly = trib(ys, iy); w0 = w1 = 0.0
            if abs(y - fy0) < 1e-6 or abs(y - fy1) < 1e-6:
                w1 += SH1 * (lx[1] - lx[0])
            if abs(x - fx0) < 1e-6 or abs(x - fx1) < 1e-6:
                w1 += SH1 * (ly[1] - ly[0])
            if (abs(y - gy0) < 1e-6 or abs(y - gy1) < 1e-6) and gx0 - 1e-6 <= x <= gx1 + 1e-6:
                w0 += SH0 * (min(lx[1], gx1) - max(lx[0], gx0))
            if (abs(x - gx0) < 1e-6 or abs(x - gx1) < 1e-6) and gy0 - 1e-6 <= y <= gy1 + 1e-6:
                w0 += SH0 * (min(ly[1], gy1) - max(ly[0], gy0))
            if w0 + w1 > 0:
                band[nid(ix, iy)] = w0 + w1             # tape / gasket area tributary to this node, mm2
    if vhb:
        for p, a in band.items():
            Ab[3 * p][0] += E_vhb / t_gap * a
    rhs, lp = [], []
    for (lx_, ly_) in loads:
        ix = min(range(nx), key=lambda i: abs(xs[i] - lx_)); iy = min(range(ny), key=lambda i: abs(ys[i] - ly_))
        f = [0.0] * n; f[3 * nid(ix, iy)] = 1.0; rhs.append(f); lp.append(nid(ix, iy))
    if line_q:
        f = [0.0] * n
        for p, a in band.items():
            f[3 * p] = line_q / vhb_w * a                  # gasket stress x tributary area (pushes the frame to +Z)
        rhs.append(f); lp.append(None)
    sols = band_solve(Ab, rhs, n, bw)
    perim = [nid(ix, iy) for ix in range(nx) for iy in range(ny)
             if ((abs(ys[iy] - gy0) < 1e-6 or abs(ys[iy] - gy1) < 1e-6) and gx0 - 1e-6 <= xs[ix] <= gx1 + 1e-6)
             or ((abs(xs[ix] - gx0) < 1e-6 or abs(xs[ix] - gx1) < 1e-6) and gy0 - 1e-6 <= ys[iy] <= gy1 + 1e-6)]
    res = []
    for p_l, u in zip(lp, sols):
        Mg = Mr = 0.0
        for dofs, kl, T, EIg, EIr, kind in elems:
            ue = [u[d] for d in dofs]
            dl = [sum(T[i][j] * ue[j] for j in range(6)) for i in range(6)]
            fl_ = [sum(kl[i][j] * dl[j] for j in range(6)) for i in range(6)]
            M = max(abs(fl_[1]), abs(fl_[4])); tot = EIg + EIr
            if EIg > 0:
                Mg = max(Mg, M * EIg / tot / (EIg / D_g))
            if EIr > E_F * I_ring * 0.5:
                Mr = max(Mr, M * (E_F * I_ring) / tot)
        res.append(dict(w=u[3 * p_l] if p_l is not None else None, w_perim=max(u[3 * p] for p in perim),
                        w_perim_min=min(u[3 * p] for p in perim), sig_g=6 * Mg / t_g ** 2, sig_r=Mr * sec["c"] / I_ring,
                        R=max(2.0e4 * u[3 * p] for p in sup), Rmin=min(2.0e4 * u[3 * p] for p in sup)))
    return res


LOADS = [("window centre", (wc_x, wc_y)), ("glass top edge, mid", (gc[0], GL[2])), ("glass side edge, mid", (GL[0], gc[1])),
         ("chin centre (over tail pocket)", (gc[0], logo[1])), ("glass bottom edge, mid", (gc[0], GL[3]))]
S4 = [FA[k] for k in ("F1", "F2", "F3", "F4")]
S8 = [FA[k] for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")]
CONF = [("S4/R4: 4 corner studs + VHB (recommended)", dict(supports=S4, vhb=True)),
        ("S8: 8 studs (+ foam gasket, no tension)", dict(supports=S8)),
        ("reference: 4 corner studs only", dict(supports=S4))]
PUSH = {}
for tg in TG_LIST:
    for name, kw in CONF:
        if name.startswith("reference") and tg != 3.0:
            continue
        r = grillage(tg, loads=[p for _, p in LOADS], **kw)
        PUSH[(tg, name)] = r
        print(f"\n  glass {tg} {GLASS[tg][0][:22]:22s} | {name}")
        print(f"    {'load point':32s} {'w@5N um':>8s} {'w@50N':>7s} {'lip line@50N':>12s} {'glass@250N':>10s} {'ring@250N':>9s} {'stud@250N':>9s}")
        for (ln, _), rr in zip(LOADS, r):
            print(f"    {ln:32s} {rr['w']*5000:8.0f} {rr['w']*50:7.3f} {rr['w_perim']*50:12.3f} {rr['sig_g']*250:7.1f} MPa {rr['sig_r']*250:6.1f} MPa {rr['R']*250:7.0f} N")
print("\n  S8 foam gasket preload (no tape): lift of the lip line between studs = visible flushness error")
LIFT = {}
for tg in (1.1, 3.0):
    for q in (0.10, 0.36, 0.84):
        rr = grillage(tg, supports=S8, line_q=q)[0]
        LIFT[(tg, q)] = rr["w_perim"]
        print(f"    glass {tg}: gasket q {q:.2f} N/mm ({q/vhb_w*1000:.0f} kPa on a 12 mm strip): lip-line lift max {rr['w_perim']*1000:5.0f} um short-term,"
              f" ~{rr['w_perim']*1000*1.3:4.0f} um long-term (frame share creeps, glass does not; ASSUMED x1.3)")

# =============================================================================================
# 8. GLASS STRENGTH: 250 N, 0.5 J (window centre and the unsupported chin over the tail pocket)
# =============================================================================================
hdr("8. GLASS STRESS (Roark SS circular plate, equivalent radius) - 250 N on a dia-10 probe and IEC 60335-1 0.5 J")
a_disp = 0.5 * min(POCKET[1] - POCKET[0], POCKET[3] - POCKET[2])
b_chin = tp_bottom - V2["panel_y1"]
w_chin = V2["tr_x1"] - V2["tr_x0"]
a_chin = 0.6 * b_chin
print(f"  display: equivalent radius {a_disp:.1f}; chin over the pocket: free span {w_chin:.1f} x {b_chin:.1f} (panel edge y {V2['panel_y1']} -> beam land y {tp_bottom}), equivalent radius {a_chin:.1f}")


def sig_point(Pn, t, r0, a):
    rp = math.sqrt(1.6 * r0 ** 2 + t ** 2) - 0.675 * t if r0 < 0.5 * t else r0
    return 3 * Pn / (2 * math.pi * t ** 2) * ((1 + NU_G) * math.log(a / rp) + 1)


def impact(k, m_move, t, a):
    E_def = 0.5 * m_move / (0.25 + m_move)                   # J into deformation, striker 0.25 kg (ASSUMED Eh 0.5 J)
    out = {}
    for lab, E in (("bound", 0.5), ("mass", E_def)):
        F = math.sqrt(2 * E * k * 1000)
        ah = (3 * F * 10 / (4 * 3400)) ** (1 / 3)              # Hertz contact radius, R10 polyamide striker
        out[lab] = (F, sig_point(F, t, ah, a), E)
    return out


STR = {}
for tg in TG_LIST:
    gname, gtol, lim = GLASS[tg]
    D_g = E_G * tg ** 3 / (12 * (1 - NU_G ** 2))
    s250 = sig_point(250, tg, 5.0, a_disp)
    l_f = (D_g / (0.3 / t_opt)) ** 0.25          # LOCA gel foundation E ~0.3 MPa (ASSUMED) -> modulus E/t
    s250_f = 3 * 250 * (1 + NU_G) / (2 * math.pi * tg ** 2) * (math.log(l_f / 5.0) + 0.616) if l_f > 5 else 3 * 250 / (2 * math.pi * tg ** 2)
    rc = PUSH[(tg, CONF[0][0])]
    k_c = 1 / rc[0]["w"]
    mm = 0.25 * (m_glass[tg] + m_panel) / 1000
    imp_c = impact(k_c, mm, tg, a_disp)
    k_glob = 1 / rc[3]["w"]
    k_loc = D_g / (0.0169 * b_chin ** 2)
    k_ser = 1 / (1 / k_glob + 1 / k_loc)
    imp_ch = impact(k_ser, mm, tg, a_chin)
    STR[tg] = dict(s250=s250, s250_f=s250_f, lim=lim, imp_c=imp_c, imp_ch=imp_ch, k_loc=k_loc, k_glob=k_glob)
    print(f"  {tg:.1f} {gname[:34]:34s} (char. {lim:.0f}): 250 N centre {s250:6.1f} MPa no panel credit / {s250_f:6.1f} on the LOCA-panel foundation;"
          f" 0.5 J centre: bound {imp_c['bound'][1]:6.1f}, mass-ratio {imp_c['mass'][1]:6.1f} MPa (F {imp_c['mass'][0]:.0f} N, SF {lim/imp_c['mass'][1]:.1f})")
    print(f"      chin over the pocket (nothing behind): k local {k_loc:.0f} / global {k_glob:.0f} N/mm; 0.5 J bound {imp_ch['bound'][1]:6.1f}, "
          f"mass-ratio {imp_ch['mass'][1]:6.1f} MPa (F {imp_ch['mass'][0]:.0f} N, SF {lim/imp_ch['mass'][1]:.1f})")
print("  Quasi-static, order of magnitude: ignores the striker/plate dynamics beyond a mass ratio; the chin has no panel behind it, so a broken chin")
print("  opens into the tail pocket (FPC tails, SELV) - no live part becomes accessible; cl. 21.1 still asks for 'no damage impairing 8.1/15.1/29'.")

print(f"  VHB spring-back (S4/R4): a 1.1 tape pressed to the 1.0 hard stops stores <= 9 % elastic strain; if the corner studs alone held the")
print(f"  frame, the lip line could stand up to ~{(1.1-t_gap)*1000:.0f} um off the seat ring between corners until the acrylic foam relaxes ->")
print(f"  keep the pressure frame on for >= 20 min after mounting and check the lip line on the first articles.")

# =============================================================================================
# 9. MASTER PARAMETER FILE (frozen for CAD) + flat concept_params.json
# =============================================================================================
hdr("9. WRITING THE MASTER PARAMETER FILE")


def ent(name, value, unit, note, **kw):
    d = {"name": name, "value": r4(value), "unit": unit, "note": note}
    d.update({k: r4(v) if isinstance(v, float) else v for k, v in kw.items()})
    return d


drv = [dict(p) for p in PARAMS if p["group"] == "driving"]
for p in drv:
    p.pop("group")
    if p["name"] == "glass_t":
        p["allowed"] = TG_LIST
        p["types"] = {str(tg): {"type": GLASS[tg][0], "thickness_tol_mm": GLASS[tg][1], "char_strength_MPa": GLASS[tg][2]} for tg in TG_LIST}
CAD_RULES = [
    "Drive every Z level from the expressions in derived_levels.expressions; never type the evaluated numbers into the model.",
    "glass_t changes only the levels in front of the panel (Z_GLASS_FRONT .. Z_TUBE_TOP); everything at Z >= Z_FORMEX_FRONT is frame v2 geometry.",
    "Step wall (s 0.4 .. 2.9 from the glass edge) is one body from Z_SHEET_BACK to Z_STEPWALL_BACK in every case; union it with the lip, the flange plate and the land plate.",
    "Level snap: if |Z_FLANGE_BACK - Z_LANDPLATE_BACK| < 0.5 (glass_t 1.1 gives 0.10), extend the flange back to Z_STEPWALL_BACK (flange 2.6) so no 0.1 mm step face is created; the stud tube top follows (Z_STEPWALL_BACK + tube_h).",
    "At glass_t 1.1 the recess floor (Z_LAND) lies only 0.10 behind the flange front: keep both faces; they are separated by the step wall, not adjacent.",
    "Lip, seat ring, corner pads, glass recess and pips are formed in the A (fixed) half; parting line on the flange outline in the flange-front plane; single pull Z, no slides.",
    "Tape strips are straight (4 pieces) and end tape_margin before the corner pads; F5-F8 have no moulded front pad so the strips run over them.",
    "Fastener slots are stadiums slot_w x slot_l at the flange front, 0.5 deg draft (wider to the back), long axis = slot_axis (towards the glass centre).",
    "Tail pocket: v2 x limits and walls, bottom face at tr_y1 147.70 with trough_R 1.5, no floor (the glass chin closes the front).",
]
CARRY = ["wall", "rib", "draft", "draft_loc", "fillet_root", "frame_r", "sheet_t", "panel_t", "Z_PCB", "Z_SEAT", "Z_SHELF_BACK", "Z_TROUGH_TOP",
         "panel_x0", "panel_x1", "panel_y0", "panel_y1", "va_x0", "va_x1", "va_y0", "va_y1", "seat_w", "pcb_rim_w", "rib_bury", "boss_od",
         "pilot_d", "pilot_floor", "cbore_d", "cbore_h", "loop_ctp_x0", "loop_ctp_x1", "loop_ctp_y1", "loop_tft_x0", "loop_tft_x1",
         "loop_tft_y1", "loop_z_top", "loop_clr", "tr_x0", "tr_x1", "tail_wall_step_y", "crib_y", "cell_r", "cell_rib_h"] + \
        [f"h{i}_{a}" for i in range(1, 10) for a in ("x", "y")]
carried = [ent(n, V2P[n], next(p["unit"] for p in v2["user_parameters"] if p["name"] == n),
               next(p["comment"] for p in v2["user_parameters"] if p["name"] == n), status="kept") for n in CARRY]
carried.append(ent("support_ribs", "26 ribs, v2 positions (Rev3.0_Frame_v2_params.json support_ribs.per_rib)", "-",
                   "kept; wall end extended to the moved pocket wall (+0.55), free ends at the shelf edge as v2", status="kept"))
superseded = [ent("pocket_clr", V2P["pocket_clr"], "mm", "v2 locating pocket", status="superseded by pocket_clr 0.80 (clearance pocket)"),
              ent("tr_y1", V2P["tr_y1"], "mm", "v2 tail-pocket bottom", status=f"superseded by tr_y1 {tp_bottom:.2f}"),
              ent("trough_r", V2P["trough_r"], "mm", "v2 tail-pocket corner", status=f"superseded by trough_R {trough_R}"),
              ent("standoff", V2P["standoff"], "mm", "v2 PCB back -> panel back", status=f"superseded: {5.0+g_bs:.2f} nominal (Z_PANEL_BACK)"),
              ent("Z_FRONT / flange / studs FH1-FH10 / pegs", "v2 values", "-", "v2 mounting system", status="replaced by the flange, F1-F8 and tape of this file")]
LANDTAB = [ent(k, v, "mm", "land width pocket face -> glass edge; bead from 0.9 to 4.9 inside the glass edge", bead_to_pocket=v - bead_edge - bead_w) for k, v in LANDS.items()]
master = {
    "about": "Rev3.0 OVEN CONTROLLER - glass-front carrier (new part family 'GlassFront'). Frozen master parameters for CAD and drawings. "
             "Generated by Design Reports/Rev3.0/tools/glassfront/concept/concept_calc.py; study and reasoning in concept.md (sec. 11 = frozen values).",
    "revision": "GF-1.0 (concept 2026-11-15 + lead amendments A1-A8; slot 5.4 x 7.0 and F5-F8 without moulded pads are deviations, see concept.md sec. 11)",
    "status": "frozen for CAD 2026-11-15",
    "units": "mm, deg, N, MPa, kPa unless stated",
    "coordinates": "X = KiCad abs x, y = KiCad abs y (down), Z = 0 at the physical PCB back, -Z towards the oven front (frame v2 convention). "
                   "s = distance outward from the glass edge. Front view: u = -(x - 103.85), v = 82.085 - y.",
    "driving_parameters": drv,
    "derived_levels": {"expressions": [ent(n, ex, "mm", note) for n, ex, note in EXPR],
                       "evaluated_by_glass_t": {str(tg): {n: r4(LV[tg][n]) for n, _, _ in EXPR} for tg in TG_LIST}},
    "plan_rectangles": [dict(name=n, x0=r4(r[0]), x1=r4(r[1]), y0=r4(r[2]), y1=r4(r[3]), R=r4(R) if R is not None else None, unit="mm", note=note)
                        for n, r, R, note in RECTS],
    "plan_points": [ent("window_centre", [r4(wc_x), r4(wc_y)], "mm", "print window centre (abs)"),
                    ent("glass_centre", [r4(gc[0]), r4(gc[1])], "mm", "glass centre = cut-out centre = fastener-pattern centre"),
                    ent("chin_border", chin, "mm", "window bottom -> glass bottom edge"),
                    ent("borders_top_left_right", B, "mm", "window edge -> glass edge")],
    "lands": LANDTAB,
    "bead": [ent("bead_w", bead_w, "mm", "bead width after squeeze"), ent("bead_s_outer", -bead_edge, "mm", "bead outer edge (s)"),
             ent("bead_s_inner", -(bead_edge + bead_w), "mm", "bead inner edge (s)"),
             ent("bond_line_nominal", t_bond, "mm", "set by the flush jig (glass front and lip top on one plate)"),
             ent("bond_line_range_wc", {str(tg): [r4(TOLZ[tg]["bond_wc"][0]), r4(TOLZ[tg]["bond_wc"][1])] for tg in TG_LIST}, "mm", "worst case per glass_t"),
             ent("adhesive", "black elastic 2-C (or 1-C) neutral silicone or MS polymer, movement class >= +-25 % (prefer +-50 %), primer on PA and print", "-", "R1/R2")],
    "pips": [ent(f"pip{i}", [r4(x), r4(y)], "mm", f"stand-off pip on the bead centre line, dia {pip_d} x {pip_h} high, 1 deg draft; top = Z_PIP_TOP")
             for i, (x, y) in enumerate(PIPS, 1)] +
            [ent("pip_clearance_wc", {str(tg): r4(TOLZ[tg]["pip_clear_wc"]) for tg in TG_LIST}, "mm", "min pip-top -> glass back in the jig stack (> 0: never touches)")],
    "fasteners": {"positions": FTAB,
                  "slot": [ent("slot_w", slot_w, "mm", "stadium width at the flange front, 0.5 deg draft"), ent("slot_l", slot_l, "mm", "stadium length, axis to the glass centre")],
                  "pad_tube": [ent("pad_d", pad_d, "mm", "F1-F4 front pad dia, top at Z_SHEET_BACK (hard stop); F5-F8 none"),
                               ent("tube_top_d", pad_d, "mm", "tube dia at its top, 1 deg draft, one 1.5 rib to the step wall"),
                               ent("tube_h", tube_h, "mm", "tube height above the flange back (top = Z_TUBE_TOP)")],
                  "hardware": [ent("stud", "M4 x 16 CD weld stud ISO 13918 (steel Cu-plated or A2), welded before coating", "-", "S4: F1-F4; S8: F1-F8"),
                               ent("washer_nut", "DIN 9021 M4 (12 x 1.0) + ISO 10511 M4 nyloc, 0.6 Nm", "-", "bearing 82 mm2 -> 6.1 MPa at 500 N"),
                               ent("rivet", "dia 4.8 blind rivet set from the front, tri-fold / bulb Al/Al, black head; grip 8.2 (8.3 at glass 1.1); backing washer DIN 9021 M5 (15 x 1.2) on the tube top", "-", "R4"),
                               ent("spacer_S8", "DIN 9021 M4 washer 1.0 on the stud between sheet and flange at F5-F8", "-", "hard stop where no pad is moulded")]},
    "print": [ent("print_window", [r4(W[0]), r4(W[1]), r4(W[2]), r4(W[3])], "mm", "x0, x1, y0, y1 abs; R0.5"),
              ent("print_inset", print_inset, "mm", "AA inset per side (frozen); alternative AA + 0.25 (print_inset -0.25, R1) shows 0.35 of black matrix"),
              ent("alignment", "active (lit 1-px border, XY-theta stage, two USB microscopes)", "-", "window edge 1-3 px inside the lit border; GUI keeps the outer 5 px black"),
              ent("print_layers", "1) logo colour in the logo zone, 2) black everywhere except the window; 15-30 um; print to the glass edge (setback 0-0.2)", "-", "R2 sec.1.5"),
              ent("ink", "fired enamel (tempered) or 2-K organic ink (CS glass) passing cross-cut GT0-1 and the silicone/LOCA adhesion coupons", "-", "R1 sec.4")],
    "logo_zone": [ent("logo_centre", [r4(logo[0]), r4(logo[1])], "mm", "chin centre"), ent("logo_w", logo[2], "mm", "max"), ent("logo_h", logo[3], "mm", "max; strokes >= 0.5, >= 1 from the window")],
    "tape_and_gasket": [ent("tape", "3M VHB 5952 (black, 1.1) or equivalent, 12 mm roll, 4 straight strips; primer 94 on PA6 and powder coat", "-", "S4 / R4"),
                        ent("tape_s", [r4(s_tape0), r4(s_tape1)], "mm", "strip edges outside the glass edge"),
                        ent("strip_lengths", {"top_bottom": r4(gW + 2.0), "sides": r4(gH + 2.0)}, "mm", "strips end 1.0 before the corner pads"),
                        ent("corner_seal", "dab of the bead adhesive over the 4 corner gaps between strip ends and pads", "-", "closes the leak path"),
                        ent("foam_gasket_S8", "closed-cell soft foam, 1.5 -> 1.0 at <= 10 kPa (12 mm) or 5 mm wide at <= 20 kPa, notched round the F5-F8 spacers", "-",
                            f"lift between studs {LIFT[(3.0, 0.10)]*1000:.0f} um at q 0.10 N/mm (3.0 glass); 30 kPa x 12 mm gives {LIFT[(3.0, 0.36)]*1000:.0f} um")],
    "sheet_variants": {
        "common": [ent("cut_out", [r4(cut_r[0]), r4(cut_r[1]), r4(cut_r[2]), r4(cut_r[3])], "mm", f"x0, x1, y0, y1 abs, R {cut_R:.1f}, +-0.1, laser; no pierce / micro-joints on the visible edge; deburr R0.2-0.5 before coating"),
                   ent("t_sheet", t_sheet, "mm", "EN 10131, +-0.08 normal; +-0.05 restricted recommended")],
        "S4": ent("S4", "4 x M4 x 16 CD weld studs at F1-F4 (template +-0.2), VHB strips; no holes", "-", "recommended"),
        "S8": ent("S8", "8 x M4 x 16 CD weld studs at F1-F8, soft foam gasket, spacers at F5-F8; serviceable, tape-free", "-", "lift risk, see tape_and_gasket"),
        "R4": ent("R4", "4 holes at F1-F4: dia 5.0 +0.1/0 (ISO 15977 dia 4.8) or dia 5.2 +0.1/0 (tri-fold 4.8, GESIPA 5.1-5.4); VHB strips; heads ~1.0-2.0 proud", "-",
                  "edge distance to the cut-out 16.2 (>= 2d)"),
        "PEM_note": ent("PEM_FH_M4_hole", "4.0 +0.08/-0 (PEM FH/FHS-M4: min sheet 1.0, head dia 5.9 +-0.4 visible, edge >= 7.2); 4.22 is the upper limit of the FH-832 hole (.163 +.003 in)", "-", "not a variant here")},
    "gaps": [ent("g2_glass_lip", g2, "mm", "20 C nominal; -20 C 0.25 / +70 C 0.55 (50 ppm); can touch at -20 C with 70 ppm WC"),
             ent("g1_lip_sheet", g1, "mm", "20 C nominal; +70/+50 C 0.20 / -20 C 0.51 (50 ppm); can touch hot with 70 ppm WC"),
             ent("g_bs_backstop", g_bs, "mm", "panel back -> Formex; WC range per glass_t in checks")],
    "drawing_tolerances": {
        "glass": [ent("thickness_tol", {str(tg): GLASS[tg][1] for tg in TG_LIST}, "mm", "+-"), ent("outline_tol", 0.2, "mm", "+- (precision CNC; R2)"),
                  ent("flatness", 0.15, "mm", "max over the 165 x 100 bond zone (R1); <= 0.2 over the pane"), ent("corner_R", R_glass, "mm", "+-0.5"),
                  ent("edge", "C-edge or flat-polished, arris 0.3-0.5 front and back", "-", "no frosted arris visible in g2")],
        "print": [ent("window_position", "set by active alignment to the AA, not by glass datums", "-", "print-to-edge +-0.2 (R2)"),
                  ent("window_size_tol", 0.1, "mm", "+- on 153.48 x 85.32"), ent("ink_thickness", "15-30 um", "-", "buried by the LOCA (R2 1.5)")],
        "sheet": [ent("cut_out_tol", 0.1, "mm", "+- size and position"), ent("stud_position_tol", 0.2, "mm", "+- (CD welding template)"),
                  ent("thickness_tol", 0.08, "mm", "+- (0.05 restricted)"), ent("flatness_round_window", 0.3, "mm", "class (R2)")],
        "frame": [ent("general", "ISO 20457 TG5", "-", "as v2"), ent("lip_above_seat_ring", 0.03, "mm", "+- (same tool half)"),
                  ent("land_Z_to_lip_top", 0.05, "mm", "+-"), ent("seat_ring_and_pads_coplanar", 0.05, "mm", "flatness of the hard-stop faces"),
                  ent("slot_position", 0.1, "mm", "+-"), ent("parting_plane_flatness_unclamped", 0.3, "mm", "the glass flattens the frame in the jig")]},
    "cad_rules": CAD_RULES,
    "carried_over_from_v2": carried,
    "v2_superseded": superseded,
    "checks": {"flush_glass_vs_sheet_RSS": 0.109, "flush_glass_vs_sheet_WC": 0.25, "glass_vs_lip_RSS": 0.061,
               "backstop_gap_wc": {str(tg): [r4(TOLZ[tg]["gbs_wc"][0]), r4(TOLZ[tg]["gbs_wc"][1])] for tg in TG_LIST},
               "push_50N_window_centre_mm": {str(tg): r4(PUSH[(tg, CONF[0][0])][0]["w"] * 50) for tg in TG_LIST},
               "push_50N_lip_line_max_mm": {str(tg): r4(max(rr["w_perim"] for rr in PUSH[(tg, CONF[0][0])]) * 50) for tg in TG_LIST},
               "impact_0p5J_SF_centre": {str(tg): r4(STR[tg]["lim"] / STR[tg]["imp_c"]["mass"][1]) for tg in TG_LIST},
               "impact_0p5J_SF_chin": {str(tg): r4(STR[tg]["lim"] / STR[tg]["imp_ch"]["mass"][1]) for tg in TG_LIST},
               "fasteners_all_rules_pass": all(f["d_board_outline_incl_ears"] >= 6.5 and f["d_ear_hole"] >= 11.0 and f["d_pcb_boss_edge_from_tube"] > 0
                                               and f["d_cut_out_edge"] >= 8.0 for f in FTAB)},
}
os.makedirs(os.path.dirname(MASTER), exist_ok=True)
json.dump(master, open(MASTER, "w"), indent=1)
json.dump({"about": "Rev3.0 glass-front concept GF-1.0, flat list (same values as the master file)", "source": "concept_calc.py",
           "master": os.path.relpath(MASTER, ROOT), "parameters": PARAMS}, open(os.path.join(HERE, "concept_params.json"), "w"), indent=1)
print(f"  wrote {os.path.relpath(MASTER, ROOT)} and concept_params.json ({len(PARAMS)} flat parameters)")
