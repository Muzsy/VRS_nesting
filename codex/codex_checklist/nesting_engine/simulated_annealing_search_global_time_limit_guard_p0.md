# Codex Checklist — simulated_annealing_search_global_time_limit_guard_p0

**Task slug:** `simulated_annealing_search_global_time_limit_guard_p0`  
**Canvas:** `canvases/nesting_engine/simulated_annealing_search_global_time_limit_guard_p0.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search_global_time_limit_guard_p0.yaml`

---

## DoD

- [x] `SaSearchConfig` tartalmazza a globális `time_limit_sec` mezőt, és ez a CLI inputból be van kötve.
- [x] `run_sa_search_over_specs` determinisztikusan clampeli az SA iters értéket az `iters + 2` eval formula szerint.
- [x] `run_sa_core` stop hookkal best-effort korai kilépést támogat (deadline guard integráció).
- [x] Új `sa_` unit tesztek (`sa_iters_are_clamped_by_time_limit_and_eval_budget`, `sa_core_stop_hook_can_short_circuit_before_first_iter`) zöldek.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_global_time_limit_guard_p0.md` PASS.
