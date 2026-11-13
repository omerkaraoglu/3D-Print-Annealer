"""L30 - Core Master SRI0605B shielded SMD power inductor.

Source: Core Master approval drawing for SRI0605B-330M (copy on the Ozdisan CDN,
cdn.ozdisan.com/ETicaret_Dosya/587409_961218.pdf, quoted via web search; the PDF
itself could not be downloaded): A 6.6+-0.3, B 6.2+-0.3, C 5.0 max,
D 4.0 ref, E 1.5 ref; land pattern L 7.0, G 2.5, H 1.8.
ESTIMATED: the terminal shape (D/E read as terminal width/height) and the
chamfered square ferrite body; envelope = A x B x C max.
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

A, B, C = 6.6, 6.2, 5.0
PAD_X = (2.5 + 2.25) / 2        # 2.375 from G 2.5 and (L-G)/2 = 2.25
TERM_W, TERM_H = 4.0, 1.5       # D, E (ref) - estimated meaning
T = 0.2


def build():
    m = Model("L_CoreMaster_SRI0605B", "Rev3:L_CoreMaster_SRI0605B",
              "Core Master SRI0605B 6.6 x 6.2 x 5.0 max")
    body = (cq.Workplane("XY").workplane(offset=T).rect(A - 2 * T, B).extrude(C - T)
            .edges("|Z").chamfer(1.0))
    top_ring = cyl(0, 0, C - 0.05, C, 5.4)
    body = body.cut(cyl(0, 0, C - 0.4, C + 0.1, 4.6))           # recessed winding window
    m.add("ferrite", body, "ferrite")
    m.add("winding_top", cyl(0, 0, C - 0.4, C - 0.25, 4.6), "copper")
    for num, sx in (("1", -1), ("2", 1)):
        # bottom terminal (solder face) centred on the pad, plus the up-turned end tab
        m.pin(num, box(sx * PAD_X - 0.75, sx * PAD_X + 0.75, -TERM_W / 2, TERM_W / 2, 0, T), "tin")
        xe = sx * (A / 2 - T / 2)
        m.add("tab" + num, box(xe - T / 2, xe + T / 2, -TERM_W / 2, TERM_W / 2, 0, TERM_H), "tin")
        m.add("foot" + num, box(min(xe, sx * (PAD_X + 0.75)), max(xe, sx * (PAD_X + 0.75)),
                                -TERM_W / 2, TERM_W / 2, 0, T), "tin")
    return m


if __name__ == "__main__":
    run(build())
