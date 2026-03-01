# Codex Checklist — nesting_engine_deterministic_work_budget_stop

**Task slug:** `nesting_engine_deterministic_work_budget_stop`  
**Canvas:** `canvases/nesting_engine/nesting_engine_deterministic_work_budget_stop.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_deterministic_work_budget_stop.yaml`

---

## DoD

- [x] `greedy.rs` StopPolicy-t használ, és BLF-et `&mut stop`-pal hívja.
- [x] `blf.rs` belső loopokban work-budget consume kapuk vannak.
- [x] Új unit teszt: `blf_budget_stop_is_deterministic` zöld.
- [x] `scripts/check.sh` futtatja a `blf_budget_` célzott tesztet.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_deterministic_work_budget_stop.md` PASS.
