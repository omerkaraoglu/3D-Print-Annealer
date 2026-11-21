"""Scope A, step 0: read every mains-side value and routed length from the CURRENT design files.

- Schematic: the five .kicad_sch sheets are copied to a scratch folder and `kicad-cli sch export netlist`
  is run on the copy (the committed Rev3.0_netlist.net is dated 2026-11-12, i.e. before the 2026-11-13
  tidy/smoothing rounds, so it is NOT used).
- PCB: 3dFilamentDryer.kicad_pcb is parsed read-only (segments + arcs per net, pad positions).
Output: design_inputs.json (values, nets, routed lengths, partial inductances) next to this script.
Nothing under KiCad/ is written.
"""
import json, math, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
KDIR = os.path.join(ROOT, "KiCad", "3dFilamentDryer")
sys.path.insert(0, os.path.join(ROOT, "Design Reports", "Rev3.0", "tools"))
import sexp  # noqa: E402

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SCRATCH = os.environ.get("AGENT_A_SCRATCH", tempfile.gettempdir())

MAINS_REFS = ["J3", "F3", "L40", "C40", "C1", "RV1", "RV2", "C4", "R5", "Q1", "R2", "R3", "U5", "R4", "F1", "L1", "PS1",
              "K1", "J4", "R1", "U1", "R6", "R7", "R8", "R9", "R10", "U6", "C2", "D5", "Q4", "R16"]
MAINS_NETS = ["LINE", "LINE_FUSED", "LINE_FILT", "NEUT", "PSU_L", "Net-(Q1-A1)", "Net-(Q1-G)", "Net-(C4-Pad1)",
              "Net-(R3-Pad1)", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N"]


def export_netlist():
    d = os.path.join(SCRATCH, "agentA_kicad_copy")
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(KDIR):
        if f.endswith((".kicad_sch", ".kicad_pro")) or f in ("sym-lib-table", "fp-lib-table"):
            shutil.copy2(os.path.join(KDIR, f), d)
    out = os.path.join(d, "current.net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out,
                    os.path.join(d, "3dFilamentDryer.kicad_sch")], check=True, capture_output=True)
    return out


def parse_netlist(path):
    net = sexp.parse(open(path, encoding="utf8").read())
    comps = {}
    for c in sexp.find(sexp.first(net, "components"), "comp"):
        ref = sexp.first(c, "ref")[1]
        flds = {}
        f = sexp.first(c, "fields")
        if f:
            for fl in sexp.find(f, "field"):
                flds[sexp.first(fl, "name")[1]] = fl[2] if len(fl) > 2 else ""
        fp = sexp.first(c, "footprint")
        comps[ref] = {"value": sexp.first(c, "value")[1], "footprint": fp[1] if fp else "", "mpn": flds.get("MPN", ""), "pins": {}}
    nets = {}
    for n in sexp.find(sexp.first(net, "nets"), "net"):
        name = sexp.first(n, "name")[1].replace("{slash}", "/")
        nodes = []
        for nd in sexp.find(n, "node"):
            r, p = sexp.first(nd, "ref")[1], sexp.first(nd, "pin")[1]
            nodes.append(f"{r}.{p}")
            if r in comps:
                comps[r]["pins"][p] = name
        nets[name] = nodes
    return comps, nets


def flat_trace_L_nH(l_mm, w_mm, t_mm=0.035):
    """Partial self-inductance of a flat straight conductor (Ruehli / Grover form), nH. Valid l >> w."""
    if l_mm <= 0:
        return 0.0
    return 0.2 * l_mm * (math.log(2 * l_mm / (w_mm + t_mm)) + 0.5 + 0.2235 * (w_mm + t_mm) / l_mm)


def parse_pcb():
    txt = open(os.path.join(KDIR, "3dFilamentDryer.kicad_pcb"), encoding="utf8").read()
    tracks = {}
    for kind in ("segment", "arc"):
        for m in re.finditer(r"\(%s\s+(.*?)\(uuid" % kind, txt, re.S):
            b = m.group(1)
            net = re.search(r'\(net "([^"]*)"\)', b)
            if not net:
                continue
            st = [float(x) for x in re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", b).groups()]
            en = [float(x) for x in re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", b).groups()]
            w = float(re.search(r"\(width ([\d.]+)\)", b).group(1))
            lay = re.search(r'\(layer "([^"]+)"\)', b).group(1)
            if kind == "arc":
                mid = [float(x) for x in re.search(r"\(mid ([-\d.]+) ([-\d.]+)\)", b).groups()]
                # arc length through three points
                ax, ay = st; bx, by = mid; cx, cy = en
                d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
                if abs(d) < 1e-12:
                    L = math.dist(st, en)
                else:
                    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
                    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
                    r = math.hypot(ax - ux, ay - uy)
                    chord = math.dist(st, en)
                    ang = 2 * math.asin(min(1.0, chord / (2 * r)))
                    # take the long way if mid is on the far side
                    if (mid[0] - st[0]) * (en[1] - st[1]) - (mid[1] - st[1]) * (en[0] - st[0]) == 0:
                        pass
                    L = r * ang
                    if math.dist(mid, [(ax + cx) / 2, (ay + cy) / 2]) > r:
                        L = r * (2 * math.pi - ang)
            else:
                L = math.dist(st, en)
            tracks.setdefault(net.group(1), []).append({"L": L, "w": w, "layer": lay, "a": st, "b": en})
    # footprints: position and absolute pad centres
    fps = {}
    starts = [m.start() for m in re.finditer(r'\n\t\(footprint "', txt)] + [len(txt)]
    for s, e in zip(starts[:-1], starts[1:]):
        blk = txt[s:e]
        lib = re.search(r'\(footprint "([^"]+)"', blk).group(1)
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", blk)
        if not (ref and at):
            continue
        x0, y0, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
        th = math.radians(rot)
        pads = {}
        for pm in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', blk, re.S):
            pa = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pm.group(2))
            pn = re.search(r'\(net "([^"]*)"\)', pm.group(2))
            if pa:
                dx, dy = float(pa.group(1)), float(pa.group(2))
                pads[pm.group(1)] = {"x": round(x0 + dx * math.cos(th) + dy * math.sin(th), 3),
                                     "y": round(y0 - dx * math.sin(th) + dy * math.cos(th), 3),
                                     "net": pn.group(1) if pn else ""}
        fps[ref.group(1)] = {"lib": lib, "x": x0, "y": y0, "rot": rot, "pads": pads}
    return tracks, fps


def path_length(tracks_net, pads, p_from, p_to, tol=0.6):
    """Shortest routed length between two pad centres over one net's track graph (Dijkstra).
    Track ends within `tol` mm of each other or of a pad centre are joined."""
    import heapq
    nodes = []
    def nid(pt):
        for i, q in enumerate(nodes):
            if math.dist(pt, q) < tol:
                return i
        nodes.append(tuple(pt)); return len(nodes) - 1
    adj = {}
    for t in tracks_net:
        a, b = nid(t["a"]), nid(t["b"])
        adj.setdefault(a, []).append((b, t["L"])); adj.setdefault(b, []).append((a, t["L"]))
    # a through-hole pad joins every track end inside its copper (use 1.5 mm radius for THT pads)
    def pad_nodes(p):
        return [i for i, q in enumerate(nodes) if math.dist(q, (p["x"], p["y"])) < 1.6]
    src, dst = pad_nodes(pads[p_from]), set(pad_nodes(pads[p_to]))
    if not src or not dst:
        return None
    dist = {s: 0.0 for s in src}; pq = [(0.0, s) for s in src]
    while pq:
        d, u = heapq.heappop(pq)
        if u in dst:
            return round(d, 2)
        if d > dist.get(u, 1e9):
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, 1e9):
                dist[v] = d + w; heapq.heappush(pq, (d + w, v))
    return None


def main():
    netpath = export_netlist()
    comps, nets = parse_netlist(netpath)
    tracks, fps = parse_pcb()
    out = {"source": {"schematic": "KiCad/3dFilamentDryer/*.kicad_sch exported with kicad-cli (copy in scratch)",
                      "pcb": "KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb (read-only parse)",
                      "trace_inductance": "flat conductor partial inductance 0.2 l [ln(2l/(w+t)) + 0.5 + 0.2235 (w+t)/l] nH (Grover); no plane under mains copper (spec 12.2)"},
           "components": {r: comps[r] for r in MAINS_REFS if r in comps}, "nets": {}, "positions_mm": {}}
    for n in MAINS_NETS:
        tr = tracks.get(n, [])
        Ltot = sum(t["L"] for t in tr)
        # inductance: treat the net's copper as one straight run of the total length at the dominant width
        wdom = max(tr, key=lambda t: t["L"])["w"] if tr else 0.0
        out["nets"][n] = {"members": nets.get(n, []), "routed_length_mm": round(Ltot, 2), "n_items": len(tr),
                          "dominant_width_mm": wdom, "layers": sorted({t["layer"] for t in tr}),
                          "partial_L_nH": round(flat_trace_L_nH(Ltot, wdom) if tr else 0.0, 1)}
    for r in MAINS_REFS:
        if r in fps:
            out["positions_mm"][r] = fps[r]
    allpads = {f"{r}.{p}": v for r, f in fps.items() for p, v in f["pads"].items()}
    BR = [("LINE", "J3.1", "F3.2"), ("LINE_FUSED", "F3.1", "L40.2"), ("LINE_FUSED", "F3.1", "K1.1"), ("LINE_FUSED", "L40.2", "K1.1"),
          ("LINE_FILT", "L40.1", "C40.1"), ("LINE_FILT", "L40.1", "Q1.2"), ("LINE_FILT", "C40.1", "Q1.2"), ("LINE_FILT", "C40.1", "C1.1"),
          ("LINE_FILT", "C40.1", "RV1.1"), ("LINE_FILT", "C40.1", "F1.1"), ("LINE_FILT", "L40.1", "F1.1"),
          ("NEUT", "J3.2", "C40.2"), ("NEUT", "C40.2", "R1.2"), ("NEUT", "J3.2", "R1.2"), ("NEUT", "J3.2", "J4.2"), ("NEUT", "C40.2", "C1.2"),
          ("NEUT", "J3.2", "L1.1"), ("NEUT", "C40.2", "L1.1"), ("Net-(Q1-A1)", "Q1.1", "R1.1"), ("Net-(J4-Pin_1)", "K1.3", "J4.1"),
          ("PSU_L", "F1.2", "L1.4")]
    out["branches_mm"] = {}
    for net, a, b in BR:
        L = path_length(tracks.get(net, []), allpads, a, b) if a in allpads and b in allpads else None
        wdom = max(tracks[net], key=lambda t: t["L"])["w"] if tracks.get(net) else 1.0
        out["branches_mm"][f"{net}:{a}->{b}"] = {"length_mm": L, "L_nH": round(flat_trace_L_nH(L, wdom), 1) if L else None}
        print(f"  branch {net:12s} {a:6s}->{b:6s} {L} mm")
    json.dump(out, open(os.path.join(HERE, "design_inputs.json"), "w", encoding="utf8"), indent=1, ensure_ascii=False)
    for n, v in out["nets"].items():
        print(f"{n:18s} {v['routed_length_mm']:7.1f} mm  w {v['dominant_width_mm']:.2f}  L {v['partial_L_nH']:6.1f} nH  {v['layers']}  {v['members']}")
    for r in ("L40", "C40", "C1", "RV1", "Q1", "K1", "F3", "J3", "R1", "PS1", "L1", "F1"):
        c = out["components"][r]
        print(r, c["value"], c["mpn"], c["pins"])


if __name__ == "__main__":
    main()
