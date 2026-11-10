"""Helpers to load KiCad .kicad_sym libraries, resolve `extends`, and flatten symbols for embedding."""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find, first, prop, Sym, dump

KICAD_SYM_DIR = r"C:/Program Files/KiCad/10.0/share/kicad/symbols"
_cache = {}

def load_lib(libname, path=None):
    if libname in _cache:
        return _cache[libname]
    p = path or os.path.join(KICAD_SYM_DIR, libname + '.kicad_sym')
    root = parse(open(p, encoding='utf-8').read())
    syms = {s[1]: s for s in find(root, 'symbol')}
    _cache[libname] = syms
    return syms

def get_symbol(libname, name, path=None):
    """Return a flattened copy of symbol `name` (extends resolved), named `libname:name`."""
    syms = load_lib(libname, path)
    s = syms[name]
    ext = first(s, 'extends')
    if ext:
        parent = get_symbol(libname, ext[1], path)   # flattened parent, already renamed
        flat = copy.deepcopy(parent)
        # replace properties with child's properties (child overrides)
        child_props = {p[1]: p for p in find(s, 'property')}
        new = []
        for item in flat:
            if isinstance(item, list) and item and item[0] == 'property':
                if item[1] in child_props:
                    new.append(copy.deepcopy(child_props.pop(item[1])))
                else:
                    new.append(item)
            else:
                new.append(item)
        for p in child_props.values():
            new.append(copy.deepcopy(p))
        flat = new
        # rename units from parent name to child name
        pname = ext[1]
        for u in find(flat, 'symbol'):
            if u[1].startswith(pname + '_'):
                u[1] = name + u[1][len(pname):]
        flat[1] = name
        out = flat
    else:
        out = copy.deepcopy(s)
    out[1] = f"{libname}:{name}"
    # KiCad embedded lib symbols keep unit names as "<name>_<unit>_<style>" (no lib prefix)
    for u in find(out, 'symbol'):
        if u[1].startswith(name + '_'):
            pass
        elif ':' in u[1]:
            u[1] = u[1].split(':', 1)[1]
    return out

def pins(symbol):
    """List of dicts for all pins of a (flattened) symbol: name, number, x, y, angle, length, unit, hide."""
    res = []
    def walk(node, unit):
        for p in find(node, 'pin'):
            at = first(p, 'at'); ln = first(p, 'length')
            hide = any(isinstance(x, list) and x and x[0] == 'hide' and (len(x) < 2 or x[1] == 'yes') for x in p) or (Sym('hide') in p)
            res.append(dict(name=first(p, 'name')[1], number=first(p, 'number')[1],
                            x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                            length=float(ln[1]), type=str(p[1]), unit=unit, hide=hide))
        for s in find(node, 'symbol'):
            u = s[1].rsplit('_', 2)
            try:
                un = int(u[1])
            except Exception:
                un = unit
            walk(s, un)
    walk(symbol, 0)
    return res

if __name__ == '__main__':
    for lib, name in [('Regulator_Switching', 'TPS562200'), ('Regulator_Linear', 'LD1117S12TR_SOT223'),
                      ('Analog_ADC', 'ADS1115IDGS'), ('Converter_ACDC', 'HLK-10M05'), ('Converter_ACDC', 'HLK-PM01'),
                      ('Device', 'Crystal_GND24'), ('Device', 'Thermistor_NTC'), ('Connector', 'Screw_Terminal_01x02'),
                      ('Device', 'L'), ('Device', 'D_Schottky'), ('Device', 'D_Zener'), ('Device', 'C'), ('Device', 'R'),
                      ('Connector_Generic', 'Conn_01x40'), ('Connector_Generic', 'Conn_01x06'), ('RF_Module', 'ESP32-WROOM-32E'),
                      ('power', 'GND'), ('power', '+3V3'), ('power', '+5V'), ('power', '+1V2'), ('Device', 'D_TVS')]:
        try:
            s = get_symbol(lib, name)
        except KeyError as e:
            print('MISSING', lib, name); continue
        fp = prop(s, 'Footprint')
        ps = pins(s)
        print(f"== {lib}:{name} fp={fp} pins={len(ps)} units={sorted(set(p['unit'] for p in ps))}")
        for p in ps:
            print(f"    {p['number']:>4} {p['name']:<14} ({p['x']:7.2f},{p['y']:7.2f}) ang={p['angle']:<5} len={p['length']} {p['type']} u{p['unit']}{' HIDE' if p['hide'] else ''}")
