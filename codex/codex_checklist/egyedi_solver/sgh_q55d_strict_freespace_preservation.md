# Q55D Codex Checklist

Task: `sgh_q55d_strict_freespace_preservation`
Canvas: `canvases/egyedi_solver/sgh_q55d_strict_freespace_preservation.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55d_strict_freespace_preservation.yaml`
Report: `codex/reports/egyedi_solver/sgh_q55d_strict_freespace_preservation.md`

## DoD

- [ ] Repo szabályfájlok + Q54D + Q55A-C elolvasva, reportban rögzítve.
- [ ] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [ ] CDE final validation semantics nem gyengült; a slot-score csak rangsoroló proxy.
- [ ] Nincs NFP, nincs bbox-corner shortcut primary, nincs cavity/hole fősolver logika.
- [ ] Continuous rotation guardrail nem sérült.
- [ ] Nincs part-id hack, nincs hardcoded 3+3.
- [ ] Task-specifikus tesztek elkészültek.
- [ ] Diagnosztika/report bizonyítja a slot-alapú döntést (can_fit_next_critical, fit_margin).
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55d_strict_freespace_preservation.md` lefutott.
- [ ] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [ ] Szintetikus: A (sűrűbb, feldarabol) vs B (megőriz critical slotot) → a solver **B-t** választja.
- [ ] LV8: az első két nagy után `can_fit_next_critical = true`, `estimated_next_critical_fit_margin > 0`.
- [ ] A candidate ranking sorrend: feasibility → role → next-critical fit → free component → fragmentation
      → aspect → density tie-break.
- [ ] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml free_space`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55d_strict_freespace_preservation.md`
