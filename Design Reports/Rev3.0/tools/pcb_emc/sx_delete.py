"""Delete top-level board items (footprint, segment, arc, via, zone, ...) by UUID from a saved .kicad_pcb, keeping
the rest of the file byte-identical.  delete_items(path, uuids) -> number of items removed."""
import re


def _top_items(txt):
    """yield (start, end) of every depth-1 item of (kicad_pcb ...)"""
    depth = 0; start = None; i = 0; n = len(txt); instr = False
    while i < n:
        c = txt[i]
        if instr:
            if c == "\\": i += 2; continue
            if c == '"': instr = False
        elif c == '"': instr = True
        elif c == "(":
            depth += 1
            if depth == 2: start = i
        elif c == ")":
            if depth == 2:
                yield start, i + 1
            depth -= 1
        i += 1


def delete_items(path, uuids):
    txt = open(path, encoding="utf-8", newline="").read()
    want = set(uuids)
    cut = []
    for a, e in _top_items(txt):
        head = txt[a:a + 4000]
        m = re.search(r'\(uuid "([0-9a-f-]+)"\)', txt[a:e])
        # the item's own uuid: first (uuid ...) at depth 1 inside the item (footprints carry it near the top)
        if m and m.group(1) in want:
            cut.append((a, e))
    for a, e in reversed(cut):
        # remove the item and the whitespace/newline before it
        s = a
        while s > 0 and txt[s - 1] in " \t":
            s -= 1
        if s > 0 and txt[s - 1] == "\n":
            s -= 1
            if s > 0 and txt[s - 1] == "\r":
                s -= 1
        txt = txt[:s] + txt[e:]
    open(path, "w", encoding="utf-8", newline="").write(txt)
    return len(cut)
