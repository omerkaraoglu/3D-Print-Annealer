"""Power sheet (A3): 5 V -> 3.3 V buck (left), 3.3 V -> 1.2 V LDO (right), notes under each group."""


def build(b, table):
    # ------------------------------------------------------------------ buck U30
    X, Y = 152.4, 109.22
    b.place("U30", X, Y, 0, f="TL")
    vin, en = b.P("U30.3"), b.P("U30.5")
    xt = X - 15.24
    b.w(vin, (xt, vin[1]), (xt, en[1]), en)
    # +5V input rail with the two input caps hanging down
    x5 = X - 73.66
    b.w((xt, vin[1]), (x5, vin[1]))
    b.power((x5, vin[1]), "+5V")
    for ref, x in (("C330", X - 63.5), ("C331", X - 40.64)):
        b.place(ref, x, vin[1] + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.pw("U30.1", 0)
    # SW node, bootstrap cap, inductor
    sw = b.P("U30.2")
    ys = Y - 7.62
    xs = X + 12.7
    b.w(sw, (xs, sw[1]), (xs, ys))
    b.place("C332", X + 25.4, Y - 3.81, 180, f="R")
    b.place("L30", X + 44.45, ys, 90, f="A")
    b.w((xs, ys), b.P("L30.1"))
    b.lab_at((xs, ys), "R", spec="U30.2")
    vb = b.P("U30.6")
    b.w(vb, b.P("C332.1"))
    b.lab_at((X + 12.7, vb[1]), "R", spec="U30.6")
    # 3V3 output rail: FB divider, flag, output caps
    xo = X + 116.84
    b.w(b.P("L30.2"), (xo, ys))
    b.power((xo, ys), "+3V3")
    xd = X + 60.96
    b.place("R330", xd, ys + 3.81, 0, f="R")
    b.place("R331", xd, Y + 6.35, 0, f="R")
    b.w(b.P("R330.2"), b.P("R331.1"))
    b.gnd(b.P("R331.2"))
    fb = b.P("U30.4")
    b.w(fb, b.P("R331.1"))
    b.lab_at((X + 12.7, fb[1]), "R", spec="U30.4")
    b.flag((X + 71.12, ys))
    for ref, x in (("C333", X + 81.28), ("C334", X + 104.14)):
        b.place(ref, x, ys + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.note(78.74, 137.16, [
        "5V -> 3V3 buck: U30 TPS562201DDCR (Texas Instruments)",
        "5 V input from PS1 HLK-10M05 (5 V / 2 A) on the root sheet; 580 kHz synchronous buck, 2 A",
        "EN tied to VIN (EN rated to 17 V, abs max 19 V; TI datasheet SLVSD91D)",
        "Vout = 0.768 V x (1 + R330/R331) = 0.768 V x (1 + 33.2k/10k) = 3.32 V",
        "C330/C331 10 uF input, C332 100 nF bootstrap (VBST-SW), L30 4.7 uH 4 A Core Master SRI0605B-4R7M",
        "C333/C334 22 uF 16 V X5R output; PWR_FLAG: L30 is passive, so the 3V3 rail is flagged for ERC",
        "Layout: C330/C331 at the VIN pin, C332 next to the IC, L30/C333/C334 loop tight,",
        "FB divider close to VFB, no copper under L30 on the inner layers",
    ])
    # ------------------------------------------------------------------ LDO U31
    X2, Y2 = 340.36, 109.22
    b.place("U31", X2, Y2, 0, f="TL")
    vi, vo = b.P("U31.3"), b.P("U31.2")
    xi = X2 - 38.1
    b.w((xi, Y2), vi)
    b.power((xi, Y2), "+3V3")
    b.place("C335", X2 - 25.4, Y2 + 3.81, 0, f="R")
    b.gnd(b.P("C335.2"))
    b.pw("U31.1", 0)
    xo2 = X2 + 55.88
    b.w(vo, (xo2, Y2))
    b.power((xo2, Y2), "+1V2")
    for ref, x in (("C336", X2 + 17.78), ("C337", X2 + 40.64)):
        b.place(ref, x, Y2 + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.note(302.26, 137.16, [
        "3V3 -> 1V2 LDO: U31 LD1117S12CTR (STMicroelectronics)",
        "1.2 V / 800 mA for the SSD1963 core and PLL (VDDD, VDDPLL)",
        "C335 1 uF at VI; C336 10 uF + C337 1 uF at VO",
        "~60 mA load -> LDO loss 0.13 W",
    ])
    # ------------------------------------------------------------------ budget
    b.note(78.74, 180.34, [
        "Power budget (Rev3.0)",
        "5 V rail: 5.5 W peak (backlight 1.6 W, ESP32 Wi-Fi 1.2 W, SSD1963 + panel 0.5 W, relay 0.4 W, fan up to 1.5 W)",
        "3V3 rail: ~0.9 A peak -> buck loss ~0.3 W",
        "1V2 rail: ~60 mA -> LDO loss 0.13 W",
    ])
    return dict(paper="A3", name="Power",
                c1="5 V -> 3.3 V buck U30 TPS562201, 3.3 V -> 1.2 V LDO U31 LD1117S12",
                c2="5 V from PS1 HLK-10M05 on the root sheet; power budget under the groups",
                regions=[("buck", 70, 85, 285, 165), ("ldo", 295, 85, 405, 155), ("budget", 70, 170, 330, 195)])
