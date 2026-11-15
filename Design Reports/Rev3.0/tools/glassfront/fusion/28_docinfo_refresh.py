"""28 - READ-ONLY: refresh the document version in scratchpad docinfo.json after the cloud upload of the final save
has finished (27 read the dataFile while the upload was still running and got the previous version number)."""
import importlib
import json
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    doc = L.app().activeDocument
    df = doc.dataFile
    p = os.path.join(L.SCR, "docinfo.json")
    info = json.load(open(p, encoding="utf-8"))
    info["version"] = df.versionNumber
    info["version_note"] = "read by 28 after the upload; isModified %s" % doc.isModified
    json.dump(info, open(p, "w", encoding="utf-8"), indent=1)
    print(df.id, df.versionNumber, doc.isModified)
