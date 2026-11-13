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
JSON = os.path.join(os.path.dirname(HERE), "bom_ozdisan_input.json")

ALIAS = {
    "C5,C6,C8": "100nF_0402", "C112-C115,C117-C119,C123,C126,C223,C225,C226": "100nF_0402", "C129,C332": "100nF_0402",
    "C116,C122,C336": "10uF_0805", "C124,C127,C330,C331": "10uF_0805",
    "C120,C121,C337": "1uF_0603", "C224,C335": "1uF_0603",
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
               url="https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0402wgj0121tce-449369"),
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


def apply(docs):
    """docs: {sheet: Doc}; returns a change log"""
    table = bom_table()
    log = []
    seen = set()
    for sheet, doc in docs.items():
        for ref, node in doc.symbols.items():
            if ref in VALUES:
                old = getprop(node, "Value")
                if old != VALUES[ref]:
                    set_prop(node, "Value", VALUES[ref])
                    log.append("%s Value %r -> %r" % (ref, old, VALUES[ref]))
            if ref in DESCRIPTIONS:
                set_prop(node, "Description", DESCRIPTIONS[ref])
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
