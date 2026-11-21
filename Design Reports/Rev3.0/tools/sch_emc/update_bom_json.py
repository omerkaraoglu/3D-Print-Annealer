"""bom_ozdisan_input.json edits of the EMC-fix rounds (Özdisan product pages read 2026-11-21, USD unit prices).
    python update_bom_json.py <json> 1   # round 1: RN 100 R, U6 AHC, D6, RV3, C9, C134/C135, RV2 removed
    python update_bom_json.py <json> 2   # round 2: U5 MOC3083X, R4 0603"""
import json, sys
U = "https://www.ozdisan.com/p/"
def round1(p):
    d = json.load(open(p, encoding="utf-8"))
    items, ozd = d["bom_items"], d["ozd"]
    def item(ref):
        return next(i for i in items if i["ref"] == ref)
    # RN1-RN7 33 R -> 100 R (150 R 0402x4 not stocked)
    it = item("RN1-RN7"); it.update(val="100R x4", mpn="4D02WGJ0101TCE", desc="RES.NET.ARRAY (4D02) 0402x4 100 Ohms 5% 1/16W")
    ozd["RN1-RN7"] = dict(code="4D02WGJ0101TCE", mfr="ROYALOHM", stock=10227, moq=20,
        tiers=[[20, 0.0055], [100, 0.00519], [500, 0.00487], [1000, 0.00456], [2000, 0.00425], [5000, 0.00393], [10000, 0.00362], [50000, 0.00347]],
        url=U + "ag-ve-sira-direncler-196/royalohm-4d02wgj0101tce-467030",
        note="33 R -> 100 R (EMC fix 2026-11-21): 150 R 0402x4 (4D02WGJ0151TCE) not stocked; 100 R is the nearest stocked value in the same 0402x4 footprint")
    # U6: value aligned with the purchased part
    it = item("U6"); it.update(val="SN74AHC1G14DBVR", mpn="SN74AHC1G14DBVR")
    ozd["U6"].update(stock=23130, moq=1, tiers=[[1, 0.093], [100, 0.087], [500, 0.081], [1000, 0.075], [3000, 0.069], [15000, 0.06624]],
        url=U + "logic-kapi-ve-cevirici-entegreleri-248/texas-sn74ahc1g14dbvr-616783",
        note="value field aligned to the purchased AHC part (was SN74LVC1G14DBVR on the symbol, 2026-11-21)")
    # RV2 MOV -> D6 TVS
    items[:] = [i for i in items if i["ref"] != "RV2"]
    ozd.pop("RV2", None)
    items.append(dict(ref="D6", val="1.5KE440CA", fp="D_DO-201AD_P15.24mm_Horizontal", mpn="1.5KE440CA-TKS", mfr="THINKING",
                      desc="DIODE TVS 1.5kW 376V DO201 (DO27) Bi-Direction THT", qty=1))
    ozd["D6"] = dict(code="1.5KE440CA-TKS", mfr="THINKING", stock=1083, moq=1,
        tiers=[[1, 0.37076], [100, 0.34684], [250, 0.32292], [500, 0.299], [1200, 0.27508], [6000, 0.26408]],
        url=U + "tvs-diyotlar-386/thinking-1-5ke440ca-tks-639232",
        note="replaces RV2 (TVR10561K MOV) across the triac: 1 kV surge clamp 620 V (EMC fix 2026-11-21)")
    # RV3 = second TVR14431KSU15Y
    it = item("RV1"); it.update(ref="RV1,RV3", qty=2)
    ozd["RV1"].update(stock=14877, tiers=[[1, 0.11608], [100, 0.10859], [500, 0.1011], [1000, 0.09361], [3000, 0.08612], [15000, 0.08268]],
        url=U + "varistorler-863/thinking-tvr14431ksu15y-603701")
    # C9 = same 1 nF C0G as C130-C133
    items.append(dict(ref="C9", val="1nF 50V C0G", fp="C_0402_1005Metric", mpn="CL05C102JB5NNNC", mfr="Samsung",
                      desc="MLCC 0402 1 nF 50 V C0G (ZCD node EFT filter)", qty=1))
    ozd["C130-C133"].update(stock=2181, moq=10, tiers=[[10, 0.01579], [100, 0.01489], [500, 0.01398], [1000, 0.01308], [2000, 0.01218], [5000, 0.01128], [10000, 0.01038], [50000, 0.00996]])
    # C134, C135 = the board's 100 nF 0402
    items.append(dict(ref="C134,C135", val="100nF 50V X7R", fp="C_0402_1005Metric", mpn="CC0402KRX7R9BB104", mfr="Yageo",
                      desc="MLCC 0402 100 nF 50 V X7R (+5V-GND at the J10 via field)", qty=2))
    ozd["100nF_0402"].update(stock=4545, moq=5, tiers=[[5, 0.02321], [100, 0.02188], [500, 0.02055], [1000, 0.01923], [2000, 0.0179], [5000, 0.01658], [10000, 0.01525], [50000, 0.01464]])
    open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, indent=1, ensure_ascii=False).replace(chr(10), chr(13) + chr(10)))
    print("ok", len(items))


# ---- round 2 (2026-11-21, owner decision): U5 MOC3083X (Isocom, 800 V zero-cross, UL + VDE), R4 120 R in 0603
def round2(p):
    d = json.load(open(p, encoding="utf-8"))
    items, ozd = d["bom_items"], d["ozd"]
    it = next(i for i in items if i["ref"] == "U5")
    it.update(val="MOC3083", mpn="MOC3083X", mfr="ISOCOM", desc="IC-3083 OPTOISO 5300V TRIAC OUTPUT DIP6 (zero-cross, 800 V, VDE)")
    ozd["U5"] = dict(code="MOC3083X", mfr="Isocom", stock=930, moq=1,
        tiers=[[1, 0.57845], [30, 0.5356], [65, 0.49275], [325, 0.47304]],
        url=U + "triyak-scr-cikisli-optokuplorler-190/isocom-moc3083x-636495",
        note="MOC3052X -> MOC3083X (owner decision 2026-11-21): 800 V zero-cross; no 800 V random-phase driver stocked. X = VDE-approved version (Isocom DE93284 p.7)")
    it = next(i for i in items if i["ref"] == "R4")
    it.update(fp="R_0603_1608Metric", mpn="0603SAJ0121T5E", mfr="ROYALOHM", desc="RES.(1608) 0603 120 Ohms 5% 1/10W-S 100PPM")
    ozd["R4"] = dict(code="0603SAJ0121T5E", mfr="ROYALOHM", stock=72660, moq=200,
        tiers=[[200, 0.0009], [500, 0.00084], [1000, 0.00078], [2000, 0.00072], [5000, 0.00066], [25000, 0.00064]],
        url=U + "smt-smd-ve-cip-direncler-194/royalohm-0603saj0121t5e-341209",
        note="R4 0402 -> 0603 1/10 W (2026-11-21): TRIG held on during a burst runs it continuously, up to 49 mW at 85 C")
    open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, indent=1, ensure_ascii=False).replace(chr(10), chr(13) + chr(10)))
    print("round2 ok")


def round3(p):
    """K1 -> TE RZ03-1A4-D005 (owner decision 2026-11-21, Özdisan pages read 2026-11-21); D5 value aligned to the
    purchased 1N4148W (the item said MMSD4148T1G, the schematic and board already carry 1N4148W)."""
    d = json.load(open(p, encoding="utf-8"))
    items, ozd = d["bom_items"], d["ozd"]
    it = next(i for i in items if i["ref"] == "K1")
    it.update(val="RZ03-1A4-D005", fp="Relay_SPST_Schrack-RT1-16A-FormA_RM5mm", mpn="RZ03-1A4-D005", mfr="TE Connectivity",
              desc="Power relay 1 form A 16 A 250 VAC AgNi, 5 VDC 60 ohm 420 mW coil, 5 kV / 10 mm reinforced coil-contact")
    ozd["K1"] = dict(code="RZ03-1A4-D005", mfr="TE CONNECTIVITY", stock=110352, moq=1,
        tiers=[[1, 1.00916], [10, 0.93441], [20, 0.85966], [100, 0.82527]],
        url=U + "genel-tip-roleler-403/te-connectivity-rz03-1a4-d005-1211236",
        note="replaces HJR-3FF-S-Z-4/05VDC (SRD type, 1500 VAC coil-contact) - owner decision 2026-11-21: reinforced 5 kV / 10 mm; "
             "MPQ 20. Second source on the same footprint: Hongfa HF115FD/005-1H3A(335), stock 93,169, 0.84704 USD at 50+ "
             "(https://www.ozdisan.com/p/genel-tip-roleler-403/hongfa-hf115fd-005-1h3a335-979825)")
    it = next(i for i in items if i["ref"] == "D5")
    it.update(val="1N4148W", mpn="1N4148W_R1_00301", mfr="Panjit", desc="Switching diode 100 V 150 mA SOD-123 (1N4148W), relay coil flyback")
    ozd["D5"]["note"] = "1N4148W (Panjit), SOD-123; the symbol is Diode:MMSD4148 (same SOD-123 pinout), value 1N4148W"
    open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, indent=1, ensure_ascii=False).replace(chr(10), chr(13) + chr(10)))
    print("round3 ok")


def round4(p):
    """RV3 across the K1 contact, Thinking TVR10471KSY (owner decision 2026-11-21; Özdisan page read 2026-11-21):
    the RV1,RV3 line is split again (RV1 stays TVR14431KSU15Y)."""
    d = json.load(open(p, encoding="utf-8"))
    items, ozd = d["bom_items"], d["ozd"]
    it = next(i for i in items if i["ref"] == "RV1,RV3")
    it.update(ref="RV1", qty=1)
    items.append(dict(ref="RV3", val="TVR10471KSY", fp="RV_Disc_D12mm_W5.8mm_P7.5mm", mpn="TVR10471KSY", mfr="Thinking",
                      desc="VARISTOR DISC 10MM 470V 2.5KA 300VAC 385VDC THT: across the fan-relay K1 contact (LINE_FUSED - fan)", qty=1))
    ozd["RV3"] = dict(code="TVR10471KSY", mfr="Thinking", stock=81163, moq=1,
        tiers=[[1, 0.0825], [50, 0.07681], [100, 0.07112], [200, 0.06543], [1000, 0.06281]],
        url=U + "varistorler-863/thinking-tvr10471ksy-351283",
        note="RV3 moved across the K1 contact, 300 V ac class (16 % margin to 253 V ac); MPQ 200. No thermally protected "
             "varistor stocked at Özdisan (Littelfuse TMOV14/20 all 0)")
    open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, indent=1, ensure_ascii=False).replace(chr(10), chr(13) + chr(10)))
    print("round4 ok")


if __name__ == "__main__":
    {"1": round1, "2": round2, "3": round3, "4": round4}[sys.argv[2] if len(sys.argv) > 2 else "1"](sys.argv[1])
