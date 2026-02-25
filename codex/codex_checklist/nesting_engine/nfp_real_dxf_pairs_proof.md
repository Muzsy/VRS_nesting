# Codex Checklist — nfp_real_dxf_pairs_proof

**Task slug:** `nfp_real_dxf_pairs_proof`  
**Canvas:** `canvases/nesting_engine/nfp_real_dxf_pairs_proof.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_real_dxf_pairs_proof.yaml`

---

## DoD

- [x] 3 fixture létrejött a `poc/nfp_regression/` alatt (`real_dxf_pair_01/02/03`).
- [x] A fixture `polygon_a/polygon_b` ringek valós DXF importból jönnek (canonical i64 egyezés smoke-ban ellenőrizve).
- [x] A három fixture `expected_nfp` és `expected_vertex_count` mezője kitöltött, és `nfp_fixture` számítással egyezik.
- [x] `scripts/smoke_real_dxf_nfp_pairs.py` PASS.
- [x] `scripts/check.sh` futtatja a real DXF NFP smoke-ot.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md` futtatva.

## Lokális ellenőrzések

- [x] `python3 scripts/smoke_real_dxf_nfp_pairs.py` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md` futtatva.
