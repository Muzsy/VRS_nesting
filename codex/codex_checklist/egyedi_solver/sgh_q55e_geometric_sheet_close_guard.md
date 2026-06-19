# Q55E Codex Checklist

Task: `sgh_q55e_geometric_sheet_close_guard`
Canvas: `canvases/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55e_geometric_sheet_close_guard.yaml`
Report: `codex/reports/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md`

## DoD

- [ ] Repo szabályfájlok + Q55A-D elolvasva, reportban rögzítve.
- [ ] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [ ] CDE final validation semantics nem gyengült.
- [ ] Nincs NFP, nincs bbox-corner shortcut primary, nincs cavity/hole fősolver logika.
- [ ] Continuous rotation guardrail nem sérült.
- [ ] Nincs part-id hack, nincs hardcoded 3+3, nincs darabszám-előrejelzés a guardban.
- [ ] Task-specifikus tesztek elkészültek.
- [ ] Diagnosztika/report bizonyítja a geometriai guardot (slot_found, band_insert_attempted, reason).
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md` lefutott.
- [ ] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [ ] Van beférő slot → `band_insert_attempted_before_close = true` a close előtt.
- [ ] Nincs slot → `critical_slot_found_before_close = false` (és csak ekkor zárhat frontier/deadline).
- [ ] Primary critical phase close reason nem `frontier_fail_limit`/`deadline` band-insert kísérlet nélkül.
- [ ] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_close`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md`
