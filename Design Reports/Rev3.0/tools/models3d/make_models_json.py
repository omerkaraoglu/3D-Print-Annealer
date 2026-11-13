"""Write models.json: the 3D-model changes the board-editing agent applies to
3dFilamentDryer.kicad_pcb (this toolchain never writes the board).

Every entry REPLACES the footprint's whole model list with the one model given
(the board's embedded copies of the Rev3 footprints carry no model; F1/F3/J3/
J4/R1 point at stock KiCad models that do not exist in KiCad 10).
"mechanical" lists footprints to ADD (not in the schematic).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FMT = "${KIPRJMOD}/../ComponentsLibrary/User Created/Rev3/Rev3.3dshapes/%s.step"
ID = {"offset": [0, 0, 0], "rotate": [0, 0, 0], "scale": [1, 1, 1]}

REFS = {
    "C40": ("Rev3:C_Rect_L32.0mm_W9.0mm_P27.50mm_X2", "C_Rect_L32.0mm_W9.0mm_P27.50mm_X2_Faratronic_C42"),
    "HS1": ("Rev3:Heatsink_Fischer_SK409_63.5_STC", "Heatsink_Fischer_SK409_63.5_STC"),
    "J10": ("Rev3:Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide",
            "Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide"),
    "J11": ("Rev3:KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide",
            "KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide"),
    "J20": ("Rev3:TerminalBlock_DEGSON_DG127H-5.08-02P", "TerminalBlock_DEGSON_DG127H-5.08-02P"),
    "L1": ("Rev3:LFU09V-103", "LFU09V-103"),
    "L11": ("Rev3:L_Viking_PCD0403", "L_Viking_PCD0403"),
    "L12": ("Rev3:L_Viking_PCD0403", "L_Viking_PCD0403"),
    "L30": ("Rev3:L_CoreMaster_SRI0605B", "L_CoreMaster_SRI0605B"),
    "L40": ("Rev3:L_Radial_CoreMaster_RC1415U", "L_Radial_CoreMaster_RC1415U"),
    "F1": ("Fuse:Fuseholder_Clip-5x20mm_Littelfuse_445-030_Inline_P20.50x5.20mm_D1.30mm_Horizontal",
           "Fuse_Reomax_R3-5A_Clips_5x20mm_P20.50x5.20mm"),
    "F3": ("Fuse:Fuseholder_Clip-5x20mm_Littelfuse_445-030_Inline_P20.50x5.20mm_D1.30mm_Horizontal",
           "Fuse_Reomax_R3-5A_Clips_5x20mm_P20.50x5.20mm"),
    "J3": ("Connector_Wire:SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm",
           "SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm_stub"),
    "R1": ("Connector_Wire:SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm",
           "SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm_stub"),
    "J4": ("Connector_Wire:SolderWire-0.75sqmm_1x02_P7mm_D1.25mm_OD3.5mm",
           "SolderWire-0.75sqmm_1x02_P7mm_D1.25mm_OD3.5mm_stub"),
}


def main():
    import tft7_sat070at40d21 as t
    out = {"_note": __doc__.strip()}
    for ref, (fp, model) in REFS.items():
        out[ref] = dict(footprint=fp, model=FMT % model, **ID)
    out["mechanical"] = {
        "DS1": {
            "footprint": "Rev3:TFT7_SAT070AT40D21_Mech",
            "model": FMT % "TFT7_SAT070AT40D21", **ID,
            "position_abs_mm": [round(t.CX, 3), round(t.CY, 3)],
            "layer": "B.Cu",
            "orientation_deg": 180.0,
            "how": ("Add on F.Cu at the position with orientation 0, then Flip left/right about its own "
                    "position (KiCad stores B.Cu, orientation 180). Panel back on the PCB back, bottom edges "
                    "flush (y 119.0), TFT tail fingers centred on J10 x 155.65."),
            "attributes": ["board_only", "exclude_from_pos_files", "exclude_from_bom", "allow_missing_courtyard"],
            "panel_outline_abs_mm": [round(t.CX - t.L_OUT / 2, 3), round(t.CY - t.H_OUT / 2, 3),
                                     round(t.CX + t.L_OUT / 2, 3), round(t.CY + t.H_OUT / 2, 3)],
        }
    }
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json")
    json.dump(out, open(p, "w", newline="\n"), indent=1)
    print("wrote", p)


if __name__ == "__main__":
    main()
