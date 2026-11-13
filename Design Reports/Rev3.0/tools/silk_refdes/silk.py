"""Legend and fabrication notes.
- Reference designators go to the assembly layer (F.Fab, 0.6 mm): the board is too dense for a readable silk
  reference on every part, and the assembly drawing (F.Fab PDF) is the rework map. Values are hidden.
- The silkscreen keeps the footprints' outlines and polarity marks and adds functional labels at the connectors
  (what the person fitting the harness needs: which plug goes where, and pin 1 / +), the debug port and the board
  name. Legend text >= 1.0 mm high with a 0.15 mm stroke.
- Each label is placed at the first candidate spot that clears every pad (0.25 mm), the other silkscreen and the
  board edge (0.5 mm).
- Fabrication notes go on Cmts.User next to the board.
- Teardrops are switched on for every via and pad; KiCad generates them with Edit > Edit Teardrops (GUI only).
python silk.py <in_stage> <out_stage>"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stage  # noqa: E402
from boardlib import MM, P  # noqa: E402

W, H = 112.0, 114.0
# text, size, rotation, candidate centres (board-local mm)
LABELS = [
    # IDC connectors on the west edge: function along the east side of each contact, polarity at the wire entry
    ("BATTERY", 1.0, 90, [(8.9, 11.0)]),
    ("+", 1.0, 0, [(1.25, 9.0)]),
    ("-", 1.0, 0, [(1.25, 13.0)]),
    ("BUTTON", 1.0, 90, [(8.9, 21.8), (8.9, 21.6)]),
    ("1", 1.0, 0, [(1.3, 25.0)]),
    ("RESET COIL", 1.0, 90, [(8.9, 36.0)]),
    ("+", 1.0, 0, [(1.25, 38.0)]),
    ("SET COIL", 1.0, 90, [(8.9, 48.0)]),
    ("+", 1.0, 0, [(1.25, 46.0)]),
    ("SWD", 1.0, 0, [(86.5, 28.6), (86.5, 37.4), (91.0, 33.0)]),
    ("LORA UART", 0.8, 0, [(103.4, 59.3), (103.4, 59.7), (103.4, 51.2), (109.6, 55.2)]),
]
TITLE = ["BATTERY SENTINEL V1.0", "PCB REV A  2026-10"]
FAB_NOTES = [
    "FABRICATION NOTES - BATTERY SENTINEL V1.0 PCB REV A",
    "1. Design per IPC-2221/IPC-2222, Type 3 multilayer (through vias only), producibility level B.",
    "2. Fabricate and accept per IPC-6012 Class 3 (with the IPC-6012FA automotive addendum where supported),",
    "   IPC-A-600 Class 3. Hole copper Class 3 (average >= 25 um).",
    "3. 4 layers, 1.6 mm (1.635 mm nominal) +-10 %, symmetric, 35 um (1 oz) finished copper on all layers:",
    "   L1 signal / prepreg 0.10 mm / L2 GND / core 1.265 mm / L3 +3V3 / prepreg 0.10 mm / L4 signal.",
    "4. Laminate IPC-4101/126 or /129: Tg >= 170 C, Td >= 340 C, CAF resistant, UL 94 V-0,",
    "   UL MOT >= 130 C for the finished board (product limit 110 C ambient; copper sized for 125 C).",
    "5. Finish ENIG. LPI solder mask both sides (IPC-SM-840 class H), mask web >= 0.1 mm. White legend, top.",
    "6. All holes plated except six M3 mounting holes (NPTH 3.2 mm). Minimum finished hole 0.3 mm.",
    "   No blind or buried vias. All vias IPC-4761 Type VI (filled and covered both sides), no via-in-pad.",
    "7. 100 % electrical test. Bow and twist <= 0.75 %. Fab UL mark and date code in copper or legend.",
    "8. Outline 112.0 x 114.0 mm, corner radius 3 mm. Assemble in a panel with >= 5 mm rails:",
    "   parts and connectors sit closer than 3.2 mm to every board edge.",
]


def _bbox_text(t):
    bb = t.GetBoundingBox()
    return (bb.GetLeft() / 1e6 - 100, bb.GetTop() / 1e6 - 100, bb.GetRight() / 1e6 - 100, bb.GetBottom() / 1e6 - 100)


def obstacles(board):
    """Rectangles (board-local mm) the legend must stay clear of: pads (+0.25), footprint silk (+0.15)."""
    out = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            out.append((bb.GetLeft() / 1e6 - 100 - 0.25, bb.GetTop() / 1e6 - 100 - 0.25,
                        bb.GetRight() / 1e6 - 100 + 0.25, bb.GetBottom() / 1e6 - 100 + 0.25))
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                bb = g.GetBoundingBox()
                out.append((bb.GetLeft() / 1e6 - 100 - 0.15, bb.GetTop() / 1e6 - 100 - 0.15,
                            bb.GetRight() / 1e6 - 100 + 0.15, bb.GetBottom() / 1e6 - 100 + 0.15))
    return out


def _hit(r, obs):
    x0, y0, x1, y1 = r
    if x0 < 0.5 or y0 < 0.5 or x1 > W - 0.5 or y1 > H - 0.5:
        return True
    return any(not (x1 < a or x0 > c or y1 < b or y0 > d) for a, b, c, d in obs)


def make_text(board, text, x, y, size, rot, layer=pcbnew.F_SilkS, stroke=0.15):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(stroke))
    t.SetPosition(P(x, y))
    t.SetTextAngleDegrees(rot)
    return t


def run(board, title_spots=None):
    for fp in board.GetFootprints():
        ref = fp.Reference()
        ref.SetLayer(pcbnew.F_Fab)
        ref.SetTextSize(pcbnew.VECTOR2I(MM(0.6), MM(0.6)))
        ref.SetTextThickness(MM(0.09))
        ref.SetPosition(fp.GetPosition())
        ref.SetVisible(True)
        fp.Value().SetLayer(pcbnew.F_Fab)
        fp.Value().SetVisible(False)
        for p in fp.Pads():
            p.SetTeardropsEnabled(True)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            t.Cast().SetTeardropsEnabled(True)
    obs = obstacles(board)
    placed, missed = [], []
    for text, size, rot, spots in LABELS:
        for (x, y) in spots:
            t = make_text(board, text, x, y, size, rot)
            r = _bbox_text(t)
            if not _hit(r, obs):
                board.Add(t)
                obs.append((r[0] - 0.2, r[1] - 0.2, r[2] + 0.2, r[3] + 0.2))
                placed.append((text, x, y))
                break
        else:
            missed.append(text)
    # board title: first spot (top-left of a 2-line block) that is free
    spots = title_spots or [(x, y) for y in (88.5, 80.0, 70.0, 60.0, 4.0) for x in (12.0, 20.0, 66.0, 74.0, 30.0)]
    for (x, y) in spots:
        ts = [make_text(board, line, x, y + i * 1.9, 1.2, 0, stroke=0.18) for i, line in enumerate(TITLE)]
        for t in ts:
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        if not any(_hit(_bbox_text(t), obs) for t in ts):
            for t in ts:
                board.Add(t)
            placed.append(("title", x, y))
            break
    else:
        missed.append("title")
    for i, line in enumerate(FAB_NOTES):
        t = make_text(board, line, W + 6.0, 2.0 + i * 1.6, 1.0, 0, layer=pcbnew.Cmts_User, stroke=0.12)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        board.Add(t)
    print("legend placed:", placed)
    if missed:
        print("legend NOT placed (no free spot):", missed)
    return missed


if __name__ == "__main__":
    b = stage.load(sys.argv[1])
    run(b)
    stage.save(b, sys.argv[2])
