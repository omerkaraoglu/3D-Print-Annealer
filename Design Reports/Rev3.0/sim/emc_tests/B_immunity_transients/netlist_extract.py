"""Extract the parts and nets that matter for scope B (transient immunity) from the CURRENT schematic.

The committed Design Reports/Rev3.0/Rev3.0_netlist.net is dated 2026-11-12 (before the 2026-11-13
tidy/smoothing rounds), so this script exports a fresh netlist with kicad-cli from a COPY of the
KiCad project in the scratch folder and reads that.  Output: netlist_extract.json next to this file.

Run:  python -X utf8 netlist_extract.py [path-to-exported-netlist]
"""
import json, os, re, subprocess, sys, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'Design Reports', 'Rev3.0', 'tools'))
import sexp  # noqa: E402

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"


def export_netlist():
    src = os.path.join(ROOT, 'KiCad', '3dFilamentDryer')
    tmp = tempfile.mkdtemp(prefix='agentB_kicad_')
    for f in os.listdir(src):
        if f.endswith('.kicad_sch') or f in ('3dFilamentDryer.kicad_pro', 'sym-lib-table', 'fp-lib-table'):
            shutil.copy(os.path.join(src, f), tmp)
    out = os.path.join(tmp, 'current.net')
    subprocess.run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out,
                    os.path.join(tmp, '3dFilamentDryer.kicad_sch')], check=True, capture_output=True)
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else export_netlist()
    tree = sexp.parse(open(path, encoding='utf-8').read())
    comps = {}
    for c in sexp.find(sexp.first(tree, 'components'), 'comp'):
        ref = sexp.first(c, 'ref')[1]
        val = sexp.first(c, 'value')[1]
        fp = (sexp.first(c, 'footprint') or [None, ''])[1]
        fields = {}
        fl = sexp.first(c, 'fields')
        if fl:
            for f in sexp.find(fl, 'field'):
                nm = sexp.first(f, 'name')[1]
                fields[nm] = f[-1] if isinstance(f[-1], str) else ''
        comps[ref] = {'value': val, 'footprint': fp, 'MPN': fields.get('MPN', '')}
    nets = {}
    for n in sexp.find(sexp.first(tree, 'nets'), 'net'):
        name = sexp.first(n, 'name')[1]
        nodes = []
        for nd in sexp.find(n, 'node'):
            ref = sexp.first(nd, 'ref')[1]
            pin = sexp.first(nd, 'pin')[1]
            pf = sexp.first(nd, 'pinfunction')
            nodes.append(f"{ref}.{pin}" + (f"({pf[1]})" if pf else ''))
        nets[name] = nodes
    # parts of interest for transient immunity
    want = re.compile(r'^(RV\d|F\d|L1$|L40|C1$|C2$|C4$|C40|C5$|C6$|C7$|C8$|R[1-9]$|R1[0-6]$|Q[1-4]$|U1$|U5$|U6$|K1|PS1|J2$|J3|J4|J10|J11|J20|D5$|D11[2-6]|D22[01]|R22[0-4]|C22[0-4]|R129|R13[01]|C126|C13[0-3]|R12[5-9]|U3$|U20|U30|HS1|TC1|V1)')
    sel = {r: comps[r] for r in sorted(comps) if want.match(r)}
    pinmap = {}
    for name, nodes in nets.items():
        for nd in nodes:
            ref = nd.split('.')[0]
            if ref in sel:
                pinmap.setdefault(ref, []).append(f"{nd.split('.', 1)[1]} -> {name}")
    for r in sel:
        sel[r]['pins'] = sorted(pinmap.get(r, []))
    mains_nets = {k: v for k, v in nets.items() if any(t in k.upper() for t in
                  ('LINE', 'NEUT', 'ZCD', 'PSU', 'PS1', 'Q1', 'RV', 'HEAT', 'FAN', 'TRIG', 'EN', 'IO0', 'TC_', 'SDA', 'SCL', 'TP_', 'LCD_RST', 'K1', 'U5', 'U1', 'R5', 'C4'))}
    out = {'source_netlist': path, 'n_components': len(comps), 'n_nets': len(nets),
           'parts': sel, 'nets_of_interest': mains_nets}
    json.dump(out, open(os.path.join(HERE, 'netlist_extract.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for r, d in sel.items():
        print(r, d['value'], d['MPN'], '|', '; '.join(d['pins']))


if __name__ == '__main__':
    main()
