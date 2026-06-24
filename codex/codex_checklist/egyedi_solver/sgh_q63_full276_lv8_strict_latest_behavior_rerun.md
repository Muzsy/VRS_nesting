# Q63 Codex Checklist

Task: `sgh_q63_full276_lv8_strict_latest_behavior_rerun`
Canvas: `canvases/egyedi_solver/sgh_q63_full276_lv8_strict_latest_behavior_rerun.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q63_full276_lv8_strict_latest_behavior_rerun.yaml`
Report: `codex/reports/egyedi_solver/sgh_q63_full276_lv8_strict_latest_behavior_rerun.md`

## DoD

- [x] A Q62 fallback-problema es a builder relevans kodutjai feltarva, reportban rogzitve.
- [x] Minden letrehozott/modositott fajl szerepel a YAML outputs listajaban.
- [x] Van explicit strict latest-behavior solver mod.
- [x] Strict modban a builder nem esik vissza csendben a nativ seedre.
- [x] Strict modban a builder nem bootstrapel random unresolved partokat.
- [x] Strict modban a skeleton-role critical admission nem rovidul le a regebbi generic direct branchre.
- [x] A Q63 benchmark artefaktok letrejottek: input, outputs, logs, summary, report, renders.
- [x] A report egyertelmuen rogziti a strict latest run placed/sheet eredmenyet es a Q62-hoz viszonyitott kulonbseget.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q63_full276_lv8_strict_latest_behavior_rerun.md` lefutott.
- [x] Report Standard v2 DoD->Evidence Matrix kitoltve path+line bizonyitekkal.

## Task-specific gates

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [x] `python3 scripts/bench_sgh_q63_full276_strict_latest_behavior.py --reuse-existing`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q63_full276_lv8_strict_latest_behavior_rerun.md`
