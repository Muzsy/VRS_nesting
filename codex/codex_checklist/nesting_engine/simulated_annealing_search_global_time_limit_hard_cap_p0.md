# Codex Checklist — simulated_annealing_search_global_time_limit_hard_cap_p0

**Task slug:** `simulated_annealing_search_global_time_limit_hard_cap_p0`  
**Canvas:** `canvases/nesting_engine/simulated_annealing_search_global_time_limit_hard_cap_p0.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search_global_time_limit_hard_cap_p0.yaml`

---

## DoD

- [x] Az SA iters clamp megengedi a `0` iteraciot (`1 initial + iters` hard budget modell).
- [x] A `run_sa_search_over_specs(...)` nem futtat kulon final greedy rerun evaluaciot a search vegen.
- [x] A search a mar kievaluelt best eredmenyt reuse-olja visszatereskor.
- [x] Uj `sa_` unit tesztek bizonyitjak a hard budget logikat.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_global_time_limit_hard_cap_p0.md` PASS.
