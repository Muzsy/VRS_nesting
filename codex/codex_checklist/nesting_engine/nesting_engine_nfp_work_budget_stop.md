# Codex Checklist — nesting_engine_nfp_work_budget_stop

**Task slug:** `nesting_engine_nfp_work_budget_stop`  
**Canvas:** `canvases/nesting_engine/nesting_engine_nfp_work_budget_stop.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_nfp_work_budget_stop.yaml`

---

## DoD

- [x] `nfp_place` `StopPolicy`-t kap es nem hasznal kozvetlen wall-clock time_limit checket.
- [x] Work_budget modban determinisztikus consume pontok vannak a NFP placerben.
- [x] Uj unit teszt zold: `nfp_budget_stop_is_deterministic`.
- [x] `scripts/check.sh` futtatja a `nfp_budget_` celzott tesztet.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_work_budget_stop.md` PASS.
