"""03 - first save: create folder 'Rev3.0 OVEN CONTROLLER' in the root of project 'Oven' (if missing) and
doc.saveAs('Rev3.0 Frame v2', folder, 'v2 frame, continuous flange', '').

Expects: the active document is the untitled v2 design (fv2/doc tag), body + flange present (02).
Leaves: saved document (or logs the exact error; the caller then falls back to .f3d archives).
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

PROJECT_ID = "a.YnVzaW5lc3M6ZWxla3Ryb21hZyMyMDI2MDMyNTEwNjk5OTY2MDE"
FOLDER = "Rev3.0 OVEN CONTROLLER"


def run(_context: str):
    app = adsk.core.Application.get()
    L.check_doc()
    proj = None
    for i in range(app.data.dataProjects.count):
        p = app.data.dataProjects.item(i)
        if p.id == PROJECT_ID:
            proj = p
    if proj is None:
        raise RuntimeError("project Oven not found")
    rf = proj.rootFolder
    folder = None
    for i in range(rf.dataFolders.count):
        if rf.dataFolders.item(i).name == FOLDER:
            folder = rf.dataFolders.item(i)
    if folder is None:
        folder = rf.dataFolders.add(FOLDER)
        L.log("03 folder created: %s %s" % (folder.name, folder.id))
    doc = app.activeDocument
    ok = doc.saveAs(L.DOC_NAME, folder, "v2 frame, continuous flange", "")
    L.log("03 saveAs returned %s; doc name now '%s', isSaved %s" % (ok, doc.name, doc.isSaved))
    print("saveAs", ok, doc.name, folder.id)
