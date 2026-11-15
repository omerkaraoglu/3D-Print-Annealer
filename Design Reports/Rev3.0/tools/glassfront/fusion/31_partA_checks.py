"""31 - stage 2, Part A: re-run the stage-1 checks on the fixed frame by executing the stage-1 scripts verbatim with
their TAG globals overridden (the stage-1 dumps were copied to %TEMP%\\rev3_glassfront\\stage1_dumps first):
  20_scan              -> scan_partA.json      (draft / undercut, slivers, thin strips, unfilleted roots)
  21_sections_dump     -> sections_gf.json     (plan sections for gf_offline_checks.py thin)
  23_above_z0_points   -> above_z0.json        (gf_offline_checks.py abovez)
  22_carryover_vs_v2   -> carry_measure.json / carry_sections.json (imports the v2 STEP into a temporary occurrence
                          and deletes it again, as in stage 1)
Run 90_flex_test separately (32_partA_flex.py). Offline afterwards: python gf_offline_checks.py thin / abovez / carry.
"""
import os

GF = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion"
RUN = [("20_scan.py", {"TAG": "partA"}), ("21_sections_dump.py", {"TAG": "gf"}), ("23_above_z0_points.py", {}),
       ("22_carryover_vs_v2_step.py", {})]


def run(_context: str):
    for name, over in RUN:
        p = os.path.join(GF, name)
        ns = {"__name__": "gf_script", "__file__": p}
        exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
        ns.update(over)
        print("---", name)
        ns["run"](_context)
