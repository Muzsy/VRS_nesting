# Q56C Codex Checklist

Task: `sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates`
Canvas: `canvases/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates/run.md`
Report: `codex/reports/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md`

## DoD

- [x] repo rules elolvasva
- [x] valós kód anchorok ellenőrizve
- [x] minden módosított/létrehozott fájl szerepel a YAML outputs listában
- [x] task-specifikus implementation elkészült
- [x] task-specifikus diagnosztika elkészült
- [x] task-specifikus tesztek lefutottak
- [x] verify wrapper lefutott (PASS, exit 0)
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal

## Task-specifikus kapuk

- [x] SheetEdgePlacementCatalog (vagy ekvivalens) létezik
- [x] Anchor candidate-ek mind a négy sheet-élre generálódnak (36 boundary-clear)
- [x] corner variánsok first-class; center fallback, nem egyedüli (24 corner; selected = top-right)
- [x] minden elfogadott candidate spacing-expanded true extrémát használ (boundary a shrunk sheet ellen)
- [x] margin-shrink bizonyítva (shrunk = raw − (margin − half_spacing); margin_error 0.0)
- [~] a production Anchor út ténylegesen használja a katalógust — **DEFERRED** (gated follow-up; selection API kész, lásd report §7)
- [x] kiválasztott candidate-nek van free-space score-ja (2 582 327 mm²)
- [x] JSON + SVG artifact generálva
- [x] Q55B one-part proof nem regresszál (determinizmus 10/10 byte-azonos)
