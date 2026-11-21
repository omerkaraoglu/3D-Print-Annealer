"""Fill the work area (core.SCRATCH) with the pre-round schematic and the baseline it is checked against.

    python -I prepare_base.py

- the five sheets, sym/fp-lib tables and .kicad_pro from git commit core.BASE_COMMIT -> <work>/base/3dFilamentDryer
  (sheets converted to CRLF, as in the working tree)
- the Rev3 library (symbols + footprints) from the working tree -> <work>/base/ComponentsLibrary/User Created/Rev3
  (the tables use ${KIPRJMOD}/../ComponentsLibrary, so the copy keeps them valid)
- kicad-cli: baseline.xml (netlist, kicadxml) and erc.json in the base project folder
Then:  EMC_ROUND=1 -> emc_round.py reproduces the files written on 2026-11-21 (phase 1);
       EMC_ROUND=2 (default) adds U5 MOC3083 / R4 0603 (needs the round-2 bom_ozdisan_input.json; EMC_JSON overrides the path).
The work area defaults to <temp>/readark_sch_emc (outside the repository); SCH_EMC_WORK overrides it."""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import REPO, SCRATCH, BASELINE, BASE_COMMIT, KICAD_CLI, FILES  # noqa: E402

CR, LF = bytes([13]), bytes([10])

os.makedirs(BASELINE, exist_ok=True)
for f in list(FILES.values()) + ["sym-lib-table", "fp-lib-table", "3dFilamentDryer.kicad_pro"]:
    data = subprocess.run(["git", "-C", REPO, "show", "%s:KiCad/3dFilamentDryer/%s" % (BASE_COMMIT, f)],
                          capture_output=True, check=True).stdout
    if f.endswith(".kicad_sch"):
        data = data.replace(CR + LF, LF).replace(LF, CR + LF)
    with open(os.path.join(BASELINE, f), "wb") as fh:
        fh.write(data)
lib_src = os.path.join(REPO, "KiCad", "ComponentsLibrary", "User Created", "Rev3")
lib_dst = os.path.join(SCRATCH, "base", "ComponentsLibrary", "User Created", "Rev3")
os.makedirs(lib_dst, exist_ok=True)
shutil.copy(os.path.join(lib_src, "Rev3.kicad_sym"), lib_dst)
shutil.copytree(os.path.join(lib_src, "Rev3.pretty"), os.path.join(lib_dst, "Rev3.pretty"), dirs_exist_ok=True)
sch = os.path.join(BASELINE, FILES["root"])
subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", os.path.join(BASELINE, "baseline.xml"), sch], check=True)
subprocess.run([KICAD_CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", os.path.join(BASELINE, "erc.json"), sch], check=True)
print("base ready in", BASELINE)
