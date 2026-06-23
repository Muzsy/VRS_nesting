# Q60 Codex Checklist

Task: `sgh_q60_critical_triple_simultaneous_admission`
Canvas: `canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q60_critical_triple_simultaneous_admission.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission/run.md`
Report: `codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md`

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

- [x] critical triple/simultaneous admission nem dobja el a valid 2/3 partialt
- [x] best-partial/incumbent megőrzés bizonyított (full_three_fails → best=2)
- [x] 3 critical attempt diagnosztika van (arrangements[], collision_pairs, boundary_violations)
- [x] bounded 2/3 group candidate-ek léteznek (OrientationCatalog min-width + flip)
- [x] legalább pair-szintű simultaneous mozgás/refinement (any_part_moved_in_refinement=true)
- [x] spacing-expanded collision (grid proxy) + boundary a refinement alatt (CDE marad a truth)
- [x] VRS_SIMULTANEOUS_CRITICAL gate default off → no-regression (determinizmus 10/10)
- [x] fókuszált 3-kritikus benchmark valós spacingnél őszintén jelentve (best=2, full=false; spacing=0 is best=2)
- [x] JSON + SVG artifact; honest finding (3 nem fér, best partial 2 megőrizve)
- [x] Q55B/Q56C/Q57B/Q59 utak nem regresszálnak
- [~] production simultaneous_critical_repack átkötés — **DEFERRED** (gated follow-up; API kész, §7)
