"""Electronics BOM data for the Rev3.0 OVEN CONTROLLER overview PDF.

Writes ``electronics_bom.json`` next to this script. Reads only (never writes):
  Design Reports/Rev3.0/Rev3.0_BOM.csv                    schematic BOM export (references, values, links)
  Design Reports/Rev3.0/Rev3.0_BOM_Ozdisan_100pcs.csv     sourced BOM, 100 boards (part numbers, stock, prices)
  Design Reports/Rev3.0/Rev3.0_BOM_Ozdisan_100pcs.md      stated per-board total (checked against the CSV sum)
  electronics_bom_input.json (this folder)                hand-written groups, roles, part texts and notes

Rules:
  * one JSON line per row of the sourced CSV (its numbers are copied unchanged), plus the schematic references
    that have no sourced row (status NOT_SOURCED, no price);
  * url = the sourced CSV's URL, else the schematic BOM's link for the same references, accepted only when the
    bought part number appears in it; supplier follows the link's domain;
  * status: SHORT if the CSV says so (or stock < order qty), else SUBSTITUTE if the input marks it, else OK.
    Substitutions are hand-marked and cross-checked here against value / part-number / link differences;
  * checks: every reference of Rev3.0_BOM.csv exactly once across the groups, quantity sums, per-board total
    against the .md. Problems are printed; ``--strict`` makes them fatal.

Run:  python make_electronics_bom.py [--strict]
"""
import csv
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REV3 = os.path.normpath(os.path.join(HERE, "..", "..", ".."))           # Design Reports/Rev3.0
SCH_CSV = os.path.join(REV3, "Rev3.0_BOM.csv")
SRC_CSV = os.path.join(REV3, "Rev3.0_BOM_Ozdisan_100pcs.csv")
SRC_MD = os.path.join(REV3, "Rev3.0_BOM_Ozdisan_100pcs.md")
INPUT = os.path.join(HERE, "electronics_bom_input.json")
OUT = os.path.join(HERE, "electronics_bom.json")
STRICT = "--strict" in sys.argv
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

problems = []
hand_only_subs = []     # substitutions marked by hand that the CSVs cannot show (e.g. a higher voltage rating)


def warn(msg):
    problems.append(msg)
    print("CHECK:", msg)


def expand_refs(s):
    """'C112-C115,C117' -> ['C112','C113','C114','C115','C117']"""
    out = []
    for tok in [t.strip() for t in s.split(",") if t.strip()]:
        m = re.fullmatch(r"([A-Z]+)(\d+)-([A-Z]+)?(\d+)", tok)
        if m:
            pre, a, b = m.group(1), int(m.group(2)), int(m.group(4))
            out += ["%s%d" % (pre, i) for i in range(a, b + 1)]
        else:
            out.append(tok)
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def supplier_of(url):
    if not url:
        return None
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
    return {"ozdisan.com": "Özdisan", "digikey.com": "DigiKey", "motorobit.com": "Motorobit"}.get(host, host)


def url_matches_mpn(url, mpn):
    """True when the bought part number is in the link (product page) or the link searches for its base."""
    u, m = norm(url), norm(mpn)
    if m and m in u:
        return True
    q = re.search(r"[?&](?:search|s)=([^&]+)", url or "")
    return bool(q and m.startswith(norm(q.group(1))) and len(norm(q.group(1))) >= 6)


def pretty_refs(s):
    return ", ".join(t.strip() for t in s.split(","))


# ---------------------------------------------------------------- inputs
cfg = json.load(open(INPUT, encoding="utf-8"))
sch_rows = list(csv.DictReader(open(SCH_CSV, encoding="utf-8-sig")))
src_rows = list(csv.DictReader(open(SRC_CSV, encoding="utf-8-sig")))
md_text = open(SRC_MD, encoding="utf-8").read()

sch_by_ref = {}
for r in sch_rows:
    for ref in expand_refs(r["Reference"]):
        if ref in sch_by_ref:
            warn("Rev3.0_BOM.csv lists %s twice" % ref)
        sch_by_ref[ref] = r

mfr_names = cfg["manufacturer_names"]
group_ids = [g["id"] for g in cfg["groups"]]
lines_by_group = {g: [] for g in group_ids}
line_meta = []          # (line, origin info) for the link checker / report

# ---------------------------------------------------------------- sourced rows
for r in src_rows:
    key = r["Ref"]
    h = cfg["lines"].get(key)
    if h is None:
        warn("sourced CSV row %r has no entry in electronics_bom_input.json" % key)
        continue
    refs = expand_refs(key) if key not in ("F1/F3 clips", "TC1 (probe)") else []
    sch = []
    for ref in refs:
        if ref not in sch_by_ref:
            warn("sourced ref %s (row %r) is not in Rev3.0_BOM.csv" % (ref, key))
        elif sch_by_ref[ref] not in sch:
            sch.append(sch_by_ref[ref])
    mpn = r["Part number"]

    # ---- link
    url, url_source = r["URL"].strip(), "sourced CSV"
    if not url:
        cand = [s["Ozdisan/Datasheet"].strip() for s in sch if s["Ozdisan/Datasheet"].strip()]
        cand = list(dict.fromkeys(cand))
        url, url_source = (cand[0], "Rev3.0_BOM.csv") if cand else (None, "none")
        if len(cand) > 1:
            warn("row %r: several schematic links %s" % (key, cand))
    if url and not url_matches_mpn(url, mpn):
        warn("row %r: link %s does not carry the bought part number %s -> link dropped" % (key, url, mpn))
        url, url_source = None, "dropped (part number mismatch)"
    is_search = bool(url and re.search(r"[?&](search|s)=", url))

    # ---- status
    avail = r["Availability"]
    stock = int(r["Özdisan stock"]) if r["Özdisan stock"] else None
    order = int(r["Order qty (100 boards)"]) if r["Order qty (100 boards)"] else None
    short = avail.startswith("SHORT") or (stock is not None and order is not None and stock < order)
    sub = bool(h.get("substitute"))
    # cross-check the hand mark against the CSVs
    auto = []
    for s in sch:
        if s["Value"].strip() != r["Value"].strip() and len(sch) == 1:
            auto.append("value %r -> %r" % (s["Value"], r["Value"]))
        if s["MPN"].strip() and norm(s["MPN"]) != norm(mpn):
            auto.append("MPN %s -> %s" % (s["MPN"], mpn))
        link = s["Ozdisan/Datasheet"].strip()
        if "/p/" in link and "tft-paneller" not in link and not url_matches_mpn(link, mpn):
            auto.append("schematic link is another part (%s)" % link.rsplit("/", 1)[-1])
    if auto and not sub:
        warn("row %r differs from Rev3.0_BOM.csv (%s) but is not marked substitute" % (key, "; ".join(auto)))
    if sub and not auto:
        hand_only_subs.append(key)
    status = "SHORT" if short else ("SUBSTITUTE" if sub else "OK")

    note = h.get("note", "")
    if short and "stock" not in note.lower():
        note = (avail + ". " + note).strip()
    if is_search:
        note = (note + " The link is Özdisan's site search for the part number, which opens the product page when the "
                "search has a single hit; the repo has no direct product-page link.").strip()

    line = {
        "refs": h.get("refs", pretty_refs(key)),
        "qty": int(r["Qty/board"]),
        "part": h["part"],
        "role": h["role"],
        "mpn": mpn,
        "manufacturer": h.get("manufacturer", mfr_names.get(r["Manufacturer"], r["Manufacturer"])),
        "supplier": supplier_of(url),
        "url": url,
        "unit_price_usd": float(r["Unit price USD"]),
        "line_usd_per_board": float(r["Line / board USD"]),
        "status": status,
        "note": note,
    }
    if h["group"] not in lines_by_group:
        warn("row %r: unknown group %s" % (key, h["group"]))
        continue
    lines_by_group[h["group"]].append(line)
    line_meta.append({"refs": line["refs"], "url": url, "url_source": url_source, "mpn": mpn,
                      "auto_differences": auto, "stock": stock, "order_qty_100": order,
                      "purchase_usd_per_board": float(r["Purchase / board USD"])})

# ---------------------------------------------------------------- schematic refs without a sourced row
for h in cfg["not_sourced"]:
    s = sch_by_ref.get(h["refs"])
    if s is None:
        warn("not_sourced %s is not in Rev3.0_BOM.csv" % h["refs"])
        continue
    url = h["url_override"] if "url_override" in h else (s["Ozdisan/Datasheet"].strip() or None)
    line = {
        "refs": h["refs"], "qty": int(s["Qty"]), "part": h["part"], "role": h["role"],
        "mpn": s["MPN"].strip() or None, "manufacturer": s["Manufacturer"].strip() or None,
        "supplier": supplier_of(url), "url": url,
        "unit_price_usd": None, "line_usd_per_board": None, "status": "NOT_SOURCED", "note": h["note"],
    }
    lines_by_group[h["group"]].append(line)
    line_meta.append({"refs": h["refs"], "url": url, "url_source": "none" if url is None else "Rev3.0_BOM.csv",
                      "mpn": None, "auto_differences": [], "stock": None, "order_qty_100": None,
                      "purchase_usd_per_board": None})

# lines inside a group follow the order of the input file (signal flow), not the CSV order
order_keys = [cfg["lines"][k].get("refs", pretty_refs(k)) for k in cfg["lines"]] + [h["refs"] for h in cfg["not_sourced"]]
for g in group_ids:
    lines_by_group[g].sort(key=lambda ln: order_keys.index(ln["refs"]) if ln["refs"] in order_keys else 999)

# ---------------------------------------------------------------- checks
seen = {}
for g in group_ids:
    for ln in lines_by_group[g]:
        for ref in expand_refs(ln["refs"].replace(" ", "")):
            seen.setdefault(ref, []).append(g)
extras = {"F1/F3clips", "TC1"}
for ref in sch_by_ref:
    if len(seen.get(ref, [])) != 1:
        warn("reference %s appears %d times across the groups" % (ref, len(seen.get(ref, []))))
for ref in seen:
    if ref not in sch_by_ref and ref not in extras:
        warn("reference %s is in the groups but not in Rev3.0_BOM.csv" % ref)

all_lines = [ln for g in group_ids for ln in lines_by_group[g]]
priced = [ln for ln in all_lines if ln["line_usd_per_board"] is not None]
total = sum(ln["line_usd_per_board"] for ln in priced)
total_purchase = sum(m["purchase_usd_per_board"] for m in line_meta if m["purchase_usd_per_board"] is not None)
m = re.search(r"Components at the 100-board price breaks[^|]*\|\s*\*\*([\d.]+)\*\*", md_text)
stated = float(m.group(1)) if m else None
if stated is None:
    warn("could not read the stated total from the .md")
elif round(total, 2) != stated:
    warn("per-board total %.4f does not round to the stated %.2f" % (total, stated))
qty_all = sum(ln["qty"] for ln in all_lines)
sch_qty = sum(int(r["Qty"]) for r in sch_rows)
src_qty = sum(int(r["Qty/board"]) for r in src_rows)
not_sourced_qty = sum(ln["qty"] for ln in all_lines if ln["status"] == "NOT_SOURCED")
probe_qty = sum(ln["qty"] for ln in all_lines if ln["refs"] == "TC1")
placements = qty_all - not_sourced_qty - probe_qty
non_ozd = sum(ln["line_usd_per_board"] for ln in priced if ln["supplier"] != "Özdisan")
for ln in all_lines:
    if len(ln["role"].split()) > 13:
        warn("role of %s has %d words" % (ln["refs"], len(ln["role"].split())))
    if ln["url"] is None and ln["status"] != "NOT_SOURCED":
        warn("line %s has no link" % ln["refs"])

# ---------------------------------------------------------------- output
nic = cfg["not_in_component_total"]
out = {
    "generated": datetime.date.today().isoformat(),
    "sources": [
        "Design Reports/Rev3.0/Rev3.0_BOM_Ozdisan_100pcs.csv (part numbers, stock, MOQ, prices, links; generated 2026-11-13 by tools/make_bom_ozdisan.py from tools/bom_ozdisan_input.json)",
        "Design Reports/Rev3.0/Rev3.0_BOM_Ozdisan_100pcs.md (stated per-board total, substitution notes)",
        "Design Reports/Rev3.0/Rev3.0_BOM.csv (schematic references, values and links; exported 2026-11-12, before the 2026-11-13 schematic substitutions)",
        "Design Reports/Rev3.0/Rev3.0_Design_Specification.md (function of each circuit block; display panel price §2)",
        "Design Reports/Rev3.0/Rev3.0_GlassFront_Design.md (display panel and FPC tails J10/J11; glass-front cost estimate §0.3)",
        "Design Reports/Rev3.0/tools/glassfront/overview/electronics_bom_input.json (hand-written group titles, roles, part texts, notes)",
    ],
    "price_basis": ("Özdisan's US-dollar prices read on ozdisan.com on 2026-11-12, each part at the price break of its "
                    "order quantity for 100 boards, with the HS1 heatsink at DigiKey's 2.60 USD and the TC1 probe at "
                    "Motorobit's 145.86 TL (50.3 TL/USD) as recorded in the same sourced BOM; all figures are USD per board."),
    "totals": {
        "components_usd_per_board": round(total, 2),
        "lines": len(all_lines),
        "placements": placements,
        "notes": [
            "Component total = sum of line_usd_per_board over all groups = %.4f USD, i.e. %.2f USD per board, the same as the "
            "total stated in Rev3.0_BOM_Ozdisan_100pcs.md (%s). Including the minimum-order rounding (what 100 boards "
            "actually cost, divided by 100) the sourced CSV gives %.4f USD, also %.2f." % (
                total, total, "%.2f" % stated if stated is not None else "not found", total_purchase, total_purchase),
            "Included: every purchased part of the board, the 4 fuse clips (not drawn in the schematic), the HS1 heatsink "
            "(DigiKey) and the TC1 thermocouple probe (Motorobit). Parts not bought from Özdisan: %.2f USD of the total." % non_ozd,
            "Not included: the display panel, the bare PCB, assembly and test, the glass-front module, the 1 kW heater "
            "element and the fan (oven parts), VAT, shipping and customs. The panel, PCB, assembly and glass front are "
            "listed under not_in_component_total.",
            "lines = %d: %d priced lines from the sourced CSV plus %d schematic references with nothing to buy "
            "(J3, J4, R1, V1; status NOT_SOURCED, no price)." % (len(all_lines), len(priced), len(all_lines) - len(priced)),
            "placements = %d pieces mounted on each board (%d schematic parts plus 4 fuse clips). The sum of qty over all "
            "lines is %d: it also counts the off-board probe TC1 and the four unpriced references." % (
                placements, placements - 4, qty_all),
            "Status SUBSTITUTE means the bought part differs from the value or part number in Rev3.0_BOM.csv, upgrades "
            "such as a higher voltage rating included; the note says how. The KiCad schematic already carries these "
            "substitutions (Design Specification §12.7, 2026-11-13), but Rev3.0_BOM.csv was exported on 2026-11-12 and "
            "not re-exported.",
            "VAT: the sourced BOM does not say whether the Özdisan prices of 2026-11-12 include VAT (the Design "
            "Specification §2 gives its earlier Özdisan prices excluding VAT); the probe price excludes VAT (KDV).",
        ],
    },
    "groups": [dict(g, lines=lines_by_group[g["id"]]) for g in cfg["groups"]],
    "not_in_component_total": nic,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write("\n")

# ---------------------------------------------------------------- report
print("written", OUT)
for g in cfg["groups"]:
    ls = lines_by_group[g["id"]]
    print("  %-24s %2d lines  qty %3d  %8.4f USD" % (
        g["id"], len(ls), sum(x["qty"] for x in ls), sum(x["line_usd_per_board"] or 0 for x in ls)))
print("lines %d, qty all %d (Rev3.0_BOM.csv %d, sourced CSV %d), placements %d" % (
    len(all_lines), qty_all, sch_qty, src_qty, placements))
print("total %.4f (stated %s), incl. MOQ rounding %.4f, non-Özdisan %.4f" % (total, stated, total_purchase, non_ozd))
print("schematic refs %d, all covered once: %s" % (
    len(sch_by_ref), all(len(seen.get(r, [])) == 1 for r in sch_by_ref)))
for ln in all_lines + nic:
    if ln["status"] != "OK":
        print("  %-11s %-45s %s" % (ln["status"], ln["refs"], ln["note"][:110]))
print("substitutions marked by hand only (no difference visible in the CSV value / MPN / link):", hand_only_subs)
print("%d check message(s)" % len(problems))
if STRICT and problems:
    sys.exit(1)
