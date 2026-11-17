"""Stage 5 (GF-2.1), step 1: archive the GF-2.0 release set BEFORE anything is changed (copies only).
Target Mechanical/Rev3.0_GlassFront/archive/GF-2.0/ (pattern of archive/GF-1.1/, which is not touched):
  f3d (Fusion version 18), Frame / Glass / Assembly STEP, Frame STL, Frame + Assembly reports, the GF-2.0 errata JSON,
  the master params JSON (expected sha256 7439b098...), drawings/ (full copy), the design document as
  Rev3.0_GlassFront_Design_GF-2.0.md, README.txt with the sha256 of every archived file.
Also copies the GF-2.0 Fusion renders (renders/Fusion_*.png) to renders/GF-2.0/.
Every copy is compared byte for byte with its source (filecmp, shallow=False); refuses if the target exists or the
params sha differs.   python -B gf21_archive_gf20.py"""
import filecmp
import hashlib
import os
import shutil
import sys

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront")
DST = os.path.join(MECH, "archive", "GF-2.0")
RDST = os.path.join(MECH, "renders", "GF-2.0")
DESIGN = os.path.join(REPO, "Design Reports", "Rev3.0", "Rev3.0_GlassFront_Design.md")
PARAMS_SHA = "7439b098325a09f4e31bd242b7db6372c30ae9c2bf0aa7c53e3b7003608b6082"
FILES = ["Rev3.0_GlassFront.f3d", "Rev3.0_GlassFront_Frame.step", "Rev3.0_GlassFront_Frame.stl",
         "Rev3.0_GlassFront_Glass.step", "Rev3.0_GlassFront_Assembly.step", "Rev3.0_GlassFront_Frame_report.json",
         "Rev3.0_GlassFront_Assembly_report.json", "Rev3.0_GlassFront_Frame_report_errata.json",
         "Rev3.0_GlassFront_params.json"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cp(src, dst, rows, rel):
    shutil.copy2(src, dst)
    if not filecmp.cmp(src, dst, shallow=False):
        raise SystemExit("copy differs: " + rel)
    rows.append((rel, os.path.getsize(dst), sha(dst)))


def main():
    if os.path.exists(DST) or os.path.exists(RDST):
        raise SystemExit("archive/GF-2.0 or renders/GF-2.0 exists already")
    if sha(os.path.join(MECH, "Rev3.0_GlassFront_params.json")) != PARAMS_SHA:
        raise SystemExit("params sha is not the GF-2.0 7439b098...")
    os.makedirs(os.path.join(DST, "drawings"))
    rows = []
    for f in FILES:
        cp(os.path.join(MECH, f), os.path.join(DST, f), rows, f)
    cp(DESIGN, os.path.join(DST, "Rev3.0_GlassFront_Design_GF-2.0.md"), rows, "Rev3.0_GlassFront_Design_GF-2.0.md")
    dsrc = os.path.join(MECH, "drawings")
    for root, dirs, files in os.walk(dsrc):
        rel = os.path.relpath(root, dsrc)
        tgt = os.path.join(DST, "drawings", rel) if rel != "." else os.path.join(DST, "drawings")
        os.makedirs(tgt, exist_ok=True)
        for f in sorted(files):
            r = os.path.join("drawings", rel, f) if rel != "." else os.path.join("drawings", f)
            cp(os.path.join(root, f), os.path.join(tgt, f), rows, r.replace("\\", "/"))
    os.makedirs(RDST)
    rr = []
    for f in sorted(os.listdir(os.path.join(MECH, "renders"))):
        p = os.path.join(MECH, "renders", f)
        if os.path.isfile(p) and f.startswith("Fusion_") and f.endswith(".png"):
            cp(p, os.path.join(RDST, f), rr, "renders/GF-2.0/" + f)
    dirdiff = filecmp.dircmp(dsrc, os.path.join(DST, "drawings"))
    if dirdiff.left_only or dirdiff.right_only or dirdiff.diff_files:
        raise SystemExit("drawings copy differs: %s %s %s" % (dirdiff.left_only, dirdiff.right_only, dirdiff.diff_files))
    lines = [
        "Rev3.0 glass front - GF-2.0 release set (archived 2026-11-16, before the GF-2.1 rebuild; copies only)",
        "",
        "GF-2.0 = equal 18.5 border on all four sides (glass 190.48 x 122.32), FPC tails bent back at the panel edge",
        "behind a bridge (g_bend 3.00: bridge pocket face y 122.00, nose R1.5, land break 0.3 x 45 deg, bottom land",
        "5.99), divider rib x 79.92, floors over the flange plate, S4 / R4 only (S8 and F5-F8 removed).",
        "Fusion document 'Rev3.0 GlassFront' (urn:adsk.wipprod:dm.lineage:XyXacwE-SnqsV-hz5pHg3w), version 18 = GF-2.0",
        "(v15-v17 intermediate). Not committed to git (last commit 76f5b79 = GF-1.1).",
        "Frame STEP sha256 7831768c26066dc08cd968fe16808ef4c9ae2b45bcdbc0f7efd7cb4c79ea82ad.",
        "Master params: GF-2.0 incl. the verification's post_verification_corrections / _addendum (sha256 7439b098...).",
        "",
        "Independent verification 2026-11-16: 115 PASS / 1 FAIL / 56 (as reported by the lead). Two open findings:",
        "  1. CTP tail -> bridge nose 0.946 nominal / 0.654 at the RSS panel position / 0.239 at the full worst case",
        "     (panel position 0.31 RSS / 0.60 WC after adding print-to-edge +-0.2); the 0.45 intent is not met at WC.",
        "  2. bead inner edge only 0.80 from the edge of the 0.3 x 45 land break over the bridge (rule bead_pocket_min",
        "     >= 1.0) - the FAIL.",
        "Superseded by GF-2.1 (border 19.0, larger g_bend, wider bottom land) which closes both findings.",
        "",
        "Files (sha256, bytes):"]
    for rel, n, h in rows:
        lines.append("  %s  %s  %d" % (h, rel, n))
    lines += ["", "GF-2.0 Fusion renders copied to Mechanical/Rev3.0_GlassFront/renders/GF-2.0/ (sha256, bytes):"]
    for rel, n, h in rr:
        lines.append("  %s  %s  %d" % (h, rel, n))
    lines += ["", "archive/GF-1.1/ is unchanged.", ""]
    with open(os.path.join(DST, "README.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("archived %d files + %d renders; README written" % (len(rows), len(rr)))
    for rel, n, h in rows[:12]:
        print(h, rel, n)


if __name__ == "__main__":
    main()
