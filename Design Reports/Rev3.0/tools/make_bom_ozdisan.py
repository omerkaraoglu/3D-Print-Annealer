"""Rev3.0 BOM with Özdisan availability and the 100-board unit cost.

Inputs (scratchpad of the 2026-11-12 sourcing session, copied next to this script as
``bom_ozdisan_input.json``): ``bom_items`` = reference groups from the schematic, ``ozd`` =
Özdisan product page data per group (code, mfr, stock, moq, USD price tiers, url, note).
Outputs: ``Rev3.0_BOM_Ozdisan_100pcs.csv`` and ``Rev3.0_BOM_Ozdisan_100pcs.md`` beside the spec.

Costing rule: order quantity for N boards = max(N × qty, MOQ), rounded up to a multiple of the
MOQ; the unit price is the Özdisan tier that quantity falls in. "Line / board" = that price × qty;
"purchase / board" = (order qty × price) / N, i.e. including the MOQ rounding.
"""
import json, os, sys, math, csv, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
src = json.load(open(os.path.join(HERE, "bom_ozdisan_input.json"), encoding="utf-8"))
items, ozd = src["bom_items"], src["ozd"]

# reference groups that share one purchased part
ALIAS = {
    "C5,C8": "100nF_0402", "C112-C115,C117-C119,C123,C126,C223,C225,C226": "100nF_0402", "C129,C332": "100nF_0402",
    "C116,C122,C336": "10uF_0805", "C124,C127,C330,C331": "10uF_0805",
    "C120,C121,C337": "1uF_0603", "C224,C335": "1uF_0603",
    # EMC-fix round 2026-11-21
    "C134,C135": "100nF_0402", "C9": "C130-C133", "RV1,RV3": "RV1",
}
# lines that are not purchased parts (external wiring / simulation symbol / the heater itself)
SKIP = {"V1": "simulation source, not a part", "R1": "the 1 kW heater element (customer-side)",
        "J3": "solder-wire pads for the mains lead (no part)", "J4": "solder-wire pads for the fan lead (no part)"}
# extra purchased items that have no schematic symbol
EXTRA = [
    {"ref": "F1/F3 clips", "val": "5x20 fuse clip", "fp": "Fuseholder_Clip-5x20mm (2 per fuse)", "qty": 4, "key": "FCLIP"},
    {"ref": "TC1 (probe)", "val": "K-type thermocouple, M6 ring tip, 1 m", "fp": "wired to J20 (DG127H screw terminal)", "qty": 1, "key": "TCPROBE"},
    {"ref": "SF1-SF8 (on BP1,6,8,10,11,13,15,16)", "val": "SMD spring contact finger 7.5 mm", "fp": "on LandingPad_GND_Bare6.0x5.0mm (PCB back, hand-soldered last)", "qty": 8, "key": "SPRINGF"},
    {"ref": "DS1 (panel)", "val": "7 inch 800x480 RGB TFT + capacitive touch", "fp": "plugs into J10 (TFT) and J11 (touch)", "qty": 1, "key": "DS1"},
    {"ref": "FB-FPC (on the TFT tail)", "val": "flat-cable ferrite core, 2 in series ≈ 142 Ω at 100 MHz", "fp": "both slid over the 40-way TFT tail before it is plugged into J10", "qty": 2, "key": "FPCFER"},
    {"ref": "Q1 clip", "val": "TO-220 retaining spring for SK 409", "fp": "clips Q1 onto HS1", "qty": 1, "key": "HSCLIP"},
    {"ref": "Q1 thermal compound", "val": "silicone thermal compound, 100 g jar per 100 boards", "fp": "between Q1 and HS1", "qty": 0.01, "key": "HSCOMP"},
]
# needed to build a unit but not priced or linked here
NOT_COVERED = [
    "bare PCB, assembly and the carrier frame / Formex sheet",
    "the off-PCB heater-lead inductor of spec §12.12 (≈ 200 µH, 4.35 A rms, chassis-mounted)",
    "the hardware of the ground-to-earth bond J5 (spec §12.12.8): M3 × 8 pan-head screw (ISO 7045, head Ø ≤ 5.6), M3 washer, "
    "locking element and nut, insulated M3 ring lug, about 50 mm of green/yellow lead and an M4 ring lug for chassis stud FH9",
    "fuses beyond one set per board (no spares counted), mains / fan / heater wiring and the fan",
]

def tier_price(tiers, q):
    tiers = sorted((int(str(a).replace(",", "")), float(b)) for a, b in tiers)
    p = tiers[0][1]
    for qt, pr in tiers:
        if q >= qt:
            p = pr
    return p

rows, notes = [], []
groups = []  # (group_key, [item rows])
for it in items + EXTRA:
    ref = it["ref"]
    if ref in SKIP:
        notes.append((ref, SKIP[ref])); continue
    key = it.get("key") or ALIAS.get(ref, ref)
    groups.append((key, it))

# order quantity is computed per purchased part (merged over the groups that share it)
qty_per_key = {}
for key, it in groups:
    qty_per_key[key] = qty_per_key.get(key, 0) + it["qty"]
order = {}
for key, qb in qty_per_key.items():
    d = ozd.get(key)
    if not d or not d.get("tiers"):
        continue
    moq = int(str(d.get("moq") or 1).replace(",", ""))
    need = int(math.ceil(N * qb - 1e-9))   # fractional qty = shared consumable (one jar per batch)
    q = max(need, moq)
    q = int(math.ceil(q / moq) * moq) if moq > 1 else q
    order[key] = (q, tier_price(d["tiers"], q), moq)

tot_line = tot_purchase = 0.0
seen = set()
for key, it in groups:
    d = ozd.get(key, {})
    qb = it["qty"]
    stock = d.get("stock")
    if isinstance(stock, str): stock = int(stock.replace(",", "").replace(".", ""))
    if key in order:
        q, p, moq = order[key]
        line = p * qb
        # purchase/board is attributed once per purchased part, split pro rata over its groups
        share = qb / qty_per_key[key]
        purchase = q * p / N * share
        tot_line += line; tot_purchase += purchase
        avail = "OK" if (stock or 0) >= q else ("SHORT: stock %d < %d" % (stock or 0, q))
        if d.get("stock") == 0 or stock is None: avail = "NOT STOCKED"
    else:
        q = p = line = purchase = None; avail = d.get("note", "NOT FOUND") if d else "NOT FOUND"
    rows.append({
        "Ref": it["ref"], "Qty/board": qb, "Value": it["val"], "Footprint": it.get("fp", ""),
        "Part number": d.get("code", ""), "Manufacturer": d.get("mfr", ""),
        "Özdisan stock": stock if stock is not None else "", "MOQ": d.get("moq", ""),
        "Order qty (%d boards)" % N: q or "", "Unit price USD": ("%.5f" % p) if p else "",
        "Line / board USD": ("%.4f" % line) if line is not None else "",
        "Purchase / board USD": ("%.4f" % purchase) if purchase is not None else "",
        "Availability": avail, "Note": d.get("note", "") if key not in seen else "(same part as above)",
        "Lead time (weeks)": d.get("lead") or "", "URL": d.get("url", ""),
    })
    seen.add(key)

csv_path = os.path.join(OUT_DIR, "Rev3.0_BOM_Ozdisan_%dpcs.csv" % N)
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# markdown
def md_table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in cols) + " |")
    return "\n".join(out)

read_date = src.get("read_date", "2026-11-12")
rate = src.get("try_per_usd", 50.3)
for r in rows:
    r["Part (link)"] = "[%s](%s)" % (r["Part number"], r["URL"]) if r["URL"] else r["Part number"]
    r["Supplier"] = ("Özdisan" if "ozdisan" in r["URL"] else "DigiKey" if "digikey" in r["URL"]
                     else "Motorobit" if "motorobit" in r["URL"] else "")
no_link = [r["Ref"] for r in rows if not r["URL"]]
non_ozd = [r for r in rows if r["Part number"] and "ozdisan" not in r["URL"]]
short = [r for r in rows if r["Availability"].startswith("SHORT") or r["Availability"] in ("NOT STOCKED", "NOT FOUND")]
subs = [r for r in rows if r["Note"] and r["Note"] != "(same part as above)"]
md = ["# Rev3.0 BOM — Özdisan availability and %d-board unit cost" % N,
      "",
      "Generated %s by `tools/make_bom_ozdisan.py` from the Özdisan product pages read on %s (USD prices as shown by Özdisan, **excluding KDV / VAT**; TRY/USD on the site that day ≈ %.1f). "
      "Every link was opened on that date and its page title matched the part number. "
      "The heatsink, its retaining clip and the FPC ferrite (DigiKey) and the thermocouple probe (Motorobit) are the only non-Özdisan lines; the display panel is included. Order quantity = max(%d × qty, MOQ) rounded up to the MOQ multiple "
      "(Özdisan's order multiple equals its MOQ on every line); the unit price is that quantity's tier." % (datetime.date.today().isoformat(), read_date, rate, N),
      "",
      "Lines without a link: %s." % (", ".join(no_link) if no_link else "none"),
      "",
      "## Not covered by this list",
      "",
      "\n".join("- " + s for s in NOT_COVERED),
      "",
      "## Totals",
      "",
      "| | USD / board |", "|---|---|",
      "| Components at the %d-board price breaks (qty × tier price) | **%.2f** |" % (N, tot_line),
      "| Same, including MOQ rounding (what you actually pay ÷ %d) | **%.2f** |" % (N, tot_purchase),
      "| of which not from Özdisan (HS1 heatsink, its clip and the FPC ferrite from DigiKey, thermocouple probe from Motorobit) | %.2f |" % sum(float(r["Line / board USD"]) for r in non_ozd),
      "| of which the display panel | %.2f |" % sum(float(r["Line / board USD"]) for r in rows if r["Ref"].startswith("DS1")),
      "",
      "## Lines that need attention",
      "",
      md_table(short, ["Ref", "Value", "Part (link)", "Özdisan stock", "Order qty (%d boards)" % N, "Availability", "Lead time (weeks)", "Note"]) if short else "All lines are in stock for %d boards." % N,
      "",
      "## Substitutions and merged parts (vs the schematic values)",
      "",
      md_table(subs, ["Ref", "Value", "Part number", "Note"]),
      "",
      "## Not purchased",
      "",
      "\n".join("- **%s** — %s" % n for n in notes),
      "",
      "## Thermocouple probe (not on the PCB, screws into J20)",
      "",
      "**Chosen: Motorobit WRNT-02** (BOM line TC1). Özdisan lists no thermocouple probes (sensor categories and site search checked). The probe that ships with the MAX6675 kit used on Rev2.1 is a generic "
      "**K-type, M6 ring-terminal tip, 1 m fibreglass-insulated lead with stainless-steel braid, 0–600 °C (heat-shrink at the tip softens above ≈300 °C), bare/spade ends**, "
      "which goes straight into the DG127H screw terminal J20 (red = +, blue = −; the braid can be bonded to the enclosure at the gland for EMC). Sources: "
      "Motorobit WRNT-02 (K-type, M6, 0–600 °C, 1 m) 147.29 TL + KDV ≈ 2.9 USD (2026-11-23), stock 10+, https://www.motorobit.com/wrnt-02-k-tip-0-600c-m6-termokupl-1-metre ; "
      "ProtoSupplies THC-3 (same part) 2.45 USD, https://protosupplies.com/product/thermocouple-k-type-m6-ring-terminal-sensor-1m/ ; "
      "for 100 pieces the same item is the usual AliExpress/LCSC-market 'K type thermocouple M6 1 m' at roughly 1.5–2.5 USD. "
      "If the chamber will exceed 300 °C at the sensor, use the stainless 4 × 30 mm cylindrical variant (same lead, 0–400 °C, no heat-shrink at the tip). Budget ≈ 2.5 USD per unit.",
      "",
      "## Full BOM",
      "",
      md_table(rows, ["Ref", "Qty/board", "Value", "Part (link)", "Manufacturer", "Supplier", "Özdisan stock", "MOQ", "Order qty (%d boards)" % N, "Unit price USD", "Line / board USD", "Availability"]),
      ""]
md_path = os.path.join(OUT_DIR, "Rev3.0_BOM_Ozdisan_%dpcs.md" % N)
open(md_path, "w", encoding="utf-8").write("\n".join(md))
print("lines", len(rows), "line/board %.3f purchase/board %.3f" % (tot_line, tot_purchase))
print("written", os.path.abspath(csv_path), os.path.abspath(md_path))
for r in short: print("ATTN", r["Ref"], r["Availability"])
