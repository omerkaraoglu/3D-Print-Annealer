"""Pass 4c: the zero-cross detector loses its discrete bridge. U1 4N28 + D1..D4 -> U1 = H11AA1 (AC-input optocoupler, same DIP-6
output pins 4/5/6, LED pair on pins 1/2); R6.2 -> U1.1 (net ZCD_L), R7.2 -> U1.2 (net ZCD_N). Root sheet text patch; the H11AA1
symbol has the same pin geometry as the embedded 4N28 symbol (pins 1/2 at (-7.62, +/-2.54)), so U1's wires stay."""
import re, uuid
ROOT = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/3dFilamentDryer.kicad_sch"
LIB = r"C:/Program Files/KiCad/10.0/share/kicad/symbols/Isolator.kicad_sym"
s = open(ROOT, encoding="utf-8").read()
U = lambda: str(uuid.uuid4())

def top_items(t):
    items = []; depth = 0; q = False; start = None
    for j, c in enumerate(t):
        if c == '"' and t[j - 1] != '\\': q = not q; continue
        if q: continue
        if c == '(':
            depth += 1
            if depth == 2: start = j
        elif c == ')':
            depth -= 1
            if depth == 1 and start is not None: items.append((start, j + 1)); start = None
    return items
def coords(blk): return [(float(x), float(y)) for x, y in re.findall(r'\((?:at|xy) ([\d.\-]+) ([\d.\-]+)', blk)]

# 1. delete the ladder: D1..D4 symbols, the wires/junctions that connect them (all coordinates inside x 123.2..164, y 70..102,
#    excluding the R6/R7 pin-1 wires at x <= 115.57 and U1 itself at x 171)
BB = (123.1, 70.0, 164.5, 102.5)
keep = []; removed = {"symbol": 0, "wire": 0, "junction": 0}
pos = 0; out = ""
for a, b in top_items(s):
    blk = s[a:b]
    kind = blk.split("\n", 1)[0].strip("( ").split(" ")[0] if "\n" in blk[:20] else blk[1:blk.index(" ")] if " " in blk[:12] else blk[1:12]
    kind = re.match(r'\((\w+)', blk).group(1)
    drop = False
    if kind == "symbol" and re.search(r'\(property "Reference" "D[1-4]"', blk): drop = True
    elif kind in ("wire", "junction"):
        cs = coords(blk)
        if cs and all(BB[0] <= x <= BB[2] and BB[1] <= y <= BB[3] for x, y in cs): drop = True
    if drop:
        removed[kind] += 1; out += s[pos:a]; pos = b
out += s[pos:]; s = out
assert removed == {"symbol": 4, "wire": 12, "junction": 4}, removed
print("ladder removed", removed)

# 2. U1 -> H11AA1
i = s.index('(property "Reference" "U1"')
a = s.rfind("\n\t(symbol\n", 0, i); b = s.index("\n\t)\n", i) + 4
blk = s[a:b]
blk = blk.replace('(lib_id "Isolator:4N28")', '(lib_id "Isolator:H11AA1")')
blk = re.sub(r'\(property "Value" "4N28"', '(property "Value" "H11AA1"', blk)
blk = re.sub(r'\(property "Datasheet" "[^"]*"', '(property "Datasheet" "https://www.ozdisan.com/ps/transistor-ve-fotovoltaik-cikisli-optokuplorler-189?f=&s=H11AA1"', blk)
blk = re.sub(r'\(property "Description" "[^"]*"', '(property "Description" "IC-H11AA1 AC-input optocoupler (two inverse-parallel LEDs on pins 1/2), NPN output, 5300 V, DIP-6: zero-cross detector, replaces the 4N28 + D1-D4 bridge (layout pass 4, Isocom H11AA1X, Ozdisan 1,573 pcs)"', blk)
if '(property "MPN"' in blk: blk = re.sub(r'\(property "MPN" "[^"]*"', '(property "MPN" "H11AA1X"', blk)
else:
    j = blk.index('\t\t(pin "1"')
    blk = blk[:j] + '\t\t(property "MPN" "H11AA1X"\n\t\t\t(at 171.45 86.36 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t\t(property "Manufacturer" "Isocom"\n\t\t\t(at 171.45 86.36 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n' + blk[j:]
s = s[:a] + blk + s[b:]
# lib symbol
L = open(LIB, encoding="utf-8").read()
i = L.index('(symbol "H11AA1"'); depth = 0; q = False; j = i
while True:
    c = L[j]
    if c == '"' and L[j - 1] != '\\': q = not q
    elif not q:
        if c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: break
    j += 1
lib = L[i:j + 1].replace('(symbol "H11AA1"', '(symbol "Isolator:H11AA1"', 1)
lib = "\n".join("\t" + l for l in lib.splitlines())
k = s.index("(lib_symbols"); s = s[:k + 12] + "\n" + lib + s[k + 12:]
print("U1 -> H11AA1")

# 3. new wires R6.2 -> U1.1 (ZCD_L), R7.2 -> U1.2 (ZCD_N), with labels
def wire(x1, y1, x2, y2):
    return '\t(wire\n\t\t(pts\n\t\t\t(xy %s %s)\n\t\t\t(xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, U())
def label(name, x, y, rot):
    return '\t(label "%s"\n\t\t(at %s %s %s)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (name, x, y, rot, U())
new = (wire(123.19, 81.28, 158.75, 81.28) + wire(158.75, 81.28, 158.75, 83.82) + wire(158.75, 83.82, 163.83, 83.82) + label("ZCD_L", 139.7, 81.28, 0)
       + wire(123.19, 91.44, 158.75, 91.44) + wire(158.75, 91.44, 158.75, 88.9) + wire(158.75, 88.9, 163.83, 88.9) + label("ZCD_N", 139.7, 91.44, 0)
       + '\t(text "ZCD (pass 4): H11AA1 AC-input optocoupler fed by R6/R7 (2 x 33k) from the PSU AC pair; the 4N28 + D1-D4 bridge is gone. ZCD_L/ZCD_N differ by one LED drop (0.5 mm rule)."\n\t\t(exclude_from_sim no)\n\t\t(at 123.19 68.58 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % U())
k = s.index("\t(sheet_instances"); s = s[:k] + new + s[k:]
open(ROOT, "w", encoding="utf-8").write(s); print("root written")
