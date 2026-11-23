"""Stage 5: regenerate the Rev3.0 report outputs from a COPY of the saved project (kicad-cli; same commands and options
as tools/pcb/deliver.py and the 2026-11-21 round, checked to reproduce the committed files byte for byte apart from
dates / source paths before stage 5):
  Rev3.0_netlist.net  (kicadsexpr)     Rev3.0_BOM.csv  (grouped by Value, Footprint, MPN; DNP excluded)
  Rev3.0_CPL.csv      (both sides, mm, DNP excluded)     Rev3.0_ERC.rpt (all severities)     Rev3.0_Schematic.pdf
Rev3.0_BOM_Ozdisan_100pcs.* are NOT touched (owner / main session).
    python stage5_outputs.py <project_copy_dir> <out_dir>"""
import os
import subprocess
import sys

CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
proj, out = sys.argv[1:3]
SCH = os.path.join(proj, "3dFilamentDryer.kicad_sch")
PCB = os.path.join(proj, "3dFilamentDryer.kicad_pcb")
O = lambda n: os.path.join(out, n)
JOBS = [
    ["sch", "export", "netlist", "--format", "kicadsexpr", "-o", O("Rev3.0_netlist.net"), SCH],
    ["sch", "export", "bom", "--fields", "Reference,Value,Footprint,MPN,Manufacturer,Datasheet,Description,${QUANTITY}",
     "--labels", "Reference,Value,Footprint,MPN,Manufacturer,Ozdisan/Datasheet,Description,Qty",
     "--group-by", "Value,Footprint,MPN", "--exclude-dnp", "-o", O("Rev3.0_BOM.csv"), SCH],
    ["pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--exclude-dnp", "-o", O("Rev3.0_CPL.csv"), PCB],
    ["sch", "erc", "--severity-all", "--format", "report", "-o", O("Rev3.0_ERC.rpt"), SCH],
    ["sch", "export", "pdf", "-o", O("Rev3.0_Schematic.pdf"), SCH],
]
for j in JOBS:
    r = subprocess.run([CLI] + j, capture_output=True, text=True)
    print(" ".join(j[:3]), "->", os.path.basename(j[j.index("-o") + 1]), "rc", r.returncode, (r.stdout.strip().splitlines() or [""])[-1])
    if r.returncode not in (0, 5):          # erc returns 5 when violations exist with --exit-code-violations only
        raise SystemExit(r.stderr)
