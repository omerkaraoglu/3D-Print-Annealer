"""Paths and board constants shared by the silk / refdes scripts (Rev3.0 READARK filament dryer board).

The scripts live in Design Reports/Rev3.0/tools/silk_refdes/; the working tree (orig/, stage/, work/, drc/, render/)
lives in ROOT, by default the session scratchpad, or the directory named by the environment variable SILK_ROOT.
orig/ holds the untouched board (+ .kicad_pro from HEAD + .kicad_dru); it is never written.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SILK_ROOT", r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142"
                      r"\43bde93b-5fea-45c5-b44e-584beb51a617\scratchpad")
NAME = "3dFilamentDryer"
ORIG_DIR = os.path.join(ROOT, "orig")
STAGE_DIR = os.path.join(ROOT, "stage")
WORK = os.path.join(ROOT, "work")
ORIG = os.path.join(ORIG_DIR, NAME + ".kicad_pcb")
STAGE = os.path.join(STAGE_DIR, NAME + ".kicad_pcb")
GEOM = os.path.join(WORK, "geom.json")
PLACEMENT = os.path.join(WORK, "placement.json")
LABELS = os.path.join(WORK, "labels.json")
KPY = r"C:\Program Files\KiCad\10.0\bin\python.exe"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
# board outline incl. the nine screw ears: 10.65..194.35 x 9.65..128.35 (absolute mm); raster window 0.2 mm larger
WINDOW = (10.45, 9.45, 194.55, 128.55)
# board-only mechanical footprints: reference stays hidden, no designator placed
SKIP = {"H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "DS1"}
