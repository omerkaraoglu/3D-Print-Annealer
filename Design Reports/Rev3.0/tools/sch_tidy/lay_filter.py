"""Mains input EMC filter sheet (A3): LINE_FUSED -> L40 -> LINE_FILT with C40 to NEUT, note below."""


def build(b, table):
    b.shapes = {"LINE_FUSED": "input", "LINE_FILT": "output"}
    X, Y = 190.5, 114.3
    b.place("L40", X, Y, 270, f="A")
    b.lab("L40.2", 12.7)
    xc = X + 20.32
    b.place("C40", xc, Y + 3.81, 0, f="R")
    b.w(b.P("L40.1"), b.P("C40.1"), (xc + 17.78, Y))
    b.lab_at((xc + 17.78, Y), "R", spec="L40.1")
    b.power(b.P("C40.2"), "NEUT")
    b.note(149.86, 142.24, [
        "Mains input EMC filter: L40 + C40 (main filter at the mains input, since layout pass 3)",
        "LINE -> F3 (8 A main fuse, root sheet) -> LINE_FUSED -> L40 -> LINE_FILT",
        "LINE_FILT feeds the heater triac Q1, the fan relay K1 and, through F1 (1 A), L1 (CM choke) and PS1",
        "L40 Core Master RC1415U-101K, 100 uH 5 A 100 mOhm radial: carries the heater current (4.4 A rms, 1.9 W)",
        "C40 1 uF 275 VAC X2 (Faratronic C42P2105KBSC400, P27.5 mm) LINE_FILT-NEUT; C1 100 nF X2 and RV1 on the root sheet",
        "Pi with C1: fc = 1/(2*pi*sqrt(100u*1u)) = 16 kHz; triac turn-on steps and HLK-10M05 switching filtered (EMC assessment pass 3)",
        "Layout: keep L40 (unshielded) away from the thermocouple input and the LCD bus; C40 bleeder is R6/R7 (2 x 33k) on the root sheet",
    ])
    return dict(paper="A3", name="Input filter",
                c1="Mains LC filter: L40 100 uH 5 A + C40 1 uF X2 after the main fuse F3",
                c2="LINE_FUSED in from F3; LINE_FILT out to Q1, K1 and F1 on the root sheet",
                regions=[("filter", 140, 95, 290, 165)])
