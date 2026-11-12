"""Pass 3 schematic edit: move the mains LC filter (L40 + C40, sheet Rev3_InputFilter) from the PSU branch to the mains input so
the heater (F3/Q1), the fan relay (K1) and the PSU branch (F1 -> L1 -> PS1) all sit behind it.  New topology:
  J3.L = LINE -> F3 (8 A, main fuse) -> LINE_FUSED -> L40 -> LINE_FILT ; C40, C1, RV1 across LINE_FILT/NEUT
  LINE_FILT -> Q1.A2 (heater), -> K1.1 (fan relay), -> F1 (1 A) -> PSU_L -> L1 -> PS1
Also: L40 becomes Core Master RC1415U-101K (100 uH, 5 A, 100 mOhm) because it now carries the heater current.
Scoped text edits on the root sheet + the filter sheet; verified afterwards by netlist export and ERC."""
import re, sys, uuid
ROOT = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/3dFilamentDryer.kicad_sch"
FILT = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/Rev3_InputFilter.kicad_sch"
s = open(ROOT, encoding="utf-8").read()

def once(pat, repl, flags=re.S):
    global s
    n = len(re.findall(pat, s, flags)); assert n == 1, (pat[:70], n)
    s = re.sub(pat, repl, s, count=1, flags=flags)

def del_wire(x1, y1, x2, y2):
    # wire block: (wire (pts (xy x1 y1) (xy x2 y2)) (stroke ...) (uuid ...))  with KiCad 9/10 line breaks
    global s
    body = r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\)\n\t\t\t\(xy %s %s\)\n\t\t\)\n\t\t\(stroke\n(?:\t\t\t[^\n]*\n)*?\t\t\)\n\t\t\(uuid "[^"]+"\)\n\t\)'
    p1 = body % (x1, y1, x2, y2); p2 = body % (x2, y2, x1, y1)
    n1, n2 = len(re.findall(p1, s)), len(re.findall(p2, s))
    assert n1 + n2 == 1, ("wire", x1, y1, x2, y2, n1, n2)
    s = re.sub(p1 if n1 else p2, "", s, count=1)

def del_power_symbol(x, y):
    pat = r'\n\t\(symbol\n\t\t\(lib_id "power:LINE"\)\n\t\t\(at %s %s 0\)\n.*?\n\t\)\n' % (x, y)
    once(pat, "\n")

def glabel(name, x, y, rot, shape="passive"):
    return ('\n\t(global_label "%s"\n\t\t(shape %s)\n\t\t(at %s %s %s)\n\t\t(fields_autoplaced yes)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n\t\t(uuid "%s")\n\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)'
            % (name, shape, x, y, rot, uuid.uuid4(), x, y))

# 1. F3 output -> LINE_FUSED (to the filter sheet); the triac/snubber node -> LINE_FILT
del_wire("314.96", "58.42", "314.96", "63.5")
new_labels = glabel("LINE_FUSED", "314.96", "58.42", "90") + glabel("LINE_FILT", "314.96", "63.5", "90")
# 2. fan relay K1.1 from LINE_FILT instead of LINE
del_power_symbol("281.94", "161.29")
del_wire("281.94", "161.29", "281.94", "163.83")
new_labels += glabel("LINE_FILT", "281.94", "163.83", "90")
# 3. PSU branch: F1 fed from LINE_FILT, its output PSU_L goes to L1 only; RV1/C1 stay on LINE_FILT
del_power_symbol("20.32", "22.86")
del_wire("20.32", "22.86", "20.32", "27.94")
new_labels += glabel("LINE_FILT", "20.32", "27.94", "180")
once(r'\(global_label "LINE_FUSED"\n\t\t\(shape passive\)\n\t\t\(at 43.18 27.94 0\)', '(global_label "PSU_L"\n\t\t(shape passive)\n\t\t(at 43.18 27.94 0)')
del_wire("90.17", "27.94", "68.58", "27.94")
new_labels += glabel("PSU_L", "90.17", "27.94", "180")
# insert the new labels before the first existing global label
i = s.index("\n\t(global_label ")
s = s[:i] + new_labels + s[i:]
# 4. sheet name / filter description
once(r'\(property "Sheetname" "Mains input EMC filter \(PSU branch\)"', '(property "Sheetname" "Mains input EMC filter"')
open(ROOT, "w", encoding="utf-8").write(s); print("root patched")

f = open(FILT, encoding="utf-8").read()
def frep(old, new):
    global f
    assert f.count(old) == 1, old[:60]; f = f.replace(old, new)
frep('"Rev3.0 Mains input EMC filter (PSU branch)"', '"Rev3.0 Mains input EMC filter"')
frep('(property "Value" "120uH"', '(property "Value" "100uH 5A"')
frep('(property "Footprint" "Rev3:L_Radial_D22.5mm_P9.00mm"', '(property "Footprint" "Rev3:L_Radial_CoreMaster_RC1415U"')
frep('"IND-120UH-THT"', '"RC1415U-101K"')
frep('"OEM (ozdisan)"', '"CORE MASTER"')
frep('https://www.ozdisan.com/p/sabit-induktorler-468/oem-ind-120uh-tht-954101', 'https://www.ozdisan.com/p/sabit-induktorler-468/core-master-rc1415u-101k-500941')
f = f.replace("Inductor fixed radial 120 uH, wire wound, unshielded, D22.5 x 8.25 mm, pitch 9 mm, THT",
              "Inductor fixed radial 100 uH +/-10 %, 5 A, 100 mOhm, 16.5 x 17 mm, THT (carries the heater current: pass 3 moved the filter to the mains input)")
open(FILT, "w", encoding="utf-8").write(f); print("filter sheet patched")
