"""Values for the GF-2.1 overview: the master parameters, the design document sections, the content file,
the electronics BOM, and a provenance registry of every string the PDF prints.

Nothing here writes to the master, the design document or the drawings; all inputs are read-only.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
MASTER = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
DOC = os.path.join(ROOT, "Design Reports", "Rev3.0", "Rev3.0_GlassFront_Design.md")
CONTENT = os.path.join(HERE, "overview_content.json")
ELEC = os.path.join(HERE, "electronics_bom.json")
RENDERS = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "renders")
OVR = os.path.join(RENDERS, "overview")
DRAWINGS = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "drawings")
OUT_PDF = os.path.join(ROOT, "Design Reports", "Rev3.0", "Rev3.0_GlassFront_Overview.pdf")
ASM_REPORT = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_Assembly_report.json")


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------------------------------------ master
def _rect(M, name):
    for r in M["plan_rectangles"]:
        if r["name"] == name:
            return r
    raise KeyError(name)


def _drv(M, name):
    for d in M["driving_parameters"]:
        if d["name"] == name:
            return d["value"]
    raise KeyError(name)


def _named(lst, name):
    for d in lst:
        if d["name"] == name:
            return d["value"]
    raise KeyError(name)


def master_values(M=None):
    """{name: (printed string, path / formula in the master)}. Only formatting happens here."""
    M = M or load_json(MASTER)
    v = {}

    def put(name, val, fmt, path):
        v[name] = (fmt.format(val), path)

    g = _rect(M, "glass"); c = _rect(M, "cut"); w = _rect(M, "print_window"); f = _rect(M, "flange")
    fx = _rect(M, "formex"); fl = _rect(M, "fastener_line")
    put("border", _drv(M, "border"), "{:.1f}", "driving_parameters.border")
    put("glass_w", g["x1"] - g["x0"], "{:.2f}", "plan_rectangles.glass x1-x0")
    put("glass_h", g["y1"] - g["y0"], "{:.2f}", "plan_rectangles.glass y1-y0")
    put("R_glass", _drv(M, "R_glass"), "{:.2f}", "driving_parameters.R_glass")
    put("cut_w", c["x1"] - c["x0"], "{:.2f}", "plan_rectangles.cut x1-x0")
    put("cut_h", c["y1"] - c["y0"], "{:.2f}", "plan_rectangles.cut y1-y0")
    put("R_cut", _drv(M, "R_cut"), "{:.2f}", "driving_parameters.R_cut")
    put("win_w", w["x1"] - w["x0"], "{:.2f}", "plan_rectangles.print_window x1-x0")
    put("win_h", w["y1"] - w["y0"], "{:.2f}", "plan_rectangles.print_window y1-y0")
    put("flange_w", f["x1"] - f["x0"], "{:.2f}", "plan_rectangles.flange x1-x0")
    put("flange_h", f["y1"] - f["y0"], "{:.2f}", "plan_rectangles.flange y1-y0")
    put("formex_w", fx["x1"] - fx["x0"], "{:.1f}", "plan_rectangles.formex x1-x0")
    put("formex_h", fx["y1"] - fx["y0"], "{:.1f}", "plan_rectangles.formex y1-y0")
    put("fpat_w", fl["x1"] - fl["x0"], "{:.2f}", "plan_rectangles.fastener_line x1-x0")
    put("fpat_h", fl["y1"] - fl["y0"], "{:.2f}", "plan_rectangles.fastener_line y1-y0")
    put("g_bend", _drv(M, "g_bend"), "{:.2f}", "driving_parameters.g_bend")
    put("g1", _drv(M, "g1"), "{:.2f}", "driving_parameters.g1")
    put("g2", _drv(M, "g2"), "{:.2f}", "driving_parameters.g2")
    put("lip_w", _drv(M, "lip_w"), "{:.1f}", "driving_parameters.lip_w")
    put("t_sheet", _drv(M, "t_sheet"), "{:.2f}", "driving_parameters.t_sheet")
    put("glass_t", _drv(M, "glass_t"), "{:.1f}", "driving_parameters.glass_t")
    put("t_bond", _drv(M, "t_bond"), "{:.1f}", "driving_parameters.t_bond")
    put("t_opt", _drv(M, "t_opt"), "{:.2f}", "driving_parameters.t_opt")
    put("bead_w", _drv(M, "bead_w"), "{:.1f}", "driving_parameters.bead_w")
    put("tape_w", _drv(M, "tape_w"), "{:.0f}", "driving_parameters.tape_w")
    put("bead_area", _named(M["bead"], "bead_area"), "{:.1f}", "bead.bead_area")
    put("tape_area", M["as_modelled_GF-2.1"]["tape_area_mm2"], "{:.1f}", "as_modelled_GF-2.1.tape_area_mm2")
    sl = _named(M["tape_and_gasket"], "strip_lengths")
    put("strip_tb", sl["top_bottom"], "{:.2f}", "tape_and_gasket.strip_lengths.top_bottom")
    put("strip_s", sl["sides"], "{:.2f}", "tape_and_gasket.strip_lengths.sides")
    a = M["as_modelled_GF-2.1"]
    put("frame_mass", a["frame_mass_g_at_1.36"], "{:.1f}", "as_modelled_GF-2.1.frame_mass_g_at_1.36")
    put("frame_vol", a["frame_volume_cm3"], "{:.2f}", "as_modelled_GF-2.1.frame_volume_cm3")
    put("frame_depth", a["bbox_abs"]["z"][1] - a["bbox_abs"]["z"][0], "{:.2f}", "as_modelled_GF-2.1.bbox_abs.z[1]-z[0]")
    ft = M["fold_test"]
    put("feeler", ft["feeler_mm"], "{:.2f}", "fold_test.feeler_mm")
    put("tail_limit", ft["tail_outer_surface_limit_from_panel_edge_mm"], "{:.2f}", "fold_test.tail_outer_surface_limit_from_panel_edge_mm")
    put("gap_limit", ft["border_limit_needed_gap_mm"], "{:.2f}", "fold_test.border_limit_needed_gap_mm")
    put("land_bottom", [l for l in M["lands"] if l["name"].startswith("bottom over")][0]["value"], "{:.2f}",
        "lands[bottom over the tail span].value")
    of = M["open_findings"]
    put("ctp_wc", of["1_bend_zone_clearance_worst_case"]["measured_GF-2.1_mm"]["CTP"]["full_WC"], "{:.3f}",
        "open_findings.1_bend_zone_clearance_worst_case.measured_GF-2.1_mm.CTP.full_WC")
    put("bead_break", of["2_bead_to_land_break"]["measured_GF-2.1_mm"]["on_the_land_plane_x60_x130"][0], "{:.2f}",
        "open_findings.2_bead_to_land_break.measured_GF-2.1_mm.on_the_land_plane_x60_x130[0]")
    m = re.search(r"(\d+) PASS / (\d+) FAIL / (\d+) INFO", of["about"])
    put("v_pass", int(m.group(1)), "{}", "open_findings.about (PASS)")
    put("v_fail", int(m.group(2)), "{}", "open_findings.about (FAIL)")
    put("v_info", int(m.group(3)), "{}", "open_findings.about (INFO)")
    put("flush_rss", M["checks"]["flush_glass_vs_sheet_RSS"], "{:.2f}", "checks.flush_glass_vs_sheet_RSS")
    put("flush_wc", M["checks"]["flush_glass_vs_sheet_WC"], "{:.2f}", "checks.flush_glass_vs_sheet_WC")
    lz = M["logo_zone"]
    put("logo_w", _named(lz, "logo_w"), "{:.0f}", "logo_zone.logo_w")
    put("logo_h", _named(lz, "logo_h"), "{:.0f}", "logo_zone.logo_h")
    put("revision", M["revision"].split(" ")[0], "{}", "revision")
    return v


def master_geometry(M=None):
    """raw numbers for drawings (front view, section labels); every one read from the master"""
    M = M or load_json(MASTER)
    G = {k: _rect(M, k) for k in ("glass", "cut", "print_window", "flange", "lip_in", "lip_out", "seat_ring_out",
                                  "tape_in", "tape_out", "fastener_line", "bend_gap_slot", "bridge", "tail_pocket")}
    G["logo_centre"] = _named(M["logo_zone"], "logo_centre")
    G["logo_w"] = _named(M["logo_zone"], "logo_w")
    G["logo_h"] = _named(M["logo_zone"], "logo_h")
    G["R_glass"] = _drv(M, "R_glass"); G["R_cut"] = _drv(M, "R_cut"); G["border"] = _drv(M, "border")
    G["flange_R"] = _drv(M, "flange_R")
    G["glass_t"] = _drv(M, "glass_t"); G["t_sheet"] = _drv(M, "t_sheet")
    G["positions"] = M["fasteners"]["positions"]
    G["pad_d"] = _drv(M, "pad_d")
    return G


# ------------------------------------------------------------------------------------------------ design document
def doc_sections(path=DOC):
    """{'§2.2.5': text, ...}; a section's text includes its subsections ('§2' contains '§2.2.5')"""
    lines = open(path, encoding="utf-8").read().splitlines()
    heads = []
    for i, l in enumerate(lines):
        m = re.match(r"^(#{2,5})\s+(\d+(?:\.\d+)*)\.?\s", l)
        if m:
            heads.append((i, m.group(2)))
    secs = {}
    for k, (i, num) in enumerate(heads):
        depth = num.count(".")
        j = len(lines)
        for i2, num2 in heads[k + 1:]:
            if num2.count(".") <= depth:
                j = i2
                break
        secs["§" + num] = "\n".join(lines[i:j])
    secs["§intro"] = "\n".join(lines[:heads[0][0]]) if heads else ""
    secs["§all"] = "\n".join(lines)
    return secs


# ------------------------------------------------------------------------------------------------ content
class Content:
    def __init__(self):
        self.M = load_json(MASTER)
        self.mv = master_values(self.M)
        self.C = load_json(CONTENT)

    def fill(self, text):
        """replace {m.name} by the master value; returns (text, {printed: master path})"""
        used = {}

        def rep(mo):
            s, p = self.mv[mo.group(1)]
            used[s] = p
            return s
        return re.sub(r"\{m\.([A-Za-z0-9_]+)\}", rep, text), used


def fmt_price(up):
    """USD unit price as printed: 2 decimals from 0.1 USD, else 2 significant digits (0.00044, 0.017)"""
    if up is None:
        return "—"
    return "%.2f" % up if up >= 0.1 else "%.2g" % up


# ------------------------------------------------------------------------------------------------ provenance
class Registry:
    """every string drawn into the PDF with its source; written next to the PDF builder as
    overview_provenance.json and read by audit_overview.py"""

    def __init__(self):
        self.items = []
        self.page = 0

    def add(self, text, src, mvals=None, kind="text"):
        if text is None:
            return
        self.items.append({"page": self.page, "text": str(text), "src": src or "-", "mvals": mvals or {}, "kind": kind})

    def dump(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=0)
