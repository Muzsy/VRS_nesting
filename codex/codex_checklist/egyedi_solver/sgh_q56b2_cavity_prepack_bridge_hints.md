# Q56B2 Codex Checklist

Task: `sgh_q56b2_cavity_prepack_bridge_hints`
Canvas: `canvases/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b2_cavity_prepack_bridge_hints.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints/run.md`
Report: `codex/reports/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md`

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

- [x] cavity prepack v2 szerződés dokumentálva
- [x] hole-free solver input ellenőrzés bizonyított
- [x] Rust fősolverbe nem került cavity/hole logika
- [x] CavityPrepackBridgeHints diagnosztika generálódik (artifact JSON)
- [x] prepack-engedélyezett út: top-level holes_points_mm üres
- [x] prepack-letiltott út: explicit disabled/not requested diagnosztika
- [x] validate_prepack_solver_input_hole_free hibázik ha furat marad
- [x] cavity_plan_v2 present (validated a post-solve gate-ben); normalizer expansion kompatibilis (51 teszt zöld)
- [x] nincs silent hole passthrough a fősolver felé
