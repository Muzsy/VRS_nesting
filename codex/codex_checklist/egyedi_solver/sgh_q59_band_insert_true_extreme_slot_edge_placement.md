# Q59 Codex Checklist

Task: `sgh_q59_band_insert_true_extreme_slot_edge_placement`
Canvas: `canvases/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q59_band_insert_true_extreme_slot_edge_placement.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement/run.md`
Report: `codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md`

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

- [x] SlotEdgePlacementCandidate modell létezik (true_extreme_slot_edge_band_insert source)
- [x] slot-edge candidate generálás (corner + center fallback) a szabad slot bbox-ból
- [x] elfogadott placement spacing-expanded true extrémát használ
- [x] continuous rotációk nem snappelnek 0/90/180/270-re (selected 92.75° fractional)
- [x] boundary a slot ÉS a teljes sheet ellen + neighbour clearance (a slot nem collision truth)
- [~] gate-en a bbox band_insert_seeds út nem primary — **DEFERRED** (producer kész, bpp átkötés gated, §7)
- [x] fallback elérhető és logolt (fallback_to_bbox_path)
- [x] JSON + SVG artifact generálva
- [x] Q55B/Q56C/Q57B utak nem regresszálnak (determinizmus 10/10 byte-azonos)
