"""30 - fit assembly document 'Rev3.0 Frame v2 fit assembly' (the ONE extra licence slot the owner freed):
new design document, tagged fv2/doc, saved in Oven / 'Rev3.0 OVEN CONTROLLER', then the saved frame document
'Rev3.0 Frame v2' inserted as a LINKED occurrence at the identity transform (same model frame).
Expects: frame document saved (03/12/22). Leaves: the assembly document active (the frame doc stays open)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

PROJECT_ID = "a.YnVzaW5lc3M6ZWxla3Ryb21hZyMyMDI2MDMyNTEwNjk5OTY2MDE"
FOLDER = "Rev3.0 OVEN CONTROLLER"
ASM = "Rev3.0 Frame v2 fit assembly"


def run(_context: str):
    app = adsk.core.Application.get()
    L.log("=== 30 start; docs %s" % [app.documents.item(i).name for i in range(app.documents.count)])
    proj = [app.data.dataProjects.item(i) for i in range(app.data.dataProjects.count)
            if app.data.dataProjects.item(i).id == PROJECT_ID][0]
    rf = proj.rootFolder
    folder = [rf.dataFolders.item(i) for i in range(rf.dataFolders.count) if rf.dataFolders.item(i).name == FOLDER][0]
    frame_df = None
    for i in range(folder.dataFiles.count):
        df = folder.dataFiles.item(i)
        if df.name == L.DOC_NAME:
            frame_df = df
        if df.name == ASM:
            raise RuntimeError("assembly document already exists in the folder")
    if frame_df is None:
        raise RuntimeError("frame data file not found")
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    des.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    L.mark_doc(ASM)
    L.check_doc(ASM)
    ok = doc.saveAs(ASM, folder, "fit check of the v2 frame: board STEP, Formex sheet, gasket, oven-sheet patch", "")
    L.log("30 saveAs %s -> %s" % (ok, doc.name))
    occ = des.rootComponent.occurrences.addByInsert(frame_df, adsk.core.Matrix3D.create(), True)
    L.log("30 linked frame: %s (v%s) isReferencedComponent %s" % (occ.name, frame_df.versionNumber,
                                                                  occ.isReferencedComponent))
    L.show_iso()
    print(ok, doc.name, occ.name, frame_df.versionNumber, frame_df.id)
