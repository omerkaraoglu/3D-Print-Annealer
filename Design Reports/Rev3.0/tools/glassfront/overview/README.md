# GF-2.1 visual overview PDF — builder

Builds `Design Reports/Rev3.0/Rev3.0_GlassFront_Overview.pdf` (A4 landscape) for the owner and a non-engineer
partner: what the glass front is, what every piece is, how it is made.

## One command

```
python -B make_overview.py          # system Python (3.14) with reportlab, PyMuPDF, numpy, Pillow, matplotlib
python -B audit_overview.py         # self-check, writes audit_report.json (add --png-dir DIR for the page images)
```

The renders it uses are already in `Mechanical/Rev3.0_GlassFront/renders/overview/`. To regenerate them (only
needed if the assembly STEP changes):

```
<cq-venv>\Scripts\python.exe -B render_overview.py      # CadQuery 2.8 + OCP + VTK 9 (the verify/ venv works)
```

## Files

| file | what |
|---|---|
| `make_overview.py` | page layout (reportlab canvas); every string goes through a registry with its source |
| `ov_values.py` | reads the master params (`master_values`, `master_geometry`), the design document sections, the content file; provenance registry |
| `ov_draw.py` | fonts (Segoe UI, embedded), colours (one accent), text wrapping, images, balloons, leader labels |
| `ov_section.py` | vector section figures from the planar cuts of the assembly STEP |
| `render_overview.py` | offscreen VTK renders of the assembly STEP (parts alone, exploded view with an id buffer for the balloons, process steps, hero), simple tool renders from the drawing values, and the planar sections (`sections.json`) |
| `overview_content.json` | all text; every number either a `{m.name}` master placeholder or cited with its design-document section (`src`) |
| `audit_overview.py` | rasterises the pages; checks fonts, Turkish letters, link annotations, the number audit and the BOM-vs-assembly cross-check |
| `overview_provenance.json`, `overview_layout_checks.json`, `audit_report.json` | written by the scripts above (string sources; balloon end points checked on the id buffer; audit). The builder also stops if section leaders cross each other, cross the cable on page 5, if the zoom connector crosses text on page 4, or if an electronics-table word would have to be split anywhere but at a space or hyphen |
| `electronics_bom.json` (+ `make_electronics_bom.py`, `check_electronics_bom_links.py`, `electronics_bom_input.json`) | the electronics table data, prepared separately; read only |

## Rules kept

- No number is typed into the layout code: master values are formatted from the master file, the rest comes from
  `overview_content.json` with its source. The audit re-checks every number in the PDF text layer.
- Inputs are read-only: the master params, the design document, the drawings, the renders, the assembly STEP and report.
- New images only in `Mechanical/Rev3.0_GlassFront/renders/overview/`.
- Never import or run `tools/glassfront/concept/concept_calc.py`.
