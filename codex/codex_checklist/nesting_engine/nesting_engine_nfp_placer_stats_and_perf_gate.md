# Codex Checklist — nesting_engine_nfp_placer_stats_and_perf_gate

**Task slug:** `nesting_engine_nfp_placer_stats_and_perf_gate`  
**Canvas:** `canvases/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_nfp_placer_stats_and_perf_gate.yaml`

---

## DoD

- [x] `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett `nest --placer nfp` futás stderr-re kiír 1 db `NEST_NFP_STATS_V1 {json}` sort.
- [x] A stat JSON parse-olhato, es a counterek determinisztikusak (ugyanarra a fixture-re tobbszor futtatva azonosak).
- [x] `scripts/smoke_nfp_placer_stats_and_perf_gate.py --record ...` letrehozza a baseline-t.
- [x] `scripts/smoke_nfp_placer_stats_and_perf_gate.py --check ...` PASS a baseline-nal.
- [x] `scripts/check.sh` hivja a perf gate smoke-ot, es PASS.
- [x] Report + AUTO_VERIFY frissul: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_placer_stats_and_perf_gate.md`.
