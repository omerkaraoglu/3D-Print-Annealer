"""Verification of a tidied project directory against the baseline.

    python -I checks.py <project_dir> [netlist] [erc] [pdf] [collide] [render] [bom] [ids] [all]

netlist : kicad-cli netlist export + per-net (ref, pin) set and name comparison with baseline.xml
erc     : kicad-cli ERC, counts by type compared with the baseline ERC
pdf     : kicad-cli PDF export (tidy.pdf)
collide : text-collision checker on tidy.pdf (strict 0 mm and near-miss 0.5 mm)
render  : PNG pages (60 dpi) and group crops (150 dpi) into <scratch>/schview_tidy
bom     : kicad-cli BOM export grouped by MPN vs Rev3.0_BOM_Ozdisan_100pcs.csv
ids     : symbol UUIDs, instance paths and references vs the baseline sheets; #PWR/#FLG uniqueness
"""
import csv
import json
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import FILES, BASELINE, SCRATCH, KICAD_CLI, Doc, getprop, first, find, key, RENAME  # noqa: E402

ROOT = "3dFilamentDryer.kicad_sch"
BOM_CSV = os.environ.get("BOM_CSV") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "Rev3.0_BOM_Ozdisan_100pcs.csv")
VIEW = os.environ.get("VIEW") or os.path.join(SCRATCH, "schview")
PT = 25.4 / 72.0


def O(d, name):
    """check outputs go to $TIDY_OUT (the scratch area for the real project) or next to the sheets"""
    o = os.environ.get("TIDY_OUT", d)
    os.makedirs(o, exist_ok=True)
    return os.path.join(o, name)


def cli(*args):
    r = subprocess.run([KICAD_CLI] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
    return r


# ---------------------------------------------------------------------------------------------- netlist
def read_net(path):
    root = ET.parse(path).getroot()
    nets = {}
    for n in root.find("nets"):
        nets[n.get("name")] = frozenset((nd.get("ref"), nd.get("pin")) for nd in n.findall("node"))
    comps = {}
    for c in root.find("components"):
        f = {x.get("name"): (x.text or "") for x in c.iter("field")}
        f["value"] = c.findtext("value") or ""
        f["footprint"] = c.findtext("footprint") or ""
        comps[c.get("ref")] = f
    return nets, comps


def netlist(d):
    out = O(d, "tidy_netlist.xml")
    cli("sch", "export", "netlist", "--format", "kicadxml", "-o", out, os.path.join(d, ROOT))
    bn, bc = read_net(os.path.join(BASELINE, "baseline.xml"))
    nn, nc = read_net(out)
    print("== approved net renames (round 2, programmer / auto-boot block):")
    for a, b in RENAME.items():
        same = a in bn and b in nn and bn[a] == nn[b]
        print("   %-16s -> %-6s pins %s  same pin set: %s" % (a, b, " ".join("%s.%s" % x for x in sorted(bn.get(a, ()))), same))
    bn = {RENAME.get(k, k): v for k, v in bn.items()}
    print("== netlist compare: baseline %d nets / %d components, new %d nets / %d components" % (len(bn), len(bc), len(nn), len(nc)))
    bad = 0
    for name in sorted(set(bn) | set(nn)):
        if name not in nn:
            print("  MISSING net", name, sorted(bn[name])); bad += 1
        elif name not in bn:
            print("  EXTRA net", name, sorted(nn[name])); bad += 1
        elif bn[name] != nn[name]:
            print("  DIFF net", name, "baseline-only", sorted(bn[name] - nn[name]), "new-only", sorted(nn[name] - bn[name])); bad += 1
    # name-independent: the set of pin sets
    if set(bn.values()) != set(nn.values()):
        print("  connectivity (name-independent) differs"); bad += 1
    print("  nets identical (names + pin sets): %s, differences: %d" % (bad == 0, bad))
    refs_b, refs_n = set(bc), set(nc)
    print("  components: missing %s, extra %s" % (sorted(refs_b - refs_n), sorted(refs_n - refs_b)))
    fpd = [r for r in refs_b & refs_n if bc[r]["footprint"] != nc[r]["footprint"]]
    print("  footprint changes: %s" % (fpd or "none"))
    vd = sorted((r for r in refs_b & refs_n if bc[r]["value"] != nc[r]["value"]), key=natkey)
    print("  value changes (%d): %s" % (len(vd), ", ".join("%s %s->%s" % (r, bc[r]["value"], nc[r]["value"]) for r in vd)))
    return bad


def natkey(r):
    m = re.match(r"([A-Za-z#]+)(\d+)", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)


# ---------------------------------------------------------------------------------------------- ERC
def erc(d):
    out = O(d, "tidy_erc.json")
    cli("sch", "erc", "--format", "json", "--severity-all", "-o", out, os.path.join(d, ROOT))
    def load(p):
        e = json.load(open(p, encoding="utf-8"))
        items = []
        for s in e["sheets"]:
            for v in s["violations"]:
                items.append((s["path"], v["type"], v["severity"], v["description"], tuple(i["description"] for i in v["items"])))
        return items
    b = load(os.path.join(BASELINE, "erc.json"))
    n = load(out)
    print("== ERC: baseline %d, new %d" % (len(b), len(n)))
    print("  baseline by type:", dict(Counter(x[1] for x in b)))
    print("  new by type     :", dict(Counter(x[1] for x in n)))
    for x in n:
        print("   ", x[0], x[1], x[2], x[3][:80], x[4])
    return n


# ---------------------------------------------------------------------------------------------- PDF
def pdf(d):
    out = O(d, "tidy.pdf")
    cli("sch", "export", "pdf", "-o", out, os.path.join(d, ROOT))
    print("== PDF:", out)
    return out


def page_order(d):
    """PDF page -> sheet key (page order of the sheet_instances / page numbers)"""
    return ["root", "Display", "Thermocouple", "Power", "InputFilter"]


def sheet_geometry(d, sheet):
    """per symbol: body box, pin segments, pin texts; NC points (mm)"""
    doc = Doc(os.path.join(d, FILES[sheet]), sheet)
    syms = []
    for ref, node in list(doc.symbols.items()) + [(getprop(n, "Reference"), n) for n in doc.power_syms]:
        lib = doc.libs[first(node, "lib_id")[1]]
        x, y, rot, mir, unit = doc.placement(node)
        segs, texts = [], set()
        for num, p, o, pd in doc.pins_of(node):
            if pd["hidden"]:
                continue
            q = (p[0] - o[0] * pd["len"], p[1] - o[1] * pd["len"])
            segs.append((p, q))
            texts |= {num, pd["name"]}
            texts |= set(pd["name"].split())
        b = lib.body(unit)
        box = None
        if b:
            from core import xf
            pts = [xf(px, py, rot, mir) for px, py in ((b[0], b[1]), (b[0], b[3]), (b[2], b[1]), (b[2], b[3]))]
            box = (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))
        syms.append(dict(ref=ref, box=box, segs=segs, texts=texts, power=lib.power, value=getprop(node, "Value")))
    ncs = [(float(first(n, "at")[1]), float(first(n, "at")[2])) for n in find(doc.tree, "no_connect")]
    labels = []
    for k in ("label", "global_label"):
        for l in find(doc.tree, k):
            at = first(l, "at")
            labels.append((l[1], (float(at[1]), float(at[2]))))
    return syms, ncs, labels


def inside(a, b, box, m=0.35):
    if not box:
        return False
    x0, y0, x1, y1 = box
    return all(x0 - m <= p[0] <= x1 + m and y0 - m <= p[1] <= y1 + m for p in (a, b))


def inherent(word, a, b, syms, A):
    """symbol-inherent spacing: a pin number/name or a power symbol's value (at its library offset)
    next to the graphics of its own symbol"""
    for s in syms:
        if not s["box"]:
            continue
        near_sym = inside((A[0], A[1]), (A[2], A[3]), s["box"], 6.0)
        if not near_sym:
            continue
        own = inside(a, b, s["box"]) or any(seg_on_seg(a, b, p, q) for p, q in s["segs"])
        if not own:
            continue
        if word in s["texts"]:
            return True
        if inside((A[0], A[1]), (A[2], A[3]), s["box"], 0.3) and not s["power"]:
            return True       # text drawn by the library symbol inside its own body (pin names, '+', 'U', 'BOM')
        if s["power"] and word == s["value"]:
            return True
    return False


def collide(d, pdfpath=None, near=0.5, quiet=False):
    import fitz
    pdfpath = pdfpath or O(d, "tidy.pdf")
    doc = fitz.open(pdfpath)
    order = page_order(d)
    total_strict = 0
    report = {}
    for pi, page in enumerate(doc):
        sheet = order[pi]
        W, H = page.rect.width * PT, page.rect.height * PT
        words = [(w[0] * PT, w[1] * PT, w[2] * PT, w[3] * PT, w[4], (w[5], w[6])) for w in page.get_text("words")]
        # exclusions: frame margin and title block (KiCad default page layout: 110 x 33 mm box at bottom right)
        def excluded(x0, y0, x1, y1):
            if x0 < 13 or y0 < 13 or x1 > W - 13 or y1 > H - 13:
                return True
            if x1 > W - 10 - 112 and y1 > H - 10 - 36:
                return True
            return False
        paths = []
        for dr in page.get_drawings():
            if dr.get("fill") and not dr.get("color") and dr["rect"].width > W / PT * 0.5:
                continue      # page background
            for it in dr["items"]:
                if it[0] == "l":
                    a, b = it[1], it[2]
                    paths.append(((a.x * PT, a.y * PT), (b.x * PT, b.y * PT), dr))
                elif it[0] == "re":
                    r = it[1]
                    c = [(r.x0 * PT, r.y0 * PT), (r.x1 * PT, r.y0 * PT), (r.x1 * PT, r.y1 * PT), (r.x0 * PT, r.y1 * PT)]
                    for k in range(4):
                        paths.append((c[k], c[(k + 1) % 4], dr))
                elif it[0] == "qu":
                    q = it[1]
                    c = [(q.ul.x * PT, q.ul.y * PT), (q.ur.x * PT, q.ur.y * PT), (q.lr.x * PT, q.lr.y * PT), (q.ll.x * PT, q.ll.y * PT)]
                    for k in range(4):
                        paths.append((c[k], c[(k + 1) % 4], dr))
                elif it[0] == "c":
                    pts = [(p.x * PT, p.y * PT) for p in it[1:5]]
                    for k in range(3):
                        paths.append((pts[k], pts[k + 1], dr))
        syms, ncs, labels = sheet_geometry(d, sheet)
        pinsegs_all = [sg for sm in syms for sg in sm["segs"]]
        # glyph strokes: paths fully inside a word box (+0.25 mm) belong to that word
        wb = [(x0 - 0.25, y0 - 0.25, x1 + 0.25, y1 + 0.25) for x0, y0, x1, y1, s, ln in words]
        ink = [None] * len(words)
        graphics = []
        # spatial bucket for words
        grid = defaultdict(list)
        for i, b in enumerate(wb):
            for gx in range(int(b[0] // 5), int(b[2] // 5) + 1):
                for gy in range(int(b[1] // 5), int(b[3] // 5) + 1):
                    grid[(gx, gy)].append(i)
        for a, b, dr in paths:
            x0, x1 = sorted([a[0], b[0]]); y0, y1 = sorted([a[1], b[1]])
            owner = None
            L = math.hypot(x1 - x0, y1 - y0)
            if L > 0.5 and any(seg_on_seg(a, b, p, q) for p, q in pinsegs_all):
                graphics.append((a, b))
                continue          # a pin line is never a glyph stroke
            for i in grid.get((int(x0 // 5), int(y0 // 5)), []):
                B = wb[i]
                if L > (B[3] - B[1]) - 0.4:
                    continue          # longer than a glyph stroke of this word: a real line (pin, wire, body)
                if B[0] <= x0 and x1 <= B[2] and B[1] <= y0 and y1 <= B[3]:
                    if owner is None or (wb[owner][2] - wb[owner][0]) > (B[2] - B[0]):
                        owner = i
            if owner is None:
                graphics.append((a, b))
            else:
                e = ink[owner]
                ink[owner] = (min(e[0], x0), min(e[1], y0), max(e[2], x1), max(e[3], y1)) if e else (x0, y0, x1, y1)
        pinsegs = syms
        hits, nears = [], []
        live = [i for i in range(len(words)) if ink[i] and not excluded(*ink[i])]
        # word vs word
        for ii, i in enumerate(live):
            A = ink[i]
            for j in live[ii + 1:]:
                if words[i][5] == words[j][5]:
                    continue
                B = ink[j]
                if same_symbol_pins(words[i][4], words[j][4], A, B, syms):
                    continue
                gapx = max(B[0] - A[2], A[0] - B[2]); gapy = max(B[1] - A[3], A[1] - B[3])
                gap = max(gapx, gapy)
                if gap < 0:
                    hits.append(("text/text", words[i][4], words[j][4], A))
                elif gap < near:
                    nears.append(("text/text", words[i][4], words[j][4], round(gap, 2), A))
        # word vs graphics
        for i in live:
            A = ink[i]
            for a, b in graphics:
                if near_nc(a, b, ncs):
                    continue
                if any(nm == words[i][4] and pt_seg(pt, a, b) < 0.05 for nm, pt in labels):
                    continue          # a label on its own wire
                dist = seg_box_dist(a, b, A)
                if dist < 0.0 - 1e-9 or dist == 0.0:
                    if inherent(words[i][4], a, b, pinsegs, A):
                        continue
                    hits.append(("text/line", words[i][4], fmtseg(a, b), A))
                elif dist < near:
                    if inherent(words[i][4], a, b, pinsegs, A) or encloses(a, b, A):
                        continue
                    nears.append(("text/line", words[i][4], fmtseg(a, b), round(dist, 2), A))
        report[sheet] = (hits, nears)
        total_strict += len(hits)
        if not quiet:
            print("== collisions %s: %d strict hits, %d near-misses (< %.1f mm)" % (sheet, len(hits), len(nears), near))
            for h in hits:
                print("   HIT", h[0], repr(h[1]), repr(h[2]), "at (%.1f, %.1f)" % (h[3][0], h[3][1]))
            for n in nears:
                print("   near", n[0], repr(n[1]), repr(n[2]), n[3], "mm at (%.1f, %.1f)" % (n[4][0], n[4][1]))
    return total_strict, report


def fmtseg(a, b):
    return "seg(%.1f,%.1f)-(%.1f,%.1f)" % (a[0], a[1], b[0], b[1])


def near_nc(a, b, ncs):
    for p in ncs:
        if max(abs(a[0] - p[0]), abs(a[1] - p[1]), abs(b[0] - p[0]), abs(b[1] - p[1])) < 1.2:
            return True
    return False


def encloses(a, b, A):
    return False


STRICT_SYMBOLS = {"U10"}      # round 2: SSD1963 symbol repaired; its own pin texts must not overlap


def same_symbol_pins(w1, w2, A, B, syms):
    """two pin names/numbers of one library symbol (overlaps drawn by the library symbol itself)"""
    for s in syms:
        if s["ref"] in STRICT_SYMBOLS:
            continue
        if s["box"] and w1 in s["texts"] and w2 in s["texts"] and inside((A[0], A[1]), (A[2], A[3]), s["box"], 3.0)                 and inside((B[0], B[1]), (B[2], B[3]), s["box"], 3.0):
            return True
    return False


def seg_on_seg(a, b, p, q, tol=0.15):
    def on(pt, u, v):
        if abs(u[0] - v[0]) < tol:
            return abs(pt[0] - u[0]) < tol and min(u[1], v[1]) - tol <= pt[1] <= max(u[1], v[1]) + tol
        if abs(u[1] - v[1]) < tol:
            return abs(pt[1] - u[1]) < tol and min(u[0], v[0]) - tol <= pt[0] <= max(u[0], v[0]) + tol
        return False
    return on(a, p, q) and on(b, p, q)


def seg_box_dist(a, b, box):
    """distance from segment a-b to the box (negative/zero when intersecting)"""
    x0, y0, x1, y1 = box
    if clip(a, b, box):
        return 0.0
    # min distance between segment and box edges
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    d = min(pt_seg(c, a, b) for c in corners)
    for p in (a, b):
        dx = max(x0 - p[0], 0, p[0] - x1); dy = max(y0 - p[1], 0, p[1] - y1)
        d = min(d, math.hypot(dx, dy))
    return d


def pt_seg(p, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(ax + t * dx - p[0], ay + t * dy - p[1])


def clip(a, b, box):
    """Liang-Barsky: does segment a-b intersect the box?"""
    x0, y0, x1, y1 = box
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


# ---------------------------------------------------------------------------------------------- render
def render(d, pdfpath=None):
    import fitz
    pdfpath = pdfpath or O(d, "tidy.pdf")
    os.makedirs(VIEW, exist_ok=True)
    regions = json.load(open(O(d, "tidy_regions.json")))
    doc = fitz.open(pdfpath)
    order = page_order(d)
    files = []
    for pi, page in enumerate(doc):
        sheet = order[pi]
        fn = os.path.join(VIEW, "p%d_%s.png" % (pi + 1, sheet))
        page.get_pixmap(dpi=60).save(fn); files.append(fn)
        for name, x0, y0, x1, y1 in regions.get(sheet, []):
            clipr = fitz.Rect(x0 / PT, y0 / PT, x1 / PT, y1 / PT)
            fn = os.path.join(VIEW, "p%d_%s_%s.png" % (pi + 1, sheet, name))
            page.get_pixmap(dpi=150, clip=clipr).save(fn); files.append(fn)
    print("== render: %d files in %s" % (len(files), VIEW))
    return files


# ---------------------------------------------------------------------------------------------- BOM
# round 2: R4/R9 corrected against the CSV (the CSV will be regenerated by the coordinator)
EXPECTED_CHANGE = {}


def bom(d):
    out = O(d, "tidy_bom.csv")
    cli("sch", "export", "bom", "--fields", "Reference,Value,MPN,Manufacturer,${QUANTITY}", "--labels",
        "Refs,Value,MPN,Manufacturer,Qty", "--group-by", "MPN", "--exclude-dnp", "-o", out, os.path.join(d, ROOT))
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig")))
    from fields import expand
    new_mpn = {}
    new_qty = {}
    for r in rows:
        refs = expand(r["Refs"].replace(" ", ""))
        for ref in refs:
            new_mpn[ref] = r["MPN"]
        new_qty[r["MPN"]] = int(r["Qty"])
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fields import expand
    ref_rows = list(csv.DictReader(open(BOM_CSV, encoding="utf-8-sig")))
    exp_mpn = {}
    exp_qty = Counter()
    for r in ref_rows:
        if r["Ref"].startswith("F1/F3"):
            continue
        refs = ["TC1"] if r["Ref"].startswith("TC1") else expand(r["Ref"])
        mpn = r["Part number"].split(" (")[0] if r["Ref"].startswith("TC1") else r["Part number"]
        for ref in refs:
            mpn_r = EXPECTED_CHANGE.get(ref, mpn)
            exp_mpn[ref] = mpn_r
            exp_qty[mpn_r] += 1
        assert len(refs) == int(r["Qty/board"]), r["Ref"]
    print("== BOM: kicad-cli export %d groups, %d refs; reference CSV %d lines, %d refs" % (len(rows), len(new_mpn), len(ref_rows), len(exp_mpn)))
    bad = 0
    for ref in sorted(set(exp_mpn) | set(new_mpn), key=natkey):
        e, n = exp_mpn.get(ref), new_mpn.get(ref)
        if e != n:
            if e is None and n == "":
                print("   %s: in the schematic BOM without MPN (not a purchased line)" % ref)
                continue
            print("   MISMATCH %s: csv %r, schematic %r" % (ref, e, n)); bad += 1
    for mpn in sorted(set(exp_qty) | set(new_qty)):
        if exp_qty.get(mpn) != new_qty.get(mpn) and mpn:
            print("   QTY %r: csv %s, schematic %s" % (mpn, exp_qty.get(mpn), new_qty.get(mpn))); bad += 1
    for ref, m in EXPECTED_CHANGE.items():
        print("   expected change %s: csv has the old line, schematic %r" % (ref, new_mpn.get(ref)))
    print("  BOM mismatches: %d" % bad)
    return bad


# ---------------------------------------------------------------------------------------------- ids
def ids(d):
    bad = 0
    allrefs = Counter()
    for sheet, fn in FILES.items():
        b = Doc(os.path.join(BASELINE, fn), sheet)
        n = Doc(os.path.join(d, fn), sheet)
        def info(doc):
            out = {}
            for ref, node in doc.symbols.items():
                inst = first(first(node, "instances"), "project")
                path = first(inst, "path")
                out[ref] = (first(node, "uuid")[1], path[1], first(path, "reference")[1], first(node, "lib_id")[1])
            return out
        bi, ni = info(b), info(n)
        for ref in bi:
            if ref not in ni:
                print("  %s: %s missing" % (sheet, ref)); bad += 1
            elif bi[ref][:3] != ni[ref][:3]:
                print("  %s: %s uuid/path/ref changed %s -> %s" % (sheet, ref, bi[ref], ni[ref])); bad += 1
            elif bi[ref][3] != ni[ref][3]:
                print("  %s: %s lib_id %s -> %s" % (sheet, ref, bi[ref][3], ni[ref][3]))
        for ref in ni:
            if ref not in bi:
                print("  %s: new symbol %s (%s)" % (sheet, ref, ni[ref][3]))
        for ref in ni:
            allrefs[ref] += 1
        for node in n.power_syms:
            allrefs[getprop(node, "Reference")] += 1
            path = first(first(first(node, "instances"), "project"), "path")[1]
            if path != n.inst_path:
                print("  %s: power symbol %s with path %s" % (sheet, getprop(node, "Reference"), path)); bad += 1
        # sheet symbols on the root
        if sheet == "root":
            bs = {first(s, "uuid")[1] for s in b.sheets}
            ns = {first(s, "uuid")[1] for s in n.sheets}
            if bs != ns:
                print("  sheet symbol uuids changed"); bad += 1
        tree_uuid_b = first(b.tree, "uuid")[1]; tree_uuid_n = first(n.tree, "uuid")[1]
        if tree_uuid_b != tree_uuid_n:
            print("  %s: file uuid changed" % sheet); bad += 1
    dup = [r for r, c in allrefs.items() if c > 1]
    print("== ids: %d symbols+power over 5 sheets, duplicates %s, problems %d" % (sum(allrefs.values()), dup or "none", bad + len(dup)))
    return bad + len(dup)


if __name__ == "__main__":
    d = sys.argv[1]
    what = sys.argv[2:] or ["all"]
    if "all" in what:
        what = ["netlist", "erc", "pdf", "collide", "render", "bom", "ids"]
    for w in what:
        globals()[w](d)
