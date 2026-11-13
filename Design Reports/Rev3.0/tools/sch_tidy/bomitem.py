"""Rev3:BOM_Item - pinless dashed box for parts that are in the BOM but not on the board (Battery Sentinel style).
The same node is written into Rev3.kicad_sym and embedded in the sheet (no lib_symbol_mismatch)."""
import copy

from core import S, N, U, dump, find, first, parse, LibSym, PROJECT


def _prop(name, value, x, y, hide=False, just=None):
    p = [S("property"), name, value, [S("at"), N(x), N(y), N(0)]]
    if hide:
        p.append([S("hide"), S("yes")])
    p += [[S("show_name"), S("no")], [S("do_not_autoplace"), S("no")]]
    eff = [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]]]
    if just:
        eff.append([S("justify"), S(just)])
    p.append(eff)
    return p


def lib_node(name="BOM_Item"):
    return [S("symbol"), name,
            [S("exclude_from_sim"), S("yes")], [S("in_bom"), S("yes")], [S("on_board"), S("no")], [S("in_pos_files"), S("no")],
            [S("duplicate_pin_numbers_are_jumpers"), S("no")],
            _prop("Reference", "MP", 7.62, 1.27, just="left"),
            _prop("Value", "BOM_Item", 7.62, -1.27, just="left"),
            _prop("Footprint", "", 0, 0, hide=True),
            _prop("Datasheet", "", 0, 0, hide=True),
            _prop("Description", "Part in the BOM but not on the board (probe, cable, accessory); no pins", 0, 0, hide=True),
            _prop("ki_keywords", "bom mechanical off-board accessory", 0, 0, hide=True),
            [S("symbol"), name + "_0_1",
             [S("rectangle"), [S("start"), N(-6.35), N(2.54)], [S("end"), N(6.35), N(-2.54)],
              [S("stroke"), [S("width"), N(0)], [S("type"), S("dash")]], [S("fill"), [S("type"), S("none")]]],
             [S("text"), "BOM", [S("at"), N(0), N(0), N(0)], [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]]]]],
            [S("embedded_fonts"), S("no")]]


def update_library(path):
    txt = open(path, encoding="utf-8", newline="").read()
    if '(symbol "BOM_Item"' in txt:
        return False
    nl = "\r\n" if "\r\n" in txt else "\n"
    body = dump(lib_node(), 1).replace("\n", nl)
    i = txt.rstrip().rindex(")")
    txt = txt[:i].rstrip("\r\n\t ") + nl + "\t" + body + nl + ")" + nl
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(txt)
    return True


def embed(doc):
    ls = first(doc.tree, "lib_symbols")
    name = "Rev3:BOM_Item"
    if name not in doc.libs:
        node = lib_node()
        node[1] = name
        ls.append(node)
        doc.libs[name] = LibSym(node)
    return name


def instance(doc, ref, value, props):
    """new pinless BOM item symbol on doc (placed later by Builder.place)"""
    lid = embed(doc)
    node = [S("symbol"), [S("lib_id"), lid], [S("at"), N(0), N(0), N(0)], [S("unit"), N(1)], [S("body_style"), N(1)],
            [S("exclude_from_sim"), S("yes")], [S("in_bom"), S("yes")], [S("on_board"), S("no")], [S("in_pos_files"), S("no")],
            [S("dnp"), S("no")], [S("uuid"), U()],
            _prop("Reference", ref, 0, 0), _prop("Value", value, 0, 0), _prop("Footprint", "", 0, 0, hide=True)]
    for k, v in props.items():
        node.append(_prop(k, v, 0, 0, hide=True))
    node.append([S("instances"), [S("project"), PROJECT, [S("path"), doc.inst_path, [S("reference"), ref], [S("unit"), N(1)]]]])
    doc.symbols[ref] = node
    return node
