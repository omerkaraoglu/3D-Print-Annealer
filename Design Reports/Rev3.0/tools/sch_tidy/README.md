# sch_tidy — Rev3.0 schematic tidy round (2026-11-13)

Redraws the five Rev3.0 sheets in the house style (`schematic-style-rulebook.md`) and applies the Özdisan part
substitutions. Connectivity is kept identical to the baseline netlist (the PCB, layout pass 4, is not touched).

## How it works
- `core.py` — sheet model on top of `../sexp.py`: embedded lib symbols, pin positions (rotation then mirror, KiCad
  semantics, validated by `model_check.py` reproducing the baseline netlist from the baseline drawings), the baseline
  netlist as the target (pin → net, how each net is named: power symbol / global label / local label / auto / NC).
- `builder.py` — keeps every symbol instance (UUID, reference, instance path, pins), drops all drawn items and
  regenerates wires, labels, power symbols, junctions (≥ 3 items), no-connects, notes, frames from a layout script.
  Helpers never name nets: `lab("R6.2")` draws the label of R6.2's baseline net, `pw("C5.2")` its power symbol.
  `finish()` splits wires at T-points, adds junctions, NC flags, and checks the drawing against the baseline
  (shorts, wrong / missing names, open pins, wires through bodies, dangling ends).
- `lay_root.py`, `lay_display.py`, `lay_thermo.py`, `lay_power.py`, `lay_filter.py` — one layout script per sheet
  (groups with their own origin, notes, crop regions).
- `fields.py` — values / MPN / Manufacturer / Datasheet from `../bom_ozdisan_input.json` (ALIAS as in
  `make_bom_ozdisan.py`); `bomitem.py` — `Rev3:BOM_Item` (pinless dashed box, in BOM, not on board) for TC1;
  `libfix.py` — the trivial lib_symbol_mismatch fixes (J2, J10, J11).
- `tidy.py <out_dir> <Rev3.kicad_sym> [sheets]` — builds from the untouched copies in
  `<scratch>/sch_tidy_backup/` (never from the files it overwrites); `TIDY_OUT` sets where the region file goes.
- `checks.py <project_dir> netlist erc pdf collide render bom ids` — netlist compare vs `baseline.xml`, ERC vs the
  baseline ERC, PDF export, PyMuPDF text-collision checker (strict 0 mm + near-miss 0.5 mm, title block and NC
  crosses excluded, symbol-inherent pin texts and a label on its own wire excused), 60 dpi pages + 150 dpi group
  crops, BOM export grouped by MPN vs `Rev3.0_BOM_Ozdisan_100pcs.csv`, UUID / path / reference / #PWR uniqueness.
- `dump_pins.py`, `flag_nets.py`, `model_check.py` — analysis helpers used while designing the layouts.

## Re-run
```
set TIDY_OUT=<scratch>\sch_tidy_real_out
python -I tidy.py "<proj>\KiCad\3dFilamentDryer" "<proj>\KiCad\ComponentsLibrary\User Created\Rev3\Rev3.kicad_sym"
python -I checks.py "<proj>\KiCad\3dFilamentDryer" netlist erc pdf collide render bom ids
```
The run is repeatable (same drawing, new UUIDs for the drawn items only). Paths to the scratch area are in `core.py`.

## Round 2 (2026-11-13)
- `core.RENAME`: the six approved renames of the programmer / auto-boot nets (Net-(Q3-C) -> /EN, Net-(Q2-C) -> /IO0,
  Net-(J2-Pin_2) -> /RTS, Net-(J2-Pin_3) -> /DTR, Net-(J2-Pin_4) -> /TXD0, Net-(J2-Pin_5) -> /RXD0); `tidy.py` builds
  against the renamed target, `checks.py netlist` applies the same map to the baseline and lists the renames.
- `fields.OVERRIDE`: R4 120 R (0402WGJ0121TCE) and R9 180 R (0603SAJ0181T5E) over the JSON; `checks.EXPECTED_CHANGE`.
- `libfix.fix_ssd1963_*`: Rev3:SSD1963QL9 top supply pins moved inward (library and embedded copy);
  `checks.STRICT_SYMBOLS = {"U10"}` stops excusing that symbol's own pin-name overlaps.
