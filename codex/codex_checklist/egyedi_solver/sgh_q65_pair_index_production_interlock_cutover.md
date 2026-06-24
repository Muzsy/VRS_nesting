# Q65 Codex Checklist

Task: `sgh_q65_pair_index_production_interlock_cutover`
Canvas: `canvases/egyedi_solver/sgh_q65_pair_index_production_interlock_cutover.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q65_pair_index_production_interlock_cutover.yaml`
Report: `codex/reports/egyedi_solver/sgh_q65_pair_index_production_interlock_cutover.md`

## DoD

- [x] A production Interlock ág már nem a simplified `interlock_seeds_against_anchor(...)` helperrel indul.
- [x] A live anchor rotation-aware pair transform konverzió implementálva van.
- [x] A pair út accepted source/score/transform diagnosztikailag látszik.
- [x] Van explicit fallback summary, ha a pair út nem fogad el candidate-et.
- [x] Elkészült a `artifacts/benchmarks/sgh_q65/interlock_pair_production_cutover.json`.
- [x] Minden létrehozott/módosított fájl szerepel a YAML outputs listájában.
- [x] Report Standard v2 DoD->Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml interlock_pair`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml interlock_role_consults_live_pair_index_in_production_branch -- --nocapture`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q65_pair_index_cutover production_pair_index_cutover_emits_live_pair_diagnostics -- --nocapture`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q65_pair_index_production_interlock_cutover.md`
