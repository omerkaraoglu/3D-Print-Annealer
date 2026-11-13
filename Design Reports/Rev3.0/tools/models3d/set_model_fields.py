"""Write the (model ...) field into the Rev3.pretty footprints (replaces any existing one).

Only the model block is touched; everything else in the .kicad_mod stays byte-identical.
Run with any Python 3:  python set_model_fields.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, r"..\..\..\..\KiCad\ComponentsLibrary\User Created\Rev3\Rev3.pretty"))
FMT = "${KIPRJMOD}/../ComponentsLibrary/User Created/Rev3/Rev3.3dshapes/%s.step"

MAP = {
    "C_Rect_L32.0mm_W9.0mm_P27.50mm_X2": "C_Rect_L32.0mm_W9.0mm_P27.50mm_X2_Faratronic_C42",
    "Connfly_DS1020-09-06VBT1A_1x06_P0.5mm_Horizontal": "Connfly_DS1020-09-06VBT1A_1x06_P0.5mm_Horizontal",
    "Connfly_DS1020-09-40VBT1A_1x40_P0.5mm_Horizontal": "Connfly_DS1020-09-40VBT1A_1x40_P0.5mm_Horizontal",
    "Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide": "Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide",
    "Heatsink_Fischer_SK409_63.5_STC": "Heatsink_Fischer_SK409_63.5_STC",
    "KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide": "KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide",
    "LFU09V-103": "LFU09V-103",
    "L_CoreMaster_SRI0605B": "L_CoreMaster_SRI0605B",
    "L_Radial_CoreMaster_RC1415U": "L_Radial_CoreMaster_RC1415U",
    "L_Viking_PCD0403": "L_Viking_PCD0403",
    "TerminalBlock_DEGSON_DG127H-5.08-02P": "TerminalBlock_DEGSON_DG127H-5.08-02P",
    "TFT7_SAT070AT40D21_Mech": "TFT7_SAT070AT40D21",
}


def strip_models(txt):
    out, i = [], 0
    while True:
        k = txt.find("(model ", i)
        if k < 0:
            out.append(txt[i:]); break
        ls = txt.rfind("\n", 0, k)
        out.append(txt[i:ls])
        depth, j = 0, k
        while True:
            c = txt[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            elif c == '"':
                j = txt.index('"', j + 1)
            j += 1
        i = j + 1
    return "".join(out)


def main():
    for fp, model in MAP.items():
        p = os.path.join(LIB, fp + ".kicad_mod")
        txt = open(p, encoding="utf-8").read()
        nl = "\r\n" if "\r\n" in txt else "\n"
        body = strip_models(txt).rstrip()
        assert body.endswith(")"), p
        block = ('\t(model "%s"%s\t\t(offset (xyz 0 0 0))%s\t\t(scale (xyz 1 1 1))%s\t\t(rotate (xyz 0 0 0))%s\t)%s'
                 % (FMT % model, nl, nl, nl, nl, nl))
        new = body[:-1].rstrip() + nl + block + ")" + nl
        if new != txt:
            open(p, "w", encoding="utf-8", newline="").write(new)
            print("updated", fp)
        else:
            print("unchanged", fp)


if __name__ == "__main__":
    main()
