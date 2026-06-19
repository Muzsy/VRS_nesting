# Q54C Codex Checklist

Task: `sgh_q54c_overlap_tolerant_separation`
Canvas: `canvases/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54c_overlap_tolerant_separation.yaml`
Report: `codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md`

## DoD

- [x] Repo szabályfájlok + Q53 audit (refine not-clear-feladás) + Q52 rotation-correct állapot rögzítve.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült; acceptance csak final_validation_tracker feasible.
- [x] Nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült (rotation-set a density_rotation_candidates-ből; nincs snap).
- [x] Nincs part-id hack, nincs hardcoded 3+3.
- [x] Task-specifikus unit tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a tényleges separationt (iterations, overlap, rotation, fail_reason).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] Overlapos 2-critical konkáv pár CDE-clear interlockba oldódik; rotation nem fix listán.
- [x] Szintetikus 3-critical: CDE-clear VAGY dokumentált `separation_fail_reason` mérhető iterációkkal
      (nem azonnali `seed_not_clear` feladás, mint a Q53C).
- [x] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos; budget nem starve-olja a fallbackot.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml separation`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml density_biased`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md`
