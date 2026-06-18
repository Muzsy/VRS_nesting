# Q54A Codex Checklist

Task: `sgh_q54a_skeleton_state_role_assignment`
Canvas: `canvases/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54a_skeleton_state_role_assignment.yaml`
Report: `codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md`

## DoD

- [x] Repo szabályfájlok és Q47–Q53 előzmények (+ Q53 audit) elolvasva, reportban rögzítve.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült.
- [x] Nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült.
- [x] Nincs part-id specifikus hack, nincs hardcoded `3 big per sheet` szabály.
- [x] Task-specifikus unit tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a tényleges viselkedést (role-besorolás).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] `assign_role`: Anchor→Interlock→BandInsert determinisztikus a szintetikus 3-critical szekvencián.
- [x] Üres sheet első critical-ja mindig `Anchor`; darabszám nem befolyásolja a szerepet.
- [x] `VRS_SHEET_BUILDER_SKELETON` default off → Q51/Q52 multisheet/builder output byte-azonos.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_builder`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md`
