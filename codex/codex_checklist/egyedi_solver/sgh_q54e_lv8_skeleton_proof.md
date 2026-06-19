# Q54E Codex Checklist

Task: `sgh_q54e_lv8_skeleton_proof`
Canvas: `canvases/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54e_lv8_skeleton_proof.yaml`
Report: `codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md`

## DoD

- [x] Repo szabályfájlok + Q54A-D + Q53E (FAIL) tanulság rögzítve a reportban.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában (scope-fegyelem).
- [x] CDE final validation semantics nem gyengült; a proof csak CDE-valid layouton számít.
- [x] Nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült (rotation_distribution bizonyítja: nem csak 90/270).
- [x] Nincs part-id hack a solverben, nincs hardcoded 3+3 (a fixture lehet LV8, a logika geometria-alapú).
- [x] Integrációs teszt + benchmark elkészült; artifactok az `artifacts/benchmarks/sgh_q54/` alatt.
- [x] Report őszinte verdiktet ad (PASS vagy NEGATÍV + fázis-diagnosztika); nincs túlkommunikálás.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] PROOF: 6× `Lv8_11612`, spacing 5, skeleton ON → ≥1 táblán 3 nagy CDE-valid (vagy NEGATÍV +
      fázis-diagnosztika mutatja az elakadást).
- [x] NO-REGRESSION: full276 spacing 8, skeleton ON vs OFF → 276 placed, used_sheets(ON) ≤ (OFF), valid.
- [x] `VRS_SHEET_BUILDER_SKELETON` default off → byte-azonos a Q53 utáni állapottal.
- [x] `python3 scripts/bench_sgh_q54_skeleton_admission.py --proof-time 90 --full-time 300`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md`
