"""Rev3.0 OVEN CONTROLLER - injection-moulded carrier frame (PA6-GF30, V-0 / GWFI 960).

One moulded part that holds the 7" SATOZ panel (glass outward) and the Rev3.0 PCB
5 mm behind the panel back, and mounts the assembly to the oven's front sheet
from the inside. Open on the component side (nothing above the PCB plane over
the board), see ../../Rev3.0_Frame_Design.md.

COORDINATE FRAME (= KiCad STEP export with --user-origin 0x0mm, shifted +0.08 in Z)
  X = board absolute x (mm), Y = -(board absolute y)   [KiCad is y-down]
  Z = 0 at the PCB BACK surface (physical, incl. copper + mask), +Z = component side,
      -Z = towards the panel / the oven front sheet. Pull direction of the mould = Z.
  All plan dimensions below are given in KiCad absolute coordinates (x, y-down),
  exactly as they appear in pcbnew; the helpers convert y -> Y = -y.

Every assumption is a named parameter in the PARAMETERS block. Change, then run
build.py (or `python frame.py` for the frame alone).
"""
import json
import math
import os

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_GEOM = os.path.join(HERE, "out", "board_geom.json")   # written by dump_board.py (KiCad Python)

# =====================================================================================
# PARAMETERS
# =====================================================================================
# ---- board (from the .kicad_pcb, read by dump_board.py) ---------------------------
PCB_T = 1.6                       # board thickness
HOLES = {                         # ear holes H1..H9, absolute (x, y), dia 3.2 NPTH
    "H1": (30.0, 14.2), "H2": (93.0, 14.2), "H3": (174.0, 14.2), "H4": (189.8, 30.0),
    "H5": (189.8, 109.0), "H6": (175.0, 123.8), "H7": (30.0, 123.8), "H8": (15.2, 109.0),
    "H9": (15.2, 30.0)}
EAR_W = 9.0                       # ear tab width (full-round end, R 4.5 about the hole)

# ---- panel (SAT070AT40D21 + Fannal CT0476 CTP) ------------------------------------
PANEL = (20.02, 184.92, 19.00, 119.00)   # outline x0, x1, y0, y1 (absolute, from DS1's Dwgs.User)
PANEL_T = 5.32                    # LCM 3.34 + CTP stack 1.98
PANEL_T_TOL = 0.30                # LCM thickness tolerance (+-) per SAT drawing
STANDOFF = 5.0                    # PCB back -> panel back
VA = (26.31, 181.39, 23.23, 110.15)      # cover view area (absolute; front view 3.53 from left, 8.85 from bottom)
AA = (26.76, 180.94, 23.82, 109.84)      # active area (absolute)

# ---- insulating sheet between PCB back and panel back -----------------------------
SHEET_T = 0.4                     # Formex-type PP sheet (see doc: GK-17 is 0.43 mm, GK-10 is 0.25 mm)
SHEET_INSET = 0.5                 # sheet = panel outline - 2 x 0.5 (= outline - 1 mm)
SHEET_R = 1.0                     # sheet corner radius

# ---- front sheet / gasket (oven side, NOT part of the moulding) -------------------
GASKET_T = 1.0                    # closed-cell silicone sponge, nominal
GASKET_COMP = 0.30                # design compression (fraction of GASKET_T) at the feet-plane contact
OVEN_SHEET_T = 1.0                # steel front sheet thickness (1.0..1.5); studs are chosen for it
CUTOUT_MARGIN = 0.5               # front-sheet window = cover view area + margin per side
CUTOUT_R = 1.0
GASKET_IN_MARGIN = 1.0            # gasket inner edge = cover view area + this per side (hidden behind the sheet)
GASKET_OUT_INSET = 0.3            # gasket outer edge = glass outline - this per side

# ---- moulding rules (PA6-GF30) -----------------------------------------------------
WALL = 2.5                        # nominal wall
RIB_T = 1.5                       # 0.6 x wall
DRAFT = 1.0                       # deg, all faces along the pull
DRAFT_LOC = 0.5                   # deg, panel locating faces (pocket walls)
FILLET_IN = 0.5                   # min. inside fillet (boss roots, rib roots)
FRAME_R = 5.0                     # outer corner radius of the frame body

# ---- panel seat --------------------------------------------------------------------
POCKET_CLR = 0.25                 # panel to pocket wall, per side
LEADIN = 0.8                      # 45 deg lead-in chamfer at the pocket mouth
SEAT_W = 2.6                      # shelf (panel seat) width under the panel border (inside the outline);
                                  # 2.6 keeps the F3 clip leads (top edge) >= 1 mm from the shelf edge
PCB_RIM_W = 2.1                   # PCB support ribs reach this far inside the panel outline (0.5 land to the shelf edge)
SUPPORT_PITCH = 20.0              # target pitch of the PCB support ribs along each edge
SUPPORT_SHIFT = 6.0               # a rib may move this far from its ideal position to clear pads
PAD_CLR = 1.0                     # PCB support kept >= this from any B.Cu pad / solder fillet
SHELF_T = WALL                    # shelf thickness

# ---- PCB screw bosses (thread-forming screw into PA6-GF30) ------------------------
SCREW_D = 2.9                     # ISO 7049-C / DIN 7981 ST2.9 x 9.5 (alt. PT K30 x 10, same pilot)
PILOT_D = 2.4                     # pilot hole (~0.8 d for PA-GF30, screw maker tables)
BOSS_OD = 8.0                     # >= 2 d; sized for the 16 MPa bearing limit (see calc.py)
CBORE_D, CBORE_H = 3.2, 0.5       # 0.5 mm relief at the pilot mouth (no bulge under the PCB)
RIB_TOP_GAP = 0.5                 # boss-to-rim ribs stop this far below the PCB back

# ---- tail pocket (FPC U-loops below the bottom edge) ------------------------------
LOOPS = {                         # outer envelopes of the U-loops (absolute x0, x1, y_max) and Z range
    "CTP": (40.7, 75.8, 137.4),
    "TFT": (84.0, 165.9, 146.2)}
LOOP_Z = (-9.06, 2.55)            # Z range of both loops incl. FPC thickness (from the panel model)
LOOP_CLR = 1.5                    # clearance around the loop envelopes
TROUGH_R = 5.0                    # inner corner radius at the bottom of the pocket (FPC never on a sharp corner)

# ---- mounting to the oven front sheet ----------------------------------------------
FOOT_HOLE = 4.5                   # M4 stud clearance
FOOT_OD = 9.5                     # foot tube OD (wall 2.5); DIN 9021 M4 washer (OD 12) bears on it
FOOT_H = 5.0                      # tube height above the feet plane
FOOT_PAD_W = 12.0                 # pad plate that ties the foot into the frame wall
FEET = {                          # absolute (x, y). Eight, not six: the top side between two feet is the
    "F1": (13.0, 12.0),           # weakest span (gasket force lifts the frame off the sheet, calc.py);
    "F2": (72.7, 12.0),           # corner feet + top feet at the third points keep every span <= 60 mm
    "F3": (132.3, 12.0),
    "F4": (192.0, 12.0),
    "F5": (192.4, 69.0),          # right
    "F6": (177.0, 139.0),         # bottom right (inside the corner cell)
    "F7": (28.0, 139.0),          # bottom left (inside the corner cell)
    "F8": (12.6, 69.0)}           # left
PEGS = True                       # two dia-3 locating pegs into the sheet
PEG_D, PEG_H = 3.0, 0.8           # peg height < sheet thickness
PEG_POS = {"P1": (32.5, 146.0), "P2": (172.5, 146.0)}

# =====================================================================================
# DERIVED Z LEVELS
# =====================================================================================
Z_PCB = 0.0
Z_PANEL_BACK = -STANDOFF
Z_SEAT = Z_PANEL_BACK + SHEET_T              # shelf front face (sheet sits on it, panel on the sheet)
Z_GLASS = Z_PANEL_BACK - PANEL_T             # cover glass front
Z_FRONT = Z_GLASS - GASKET_T * (1 - GASKET_COMP)   # feet plane = inner face of the oven front sheet
Z_SHELF_BACK = Z_SEAT + SHELF_T              # top of the outer walls / shelf back face
Z_TROUGH_TOP = LOOP_Z[1] + LOOP_CLR          # tail-pocket walls rise to here (outside the board only)

# =====================================================================================
# DERIVED PLAN GEOMETRY (absolute, y-down)
# =====================================================================================
PX0, PX1, PY0, PY1 = PANEL
POCKET = (PX0 - POCKET_CLR, PX1 + POCKET_CLR, PY0 - POCKET_CLR, PY1 + POCKET_CLR)
OUTER = (POCKET[0] - WALL, POCKET[1] + WALL, POCKET[2] - WALL, None)   # bottom set below
TR_X0 = LOOPS["CTP"][0] - LOOP_CLR
TR_X1 = LOOPS["TFT"][1] + LOOP_CLR
TR_Y0 = POCKET[3]                             # pocket starts at the panel pocket line
TR_Y1 = max(LOOPS["TFT"][2], LOOPS["CTP"][2]) + max(LOOP_CLR, TROUGH_R)   # R5 corner keeps >= 1.5 to the loop corner
BEAM_Y1 = TR_Y1 + WALL
OUTER = (OUTER[0], OUTER[1], OUTER[2], BEAM_Y1)


def Yc(y):
    """absolute y (down) -> model Y (up)"""
    return -y


# =====================================================================================
# PRIMITIVES
# =====================================================================================
def prism(x0, x1, y0, y1, z0, z1, taper=0.0, r=0.0):
    """Rectangle (absolute x0..x1, y0..y1), optional corner radius r, extruded from z0 to z1.
    taper > 0: the section shrinks going from z0 to z1 (draft for a pull towards z1)."""
    up = z1 > z0
    pl = cq.Plane(origin=(0, 0, z0), xDir=(1, 0, 0), normal=(0, 0, 1 if up else -1))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ly = Yc(cy) if up else -Yc(cy)                   # local y flips with the normal
    w, h = abs(x1 - x0), abs(y1 - y0)
    sk = cq.Sketch().rect(w, h)
    if r > 0:
        sk = sk.vertices().fillet(min(r, w / 2 - 1e-3, h / 2 - 1e-3))
    wp = cq.Workplane(pl).center(cx, ly).placeSketch(sk)
    return wp.extrude(abs(z1 - z0), taper=taper)


def tube(x, y, z0, z1, od, idia=0.0, taper=0.0):
    up = z1 > z0
    pl = cq.Plane(origin=(0, 0, z0), xDir=(1, 0, 0), normal=(0, 0, 1 if up else -1))
    ly = Yc(y) if up else -Yc(y)
    s = cq.Workplane(pl).center(x, ly).circle(od / 2).extrude(abs(z1 - z0), taper=taper)
    if idia > 0:
        s = s.cut(cq.Workplane(pl).center(x, ly).circle(idia / 2).extrude(abs(z1 - z0)))
    return s


def ring(o, i, z0, z1, taper=0.0, r_o=0.0, r_i=0.0):
    a = prism(*o, z0, z1, taper=taper, r=r_o)
    b = prism(*i, z0 - 1, z1 + 1, r=r_i)
    return a.cut(b)


# =====================================================================================
# PCB SUPPORT SEGMENTS (rim top face), clear of every B.Cu pad by PAD_CLR
# =====================================================================================
def _pad_boxes():
    if not os.path.exists(BOARD_GEOM):
        return []
    d = json.load(open(BOARD_GEOM))
    out = []
    for p in d["pads"]:
        if not p["on_bcu"] or p["attr"] == "NPTH" or not p["poly"]:
            continue
        xs = [q[0] for poly in p["poly"] for q in poly]
        ys = [q[1] for poly in p["poly"] for q in poly]
        out.append((min(xs) - PAD_CLR, max(xs) + PAD_CLR, min(ys) - PAD_CLR, max(ys) + PAD_CLR,
                    "%s.%s" % (p["ref"], p["num"])))
    return out


def support_ribs():
    """PCB support ribs (top face = PCB back) from the outer wall's inner face to PCB_RIM_W inside the
    panel outline, about every SUPPORT_PITCH, each >= PAD_CLR from every B.Cu pad.
    Returns [(x0, x1, y0, y1, side)], [skipped (side, position)]."""
    pads = _pad_boxes()
    hw = RIB_T / 2
    ribs, skipped = [], []
    sides = {  # side: (run axis range, fixed range across the rib)
        "T": ((PX0 + 8, PX1 - 8), (POCKET[2] - 0.1, PY0 + PCB_RIM_W)),
        "B": ((PX0 + 8, PX1 - 8), (PY1 - PCB_RIM_W, POCKET[3] + 0.1)),
        "L": ((PY0 + 8, PY1 - 8), (POCKET[0] - 0.1, PX0 + PCB_RIM_W)),
        "R": ((PY0 + 8, PY1 - 8), (PX1 - PCB_RIM_W, POCKET[1] + 0.1))}
    for side, (run, fix) in sides.items():
        n = max(2, int(round((run[1] - run[0]) / SUPPORT_PITCH)) + 1)
        for k in range(n):
            ideal = run[0] + k * (run[1] - run[0]) / (n - 1)
            best = None
            for step in [i * 0.25 for i in range(int(SUPPORT_SHIFT / 0.25) + 1)]:
                for sgn in (1, -1):
                    c = ideal + sgn * step
                    if side in "TB":
                        f0, f1 = fix
                        if side == "B" and TR_X0 - hw - 1 < c < TR_X1 + hw + 1:
                            f1 = PY1 - 0.5          # the shelf ends at the panel edge over the tail pocket
                        r = (c - hw, c + hw, f0, f1)
                    else:
                        r = (fix[0], fix[1], c - hw, c + hw)
                    if all(r[1] <= p[0] or r[0] >= p[1] or r[3] <= p[2] or r[2] >= p[3] for p in pads):
                        best = r
                        break
                if best:
                    break
            if best:
                ribs.append(best + (side,))
            else:
                skipped.append((side, round(ideal, 1)))
    return ribs, skipped


# =====================================================================================
# FRAME
# =====================================================================================
def _bop(kind, base, tools):
    """One multi-tool boolean (much faster than chained Workplane unions/cuts)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    if not tools:
        return base
    op = BRepAlgoAPI_Fuse() if kind == "fuse" else BRepAlgoAPI_Cut()
    a, t = TopTools_ListOfShape(), TopTools_ListOfShape()
    a.Append(base.wrapped)
    for x in tools:
        t.Append((x.val() if isinstance(x, cq.Workplane) else x).wrapped)
    op.SetArguments(a)
    op.SetTools(t)
    op.SetRunParallel(True)
    op.Build()
    if not op.IsDone():
        raise RuntimeError("boolean %s failed" % kind)
    return cq.Shape.cast(op.Shape()).clean()


def _v(w):
    return w.val() if isinstance(w, cq.Workplane) else w


def build_frame(log=print):
    import time
    t0 = time.time()
    t = math.tan(math.radians(DRAFT))
    base_d = BOSS_OD + 2 * (Z_PCB - Z_FRONT) * t
    adds, cuts = [], []

    # 1. body: outer outline from the feet plane up to the PCB back plane (outer wall top = PCB plane)
    body = _v(prism(OUTER[0], OUTER[1], OUTER[2], OUTER[3], Z_FRONT, Z_PCB, taper=DRAFT, r=FRAME_R))

    # 2. tall walls of the tail pocket (sides + bottom beam) up to Z_TROUGH_TOP (outside the board only)
    xL0, xR1 = TR_X0 - WALL, TR_X1 + WALL
    adds += [prism(xL0, xR1, TR_Y1, BEAM_Y1, Z_FRONT, Z_TROUGH_TOP, taper=DRAFT),
             prism(xL0, TR_X0 + 0.5, TR_Y0, BEAM_Y1, Z_FRONT, Z_TROUGH_TOP, taper=DRAFT),
             prism(TR_X1 - 0.5, xR1, TR_Y0, BEAM_Y1, Z_FRONT, Z_TROUGH_TOP, taper=DRAFT)]

    # 3. bosses under the nine ears (cone, top dia BOSS_OD at the PCB back)
    for h, (x, y) in HOLES.items():
        adds.append(tube(x, y, Z_FRONT, Z_PCB, base_d, taper=DRAFT))

    # 4. feet outside the outline: pad plate (feet plane, WALL thick) + tube
    for f, (x, y) in FEET.items():
        tx = min(max(x, OUTER[0] + WALL), OUTER[1] - WALL)
        ty = min(max(y, OUTER[2] + WALL), OUTER[3] - WALL)
        hw = FOOT_PAD_W / 2
        inside = OUTER[0] < x < OUTER[1] and OUTER[2] < y < OUTER[3]
        if not inside:
            # one rounded block from the foot into the wall (no tangent disc/rect pairs -> no zero faces)
            adds.append(prism(min(x - hw, tx), max(x + hw, tx), min(y - hw, ty), max(y + hw, ty),
                              Z_FRONT, Z_FRONT + WALL, taper=DRAFT, r=3.0))
            adds.append(tube(x, y, Z_FRONT, Z_FRONT + FOOT_H, FOOT_OD + 2 * FOOT_H * t, taper=DRAFT))
    body = _bop("fuse", body, adds)
    log("  [%.0fs] positive features fused" % (time.time() - t0))

    # 5. cuts: window, pocket, lead-in, open space above the shelf, tail pocket, corner cells
    win = (PX0 + SEAT_W, PX1 - SEAT_W, PY0 + SEAT_W, PY1 - SEAT_W)
    gw = (Z_PCB - Z_FRONT + 2) * t
    cuts.append(prism(win[0] + gw, win[1] - gw, win[2] + gw, win[3] - gw, Z_FRONT - 1, Z_PCB + 1, taper=-DRAFT, r=1.0))
    cuts.append(prism(*POCKET, Z_SEAT, Z_FRONT - 0.01, taper=-DRAFT_LOC, r=0.5))
    li = LEADIN + (Z_SEAT - Z_FRONT) * math.tan(math.radians(DRAFT_LOC))
    cuts.append(prism(POCKET[0] - li, POCKET[1] + li, POCKET[2] - li, POCKET[3] + li,
                      Z_FRONT - 0.01, Z_FRONT + LEADIN + 0.01, taper=45.0, r=0.5 + li))
    cuts.append(prism(*POCKET, Z_SHELF_BACK, Z_PCB + 0.01, taper=-DRAFT, r=0.5))      # above the shelf
    trr = prism(TR_X0, TR_X1, TR_Y0 - 2 * TROUGH_R, TR_Y1, Z_FRONT - 0.01, Z_TROUGH_TOP + 0.01,
                taper=-DRAFT, r=TROUGH_R)
    cuts.append(trr.intersect(prism(TR_X0 - 5, TR_X1 + 5, TR_Y0 + 2 * TROUGH_R, TR_Y1 + 5,
                                    Z_FRONT - 1, Z_TROUGH_TOP + 2)))
    cuts.append(prism(TR_X0, TR_X1, TR_Y0 - 0.5, TR_Y0 + 2 * TROUGH_R + 1, Z_FRONT - 0.01, Z_TROUGH_TOP + 0.01,
                      taper=-DRAFT).intersect(prism(TR_X0 - 5, TR_X1 + 5, PY1, TR_Y0 + 2 * TROUGH_R + 0.5,
                                                    Z_FRONT - 1, Z_TROUGH_TOP + 2)))
    cells = [(OUTER[0] + WALL, TR_X0 - WALL, POCKET[3] + WALL, TR_Y1),
             (TR_X1 + WALL, OUTER[1] - WALL, POCKET[3] + WALL, TR_Y1)]
    for c in cells:
        cuts.append(prism(*c, Z_FRONT + WALL, Z_TROUGH_TOP + 1, taper=-DRAFT, r=2.0))
    body = _bop("cut", body, cuts)
    log("  [%.0fs] cavities cut" % (time.time() - t0))

    # 6. second positive pass: features inside the cavities
    adds = []
    for f, (x, y) in FEET.items():                       # feet inside the corner cells
        if OUTER[0] < x < OUTER[1] and OUTER[2] < y < OUTER[3]:
            adds.append(tube(x, y, Z_FRONT, Z_FRONT + FOOT_H, FOOT_OD + 2 * FOOT_H * t, taper=DRAFT))
    for h in ("H6", "H7"):                               # bosses that stand in the cells
        x, y = HOLES[h]
        adds.append(tube(x, y, Z_FRONT, Z_PCB, base_d, taper=DRAFT))
    ribs, skipped = support_ribs()                       # PCB support ribs on the shelf
    for (x0, x1, y0, y1, side) in ribs:
        adds.append(prism(x0, x1, y0, y1, Z_SHELF_BACK - 0.01, Z_PCB, taper=DRAFT))
    for h, f in (("H6", "F6"), ("H7", "F7")):            # cell ribs: boss -> foot -> cell walls
        x, y = HOLES[h]
        fx, fy = FEET[f]
        adds.append(prism(x - RIB_T / 2, x + RIB_T / 2, y, fy, Z_FRONT + WALL - 0.01, Z_FRONT + FOOT_H, taper=DRAFT))
        c = cells[0] if fx < 100 else cells[1]
        adds.append(prism(c[0] - 0.01, c[1] + 0.01, fy - RIB_T / 2, fy + RIB_T / 2, Z_FRONT + WALL - 0.01,
                          Z_FRONT + FOOT_H, taper=DRAFT))
    if PEGS:
        for p, (x, y) in PEG_POS.items():
            adds.append(tube(x, y, Z_FRONT + 0.01, Z_FRONT - PEG_H, PEG_D, taper=DRAFT_LOC))
    body = _bop("fuse", body, adds)
    log("  [%.0fs] ribs, cell feet, pegs fused" % (time.time() - t0))

    # 7. holes + final trims (pocket re-cut, nothing above the PCB plane over the board)
    cuts = []
    for h, (x, y) in HOLES.items():
        cuts.append(tube(x, y, Z_FRONT - 1, Z_PCB + 1, PILOT_D))
        cuts.append(tube(x, y, Z_PCB - CBORE_H, Z_PCB + 1, CBORE_D))
    for f, (x, y) in FEET.items():
        cuts.append(tube(x, y, Z_FRONT - 1, Z_FRONT + FOOT_H + 1, FOOT_HOLE))
    cuts.append(prism(*POCKET, Z_SEAT, Z_FRONT - 0.01, taper=-DRAFT_LOC, r=0.5))
    cuts.append(prism(OUTER[0] - 30, OUTER[1] + 30, OUTER[2] - 30, POCKET[3], Z_PCB, Z_PCB + 20))
    body = _bop("cut", body, cuts)
    log("  [%.0fs] holes cut" % (time.time() - t0))

    solid = body
    if log:
        log("frame: valid=%s solids=%d volume=%.1f cm3 mass=%.0f g (1.36 g/cm3)" % (
            solid.isValid(), len(solid.Solids()), solid.Volume() / 1000, solid.Volume() / 1000 * 1.36))
        log("support ribs: %d, skipped positions: %s" % (len(ribs), skipped))
    return cq.Workplane().add(solid), ribs, skipped


def build_sheet():
    """Formex-type insulating sheet: panel outline - 1 mm, between PCB back and panel back."""
    return prism(PX0 + SHEET_INSET, PX1 - SHEET_INSET, PY0 + SHEET_INSET, PY1 - SHEET_INSET,
                 Z_PANEL_BACK, Z_SEAT, r=SHEET_R)


def build_gasket():
    """Compressed silicone sponge gasket between glass and oven sheet (for the assembly picture)."""
    o = (PX0 + GASKET_OUT_INSET, PX1 - GASKET_OUT_INSET, PY0 + GASKET_OUT_INSET, PY1 - GASKET_OUT_INSET)
    i = (VA[0] - GASKET_IN_MARGIN, VA[1] + GASKET_IN_MARGIN, VA[2] - GASKET_IN_MARGIN, VA[3] + GASKET_IN_MARGIN)
    return ring(o, i, Z_FRONT, Z_GLASS, r_o=1.0, r_i=1.0)


def build_oven_sheet(margin=25.0):
    """A patch of the oven front sheet (steel, OVEN_SHEET_T) with the window, stud and peg holes."""
    x0, x1, y0, y1 = OUTER[0] - margin, OUTER[1] + margin, OUTER[2] - margin, OUTER[3] + margin
    s = prism(x0, x1, y0, y1, Z_FRONT, Z_FRONT - OVEN_SHEET_T, r=3.0)
    co = (VA[0] - CUTOUT_MARGIN, VA[1] + CUTOUT_MARGIN, VA[2] - CUTOUT_MARGIN, VA[3] + CUTOUT_MARGIN)
    s = s.cut(prism(*co, Z_FRONT + 1, Z_FRONT - OVEN_SHEET_T - 1, r=CUTOUT_R))
    if PEGS:
        for p, (x, y) in PEG_POS.items():
            s = s.cut(tube(x, y, Z_FRONT + 1, Z_FRONT - OVEN_SHEET_T - 1, PEG_D + 0.2))
    return s


def cutout_rect():
    return (VA[0] - CUTOUT_MARGIN, VA[1] + CUTOUT_MARGIN, VA[2] - CUTOUT_MARGIN, VA[3] + CUTOUT_MARGIN)


def summary():
    return {
        "Z_FRONT": Z_FRONT, "Z_GLASS": Z_GLASS, "Z_PANEL_BACK": Z_PANEL_BACK, "Z_SEAT": Z_SEAT,
        "Z_SHELF_BACK": Z_SHELF_BACK, "Z_TROUGH_TOP": Z_TROUGH_TOP,
        "OUTER": OUTER, "POCKET": POCKET, "TROUGH": (TR_X0, TR_X1, TR_Y0, TR_Y1), "BEAM_Y1": BEAM_Y1,
        "boss_base_d": BOSS_OD + 2 * (Z_PCB - Z_FRONT) * math.tan(math.radians(DRAFT)),
    }


if __name__ == "__main__":
    f, ribs, skipped = build_frame()
    print(json.dumps(summary(), indent=1))
    cq.exporters.export(f, os.path.join(HERE, "out", "frame_only.step"))
