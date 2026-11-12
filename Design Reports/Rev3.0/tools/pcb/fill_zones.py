"""Fill all zones and save (so the delivered board carries its fills and DRC without --refill-zones is valid).
Pass 4: verify that the copper zones really got a fill (one delivery run saved an unfilled board) and retry once."""
import sys, pcbnew
src, dst = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
b = pcbnew.LoadBoard(src)
def filled_count():
    return sum(1 for z in b.Zones() if not z.GetIsRuleArea() and z.IsFilled() and z.GetFilledPolysList(z.GetLayerSet().Seq()[0]).OutlineCount() > 0)
copper = sum(1 for z in b.Zones() if not z.GetIsRuleArea())
for attempt in (1, 2):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    if filled_count() == copper: break
    print("fill attempt %d: %d of %d copper zones filled, retrying" % (attempt, filled_count(), copper))
assert filled_count() == copper, "zone fill failed: %d of %d copper zones filled" % (filled_count(), copper)
pcbnew.SaveBoard(dst, b); print("filled", len(b.Zones()), "zones (%d copper) ->" % copper, dst)
