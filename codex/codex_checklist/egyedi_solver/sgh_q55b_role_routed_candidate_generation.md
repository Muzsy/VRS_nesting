# Q55B Codex Checklist

Task: `sgh_q55b_role_routed_candidate_generation`
Canvas: `canvases/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55b_role_routed_candidate_generation.yaml`
Report: `codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md`

## DoD

- [x] Repo szabályfájlok + Q54 előzmények + Q55A elolvasva, reportban rögzítve.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült.
- [x] Nincs NFP, nincs bbox-corner shortcut primary, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült.
- [x] Nincs part-id hack, nincs hardcoded 3+3, nincs darabszám-előrejelzés a routingban.
- [x] Task-specifikus tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a role-routingot (role-by-role candidate counts).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] A role-routing a megfelelő ágat választja (anchor → sheet-edge; interlock → feature-pár; band → hook).
- [x] Role-by-role diagnosztika kitöltődik (generated + accepted role-onként + rejection summary).
- [x] `try_admit_critical` aláírás-bővítés additív (None = régi viselkedés); default off → byte-azonos.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml role_rout`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md`
