# Codex Checklist — simulated_annealing_search_cli_and_evaluator_integration

**Task slug:** `simulated_annealing_search_cli_and_evaluator_integration`  
**Canvas:** `canvases/nesting_engine/simulated_annealing_search_cli_and_evaluator_integration.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search_cli_and_evaluator_integration.yaml`

---

## DoD

- [x] `nest --search none` baseline output valtozatlan (smoke + determinism hash gate zold).
- [x] `nest --search sa` mukodik, es fix seed mellett reprodukalhato (unit teszt).
- [x] `scripts/check.sh` futtatja `cargo test --manifest-path rust/nesting_engine/Cargo.toml sa_` filtert.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_cli_and_evaluator_integration.md` PASS.
- [x] Report Standard v2 + AUTO_VERIFY + `.verify.log` elmentve.
