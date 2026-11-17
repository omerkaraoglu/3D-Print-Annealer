"""GF-2.1 master params: second addendum - state claims reworded so the master stays true whatever later work does.

  <venv>\\Scripts\\python.exe -B params_gf21_addendum2.py            (writes the master + the numeric diff)
  <venv>\\Scripts\\python.exe -B params_gf21_addendum2.py --dry-run  (preview only)

The drawings and the design document cite the master's sha256; a statement in the master about their current state (or
any other state that later work changes) would force an edit and a new sha. Reworded (text only):
  * to_be_reverified_at_GF-2.1: the drawings and design-document entries (where their revision / params sha are recorded,
    not covered by the independent verification, GF-2.0 issues archived) and the 'design document tables are not updated by
    this' remark (-> 'this verification does not edit the design document');
  * to_be_reverified_at_GF-2.0: the DONE entry that said the drawings folder 'holds the GF-2.0 set' (-> what was generated,
    from which params sha, where the set is archived) and the same 'not updated by this' remark;
  * status: 'still gated by the real-panel fold test' (false once the test is done) -> 'subject to the real-panel fold test'.
Discipline: refuses a second run (change_log KEY), byte-exact writer check, previous master saved to
out/params_before_GF21_addendum2.json, numeric diff to out/params_GF21_addendum2_numeric_diff.json, assertion that no numeric
value changes (only the change-log entry adds text).
"""
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon as C
from params_gf20_post_verification_fix import sha, write_master, numeric_leaves

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PARAMS = C.GF_PARAMS
PARAMS_SHA_IN = "a019e9ae13e83f8e95297790167ca9a85ee35901a9493d249c3bf8baccaab8b5"
DATE = "2026-11-17"
KEY = "independent_verification_GF-2.1_addendum2_%s" % DATE
BACKUP = os.path.join(OUT, "params_before_GF21_addendum2.json")
DIFF = os.path.join(OUT, "params_GF21_addendum2_numeric_diff.json")


def main(argv):
    dry = "--dry-run" in argv
    raw = json.load(open(PARAMS, encoding="utf8"))
    if KEY in raw.get("change_log", {}):
        print("already applied (change_log has %s) - restore %s first to re-run" % (KEY, BACKUP))
        return 1
    sha_old = sha(PARAMS)
    assert sha_old == PARAMS_SHA_IN, "the master is not the file this addendum was written for (%s)" % sha_old
    probe = os.path.join(OUT, "_params_format_probe.json")
    write_master(raw, probe)
    same = open(probe, "rb").read() == open(PARAMS, "rb").read()
    os.remove(probe)
    assert same, "write_master does not reproduce the master format - nothing written"
    before = json.loads(json.dumps(raw))
    arch = os.path.join(C.GF_DIR, "archive", "GF-2.0", "drawings", "drawings_report.json")
    rep20 = json.load(open(arch, encoding="utf8"))
    assert rep20["master"]["revision"] == "GF-2.0"
    changes = []

    def swap(lst_key, i, old_exact, new, why):
        lst = raw[lst_key]
        assert lst[i] == old_exact, (lst_key, i, lst[i])
        lst[i] = new
        changes.append({"path": "%s[%d]" % (lst_key, i), "old": old_exact, "new": new, "reason": why})

    t21 = raw["to_be_reverified_at_GF-2.1"]
    swap("to_be_reverified_at_GF-2.1", 1, "drawings GF-D01..D50 (Mechanical/Rev3.0_GlassFront/drawings hold the GF-2.0 set; archived in archive/GF-2.0)",
         "drawings GF-D01..D50: the revision and the params sha256 a set was generated from are recorded in "
         "Mechanical/Rev3.0_GlassFront/drawings/drawings_report.json and on each sheet; the drawings are not covered by the independent "
         "verification; the GF-2.0 issue is archived in archive/GF-2.0/drawings/ (GF-1.1 in archive/GF-1.1/drawings/)",
         "state claim that regeneration would falsify")
    swap("to_be_reverified_at_GF-2.1", 2, "design document Rev3.0_GlassFront_Design.md (GF-2.0; archived as archive/GF-2.0/Rev3.0_GlassFront_Design_GF-2.0.md)",
         "design document Rev3.0_GlassFront_Design.md: its issue and the params sha256 it was written from are stated in its header; "
         "the document is not covered by the independent verification; the GF-2.0 issue is archived as "
         "archive/GF-2.0/Rev3.0_GlassFront_Design_GF-2.0.md",
         "state claim that regeneration would falsify")
    i3 = 3
    assert t21[i3].endswith("; the design document tables are not updated by this")
    swap("to_be_reverified_at_GF-2.1", i3, t21[i3], t21[i3][:-len("; the design document tables are not updated by this")] +
         "; this verification does not edit the design document", "reads as a state of the document")
    t20 = raw["to_be_reverified_at_GF-2.0"]
    i4 = 4
    assert t20[i4].endswith("; the design document 7.4 tables are not updated by this")
    swap("to_be_reverified_at_GF-2.0", i4, t20[i4], t20[i4][:-len("; the design document 7.4 tables are not updated by this")] +
         "; this verification does not edit the design document", "reads as a state of the document")
    i12 = 12
    old12 = t20[i12]
    assert "the folder holds the GF-2.0 set" in old12
    head = old12.split(" -> ")[0]
    assert "(Mechanical/Rev3.0_GlassFront/drawings are GF-1.1)" in head
    head = head.replace("(Mechanical/Rev3.0_GlassFront/drawings are GF-1.1)", "(at the start of GF-2.0 the drawings folder held the GF-1.1 set)")
    swap("to_be_reverified_at_GF-2.0", i12, old12,
         "%s -> the GF-2.0 set was regenerated from the corrected GF-2.0 master and self-checked; the issued GF-2.0 set is archived in "
         "archive/GF-2.0/drawings/ (generated %s from params sha256 %s, see its drawings_report.json); the GF-1.1 set is archived in "
         "archive/GF-1.1/drawings/" % (head, rep20["generated"].replace("T", " "), rep20["master"]["sha256"][:16]),
         "'the folder holds the GF-2.0 set' is falsified by any regeneration")
    old = raw["status"]
    assert old.endswith("border 19.0 / g_bend 3.23 still gated by the real-panel fold test (fold_test)")
    raw["status"] = old.replace("still gated by the real-panel fold test (fold_test)",
                                "subject to the real-panel fold test (fold_test: rule, pass and fail branch)")
    changes.append({"path": "status", "old": old, "new": raw["status"], "reason": "'still gated' is falsified once the test is done"})
    raw["change_log"][KEY] = {
        "date": DATE, "by": "independent verification agent (tools/glassfront/verify/params_gf21_addendum2.py)",
        "summary": "text only: statements about the state of the drawings, the design document and the fold test reworded so they stay "
                   "true whatever later work does (where revisions / shas are recorded, what is archived, what the verification "
                   "covers). No numeric value changed; revision stays GF-2.1",
        "params_sha256_before": sha_old, "changes": changes}
    a, b = numeric_leaves(before), numeric_leaves(json.loads(json.dumps(raw)))
    diff = {"changed": {k: [a[k], b[k]] for k in sorted(set(a) & set(b)) if a[k] != b[k]},
            "removed": {k: a[k] for k in sorted(set(a) - set(b))},
            "added": {k: b[k] for k in sorted(set(b) - set(a))}, "count_before": len(a), "count_after": len(b)}
    assert not diff["changed"] and not diff["removed"] and all(k.startswith("change_log.") for k in diff["added"]), diff
    for c in changes:
        print("CHANGED %s\n   old: %s\n   new: %s" % (c["path"], c["old"], c["new"]))
    if dry:
        print("dry run - nothing written")
        return 0
    if not os.path.exists(BACKUP):
        shutil.copyfile(PARAMS, BACKUP)
    write_master(raw, PARAMS)
    sha_new = sha(PARAMS)
    diff["params_sha256_before"], diff["params_sha256_after"] = sha_old, sha_new
    C.dump(diff, DIFF)
    print("params sha256 %s -> %s" % (sha_old, sha_new))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
