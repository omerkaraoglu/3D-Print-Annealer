"""Fill all zones and save (so the delivered board carries its fills and DRC without --refill-zones is valid)."""
import sys, pcbnew
src, dst = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
b = pcbnew.LoadBoard(src)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(dst, b); print("filled", len(b.Zones()), "zones ->", dst)
