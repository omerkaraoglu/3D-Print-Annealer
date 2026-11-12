"""Pass 4 schematic edits (EMC provisions + top-side FPC connectors), scoped text patches:
Rev3_Display.kicad_sch:
  - J10 -> Connfly DS1020-09-40VBT1B (upper contact, top side), J11 -> KLS L-KLS1-242D-1.2-06-T-U-R (upper contact, top side)
  - 7 x 33R 4-element arrays RN1..RN7 between the SSD1963 and the panel lines (U10-side labels renamed <net>_T)
  - C129 100 nF VLED_P-VLED_N, C130/C131 1 nF VLED_P/VLED_N-GND, C132 1 nF TFT_VDD-GND at J10; C133 1 nF TP_VDD-GND at J11
  - D115/D116 PESD5V0S1BA on TP_INT and LCD_RST at J11
3dFilamentDryer.kicad_sch (root): RV1 -> Thinking TVR14431KSU15Y (275 V ac class, 14 mm)."""
import re, uuid
PRJ = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/"
DISP = PRJ + "Rev3_Display.kicad_sch"; ROOT = PRJ + "3dFilamentDryer.kicad_sch"
SCR = r"C:/Users/lenovo/AppData/Local/Temp/claude/dad0af2289ad5142/c8708701-d586-4d89-8e7b-a64a4af1e14d/scratchpad/"
PATH = "/ea3996f2-7d6b-4a86-86ab-4ed62213f41f/3a0f6c2e-0001-4c3e-9b1e-000000000001"
s = open(DISP, encoding="utf-8").read()
U = lambda: str(uuid.uuid4())
def reuuid(t): return re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda m: '(uuid "%s")' % U(), t)

# ---------------------------------------------------------------- helpers ----
def top_items(t):
    """split the file body into top-level items [(start, end)] (depth-1 parentheses), starting after '(kicad_sch'"""
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
def sym_block(t, ref):
    i = t.index('(property "Reference" "%s"' % ref)
    for a, b in top_items(t):
        if a < i < b: return a, b
    raise KeyError(ref)
def coords(blk):
    return [(float(x), float(y)) for x, y in re.findall(r'\((?:at|xy) ([\d.\-]+) ([\d.\-]+)', blk)]
def shift(blk, dx, dy):
    return re.sub(r'\((at|xy) ([\d.\-]+) ([\d.\-]+)', lambda m: '(%s %s %s' % (m.group(1), round(float(m.group(2)) + dx, 2), round(float(m.group(3)) + dy, 2)), blk)
def clone_cluster(t, bbox, dx, dy, subs):
    """copy every top-level item whose coordinates all lie inside bbox (x1,y1,x2,y2), shifted by (dx,dy), new uuids, text subs"""
    x1, y1, x2, y2 = bbox; out = []
    for a, b in top_items(t):
        blk = t[a:b]
        if blk.startswith("(symbol") and "(lib_id" not in blk[:60]: continue      # lib_symbols container
        if not blk.startswith(("(symbol", "(wire", "(label", "(global_label")): continue
        cs = coords(blk)
        if cs and all(x1 <= x <= x2 and y1 <= y <= y2 for x, y in cs):
            nb = reuuid(shift(blk, dx, dy))
            for o, n in subs: nb = nb.replace(o, n)
            out.append(nb)
    return out
def prop(name, value, x, y, hide=True):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n'
            % (name, value, x, y, "\t\t\t(hide yes)\n" if hide else "", "" if hide else "\t\t\t\t(justify left)\n"))
def wire(x1, y1, x2, y2):
    return '\t(wire\n\t\t(pts\n\t\t\t(xy %s %s)\n\t\t\t(xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, U())
def label(name, x, y, rot):
    return '\t(label "%s"\n\t\t(at %s %s %s)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (name, x, y, rot, U())
def set_prop(blk, name, value):
    pat = r'\(property "%s" "(?:[^"\\]|\\.)*"' % name
    assert len(re.findall(pat, blk)) == 1, name
    return re.sub(pat, lambda m: '(property "%s" "%s"' % (name, value), blk)

def check_count(blocks, kind, n):
    k = sum(1 for b in blocks if b.startswith(kind)); assert k == n, (kind, k, n)

# ---------------------------------------------------------------- 1. connectors ----
a, b = sym_block(s, "J10"); blk = s[a:b]
blk = set_prop(blk, "Footprint", "Rev3:Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide")
blk = set_prop(blk, "MPN", "DS1020-09-40VBT1B")
blk = set_prop(blk, "Description", "SATOZ SAT070AT40D21 7\\\" 800x480 TFT, 24-bit RGB, 40-pin 0.5 mm FPC. Connector on the TOP side (pass 4): Connfly DS1020-09-40VBT1B UPPER contact, tail folded once around the PCB bottom edge; footprint pads numbered in panel order (mirrored)")
s = s[:a] + blk + s[b:]
a, b = sym_block(s, "J11"); blk = s[a:b]
blk = set_prop(blk, "Footprint", "Rev3:KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide")
blk = set_prop(blk, "MPN", "L-KLS1-242D-1.2-06-T-U-R")
blk = set_prop(blk, "Manufacturer", "KLS Electronic")
blk = set_prop(blk, "Description", "Fannal FN070A133 capacitive touch panel (GT911, I2C 0x5D/0x14), 6-pin 0.5 mm FPC. Connector on the TOP side (pass 4): KLS L-KLS1-242D-1.2-06-T-U-R UPPER contact, H 1.2 mm; footprint pads numbered in panel order (mirrored)")
s = s[:a] + blk + s[b:]
print("connectors done")

# ---------------------------------------------------------------- 2. rename the U10-side labels -> <net>_T ----
NETS = [f"{c}{i}" for c in "RGB" for i in range(8)] + ["PCLK", "HSYNC", "VSYNC", "DE"]
for n in NETS:
    pat = r'\(label "%s"\n\t\t\(at 217\.17 ' % re.escape(n)
    assert len(re.findall(pat, s)) == 1, n
    s = re.sub(pat, '(label "%s_T"\n\t\t(at 217.17 ' % n, s)
print("labels renamed")

# ---------------------------------------------------------------- 3. R_Pack04 lib symbol + 7 arrays ----
lib = open(SCR + "rpack04_sym.txt", encoding="utf-8").read().replace('(symbol "R_Pack04"', '(symbol "Device:R_Pack04"', 1)
lib = "\n".join("\t" + l for l in lib.splitlines())
i = s.index("(lib_symbols")
s = s[:i + len("(lib_symbols")] + "\n" + lib + s[i + len("(lib_symbols"):]
a, b = sym_block(s, "R125"); tmpl = s[a:b]
new = ""
groups = [("RN1", ["R0", "R1", "R2", "R3"]), ("RN2", ["R4", "R5", "R6", "R7"]), ("RN3", ["G0", "G1", "G2", "G3"]), ("RN4", ["G4", "G5", "G6", "G7"]),
          ("RN5", ["B0", "B1", "B2", "B3"]), ("RN6", ["B4", "B5", "B6", "B7"]), ("RN7", ["PCLK", "HSYNC", "VSYNC", "DE"])]
XOFF = [-5.08, -2.54, 0.0, 2.54]
for k, (ref, nets) in enumerate(groups):
    X, Y = 254.0, 66.04 + 19.05 * k
    blk = tmpl.replace('(lib_id "Device:R")', '(lib_id "Device:R_Pack04")')
    blk = re.sub(r'\(at 330\.2 59\.69 0\)', '(at %s %s 0)' % (X, Y), blk, count=1)
    blk = blk.replace('(at 332.74 57.15 0)', '(at %s %s 0)' % (X + 7.62, Y - 2.54)).replace('(at 332.74 59.69 0)', '(at %s %s 0)' % (X + 7.62, Y))
    blk = blk.replace('(at 330.2 59.69 0)', '(at %s %s 0)' % (X, Y))
    blk = set_prop(blk, "Reference", ref).replace('(reference "R125")', '(reference "%s")' % ref)
    blk = set_prop(blk, "Value", "33R x4")
    blk = set_prop(blk, "Footprint", "Resistor_SMD:R_Array_Convex_4x0402")
    blk = set_prop(blk, "Datasheet", "https://www.ozdisan.com/c?search=4D02WGJ0330TCE")
    blk = set_prop(blk, "Description", "Resistor array 4 x 33 Ohm 5 % 1/16 W, 0402x4 convex (1206 size, 0.8 mm pitch): series termination of the RGB/sync lines at the SSD1963 (EMC pass 4)")
    pins = "".join('\t\t(pin "%d"\n\t\t\t(uuid "%s")\n\t\t)\n' % (p, U()) for p in range(1, 9))
    blk = re.sub(r'\t\t\(pin "1"\n.*?\t\t\(pin "2"\n\t\t\t\(uuid "[^"]+"\)\n\t\t\)\n', pins, blk, count=1, flags=re.S)
    j = blk.index("\t\t(pin \"1\"")
    blk = blk[:j] + prop("MPN", "4D02WGJ0330TCE", X, Y) + prop("Manufacturer", "Royalohm", X, Y) + blk[j:]
    blk = reuuid(blk)
    new += blk + "\n"
    for xo, net in zip(XOFF, nets):
        new += wire(round(X + xo, 2), round(Y + 5.08, 2), round(X + xo, 2), round(Y + 7.62, 2)) + label(net + "_T", round(X + xo, 2), round(Y + 7.62, 2), 270)
        new += wire(round(X + xo, 2), round(Y - 5.08, 2), round(X + xo, 2), round(Y - 7.62, 2)) + label(net, round(X + xo, 2), round(Y - 7.62, 2), 90)
new += '\t(text "RN1-RN7: 33 Ohm series termination of the 24 RGB + 4 sync lines at the SSD1963 (EMI rule 11, EMC pass 4); <net>_T = controller side."\n\t\t(exclude_from_sim no)\n\t\t(at 240 50 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % U()
print("arrays built")

# ---------------------------------------------------------------- 4. capacitors at the connectors ----
c123 = clone_cluster(s, (352, 61, 360, 78), 0, 0, [])
check_count(c123, "(symbol", 2); check_count(c123, "(wire", 2); check_count(c123, "(label", 1)
def cap_clone(dx, ref, value, descr, topnet, botnet_label=None):
    items = clone_cluster(s, (352, 61, 360, 78), dx, 0, [('"C123"', '"%s"' % ref), ('(label "TFT_VDD"', '(label "%s"' % topnet)])
    out = ""
    for it in items:
        if it.startswith("(symbol") and '(lib_id "Device:C")' in it:
            it = set_prop(it, "Value", value); it = set_prop(it, "Description", descr)
        if botnet_label and it.startswith("(symbol") and '(lib_id "power:GND")' in it:
            x, y = coords(it)[0]
            it = label(botnet_label, x, y, 270).strip("\t\n")        # replace the GND power symbol by a net label
        out += "\t" + it + "\n"
    return out
new += cap_clone(15.24, "C129", "100nF 25V X7R", "100 nF across the backlight pair at J10: RF return for the FPC (EMC pass 4)", "VLED_P", "VLED_N")
new += cap_clone(25.4, "C130", "1nF 50V C0G", "1 nF RF return at J10 pin 2 (EMC pass 4)", "VLED_P")
new += cap_clone(35.56, "C131", "1nF 50V C0G", "1 nF RF return at J10 pin 1 (EMC pass 4)", "VLED_N")
new += cap_clone(45.72, "C132", "1nF 50V C0G", "1 nF RF return at J10 pin 4 next to C123 (EMC pass 4)", "TFT_VDD")
c126 = clone_cluster(s, (142, 235, 148, 256), 12.7, 0, [('"C126"', '"C133"')])
check_count(c126, "(symbol", 2)
for it in c126:
    if it.startswith("(symbol") and '(lib_id "Device:C")' in it:
        it = set_prop(it, "Value", "1nF 50V C0G"); it = set_prop(it, "Description", "1 nF RF return at J11 pin 1 (EMC pass 4)")
    new += "\t" + it + "\n"
print("capacitors built")

# ---------------------------------------------------------------- 5. ESD diodes on TP_INT and LCD_RST ----
d112 = clone_cluster(s, (166, 252, 175, 272), 0, 0, [])
check_count(d112, "(symbol", 2); check_count(d112, "(global_label", 1)
for dx, ref, net in ((45.72, "D115", "TP_INT"), (60.96, "D116", "LCD_RST")):
    for it in clone_cluster(s, (166, 252, 175, 272), dx, 0, [('"D112"', '"%s"' % ref), ('(global_label "I2C_SDA"', '(global_label "%s"' % net)]):
        new += "\t" + it + "\n"
print("ESD built")

# insert everything before the sheet_instances block
i = s.rstrip().rfind(")")            # sub-sheet: no sheet_instances block; insert before the final closing paren
s = s[:i] + new + s[i:]
open(DISP, "w", encoding="utf-8").write(s); print("display sheet written")

# ---------------------------------------------------------------- 6. root: RV1 ----
r = open(ROOT, encoding="utf-8").read()
a, b = sym_block(r, "RV1"); blk = r[a:b]
blk = set_prop(blk, "Value", "TVR14431KSU15Y")
blk = set_prop(blk, "Footprint", "Varistor:RV_Disc_D15.5mm_W5mm_P7.5mm")
blk = set_prop(blk, "Datasheet", "https://www.ozdisan.com/c?search=TVR14431KSU15Y")
blk = set_prop(blk, "Description", "VARISTOR DISC 14MM 430V 4.5KA 275VAC 350VDC THT (pass 4: 275 V ac class so the 1 kV L-N surge clamps below the BTA24's 800 V; was 10561K)")
r = r[:a] + blk + r[b:]
open(ROOT, "w", encoding="utf-8").write(r); print("root RV1 written")

# ---------------------------------------------------------------- 7. renumber duplicated power-symbol references created by the clones ----
import collections
for F in (DISP,):
    t = open(F, encoding="utf-8").read()
    refs = re.findall(r'\(property "Reference" "(#PWR\d+)"', t)
    dup = [r for r, n in collections.Counter(refs).items() if n > 1]
    nxt = max(int(r[4:]) for r in refs) + 1
    for r in dup:
        parts = t.split('(property "Reference" "%s"' % r)
        # parts[0] + first occurrence stay; every later occurrence (its block runs until the next top-level item) gets a new number
        out = parts[0] + '(property "Reference" "%s"' % r + parts[1]
        for seg in parts[2:]:
            seg = seg.replace('(reference "%s")' % r, '(reference "#PWR%d")' % nxt, 1)
            out += '(property "Reference" "#PWR%d"' % nxt + seg; nxt += 1
        t = out
    open(F, "w", encoding="utf-8").write(t); print("renumbered power refs:", dup)
