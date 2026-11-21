"""Part substitutions and BOM fields (MPN / Manufacturer / Datasheet) of the 2026-11-13 tidy round.

Source of the part data: ../bom_ozdisan_input.json (bom_items + ozd, ALIAS as in make_bom_ozdisan.py).
Every BOM line gets hidden MPN, Manufacturer and Datasheet (the Özdisan / DigiKey / Motorobit URL of the JSON;
when the JSON has no URL the existing Datasheet is kept). R1, J3, J4 and V1 are not purchased: no MPN.
"""
import json
import os
import re

from core import S, N, find, first, prop_node, getprop

HERE = os.path.dirname(os.path.abspath(__file__))
JSON = os.environ.get("EMC_JSON") or os.path.join(os.path.dirname(HERE), "bom_ozdisan_input.json")   # tools/bom_ozdisan_input.json

ALIAS = {
    "C5,C6,C8": "100nF_0402", "C5,C8": "100nF_0402", "C112-C115,C117-C119,C123,C126,C223,C225,C226": "100nF_0402", "C129,C332": "100nF_0402",
    "C116,C122,C336": "10uF_0805", "C124,C127,C330,C331": "10uF_0805",
    "C120,C121,C337": "1uF_0603", "C224,C335": "1uF_0603",
    # EMC-fix round 2026-11-21
    "C134,C135": "100nF_0402", "C9": "C130-C133", "RV1,RV3": "RV1",
}
NOT_PURCHASED = {"R1", "J3", "J4", "V1"}

# value / description changes (brief of 2026-11-13); fields-only parts are not listed
C100N = ["C5", "C8", "C112", "C113", "C114", "C115", "C117", "C118", "C119", "C123", "C126", "C223", "C225", "C226",
         "C129", "C332"]
VALUES = {
    "K1": "HJR-3FF-S-Z-4/05VDC", "U5": "MOC3052M", "Q2": "MMBT4401", "Q3": "MMBT4401",
    "D5": "1N4148W", "D114": "MMSZ15V 500mW", "L12": "10uH 1A",
    "C125": "4.7uF 50V X5R", "C128": "47uF 16V", "C221": "10nF 50V X7R", "C222": "10nF 50V X7R",
    "C333": "22uF 16V X5R", "C334": "22uF 16V X5R", "C116": "10uF 10V X5R", "C122": "10uF 10V X5R", "C336": "10uF 10V X5R",
    "C120": "1uF 16V X7R", "C121": "1uF 16V X7R", "C337": "1uF 16V X7R",
    "R122": "18R 0.1%", "R123": "18R 0.1%", "R132": "0.5R 0.5W 1%",
}
for r in C100N:
    VALUES[r] = "100nF 50V X7R"
# round 2 (2026-11-13): the MOC3052 LED resistor is R4 (TRIG -> U5.1), not R9 (ZCD series resistor)
VALUES["R4"] = "120"
VALUES["R9"] = "180 1/10W"
# C6 (ESP32 EN RC) 100 nF -> 1 uF, Espressif recommendation (2026-11-13, user decision)
VALUES["C6"] = "1uF 6.3V X5R"
OVERRIDE = {
    "C6": dict(mpn="CL05A105KQ5NNNC", mfr="SAMSUNG",
               url="https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl05a105kq5nnnc-418943"),
    "R4": dict(mpn="0402WGJ0121TCE", mfr="ROYALOHM",
               url="https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0402wgj0121tce-449369"),   # replaced below unless --repro
    "R9": dict(mpn="0603SAJ0181T5E", mfr="ROYALOHM",
               url="https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0603saj0181t5e-336227"),
}
DESCRIPTIONS = {
    "C6": "MLCC (1005) 0402 1 uF 6.3 V X5R 10% (ESP32 EN RC: 10k + 1 uF per Espressif)",
    "K1": "Relay SPDT 5 V coil, 7 A 250 VAC contacts, Tianbo HJR-3FF-S-Z (SRD-05 footprint and pinout)",
    "U5": "Random-phase opto-triac 600 V, IFT 10 mA max (MOC3052), DIP-6",
    "R4": "RES.(1005) 0402 120 Ohms 5% 1/16W 100PPM",
    "R9": "RES.(1608) 0603 180 Ohms 5% 1/10W-S 100PPM",
    "Q2": "NPN 40 V 600 mA SOT-23 (MMBT4401), auto-boot transistor",
    "Q3": "NPN 40 V 600 mA SOT-23 (MMBT4401), auto-boot transistor",
    "D5": "Switching diode 100 V 150 mA SOD-123 (1N4148W), relay coil flyback",
    "D114": "Zener 15 V 500 mW SOD-123 (MMSZ15V), open-LED clamp",
    "L12": "Pi-filter inductor 10 uH 1 A 4x4 mm, Viking PCD0403MT100 (same part as L11)",
    "C125": "MLCC 0805 4.7 uF 50 V X5R",
    "C128": "Pi-filter damper 47 uF 16 V aluminium electrolytic SMD 5x5.8 (Panasonic FK), in series with R132 0.5R",
    "C221": "MLCC 0603 10 nF 50 V X7R 10% (common-mode filter cap)",
    "C222": "MLCC 0603 10 nF 50 V X7R 10% (common-mode filter cap)",
    "C333": "MLCC 0805 22 uF 16 V X5R", "C334": "MLCC 0805 22 uF 16 V X5R",
    "R122": "RES 0805 18 Ohm 0.1% thin film (LED current sense)", "R123": "RES 0805 18 Ohm 0.1% thin film (LED current sense)",
    "R132": "RES 1206 0.5 Ohm 1% 0.5 W (pi-filter damper)",
    "TH220": "NTC thermistor 10k 1% B25/50=3380K 0603 (Thinking TSM1B103F3381RZ) - cold junction sensor, place touching J20",
}
for r in C100N:
    DESCRIPTIONS[r] = "MLCC 0402 100 nF 50 V X7R 10%"


# ---- EMC-fix round 2026-11-21 (EMC test campaign 2026-11-18, owner decisions 2026-11-21) -- skipped with --repro
EMC_VALUES = {"C9": "1nF 50V C0G", "D6": "1.5KE440CA", "RV3": "TVR14431KSU15Y", "C134": "100nF 50V X7R", "C135": "100nF 50V X7R",
              "U6": "SN74AHC1G14DBVR"}
for _k in range(1, 8):
    EMC_VALUES["RN%d" % _k] = "100R x4"
ROUND2 = os.environ.get("EMC_ROUND", "2") == "2"
if ROUND2:
    EMC_VALUES["U5"] = "MOC3083"                 # round 2 (owner decision 2026-11-21); R4 stays "120" (0603 now)
EMC_DESCRIPTIONS = {
    "C9": "MLCC 0402 1 nF 50 V C0G: ZCD node (U6 input) to GND, keeps the 1 kV EFT burst off U6 (EMC fix 2026-11-21)",
    "D6": "Bidirectional TVS 1500 W (10/1000 us), VRWM 376 V, VBR 418-462 V, VC 602 V @ 2.5 A, DO-201AD (Thinking 1.5KE440CA-TKS): "
          "triac A2-A1 clamp in the 1 kV surge, replaces the RV2 MOV (EMC fix 2026-11-21)",
    "RV3": "VARISTOR DISC 14MM 430V 4.5KA 275VAC 350VDC THT (same part as RV1): LINE_FUSED-NEUT, protects the fan relay K1 "
           "contact in the 1 kV surge (EMC fix 2026-11-21)",
    "C134": "MLCC 0402 100 nF 50 V X7R 10%: +5V-GND at the J10 via field (EMC fix 2026-11-21)",
    "C135": "MLCC 0402 100 nF 50 V X7R 10%: +5V-GND at the J10 via field (EMC fix 2026-11-21)",
    "U6": "Single Schmitt-trigger inverter, 74AHC, 2-5.5 V, SOT-23-5 (TI SN74AHC1G14DBVR; symbol 74xGxx:SN74LVC1G14DBV, same pin-out)",
}
if ROUND2:
  EMC_DESCRIPTIONS["U5"] = ("Zero-cross opto-triac 800 V, IFT 5 mA max, VINH 20 V max, 5000 Vrms, UL + VDE (Isocom MOC3083X, DE93284), DIP-6; "
                          "replaces the 600 V MOC3052 (1 kV surge: 620-635 V across Q1/U5 with D6)")
  EMC_DESCRIPTIONS["R4"] = "RES.(1608) 0603 120 Ohms 5% 1/10W-S 100PPM (U5 LED; 49 mW max with TRIG held on, 0402 -> 0603 2026-11-21)"
for _k in range(1, 8):
    EMC_DESCRIPTIONS["RN%d" % _k] = "Resistor array 4 x 100 Ohm 5 % 1/16 W, 0402x4 convex (Royalohm 4D02WGJ0101TCE); 33 R -> 100 R (EMC fix 2026-11-21)"


def expand(refstr):
    out = []
    for part in refstr.split(","):
        part = part.strip()
        m = re.match(r"([A-Z]+)(\d+)-([A-Z]+)?(\d+)$", part)
        if m:
            for i in range(int(m.group(2)), int(m.group(4)) + 1):
                out.append("%s%d" % (m.group(1), i))
        else:
            out.append(part)
    return out


def bom_table():
    """ref -> dict(mpn, mfr, url, key) for every purchased schematic part"""
    d = json.load(open(JSON, encoding="utf-8"))
    ozd = d["ozd"]
    res = {}
    for it in d["bom_items"]:
        key = ALIAS.get(it["ref"], it["ref"])
        for r in expand(it["ref"]):
            if r in NOT_PURCHASED:
                continue
            o = ozd.get(key)
            assert o, ("no ozd entry", it["ref"], key)
            res[r] = dict(mpn=o["code"], mfr=o["mfr"], url=o.get("url") or "", key=key, qty=it["qty"])
    for r, o in OVERRIDE.items():
        res[r] = dict(res[r], **o)
    res["TC1"] = dict(mpn="WRNT-02", mfr="Motorobit", url=ozd["TCPROBE"]["url"], key="TCPROBE", qty=1)
    return res


def set_prop(node, name, value, hidden=True):
    p = prop_node(node, name)
    if p is None:
        at = first(node, "at")
        last = max(i for i, x in enumerate(node) if isinstance(x, list) and x and x[0] == "property")
        p = [S("property"), name, value, [S("at"), at[1], at[2], N(0)], [S("hide"), S("yes")], [S("show_name"), S("no")],
             [S("do_not_autoplace"), S("no")], [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]]]]
        node.insert(last + 1, p)
    else:
        p[2] = value
    return p


def del_prop(node, name):
    p = prop_node(node, name)
    if p is not None:
        node.remove(p)


def apply(docs, repro=True):
    """docs: {sheet: Doc}; returns a change log"""
    table = bom_table()
    log = []
    VALUES_ = dict(VALUES); DESC_ = dict(DESCRIPTIONS)
    if not repro:
        VALUES_.update(EMC_VALUES); DESC_.update(EMC_DESCRIPTIONS)
        if ROUND2:
            table["R4"].update(mpn="0603SAJ0121T5E", mfr="ROYALOHM",
                               url="https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0603saj0121t5e-341209")
    seen = set()
    for sheet, doc in docs.items():
        for ref, node in doc.symbols.items():
            if ref in VALUES_:
                old = getprop(node, "Value")
                if old != VALUES_[ref]:
                    set_prop(node, "Value", VALUES_[ref])
                    log.append("%s Value %r -> %r" % (ref, old, VALUES_[ref]))
            if ref in DESC_:
                set_prop(node, "Description", DESC_[ref])
            if ref in NOT_PURCHASED:
                for k in ("MPN", "Manufacturer"):
                    del_prop(node, k)
                continue
            b = table.get(ref)
            if not b:
                log.append("WARNING %s not in the BOM JSON" % ref)
                continue
            seen.add(ref)
            set_prop(node, "MPN", b["mpn"])
            set_prop(node, "Manufacturer", b["mfr"])
            if b["url"]:
                set_prop(node, "Datasheet", b["url"])
    missing = sorted(set(table) - seen - {"TC1"})
    if missing:
        log.append("WARNING BOM refs without a symbol: %s" % missing)
    return log, table
