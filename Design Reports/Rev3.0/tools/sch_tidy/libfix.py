"""Trivial lib_symbol_mismatch fixes (no pin or graphic change):
- Rev3.kicad_sym: the default Footprint of TFT_SAT070AT40D21_FPC40 / CTP_GT911_FPC6 set to the value the embedded
  copies in Rev3_Display.kicad_sch carry (the only difference KiCad reported);
- root sheet: the embedded Connector:Conn_01x06_Pin (J2) replaced by the KiCad 10 library copy (identical pins and
  graphics, only the default property values differed)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kicad_lib import get_symbol  # noqa: E402
from core import find, first, LibSym  # noqa: E402

FP = {"TFT_SAT070AT40D21_FPC40": "Rev3:Connfly_DS1020-09-40VBT1A_1x40_P0.5mm_Horizontal",
      "CTP_GT911_FPC6": "Rev3:Connfly_DS1020-09-06VBT1A_1x06_P0.5mm_Horizontal"}


def fix_library(path):
    txt = open(path, encoding="utf-8", newline="").read()
    n = 0
    for name, fp in FP.items():
        i = txt.index('\t(symbol "%s"' % name)
        j = txt.index('(property "Footprint" "', i)
        k = txt.index('"', j + len('(property "Footprint" "'))
        old = txt[j + len('(property "Footprint" "'):k]
        if old != fp:
            txt = txt[:j] + '(property "Footprint" "' + fp + txt[k:]
            n += 1
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(txt)
    return n


def fix_root_j2(doc):
    lid = "Connector:Conn_01x06_Pin"
    ls = first(doc.tree, "lib_symbols")
    for i, s in enumerate(ls):
        if isinstance(s, list) and s and s[0] == "symbol" and s[1] == lid:
            new = get_symbol("Connector", "Conn_01x06_Pin")
            assert LibSym(new).pins == LibSym(s).pins and LibSym(new).gfx == LibSym(s).gfx
            ls[i] = new
            doc.libs[lid] = LibSym(new)
            return True
    return False


# round 2: Rev3:SSD1963QL9 top supply pins moved inward along the top edge (pitch 7.62 -> 5.08) so their vertical
# pin names no longer run into the D0-D2 / LDATA23-21 names of the side columns. Same pin numbers, same edge.
SSD_TOP_X = {"-11.43": "-10.16", "-3.81": "-5.08", "3.81": "0", "11.43": "5.08"}


def fix_ssd1963_library(path):
    txt = open(path, encoding="utf-8", newline="").read()
    i = txt.index('\t(symbol "SSD1963QL9"')
    j = txt.index('\n\t(symbol "', i + 10)
    blk = txt[i:j]
    if "(at -10.16 48.26 270)" in blk:
        return 0
    n = [0]

    def rep(m):
        n[0] += 1
        return "(at %s 48.26 270)" % SSD_TOP_X[m.group(1)]
    blk = re.sub(r"\(at (-11\.43|-3\.81|3\.81|11\.43) 48\.26 270\)", rep, blk)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(txt[:i] + blk + txt[j:])
    return n[0]


def fix_ssd1963_embedded(doc):
    from core import S
    lid = "Rev3:SSD1963QL9"
    node = doc.libs[lid].node
    n = 0
    for sub in find(node, "symbol"):
        for p in find(sub, "pin"):
            at = first(p, "at")
            if str(at[2]) == "48.26" and str(at[3]) == "270" and str(at[1]) in SSD_TOP_X:
                at[1] = S(SSD_TOP_X[str(at[1])])
                n += 1
    doc.libs[lid] = LibSym(node)
    return n
