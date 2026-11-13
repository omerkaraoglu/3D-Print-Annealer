"""Rev C.23 legend pass (silk.py rules for the new and moved parts, without re-adding labels and notes):
- every reference designator on F.Fab (0.6 mm, at the part centre), values hidden; teardrops on;
- 'LORA UART' moves off R88 (first free candidate spot);
- fabrication note 4: laminate rated for >= 130 C continuous (product limit 110 C ambient, copper sized for 125 C).
python silk_c23.py <in_stage> <out_stage>"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import silk  # noqa: E402
import stage  # noqa: E402
from boardlib import MM  # noqa: E402

LORA_SPOTS = [(103.4, 59.3), (103.4, 59.7), (103.4, 51.2), (104.3, 61.4), (100.9, 61.4), (98.4, 51.0)]
# new harness labels (silk.py style): J7 like J3, the shunt bolts just above the shunt body outline (y 94.4): with the
# shunt on the battery side, the fitter must not swap the battery and relay cables
NEW_LABELS = [("RELAY SENSE", 1.0, 0, [(6.0, 77.4), (6.5, 77.4), (6.0, 77.8), (6.5, 64.6), (6.5, 64.2)]),
              ("1", 1.0, 0, [(1.3, 69.0)]),
              ("TO RELAY", 1.0, 0, [(26.75, 93.2), (26.75, 92.8)]), ("BATTERY +", 1.0, 0, [(86.75, 93.2), (86.75, 92.8)])]
NOTE4 = ["4. Laminate IPC-4101/126 or /129: Tg >= 170 C, Td >= 340 C, CAF resistant, UL 94 V-0,",
         "   UL MOT >= 130 C for the finished board (product limit 110 C ambient; copper sized for 125 C)."]


def refs(board):
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


def _legend_obstacles(board):
    obs = silk.obstacles(board)
    for d in board.GetDrawings():                       # the other legend texts
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_SilkS:
            r = silk._bbox_text(d)
            obs.append((r[0] - 0.2, r[1] - 0.2, r[2] + 0.2, r[3] + 0.2))
    return obs


def place(board, text, size, rot, spots):
    obs = _legend_obstacles(board)
    for x, y in spots:
        t = silk.make_text(board, text, x, y, size, rot)
        if not silk._hit(silk._bbox_text(t), obs):
            board.Add(t)
            print("%s at %s" % (text, (x, y)))
            return t
    raise SystemExit("no free spot for " + text)


def lora_label(board):
    old = [d for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetText() == "LORA UART"]
    for d in old:
        board.Remove(d)
    place(board, "LORA UART", 0.8, 0, LORA_SPOTS)
    return old


def fab_note(board):
    texts = [d for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.Cmts_User]
    a = [t for t in texts if t.GetText().startswith("4. Laminate")]
    b = [t for t in texts if t.GetText().startswith("   UL MOT")]
    assert len(a) == 1 and len(b) == 1, (len(a), len(b))
    a[0].SetText(NOTE4[0])
    b[0].SetText(NOTE4[1])


if __name__ == "__main__":
    bd = stage.load(sys.argv[1])
    refs(bd)
    keep = lora_label(bd)
    for text, size, rot, spots in NEW_LABELS:
        place(bd, text, size, rot, spots)
    fab_note(bd)
    stage.save(bd, sys.argv[2])
