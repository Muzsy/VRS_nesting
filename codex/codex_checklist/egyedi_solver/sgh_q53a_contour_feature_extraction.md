# Q53A Codex Checklist

Task: `sgh_q53a_contour_feature_extraction`
Canvas: `canvases/egyedi_solver/sgh_q53a_contour_feature_extraction.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53a_contour_feature_extraction.yaml`
Report: `codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md`

## DoD

- [x] Repo szabályfájlok és releváns Q47–Q52 előzmények elolvasva, reportban rögzítve.
- [x] Minden módosított/létrehozott fájl szerepelt a YAML outputs listájában.
- [x] CDE final validation semantics nem gyengült.
- [x] Nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- [x] Continuous rotation guardrail nem sérült.
- [x] Nincs part-id specifikus LV8 hack.
- [x] Task-specifikus unit/integration tesztek elkészültek.
- [x] Diagnosztika/report bizonyítja a task tényleges viselkedését.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md` lefutott.
- [x] Report Standard v2 DoD→Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml contour_features`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml shape_profile`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md`
