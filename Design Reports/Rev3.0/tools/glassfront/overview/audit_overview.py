"""Self-check of Rev3.0_GlassFront_Overview.pdf.

    python -B audit_overview.py [--png-dir DIR]

1. rasterises every page (110 dpi) into DIR for a visual review (default: a temp folder);
2. fonts: every font embedded, one family (Segoe UI); the Turkish letters used are in the text layer and in the
   embedded subsets, and the full font covers all twelve Turkish letters;
3. links: one URI link annotation per electronics line that has a url (same URLs); page count; file size;
4. numbers: every number in the PDF text layer is matched to a registered string (overview_provenance.json) and its
   source is checked: master value (re-read from the master), design-document section (the number must occur in
   that section's text; 'a / b / c k' means thousands), electronics_bom.json, a body count of the assembly CAD,
   or a structural number (page, footer, BOM item, station, week axis, file path);
5. mechanical BOM vs the assembly: every component of the Assembly report is covered by a BOM item, quantities agree.

Writes audit_report.json next to this script and prints a summary.
"""
import argparse
import json
import os
import re
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz

import ov_values as V

NUM = re.compile(r"\d+(?:[.,]\d+)*")
IDCH = re.compile(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşüØ§.\-_/']")
KSEQ = re.compile(r"(?:\s*[/–-]\s*\d+(?:[.,]\d+)*)*\s?k(?![A-Za-z])")
REFS = re.compile(r"\b(?:items?|see|lines?|with)\s+\d+(?:\s*(?:,|–|-|and)\s*\d+)*")
FOOT = re.compile(r"(GF-\d+\.\d+) · (\d{4}-\d{2}-\d{2}) · page (\d+)/(\d+)")
TURKISH = "ÖöÇçŞşĞğİıÜü"


def norm_num(s):
    """'1,390' -> '1390'; '3,0' (Turkish decimal comma) -> '3.0'"""
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):
        return s.replace(",", "")
    return s.replace(",", ".") if re.fullmatch(r"\d+,\d+", s) else s


def as_float(s):
    try:
        return float(norm_num(s))
    except ValueError:
        return None


def tokens(text):
    """[(kind, token, k_scaled)]: kind 'num', 'ref' (BOM item reference: 'items 2, 10', 'see 3', 'line 3', 'with 5, 7')
    or 'id' (a number glued to letters: D15, GF-D21, M4, R1.5, Ø5.8, §12.1)"""
    out = []
    refspans = [m.span() for m in REFS.finditer(text)]
    for m in NUM.finditer(text):
        a, b = m.span()
        pre = text[a - 1] if a > 0 else " "
        post = text[b] if b < len(text) else " "
        if any(r0 <= a and b <= r1 for r0, r1 in refspans) and not pre.isalpha():
            out.append(("ref", m.group(0), False))
            continue
        if pre.isalpha() or pre in "§Ø_" or (pre == "-" and a > 1 and text[a - 2].isalpha()) or \
                (post.isalpha() and post not in "kx×"):
            i, j = a, b
            while i > 0 and IDCH.match(text[i - 1]):
                i -= 1
            while j < len(text) and IDCH.match(text[j]):
                j += 1
            out.append(("id", text[i:j].strip(".-/'"), False))
            continue
        out.append(("num", norm_num(m.group(0)), bool(KSEQ.match(text, b))))
    return out


def num_set(text):
    s = set()
    for k, t, _ in tokens(text):
        if k in ("num", "ref"):
            s.add(norm_num(t))
            f = as_float(t)
            if f is not None:
                s.add(repr(round(f, 6)))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png-dir", default=os.path.join(tempfile.gettempdir(), "gf_overview_pages"))
    a = ap.parse_args()
    rep = {"pdf": os.path.relpath(V.OUT_PDF, V.ROOT).replace("\\", "/")}
    doc = fitz.open(V.OUT_PDF)
    rep["pages"] = len(doc)
    rep["size_MB"] = round(os.path.getsize(V.OUT_PDF) / 1e6, 2)
    reg = json.load(open(os.path.join(V.HERE, "overview_provenance.json"), encoding="utf-8"))
    # ---- 1 rasterise
    os.makedirs(a.png_dir, exist_ok=True)
    for i, p in enumerate(doc):
        p.get_pixmap(dpi=110).save(os.path.join(a.png_dir, "p%02d.png" % (i + 1)))
    rep["png_dir"] = a.png_dir
    # ---- 2 fonts
    fonts = {}
    for p in doc:
        for f in p.get_fonts(full=True):
            fonts[f[0]] = {"base": f[3], "type": f[2], "ext": f[1]}
    embedded = {}
    for xref, f in fonts.items():
        nm, ext, typ, buf = doc.extract_font(xref)
        glyphs = {}
        if buf:
            ft = fitz.Font(fontbuffer=buf)
            glyphs = {ch: ft.has_glyph(ord(ch)) > 0 for ch in TURKISH}
        embedded[f["base"]] = {"embedded": bool(buf), "type": f["type"], "turkish_glyphs_in_subset": glyphs}
    alltext = "".join(p.get_text() for p in doc)
    rep["fonts"] = embedded
    rep["fonts_all_embedded"] = all(v["embedded"] for v in embedded.values())
    rep["font_families"] = sorted({b.split("+")[-1].split("-")[0] for b in embedded})
    used = sorted({ch for it in reg for ch in it["text"] if ch in TURKISH})
    rep["turkish_letters_used"] = used
    rep["turkish_in_text_layer"] = {ch: (ch in alltext) for ch in used}
    # (reportlab re-encodes TrueType subsets, so the subsets' own cmaps are not Unicode; the text layer's
    # ToUnicode round trip and the full font's coverage are checked instead, the rendering by eye)
    full = fitz.Font(fontfile=os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "segoeui.ttf"))
    rep["turkish_glyphs_in_full_font"] = {ch: full.has_glyph(ord(ch)) > 0 for ch in TURKISH}
    # ---- 3 links
    E = V.load_json(V.ELEC)
    urls_json = [l["url"] for g in E["groups"] for l in g["lines"] if l.get("url")] + \
        [l["url"] for l in E["not_in_component_total"] if l.get("url")]
    links = []
    for i, p in enumerate(doc):
        for l in p.get_links():
            if l.get("kind") == fitz.LINK_URI:
                links.append((i + 1, l["uri"]))
    rep["links"] = {"uri_annotations": len(links), "lines_with_url": len(urls_json),
                    "same_urls": sorted(u for _, u in links) == sorted(urls_json)}
    rep["links"]["match"] = rep["links"]["uri_annotations"] == rep["links"]["lines_with_url"] and rep["links"]["same_urls"]
    # ---- 4 numbers
    secs = V.doc_sections()
    sec_nums = {k: num_set(v) for k, v in secs.items()}
    doc_all = secs["§all"]
    M = V.load_json(V.MASTER)
    mv = V.master_values(M)
    master_dump = json.dumps(M, ensure_ascii=False)
    elec_dump = json.dumps(E, ensure_ascii=False)
    elec_nums = num_set(elec_dump)
    group_sums = {"%.2f" % sum(l["line_usd_per_board"] or 0 for l in g["lines"]) for g in E["groups"]}
    prices = set()
    for l in [l for g in E["groups"] for l in g["lines"]] + E["not_in_component_total"]:
        if l.get("unit_price_usd") is not None:
            prices.add(V.fmt_price(l["unit_price_usd"]))
    C = V.load_json(V.CONTENT)
    content_dump = json.dumps(C, ensure_ascii=False)
    census_p = os.path.join(V.OVR, "assembly_census.json")
    census = V.load_json(census_p) if os.path.exists(census_p) else None
    counts = {str(v) for v in census["by_item"].values()} if census else set()

    def check_num(tok, ks, item):
        src = item["src"]
        if src.startswith("structure: footer"):
            m_ = FOOT.fullmatch(item["text"])
            ok = m_ and m_.group(1) == mv["revision"][0] and m_.group(2) == C["meta"]["date"] and \
                int(m_.group(3)) == item["page"] and int(m_.group(4)) == len(doc)
            return "structure:footer" if ok else None
        if src.startswith("structure"):
            return "structure"
        if tok in item.get("mvals", {}):
            for name, (s_, path) in mv.items():
                if path == item["mvals"][tok] and s_ == tok:
                    return "master:" + path
            return None
        fl = as_float(tok)
        cand = {tok}
        if fl is not None:
            cand.add(repr(round(fl, 6)))
            if ks:
                cand.add(repr(round(fl * 1000, 6)))
                cand.add("%d" % round(fl * 1000))
        if src.startswith("CAD") and tok in counts | {"1"}:
            return "CAD:body count"
        if src.startswith("elec"):
            if "sum of line_usd" in src and tok in group_sums:
                return "elec:group sum"
            if "unit_price" in src and tok in prices:
                return "elec:unit price"
            if cand & elec_nums:
                return "elec"
            return None
        for s in re.findall(r"§[\w.]+", src):
            s = s.rstrip(".,")
            key = s if s in sec_nums else s.split(".")[0]
            if key in sec_nums and cand & sec_nums[key]:
                return "doc " + s
        if "master" in src:
            for name, (s_, path) in mv.items():
                if s_ == tok:
                    return "master:" + path
        return None

    results = []
    by_page = {}
    for it in reg:
        by_page.setdefault(it["page"], []).append(it)
        for kind, tok, ks in tokens(it["text"]):
            if kind == "ref":
                ok = any(str(b["no"]) == tok for b in C["bom"])
                v = "structure:BOM item ref" if ok else None
            elif kind == "id":
                ok = (tok in doc_all or tok in master_dump or tok in elec_dump or tok in content_dump)
                v = "id-in-sources" if ok else None
            else:
                v = check_num(tok, ks, it)
            results.append({"page": it["page"], "token": tok, "kind": kind, "src": it["src"], "verified": v,
                            "text": it["text"][:100]})
    coverage = []
    for i, p in enumerate(doc):
        regtoks = set()
        for it in by_page.get(i + 1, []):
            regtoks |= {t for k, t, _ in tokens(it["text"])}
        for k, t, _ in tokens(p.get_text()):
            if t not in regtoks:
                coverage.append({"page": i + 1, "token": t})
    unresolved = [r for r in results if not r["verified"]]
    by_source = {}
    for r in results:
        if r["verified"]:
            k = r["verified"].split(":")[0].split(" ")[0]
            by_source[k] = by_source.get(k, 0) + 1
    rep["numbers"] = {"tokens_checked": len(results),
                      "numeric": sum(1 for r in results if r["kind"] == "num"),
                      "item_refs": sum(1 for r in results if r["kind"] == "ref"),
                      "identifiers": sum(1 for r in results if r["kind"] == "id"),
                      "by_source": by_source, "unresolved": unresolved, "text_layer_not_registered": coverage,
                      "all": [{"page": r["page"], "token": r["token"], "kind": r["kind"], "source": r["verified"],
                               "cited": r["src"], "text": r["text"]} for r in results]}
    # master values that do not occur verbatim in the design document (reported, not an error by itself)
    rep["master_values_not_verbatim_in_doc"] = [{"value": n, "master": s_, "path": p_} for n, (s_, p_) in mv.items()
                                                if s_ not in doc_all and n != "revision"]
    # ---- 5 BOM vs assembly
    asm = V.load_json(V.ASM_REPORT)
    comp_map = {"Frame GF": "9", "Glass": "4", "Optical bond": "5", "Formex sheet": "8", "Bead": "7",
                "VHB tape strips": "3", "Oven sheet": "1 (S4 body; R4 body hidden)", "Rivets R4 F1-F4 (hidden)": "14 + 15",
                "Check - socket cylinders (hidden)": "reference geometry (socket-access check), not a part",
                "Rev3.0 PCB full (KiCad STEP)": "12 (board + components) and 6 (DS1 panel bodies)",
                "Weld studs S4 F1-F4": "2", "Washers + nyloc nuts S4 F1-F4": "10 + 11",
                "Tails GF-2.0 (bent-back route)": "6 (the panel's two flat cables)"}
    rows = []
    for ct in asm["component_tree"]:
        comp = ct["occurrence"].rsplit(":", 1)[0]
        rows.append({"component": comp, "bodies": [b["name"] for b in ct["bodies"]] or "sub-assembly",
                     "visible": ct["visible"], "bom_item": comp_map.get(comp)})
    names = [b["name"] for ct in asm["component_tree"] for b in ct["bodies"]]
    found = {"2": sum(n.startswith("Weld stud") for n in names), "3": sum(n.startswith("VHB strip") for n in names),
             "10": sum(n.startswith("Washer DIN 9021 M4") for n in names), "11": sum(n.startswith("Nyloc") for n in names),
             "14": sum(n.startswith("Blind rivet") for n in names),
             "15": sum(n.startswith("Backing washer DIN 9021 M5") for n in names)}
    bom_qty = {str(b["no"]): b["qty"]["t"] for b in C["bom"]}
    qty = {k: {"bom": bom_qty[k], "assembly_report": v, "agree": bom_qty[k].startswith(str(v))} for k, v in found.items()}
    rep["bom_vs_assembly"] = {"components": rows, "uncovered": [r for r in rows if r["bom_item"] is None],
                              "quantities": qty, "quantities_agree": all(q["agree"] for q in qty.values()),
                              "step_census": census and {"solid_instances": census["solid_instances"],
                                                         "by_item": census["by_item"],
                                                         "report_assembly_step_solids": asm["assembly_step_content"]["assembly_step_solids"],
                                                         "report_assembly_step_products": asm["assembly_step_content"]["assembly_step_products"]},
                              "bom_items_without_a_body": ["13 PCB screws (not modelled)", "16 primers and cleaning (consumables)",
                                                           "14, 15 R4 parts (hidden component, not in the STEP export)"]}
    out = os.path.join(V.HERE, "audit_report.json")
    json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = rep["numbers"]
    print("pages", rep["pages"], "size MB", rep["size_MB"])
    print("fonts embedded", rep["fonts_all_embedded"], rep["font_families"])
    print("turkish used", "".join(used), "text layer", all(rep["turkish_in_text_layer"].values()),
          
          "full font", all(rep["turkish_glyphs_in_full_font"].values()))
    print("links", rep["links"])
    print("tokens", n["tokens_checked"], "numeric", n["numeric"], "refs", n["item_refs"], "ids", n["identifiers"], n["by_source"])
    print("unresolved", len(n["unresolved"]))
    for r in n["unresolved"][:120]:
        print("   p%d %-12s %-4s src=%s | %s" % (r["page"], r["token"], r["kind"], r["src"], r["text"]))
    print("text layer tokens not registered", len(n["text_layer_not_registered"]), n["text_layer_not_registered"][:20])
    print("master values not verbatim in doc", rep["master_values_not_verbatim_in_doc"])
    print("bom vs assembly uncovered", rep["bom_vs_assembly"]["uncovered"], "qty agree", rep["bom_vs_assembly"]["quantities_agree"])
    print("wrote", out)


if __name__ == "__main__":
    main()
