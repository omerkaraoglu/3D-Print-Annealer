"""Write the checked round-2 result (U5 MOC3083, R4 0603, rule files for the renamed nets) into the project.

    python -I apply_round2.py <staged_dir>

<staged_dir> holds KiCad/3dFilamentDryer.kicad_sch and the regenerated Design Reports/Rev3.0 files (made by the
2026-11-21 round, checked: netlist vs phase 1 = U5/R4 fields only, ERC 1, collisions 0/0, BOM 0 mismatches).
Refuses to run while a ~*.lck file exists in KiCad/3dFilamentDryer or a kicad process runs; refuses if the root /
Display sheets are not the phase-1 files the staged copy was built from. Backs up every file it overwrites into
<staged_dir>/overwritten_<time>/. The netclass pattern and DRC rule edits are applied to the *current* .kicad_pro /
.kicad_dru (an open KiCad may have rewritten them), not copied."""
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PRJ = os.path.join(REPO, "KiCad", "3dFilamentDryer")
REP = os.path.join(REPO, "Design Reports", "Rev3.0")
PHASE1_MD5 = {"3dFilamentDryer.kicad_sch": "0270d8198ea82cf3284b8a05fad02560", "Rev3_Display.kicad_sch": "1140aa0e61d1be5eea314c33c930a127"}


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main(staged):
    locks = [f for f in os.listdir(PRJ) if f.startswith("~") and f.endswith(".lck")]
    procs = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    if locks or "kicad.exe" in procs or "eeschema" in procs or "pcbnew" in procs:
        sys.exit("KiCad is open (locks %s): nothing written" % locks)
    for f, h in PHASE1_MD5.items():
        if md5(os.path.join(PRJ, f)) != h:
            sys.exit("%s changed since phase 1: nothing written, rebuild the round" % f)
    bk = os.path.join(staged, "overwritten_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(bk)
    def put(src, dst):
        if os.path.exists(dst):
            shutil.copy(dst, os.path.join(bk, os.path.basename(dst)))
        shutil.copy(src, dst)
        print("written", dst)
    put(os.path.join(staged, "KiCad", "3dFilamentDryer.kicad_sch"), os.path.join(PRJ, "3dFilamentDryer.kicad_sch"))
    # rule files: add the renamed nets next to the old auto names (old names kept until the PCB is updated)
    p = os.path.join(PRJ, "3dFilamentDryer.kicad_pro")
    s = open(p, encoding="utf-8", newline="").read()
    if '"pattern": "/Q1_A1"' not in s:
        nl = "\r\n" if "\r\n" in s else "\n"
        old = '      {' + nl + '        "netclass": "MainsHeater",' + nl + '        "pattern": "Net-(Q1-A1)"' + nl + '      },'
        assert s.count(old) == 1, "MainsHeater Net-(Q1-A1) pattern not found once"
        s = s.replace(old, old + nl + '      {' + nl + '        "netclass": "MainsHeater",' + nl + '        "pattern": "/Q1_A1"' + nl + '      },')
        shutil.copy(p, os.path.join(bk, os.path.basename(p)))
        open(p, "w", encoding="utf-8", newline="").write(s)
        print("netclass pattern /Q1_A1 added:", p)
    d = os.path.join(PRJ, "3dFilamentDryer.kicad_dru")
    t = open(d, encoding="utf-8", newline="").read()
    if "/Q1_A1" not in t:
        shutil.copy(d, os.path.join(bk, os.path.basename(d)))
        t = re.sub(r"([AB])\.NetName == 'Net-\(Q1-A1\)'", r"\1.NetName == 'Net-(Q1-A1)' || \1.NetName == '/Q1_A1'", t)
        t = re.sub(r"([AB])\.NetName == 'Net-\(R8-Pad2\)'", r"\1.NetName == 'Net-(R8-Pad2)' || \1.NetName == '/ZCD_RAW'", t)
        open(d, "w", encoding="utf-8", newline="").write(t)
        print("DRC rules: /Q1_A1 and /ZCD_RAW added:", d)
    for f in ("Rev3.0_netlist.net", "Rev3.0_Schematic.pdf", "Rev3.0_ERC.rpt", "Rev3.0_BOM.csv",
              "Rev3.0_BOM_Ozdisan_100pcs.csv", "Rev3.0_BOM_Ozdisan_100pcs.md"):
        put(os.path.join(staged, "Design Reports", "Rev3.0", f), os.path.join(REP, f))
    put(os.path.join(staged, "Design Reports", "Rev3.0", "tools", "bom_ozdisan_input.json"), os.path.join(REP, "tools", "bom_ozdisan_input.json"))
    print("done; backups in", bk)


if __name__ == "__main__":
    main(sys.argv[1])
