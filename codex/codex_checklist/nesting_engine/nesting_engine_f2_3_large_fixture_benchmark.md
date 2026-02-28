# Codex Checklist — nesting_engine_f2_3_large_fixture_benchmark

**Task slug:** `nesting_engine_f2_3_large_fixture_benchmark`  
**Canvas:** `canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_large_fixture_benchmark.yaml`

---

## DoD

- [x] Generált fixture-ek léteznek és JSON-validak:
  - `poc/nesting_engine/f2_3_large_500_noholes_v2.json`
  - `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`
- [x] `scripts/bench_nesting_engine_f2_3_large_fixture.py` lefut és kimenti a bench JSON-t.
- [x] A script ellenőrzi és riportálja, hogy run-onként a `determinism_hash` stabil-e (placer+input szerint).
- [x] `./scripts/check.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` PASS.
