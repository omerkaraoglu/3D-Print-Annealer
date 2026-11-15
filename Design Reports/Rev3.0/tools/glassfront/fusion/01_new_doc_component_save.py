"""01 - the ONE new Fusion design document 'Rev3.0 GlassFront' (project Oven, folder 'Rev3.0 OVEN CONTROLLER'):
parametric, mm, attribute guard gf/doc = 'Rev3.0 GlassFront', component 'Frame GF' under the root, and the first
saveAs (so a document-limit failure shows up before any modelling work).
Also probes which expression functions Fusion accepts (max / min / floor / abs / sqrt, argument separator) for the
level-snap rule; the probe is read-only (UnitsManager.isValidExpression).

Expects: no document named 'Rev3.0 GlassFront' in the folder (refuses otherwise). Touches no other document.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

PROBES = ["max(1 mm; 2 mm)", "max(1 mm, 2 mm)", "min(1; 2)", "min(1, 2)", "floor(2.7)", "abs(-1 mm)",
          "sqrt(( 3 mm ) ^ 2 + ( 4 mm ) ^ 2)", "floor(abs(-0.1 mm) / 0.5 mm)", "cos(45 deg)", "tan(1 deg)"]


def run(_context: str):
    app = adsk.core.Application.get()
    L.log("=== 01 start; open docs before: %s" % [app.documents.item(i).name for i in range(app.documents.count)])
    folder = L.gf_folder()
    for j in range(folder.dataFiles.count):
        if folder.dataFiles.item(j).name == L.DOC_NAME:
            raise RuntimeError("a document named %r already exists in %s - refusing" % (L.DOC_NAME, L.FOLDER))
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    des.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    des.attributes.add(L.TAG_GROUP, L.TAG_NAME, L.DOC_NAME)
    L.check_doc()
    o = des.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    o.component.name = L.COMP_NAME
    um = des.unitsManager
    res = []
    for e in PROBES:
        ok = um.isValidExpression(e, "mm") or um.isValidExpression(e, "")
        val = None
        if um.isValidExpression(e, "mm"):
            val = um.evaluateExpression(e, "mm") * 10.0
        elif um.isValidExpression(e, ""):
            val = um.evaluateExpression(e, "")
        res.append((e, ok, val))
    L.log("01 expression probes: %s" % res)
    ok = doc.saveAs(L.DOC_NAME, folder, "GF-1.0 frame: empty document, component 'Frame GF'", "")
    df = doc.dataFile
    L.log("01 saveAs returned %s; doc '%s' isSaved %s id %s version %s" % (
        ok, doc.name, doc.isSaved, df.id if df else None, df.versionNumber if df else None))
    print("saveAs", ok, doc.name, df.id if df else None, df.versionNumber if df else None)
    print(res)
