"""Panel bond, step 4: drawings.  Reads results.json, out/board_pads.json, out/finger_model.json and writes
to Mechanical/Rev3.0_PanelBond/:
  PB_Formex_Openings_v2.dxf / .png, PB_Formex_Openings_GF21.dxf / .png  (sheet seen from the PCB side, KiCad abs mm)
  PB_Contact_Map_v2.png, PB_Contact_Map_GF21.png
  PB_Section_v2_GF21.png  (both stack-ups to scale)
  PB_Finger_Model.png     (copy of the model plot)
  Rev3.0_PanelBond_Overview.pdf (2 pages)
and runs a text/box overlap check on every matplotlib figure (prints the count; 0 required).
Run: python -X utf8 draw.py
"""
import json, math, os, shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTD = os.path.join(ROOT, 'Mechanical', 'Rev3.0_PanelBond')
R = json.load(open(os.path.join(HERE, 'results.json'), encoding='utf8'))
BRD = json.load(open(os.path.join(HERE, 'out', 'board_pads.json'), encoding='utf8'))
FM = json.load(open(os.path.join(HERE, 'out', 'finger_model.json')))
OFF = 20.0
SETS = R['contact_sets']
REC = SETS['recommended_8']
MIN = SETS['minimum_6']
DES = {'v2': 'Frame v2', 'GF': 'Glass front GF-2.1'}
FILE = {'v2': 'v2', 'GF': 'GF21'}

# ------------------------------------------------------------------ DXF (R12 ASCII, hand written)
class DXF:
    def __init__(self):
        self.e = []
        self.layers = {}

    def layer(self, name, color):
        self.layers[name] = color

    def line(self, a, b, ly):
        self.e += ['0', 'LINE', '8', ly, '10', f'{a[0]:.4f}', '20', f'{a[1]:.4f}', '30', '0.0', '11', f'{b[0]:.4f}', '21', f'{b[1]:.4f}', '31', '0.0']

    def arc(self, c, r, a0, a1, ly):
        self.e += ['0', 'ARC', '8', ly, '10', f'{c[0]:.4f}', '20', f'{c[1]:.4f}', '30', '0.0', '40', f'{r:.4f}', '50', f'{a0:.4f}', '51', f'{a1:.4f}']

    def circle(self, c, r, ly):
        self.e += ['0', 'CIRCLE', '8', ly, '10', f'{c[0]:.4f}', '20', f'{c[1]:.4f}', '30', '0.0', '40', f'{r:.4f}']

    def text(self, p, h, s, ly, align=0):
        self.e += ['0', 'TEXT', '8', ly, '10', f'{p[0]:.4f}', '20', f'{p[1]:.4f}', '30', '0.0', '40', f'{h:.3f}', '1', s]
        if align:
            self.e += ['72', str(align), '11', f'{p[0]:.4f}', '21', f'{p[1]:.4f}', '31', '0.0']

    def rrect(self, x0, x1, y0, y1, r, ly):
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        self.line((x0 + r, y0), (x1 - r, y0), ly)
        self.line((x1, y0 + r), (x1, y1 - r), ly)
        self.line((x1 - r, y1), (x0 + r, y1), ly)
        self.line((x0, y1 - r), (x0, y0 + r), ly)
        self.arc((x1 - r, y0 + r), r, 270, 360, ly)
        self.arc((x1 - r, y1 - r), r, 0, 90, ly)
        self.arc((x0 + r, y1 - r), r, 90, 180, ly)
        self.arc((x0 + r, y0 + r), r, 180, 270, ly)

    def save(self, path):
        h = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1009', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC',
             '0', 'SECTION', '2', 'TABLES', '0', 'TABLE', '2', 'LAYER', '70', str(len(self.layers))]
        for n, c in self.layers.items():
            h += ['0', 'LAYER', '2', n, '70', '0', '62', str(c), '6', 'CONTINUOUS']
        h += ['0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
        t = ['0', 'ENDSEC', '0', 'EOF']
        open(path, 'w', encoding='ascii').write('\n'.join(h + self.e + t) + '\n')


# ------------------------------------------------------------------ overlap checker
def overlap_check(fig, tag):
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    boxes = []
    for ax in fig.axes:
        for t in ax.texts:
            if t.get_visible() and t.get_text().strip():
                boxes.append((t.get_window_extent(rend).expanded(1.02, 1.05), t.get_text()[:30], id(ax)))
        for t in (ax.title, ax.xaxis.label, ax.yaxis.label):
            if t.get_visible() and t.get_text().strip():
                boxes.append((t.get_window_extent(rend), 'AX:' + t.get_text()[:28], id(ax)))
    for t in fig.texts:
        if t.get_text().strip():
            boxes.append((t.get_window_extent(rend), t.get_text()[:30], 'fig'))
    n = 0
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i][0].overlaps(boxes[j][0]):
                n += 1
                bad.append((boxes[i][1], boxes[j][1]))
    print(f'[overlap] {tag}: {n} text-text overlaps', bad[:5])
    return n


def local_to_abs(x, y):
    return x + OFF, y + OFF


# ------------------------------------------------------------------ Formex opening drawings
def formex_drawing(d):
    op = R['openings'][d]
    sh = R['inputs']['formex_sheet_abs']['value']
    win = R['inputs']['shelf_window_local']['value']
    dx = DXF()
    for n, c in (('SHEET', 7), ('OPENINGS', 1), ('REF_SHELF_WINDOW', 8), ('REF_PADS', 3), ('TEXT', 7)):
        dx.layer(n, c)
    # DXF in KiCad abs coordinates with y flipped (DXF y up = -abs y): seen from the PCB side
    fy = lambda y: -y
    dx.rrect(sh[0], sh[1], fy(sh[3]), fy(sh[2]), 1.0, 'SHEET')
    dx.rrect(win[0] + OFF, win[1] + OFF, fy(win[3] + OFF), fy(win[2] + OFF), 0.5, 'REF_SHELF_WINDOW')
    for r in op['rows']:
        o = r['opening_abs']
        dx.rrect(o[0], o[1], fy(o[3]), fy(o[2]), R['inputs']['opening_R']['value'], 'OPENINGS')
        p = [b for b in BRD['landing_pads'] if b['ref'] == r['ref']][0]
        cx, cy = local_to_abs(p['x'], p['y'])
        dx.rrect(cx - 3.0, cx + 3.0, fy(cy + 2.5), fy(cy - 2.5), 0.0, 'REF_PADS')
        dx.text((r['centre_abs'][0], fy(o[2]) + 0.6), 1.5, f"{r['ref']} {r['size'][0]:.1f}x{r['size'][1]:.1f}", 'TEXT')
    dx.text((sh[0] + 2, fy(sh[3]) - 4), 2.0, f"PB-{FILE[d]} Formex openings, {DES[d]}; seen from the PCB side; KiCad abs mm, DXF y = -y; R1 corners", 'TEXT')
    dxf_path = os.path.join(OUTD, f'PB_Formex_Openings_{FILE[d]}.dxf')
    dx.save(dxf_path)
    # PNG
    fig = plt.figure(figsize=(16.5, 11.7))
    ax = fig.add_axes([0.04, 0.37, 0.92, 0.57])
    ax.add_patch(FancyBboxPatch((sh[0] + 1, sh[2] + 1), sh[1] - sh[0] - 2, sh[3] - sh[2] - 2, boxstyle='round,pad=1',
                                fc='#f3ead2', ec='k', lw=1.2))
    ax.add_patch(Rectangle((win[0] + OFF, win[2] + OFF), win[1] - win[0], win[3] - win[2], fc='none', ec='0.5', ls='--', lw=0.8))
    for r in op['rows']:
        o = r['opening_abs']
        ax.add_patch(FancyBboxPatch((o[0] + 1, o[2] + 1), o[1] - o[0] - 2, o[3] - o[2] - 2, boxstyle='round,pad=1', fc='white', ec='tab:red', lw=1.2))
        p = [b for b in BRD['landing_pads'] if b['ref'] == r['ref']][0]
        cx, cy = local_to_abs(p['x'], p['y'])
        ax.add_patch(Rectangle((cx - 3.0, cy - 2.5), 6.0, 5.0, fc='none', ec='tab:green', lw=0.6, ls=':'))
        ax.plot(*r['centre_abs'], '+', color='tab:red', ms=6)
        ax.text(r['centre_abs'][0], o[2] - 1.0, r['ref'], ha='center', va='bottom', fontsize=9, color='tab:red')
    ax.set_xlim(sh[0] - 4, sh[1] + 4)
    ax.set_ylim(sh[3] + 4, sh[2] - 6)
    ax.set_aspect('equal')
    ax.set_xlabel('KiCad abs x (mm)')
    ax.set_ylabel('KiCad abs y (mm, down)')
    ax.set_title(f"PB-{FILE[d]}: Formex sheet {sh[1]-sh[0]:.2f} x {sh[3]-sh[2]:.2f} with {len(op['rows'])} openings - {DES[d]} - seen from the PCB side (front view is mirrored)", fontsize=11)
    fig.text(0.04, 0.285, 'dashed grey: shelf window (reference)   dotted green: 6.0 x 5.0 bare pad (reference)   red: openings, R1 corners, centre cross',
             fontsize=8, va='bottom')
    tab = fig.add_axes([0.04, 0.02, 0.92, 0.25]); tab.axis('off')
    cols = ['opening', 'centre x', 'centre y', 'size x', 'size y', 'x0', 'x1', 'y0', 'y1', 'web to sheet edge', 'in shelf window']
    rows = [[r['ref'], f"{r['centre_abs'][0]:.2f}", f"{r['centre_abs'][1]:.2f}", f"{r['size'][0]:.2f}", f"{r['size'][1]:.2f}",
             *[f"{v:.2f}" for v in r['opening_abs']], f"{r['web_to_sheet_edge']:.2f}", f"{r['window_margin']:.2f}"] for r in op['rows']]
    t = tab.table(cellText=rows, colLabels=cols, loc='upper center', cellLoc='center')
    t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.25)
    w = op['min_web_between']
    tab.text(0.0, 0.0, f"All mm, KiCad abs. Size = finger envelope + per side x {op['added_per_side_x']:.2f} / y {op['added_per_side_y']:.2f} "
             f"(finger tolerance, placement 0.15, PCB-to-frame 0.30, sheet-to-frame {R['inputs']['tol_sheet_'+('v2' if d=='v2' else 'gf')]['value']:.2f}, running gap 0.30). "
             f"Smallest web between openings {w[0]:.2f} ({w[1]}-{w[2]}). Source: tools/panel_bond/results.json openings.{d}.", fontsize=8, va='bottom')
    n = overlap_check(fig, f'formex {d}')
    fig.savefig(os.path.join(OUTD, f'PB_Formex_Openings_{FILE[d]}.png'), dpi=110)
    plt.close(fig)
    return n


# ------------------------------------------------------------------ contact maps
def contact_map(d, ax=None, small=False):
    own = ax is None
    if own:
        fig = plt.figure(figsize=(15, 10))
        ax = fig.add_axes([0.05, 0.12, 0.9, 0.8])
    ax.add_patch(Rectangle((0, 0), 164, 99, fc='#e8f0e8', ec='k', lw=1))
    # mains boundary
    for s in BRD['cmts_user']:
        xs = [p[0] for p in s]; ys = [p[1] for p in s]
        ax.plot(xs, ys, color='m', lw=1.2)
    ax.text(82, -1.5, 'magenta line: mains band boundary (Cmts.User); magenta dots: mains / HS1 pins', color='m',
            fontsize=8 if not small else 6, ha='center', va='bottom')
    lab = R['inputs']['panel_label_local']['value']
    ax.add_patch(Rectangle((lab[0], lab[2]), lab[1] - lab[0], lab[3] - lab[2], fc='#fff2b3', ec='orange', lw=0.8, hatch='//'))
    ax.text((lab[0] + lab[1]) / 2, lab[2] - 1.0, 'panel label', fontsize=7 if not small else 5, ha='center', va='bottom', color='darkorange')
    # tails at the panel bottom edge (outside the board)
    for (x0, x1, nm) in ((40.72 - OFF, 75.82 - OFF, 'CTP tail exit'), (84.02 - OFF, 122.62 - OFF, 'TFT tail exit')):
        ax.add_patch(Rectangle((x0, 99.6), x1 - x0, 2.4, fc='#d9c2e9', ec='purple', lw=0.6))
        ax.text((x0 + x1) / 2, 102.6, nm, fontsize=7 if not small else 5, ha='center', va='top', color='purple')
    for ref in ('J10', 'J11'):
        c = BRD['connectors'][ref]
        x0, x1 = c['pads_x'][0] - 0.5, c['pads_x'][1] + 0.5
        y0, y1 = c['pads_y'][0] - 0.5, c['pads_y'][1] + 0.5
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='none', ec='b', lw=0.8, ls='--'))
        ax.text(x0 + 0.3, y1 + 0.5, f'{ref} pads (top side)', fontsize=7 if not small else 4.5, color='b', ha='left', va='top')
    for row in R['openings'][d]['rows']:
        o = row['opening_local']
        ax.add_patch(Rectangle((o[0], o[2]), o[1] - o[0], o[3] - o[2], fc='none', ec='tab:red', lw=0.8))
    for b in BRD['landing_pads']:
        ref = b['ref']
        col = '#bbbbbb'
        if ref in REC:
            col = '#2ca02c'
        if ref in MIN:
            col = '#1f5f1f'
        ax.add_patch(Rectangle((b['x'] - 3, b['y'] - 2.5), 6, 5, fc=col, ec='k', lw=0.5))
        ax.text(b['x'], b['y'], ref[2:], ha='center', va='center', fontsize=8 if not small else 5.5,
                color='white' if ref in REC else 'k')
    for m in [p for p in BRD['tht_pads'] if p['mains_net'] or p['ref'] == 'HS1']:
        ax.plot(m['x'], m['y'], 'o', ms=3 if not small else 2, color='m')
    ax.set_xlim(-3, 167); ax.set_ylim(106, -6)
    ax.set_aspect('equal')
    if own:
        ax.set_xlabel('local x = KiCad abs - 20 (mm), seen from the component side (looking at the panel back)')
        ax.set_ylabel('local y (mm)')
        ax.set_title(f"Contact map, {DES[d]}: dark green = minimum set ({len(MIN)}), all green = recommended set ({len(REC)}), grey = unused; red = Formex openings; magenta dots = mains pins", fontsize=10)
        fig.text(0.05, 0.015, 'Minimum: ' + ', '.join(MIN) + '.   Recommended: ' + ', '.join(REC) + '.\n'
                 'Panel label box scaled from the SAT070 datasheet p.16 back view (undimensioned; BP3 and BP17 sit on it). J10/J11 boxes = their pads + 0.5. '
                 'The tails leave the panel below the board edge in both designs.', fontsize=8, va='bottom')
        n = overlap_check(fig, f'contact map {d}')
        fig.savefig(os.path.join(OUTD, f'PB_Contact_Map_{FILE[d]}.png'), dpi=110)
        plt.close(fig)
        return n
    return 0


# ------------------------------------------------------------------ cross-sections
def section(ax, d):
    """section from the opening's pad to its governing mains pin, true scale (axis equal)."""
    ins = R['insulation'][d]
    gov = min(ins, key=lambda r: r['clear_panel']['mm'])
    ref = gov['ref']
    row = [r for r in R['openings'][d]['rows'] if r['ref'] == ref][0]
    pad = [b for b in BRD['landing_pads'] if b['ref'] == ref][0]
    item = gov['clear_panel']['item']
    pref, pnum = item.split(' ')[0].split('.')
    pin = [p for p in BRD['tht_pads'] if p['ref'] == pref and p['num'] == pnum]
    pin = min(pin, key=lambda p: math.hypot(p['x'] - pad['x'], p['y'] - pad['y']))
    prot = R['inputs']['protrusion']['value'].get(pref, R['inputs']['protrusion_default']['value'])
    L = math.hypot(pin['x'] - pad['x'], pin['y'] - pad['y'])
    ux, uy = (pin['x'] - pad['x']) / L, (pin['y'] - pad['y']) / L
    # where the section line leaves the opening
    o = row['opening_local']
    ts = [t for t in np.linspace(0, L, 4001) if o[0] <= pad['x'] + ux * t <= o[1] and o[2] <= pad['y'] + uy * t <= o[3]]
    s_open = max(ts)
    s_open_neg = -min(abs(pad['x'] - o[0]) / max(abs(ux), 1e-6), abs(o[1] - pad['x']) / max(abs(ux), 1e-6),
                      abs(pad['y'] - o[2]) / max(abs(uy), 1e-6), abs(o[3] - pad['y']) / max(abs(uy), 1e-6))
    if d == 'v2':
        zf_back, tf, zp = 4.6, 0.40, 5.0
        hcase = '5.0'
    else:
        zf_back, tf, zp = 4.6, 0.40, 5.8
        hcase = '5.8'
    s0, s1 = s_open_neg - 4, L + 4
    # PCB
    ax.add_patch(Rectangle((s0, 0.0), s1 - s0, 1.6, fc='#cfe3cf', ec='k', lw=0.6))
    ax.text(s0 + 0.5, 0.8, 'PCB 1.6', va='center', fontsize=7)
    # pad copper (8 mm along x; section through the centre)
    ax.add_patch(Rectangle((-4.0, -0.035), 8.0, 0.035, fc='#c87533', ec='none'))
    # finger: model shapes, base centred on the pad, drawn in its own plane rotated into the section
    case = FM['cases']['t_nom_0.127']
    X0 = np.array(case['X0']); S = np.array(case['shapes'][hcase])
    sgn = 1 if (R['pads'][ref]['bend_dir'] * ux) >= 0 else -1
    ax.plot(sgn * (S[:, 0] - 2.5), -(S[:, 1] + 0.03), color='goldenrod', lw=1.6)
    # Formex with the opening
    ax.add_patch(Rectangle((s0, -zf_back - tf), s_open_neg - s0, tf, fc='#f0e0b0', ec='k', lw=0.5))
    ax.add_patch(Rectangle((s_open, -zf_back - tf), s1 - s_open, tf, fc='#f0e0b0', ec='k', lw=0.5))
    # panel back metal + some of the panel
    ax.add_patch(Rectangle((s0, -zp - 1.2), s1 - s0, 1.2, fc='#b8c4d6', ec='k', lw=0.6))
    ax.text(s0 + 0.5, -zp - 0.6, 'panel (metal back)', va='center', fontsize=7)
    # mains pin: pad, lead, tip
    pr = max(pin['sx'], pin['sy']) / 2
    lr = max((pin['drill'][0] if pin['drill'] else 1.0) - 0.2, 0.5) / 2
    ax.add_patch(Rectangle((L - pr, -0.035), 2 * pr, 0.035, fc='#c87533', ec='none'))
    ax.add_patch(Polygon([[L - pr, 0], [L + pr, 0], [L + lr, -0.6], [L - lr, -0.6]], fc='#a0a0a0', ec='k', lw=0.4))
    ax.add_patch(Rectangle((L - lr, -prot), 2 * lr, prot, fc='#888888', ec='k', lw=0.5))
    ax.add_patch(Rectangle((L - lr, 0), 2 * lr, 1.6, fc='#888888', ec='none', alpha=0.6))
    # clearance line: pin tip to the opening rim at the panel
    tip = (L - lr, -prot)
    rim = (s_open, -zp)
    ax.annotate('', xy=rim, xytext=tip, arrowprops=dict(arrowstyle='<->', color='r', lw=0.9))
    dmm = gov['clear_panel']['mm']
    ax.text(rim[0] + 1.0, -2.3, f"{dmm:.1f} mm >= 6.4", color='r', fontsize=8, ha='left', va='bottom')
    ax.text(L, 2.4, f"{pref}.{pnum} {pin['net']}\nlead tip -{prot:.2f}", ha='center', va='bottom', fontsize=7)
    ax.text(0.0, 2.4, f"{ref} + finger", ha='center', va='bottom', fontsize=7)
    ax.text(s1 - 0.3, -zf_back + 0.2, f"Formex {tf:.2f}", ha='right', va='bottom', fontsize=7)
    ax.set_xlim(s0, s1)
    ax.set_ylim(-zp - 1.6, 4.4)
    ax.set_aspect('equal')
    ax.set_xlabel(f'distance along the line {ref} -> {pref}.{pnum} (mm)')
    ax.set_ylabel('Z (mm), PCB back = 0')
    ax.set_title(f"{DES[d]}: panel back at -{zp:.1f} (nominal); finger compressed to h {hcase} (beam model)", fontsize=9)
    return gov


def finger_inset(ax, d):
    """free and compressed finger side by side, same scale, with the design's panel level."""
    case = FM['cases']['t_nom_0.127']
    X0 = np.array(case['X0'])
    hcase = '5.0' if d == 'v2' else '5.8'
    S = np.array(case['shapes'][hcase])
    ax.add_patch(Rectangle((-1.0, 0.0), 17.0, 0.6, fc='#cfe3cf', ec='k', lw=0.5))
    ax.plot(X0[:, 0], -(X0[:, 1] + 0.03), color='0.3', lw=1.2)
    ax.plot(S[:, 0] + 8.5, -(S[:, 1] + 0.03), color='goldenrod', lw=1.4)
    zp = float(hcase)
    ax.add_patch(Rectangle((7.5, -zp - 0.8), 8.5, 0.8, fc='#b8c4d6', ec='k', lw=0.5, hatch='///'))
    ax.text(3.0, 0.9, 'free 7.5', ha='center', va='bottom', fontsize=7)
    ax.text(11.5, 0.9, f'at h {hcase}', ha='center', va='bottom', fontsize=7)
    ax.text(11.75, -zp - 1.1, 'panel back', ha='center', va='top', fontsize=6.5)
    ax.set_xlim(-1.5, 16.5); ax.set_ylim(-8.6, 2.2); ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([0, -2, -4, -6])
    ax.set_title('finger, same scale', fontsize=8)


def section_fig():
    fig = plt.figure(figsize=(16, 9))
    a1 = fig.add_axes([0.05, 0.56, 0.70, 0.36]); a2 = fig.add_axes([0.05, 0.10, 0.70, 0.36])
    g1 = section(a1, 'v2'); g2 = section(a2, 'GF')
    finger_inset(fig.add_axes([0.78, 0.58, 0.19, 0.32]), 'v2')
    finger_inset(fig.add_axes([0.78, 0.12, 0.19, 0.32]), 'GF')
    fig.text(0.05, 0.96, 'PB sections, true scale: PCB, landing pad, Laird LT17BH0731 compressed (beam model), Formex opening, panel back and the governing mains lead tip; right: the finger free and compressed',
             fontsize=10)
    fig.text(0.05, 0.02, 'The finger profile is drawn in its own plane, rotated into the section line. Lead protrusions: Rev3.0_Frame_Design.md s6 (others assumed 2.5). '
             'Clearance drawn = shortest air path from the lead tip to the panel metal through the opening (results.json insulation).', fontsize=8)
    n = overlap_check(fig, 'sections')
    fig.savefig(os.path.join(OUTD, 'PB_Section_v2_GF21.png'), dpi=110)
    plt.close(fig)
    return n, g1, g2


# ------------------------------------------------------------------ overview PDF
def overview():
    pdf = PdfPages(os.path.join(OUTD, 'Rev3.0_PanelBond_Overview.pdf'))
    n = 0
    # page 1
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.text(0.03, 0.965, 'Rev3.0 panel bond - SMD spring fingers from the PCB back pads to the panel metal (proposal, 2026-11-21)', fontsize=15, weight='bold')
    fig.text(0.03, 0.94, 'Part: Laird LT17BH0731 SMD contact finger (BeCu, Au flash over Ni), free height 7.5, base 5 x 5 - Ozdisan stock 602,220, 0.17 USD at 1. '
             'One part for both designs.', fontsize=10)
    a = fig.add_axes([0.03, 0.50, 0.45, 0.40]); contact_map('v2', a, small=True)
    a.set_title(f'Frame v2: minimum {len(MIN)} (dark), recommended {len(REC)} (green)', fontsize=9)
    b = fig.add_axes([0.52, 0.50, 0.45, 0.40]); contact_map('GF', b, small=True)
    b.set_title(f'Glass front GF-2.1: same pads; openings sized for its sheet tolerance', fontsize=9)
    c = fig.add_axes([0.03, 0.06, 0.30, 0.38])
    case = FM['cases']['t_nom_0.127']
    X0 = np.array(case['X0'])
    c.plot(X0[:, 0], X0[:, 1], 'k-', lw=1.2, label='free 7.5')
    for hs, col in (('6.25', 'tab:blue'), ('5.8', 'tab:green'), ('5.0', 'tab:orange')):
        if hs in case['shapes']:
            S = np.array(case['shapes'][hs]); c.plot(S[:, 0], S[:, 1], color=col, lw=1, label=f'h {hs}')
    c.set_aspect('equal'); c.grid(alpha=0.3); c.legend(fontsize=7, loc='lower right')
    c.set_title('finger centre line (beam model)', fontsize=9)
    d = fig.add_axes([0.38, 0.06, 0.28, 0.38])
    for nm, col in (('t_min_0.107', 'tab:blue'), ('t_nom_0.127', 'k'), ('t_max_0.147', 'tab:red')):
        h = [r['h'] for r in FM['cases'][nm]['hist']]; F = [r['F'] for r in FM['cases'][nm]['hist']]
        d.plot(h, F, color=col, lw=1, label=nm)
    for dd, key, col, yy in (('v2', 'v2_formex_0.40', 'tab:orange', 0.97), ('GF', 'GF-2.1', 'tab:green', 0.89)):
        st = R['stackups'][key]
        d.axvspan(st['wc'][0], st['wc'][1], color=col, alpha=0.15)
        d.text((st['wc'][0] + st['wc'][1]) / 2, yy, DES[dd] + ' WC range', transform=d.get_xaxis_transform(), ha='center', va='top', fontsize=7, color=col)
    d.axvline(R['elastic_limit']['h_at_yield_nominal_strip'], color='r', ls=':', lw=1)
    d.text(R['elastic_limit']['h_at_yield_nominal_strip'] - 0.05, 0.80, 'yield (t 0.127)', transform=d.get_xaxis_transform(), fontsize=7, color='r', ha='left', va='top')
    d.invert_xaxis(); d.grid(alpha=0.3); d.legend(fontsize=7, loc='center left')
    d.set_xlabel('working height (mm)'); d.set_ylabel('force per finger (N, estimate)')
    e = fig.add_axes([0.70, 0.06, 0.28, 0.38]); e.axis('off')
    fv = R['finger']['per_design']
    lines = [('', 'frame v2', 'GF-2.1'),
             ('height nom (mm)', f"{fv['v2_formex_0.40']['h_nom']:.2f}", f"{fv['GF-2.1']['h_nom']:.2f}"),
             ('height WC', f"{fv['v2_formex_0.40']['h_wc'][0]:.2f}-{fv['v2_formex_0.40']['h_wc'][1]:.2f}", f"{fv['GF-2.1']['h_wc'][0]:.2f}-{fv['GF-2.1']['h_wc'][1]:.2f}"),
             ('force nom (N)', f"{fv['v2_formex_0.40']['F_nom']:.2f}", f"{fv['GF-2.1']['F_nom']:.2f}"),
             ('force WC (N)', f"{fv['v2_formex_0.40']['F_min_wc']:.2f}-{fv['v2_formex_0.40']['F_max_wc']:.2f}", f"{fv['GF-2.1']['F_min_wc']:.2f}-{fv['GF-2.1']['F_max_wc']:.2f}"),
             ('total, 8 fingers WC (N)', f"{R['forces']['v2_recommended_8']['total_max']:.1f}", f"{R['forces']['GF_recommended_8']['total_max']:.1f}"),
             ('stress WC (MPa)', f"{fv['v2_formex_0.40']['sigma_max_wc_tmax']}", f"{fv['GF-2.1']['sigma_max_wc_tmax']}"),
             ('min insulation (mm)', f"{min(min(r['clear_finger']['mm'], r['clear_panel']['mm'], r['creep_formex']['mm']) for r in R['insulation']['v2']):.1f}",
              f"{min(min(r['clear_finger']['mm'], r['clear_panel']['mm'], r['creep_formex']['mm']) for r in R['insulation']['GF']):.1f}")]
    t = e.table(cellText=[list(l) for l in lines[1:]], colLabels=list(lines[0]), loc='upper center', cellLoc='center')
    t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.5)
    e.text(0.0, 0.18, 'Force and stress are model estimates: the maker states\nno force, range, current or temperature. Yield assumed\n965 MPa. Bench test required (results.json finger).',
           fontsize=8, va='top')
    n += overlap_check(fig, 'overview p1')
    pdf.savefig(fig); plt.close(fig)
    # page 2
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.text(0.03, 0.965, 'Formex openings and the stack-ups to scale', fontsize=15, weight='bold')
    for k, (dd, pos) in enumerate((('v2', [0.03, 0.60, 0.45, 0.32]), ('GF', [0.52, 0.60, 0.45, 0.32]))):
        ax = fig.add_axes(pos)
        sh = R['inputs']['formex_sheet_abs']['value']
        ax.add_patch(Rectangle((sh[0], sh[2]), sh[1] - sh[0], sh[3] - sh[2], fc='#f3ead2', ec='k'))
        for r in R['openings'][dd]['rows']:
            o = r['opening_abs']
            ax.add_patch(Rectangle((o[0], o[2]), o[1] - o[0], o[3] - o[2], fc='white', ec='tab:red'))
            ax.text(r['centre_abs'][0], o[2] - 0.8, r['ref'], ha='center', va='bottom', fontsize=6.5, color='tab:red')
        ax.set_xlim(sh[0] - 3, sh[1] + 3); ax.set_ylim(sh[3] + 3, sh[2] - 5); ax.set_aspect('equal')
        ax.set_title(f"{DES[dd]}: sheet seen from the PCB side, abs mm (PB_Formex_Openings_{FILE[dd]}.dxf)", fontsize=9)
    a1 = fig.add_axes([0.03, 0.335, 0.70, 0.21]); section(a1, 'v2'); finger_inset(fig.add_axes([0.76, 0.34, 0.21, 0.20]), 'v2')
    a2 = fig.add_axes([0.03, 0.05, 0.70, 0.21]); section(a2, 'GF'); finger_inset(fig.add_axes([0.76, 0.055, 0.21, 0.20]), 'GF')
    n += overlap_check(fig, 'overview p2')
    pdf.savefig(fig); plt.close(fig)
    pdf.close()
    return n


def main():
    os.makedirs(OUTD, exist_ok=True)
    n = 0
    for d in ('v2', 'GF'):
        n += formex_drawing(d)
        n += contact_map(d)
    k, g1, g2 = section_fig()
    n += k
    n += overview()
    shutil.copy(os.path.join(HERE, 'out', 'finger_model.png'), os.path.join(OUTD, 'PB_Finger_Model.png'))
    print('TOTAL text overlaps', n)
    print('governing sections', g1['ref'], g1['clear_panel'], g2['ref'], g2['clear_panel'])


if __name__ == '__main__':
    main()
