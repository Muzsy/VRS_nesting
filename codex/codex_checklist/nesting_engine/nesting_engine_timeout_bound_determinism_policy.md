# Codex Checklist — nesting_engine_timeout_bound_determinism_policy

**Task slug:** `nesting_engine_timeout_bound_determinism_policy`  
**Canvas:** `canvases/nesting_engine/nesting_engine_timeout_bound_determinism_policy.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_timeout_bound_determinism_policy.yaml`

---

## DoD

- [x] `io_contract_v2.md` tartalmaz explicit determinism vs timeout policy szöveget (TIME_LIMIT_EXCEEDED említéssel).
- [x] `testing_guidelines.md` kimondja: determinism gate-et csak “komfortosan limit alatt” futó fixture-re.
- [x] `architecture.md` tartalmaz time_limit / timeout-bound viselkedés fejezetet + középtávú work-budget irányt (csak említés).
- [x] `bench_nesting_engine_f2_3_large_fixture.py` jelöli a timeout-bound futásokat és ezt beleírja az outputba.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_timeout_bound_determinism_policy.md` PASS.
