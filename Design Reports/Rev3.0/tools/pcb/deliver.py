"""Deliver the routed board into the project: board file, netlist, BOM, CPL, DRC (with schematic parity), tools copy."""
import os, sys, shutil, subprocess, json
SCR = os.path.dirname(os.path.abspath(__file__))
PRJ = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer"
REP = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0"
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
SCH = os.path.join(PRJ, "3dFilamentDryer.kicad_sch")
PCB = os.path.join(PRJ, "3dFilamentDryer.kicad_pcb")
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCR, "rev3_final.kicad_pcb")
only = sys.argv[2] if len(sys.argv) > 2 else "all"

def run(*a):
    r = subprocess.run(list(a), capture_output=True, text=True)
    if r.returncode: print("FAILED", a[:3], r.stdout[-800:], r.stderr[-800:])
    return r

if only in ("all", "board"):
    shutil.copy(src, PCB); print("board ->", PCB)
    # fill the zones in place: under the project name pcbnew loads the .kicad_pro/.kicad_dru, so the fills honour the custom rules
    run(r"C:/Program Files/KiCad/10.0/bin/python.exe", os.path.join(SCR, "fill_zones.py"), PCB); print("zones filled")
    out = os.path.join(SCR, "final_norefill_drc.json")
    run(CLI, "pcb", "drc", "--severity-error", "--all-track-errors", "--format", "json", "-o", out, PCB)
    d = json.load(open(out, encoding="utf-8"))
    print("DRC as saved (no refill): violations", len(d["violations"]), "unconnected", len(d["unconnected_items"]))
if only in ("all", "net"):
    run(CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", os.path.join(REP, "Rev3.0_netlist.net"), SCH); print("netlist")
if only in ("all", "bom"):
    run(CLI, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,MPN,Manufacturer,Datasheet,Description,${QUANTITY}",
        "--labels", "Reference,Value,Footprint,MPN,Manufacturer,Ozdisan/Datasheet,Description,Qty",
        "--group-by", "Value,Footprint,MPN", "--exclude-dnp", "-o", os.path.join(REP, "Rev3.0_BOM.csv"), SCH); print("bom")
if only in ("all", "cpl"):
    run(CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--smd-only" if False else "--exclude-dnp",
        "-o", os.path.join(REP, "Rev3.0_CPL.csv"), PCB); print("cpl")
if only in ("all", "drc"):
    out = os.path.join(SCR, "final_project_drc.json")
    run(CLI, "pcb", "drc", "--schematic-parity", "--severity-error", "--format", "json", "-o", out, PCB)
    d = json.load(open(out, encoding="utf-8"))
    print("DRC violations", len(d["violations"]), "unconnected", len(d["unconnected_items"]), "parity", len(d.get("schematic_parity", [])))
    for v in (d["violations"] + d["unconnected_items"] + d.get("schematic_parity", []))[:30]:
        print("  ", v["type"], v["description"][:120])
if only in ("all", "tools"):
    T = os.path.join(REP, "tools", "pcb"); os.makedirs(T, exist_ok=True)
    for f in ["sx.py", "gen_footprints.py", "netclasses.py", "placement.py", "build_board.py", "export_geom.py", "handroute.py",
              "disp_lib.py", "route_display.py", "route_signals.py", "route_power.py", "route_mains.py", "merge_final.py",
              "import_tracks.py", "finalize_board.py", "drc_run.py", "render.py", "crop.py", "overlap.py", "metrics.py", "netdump.py",
              "mains_placement_proposal.py", "mains_propcheck.py",
              "gen_heatsink_fp.py", "sch_pass2.py", "extract_sym.py", "fill_zones.py", "deliver.py",
              "placement_override_display.py", "placement_override_power.py", "placement_override_mains.py", "AGENT_BRIEF.md", "PASS2_BRIEF.md",
              "mains2_check.py", "dump_crt.py", "d2_lanes.py", "display_lane_decision.md", "sch_pass3.py", "in1_web_check.py", "gen_l40_fp.py", "disp_web.py", "web_json.py"]:
        p = os.path.join(SCR, f)
        if os.path.exists(p): shutil.copy(p, T)
        else: print("tools: missing", f)
    for f in ["router_core.py", "route_all.py"]:
        p = os.path.join(T, f)
        if os.path.exists(p): os.remove(p); print("tools: removed", f)
    print("tools copied")
