# Q57B Codex Checklist

Task: `sgh_q57b_pair_candidates_to_interlock_role`
Canvas: `canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57b_pair_candidates_to_interlock_role.yaml`
Runner: `codex/prompts/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role/run.md`
Report: `codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md`

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

- [x] Interlock role konzultálja a PairCompatibilityIndex-et (pair_index_queries=1)
- [x] pair relatív transzform → placement seed konverzió (origin szemantika bizonyítva, pontos matek)
- [x] elfogadott candidate exact boundary + clearance gate (CDE marad a truth)
- [x] pair-index Interlock source látható a diagnosztikában
- [x] neighbour feature candidate fallback megőrizve + logolva (LV8: fallback=true)
- [x] rejection okok aggregálva (boundary/collision/pair_not_found/transform_invalid/cde_not_clear)
- [x] env-gate default off → no-regression bizonyítva (determinizmus 10/10 byte-azonos)
- [x] interlock_pair_admission.json artifact generálva
- [~] production try_admit_critical bekötés — **DEFERRED** (gated follow-up, API kész; lásd report §7)
