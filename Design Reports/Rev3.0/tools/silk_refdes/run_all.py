"""Whole silk / refdes chain for the Rev3.0 board, deterministic, always from the untouched orig/:
  1. refdes_geom.py (KiCad python)   orig            -> work/geom0.json
  2. silk_labels.py                  board legend    -> work/labels.json
  3. refdes_apply.py (labels only)   orig + legend   -> work/labelled/3dFilamentDryer.kicad_pcb
  4. refdes_geom.py (KiCad python)   labelled board  -> work/geom.json   (the legend is an obstacle for the designators)
  5. refdes_place.py                 designators + legend maps -> work/placement.json
  6. refdes_apply.py                 orig + legend + designators + maps -> stage/3dFilamentDryer.kicad_pcb
  6b. silk_fix.py                    U1/U5 outlines off the creepage slot, J20 pin-1 mark off D220, Q1/HS1 silk rule
  6c. art/art_gen.py, art/art_apply.py   readark logo + Manrope text block in place of the four title-block texts
  6d. refdes_geom.py (KiCad python)  stage           -> work/geom_now.json  (the board with legend, designators, artwork)
      art/qr_gen.py VIDEO_URL        QR code to the AnnealX video, placed left of J10 -> work/art/qr.json
      art/qr_apply.py (KiCad python) stage + QR code -> stage/3dFilamentDryer.kicad_pcb
  7. work/regions.json              crop windows of the circuit groups (for refdes_render.py)
python run_all.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import GEOM, KPY, LABELS, ORIG, PLACEMENT, STAGE, WORK  # noqa: E402

VIDEO_URL = "https://readark.eu/annealx/7j7aux/"     # unlisted AnnealX product video page (readark-website acee62a)

GROUPS = {
    "mains_input": "J4 F3 J3 RV1 C1 C40 L40",
    "heater_stage": "R1 HS1 Q1 R2 R3 R5 C4 RV2 F1 L1",
    "psu": "PS1 C2 R6 R7",
    "relay_optos_zcd": "K1 U1 U5 R4 R8 R9 R10 U6 Q4 D5 R15",
    "esp32": "U3 J2 R110 R111 R112 R113 R114 R115 R116 R117 R118 R119 R120 R121 R130 R131 R16 R12",
    "programmer": "Q2 Q3 R11 R13 R14 C5 C6 C7 C8",
    "ssd1963": "U10 Y10 C110 C111 C112 C113 C114 C115 C116 C117 C118 C119 C120 C121 R124",
    "rgb_arrays": "RN1 RN2 RN3 RN4 RN5 RN6 RN7",
    "lv_power": "U30 L30 C330 C331 C332 C333 C334 C335 C336 C337 U31 R330 R331 R126 R127 R128",
    "boost_pi_filter": "U11 L11 L12 C124 C125 C127 C128 R122 R123 R132 D111 D114",
    "thermocouple": "J20 U20 TH220 R220 R221 R222 R223 R224 R225 R226 R227 C220 C221 C222 C223 C224 C225 C226 D220 D221",
    "touch_fpc_j11": "J11 D112 D113 D115 D116 R129 C126 C133",
    "tft_fpc_j10": "J10 C122 C123 C129 C130 C131 C132 R125",
}


def run(*a):
    print(">", " ".join(os.path.basename(x) if os.sep in x or "/" in x else x for x in a))
    subprocess.run(list(a), check=True)


def regions():
    G = json.load(open(GEOM, encoding="utf-8"))
    fps = {f["ref"]: f for f in G["fps"]}
    L = json.load(open(LABELS, encoding="utf-8"))
    out = {}
    for name, refs in GROUPS.items():
        bbs = []
        for r in refs.split():
            f = fps.get(r)
            if f is None:
                continue
            bb = f["cybb"] or [min(p["bb"][0] for p in f["pads"]), min(p["bb"][1] for p in f["pads"]),
                               max(p["bb"][2] for p in f["pads"]), max(p["bb"][3] for p in f["pads"])]
            bbs.append(bb)
        out[name] = [round(min(b[0] for b in bbs) - 3, 2), round(min(b[1] for b in bbs) - 3, 2),
                     round(max(b[2] for b in bbs) + 3, 2), round(max(b[3] for b in bbs) + 3, 2)]
    tl = [t["rect"] for t in L["texts"] if t["name"].startswith("title")]
    out["title_block"] = [round(min(r[0] for r in tl) - 4, 2), round(min(r[1] for r in tl) - 4, 2),
                          round(max(r[2] for r in tl) + 4, 2), round(max(r[3] for r in tl) + 4, 2)]
    json.dump(out, open(os.path.join(WORK, "regions.json"), "w", encoding="utf-8"), indent=1)


def main():
    os.makedirs(WORK, exist_ok=True)
    g0 = os.path.join(WORK, "geom0.json")
    lab = os.path.join(WORK, "labelled", os.path.basename(ORIG))
    run(KPY, os.path.join(HERE, "refdes_geom.py"), ORIG, g0)
    run(sys.executable, os.path.join(HERE, "silk_labels.py"), g0, LABELS)
    run(sys.executable, os.path.join(HERE, "refdes_apply.py"), LABELS, "-", lab)
    run(KPY, os.path.join(HERE, "refdes_geom.py"), lab, GEOM)
    run(sys.executable, os.path.join(HERE, "refdes_place.py"))
    run(sys.executable, os.path.join(HERE, "refdes_apply.py"), LABELS, PLACEMENT, STAGE)
    run(sys.executable, os.path.join(HERE, "silk_fix.py"), STAGE, STAGE)
    run(sys.executable, os.path.join(HERE, "art", "art_gen.py"))
    run(KPY, os.path.join(HERE, "art", "art_apply.py"), STAGE, STAGE)
    run(KPY, os.path.join(HERE, "refdes_geom.py"), STAGE, os.path.join(WORK, "geom_now.json"))
    run(sys.executable, os.path.join(HERE, "art", "qr_gen.py"), VIDEO_URL)
    run(KPY, os.path.join(HERE, "art", "qr_apply.py"), STAGE, STAGE)
    regions()


if __name__ == "__main__":
    main()
