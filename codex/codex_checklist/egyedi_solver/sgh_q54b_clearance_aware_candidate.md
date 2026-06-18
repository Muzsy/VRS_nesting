# Q54B Codex Checklist

Task: `sgh_q54b_clearance_aware_candidate`
Canvas: `canvases/egyedi_solver/sgh_q54b_clearance_aware_candidate.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54b_clearance_aware_candidate.yaml`
Report: `codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.md`

## DoD

- [x] Repo szabályfájlok + Q53 audit (point_alignment_seed pont-pont gyökér) elolvasva, reportban rögzítve.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült; a clearance-offset csak seed, nem collision döntés.
- [x] Nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült (nincs snapping; anchor szög folytonos).
- [x] Nincs part-id hack, nincs hardcoded 3+3.
- [x] Task-specifikus unit tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a tényleges viselkedést (clearance/seed-clear számlálók).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] Anchor candidate él-párhuzamos, margin+spacing távolságra (nem bbox-sarok, nem pont-pont).
- [x] Interlock seed clearance-offsettel közvetlenül CDE-clear VAGY `seed_overlap` < kontrollált küszöb
      (szemben a Q53 garantált `seed_not_clear`-jével).
- [x] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos a jelenlegivel.
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml clearance`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.md`
