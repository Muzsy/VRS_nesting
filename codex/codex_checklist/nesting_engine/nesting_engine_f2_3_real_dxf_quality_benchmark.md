# Codex Checklist — nesting_engine_f2_3_real_dxf_quality_benchmark

**Task slug:** `nesting_engine_f2_3_real_dxf_quality_benchmark`  
**Canvas:** `canvases/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_real_dxf_quality_benchmark.yaml`

---

## DoD

- [x] A ket fixture letezik:
  - `poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json`
  - `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`
- [x] A benchmark lefut mindkettore:
  - `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input ...`
- [x] A report tartalmazza a median osszefoglalot + determinism megallapitast.
- [x] `./scripts/check.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md` PASS.
