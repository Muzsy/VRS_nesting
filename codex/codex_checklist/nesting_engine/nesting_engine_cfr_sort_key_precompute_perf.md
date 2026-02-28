# Codex Checklist — nesting_engine_cfr_sort_key_precompute_perf

**Task slug:** `nesting_engine_cfr_sort_key_precompute_perf`  
**Canvas:** `canvases/nesting_engine/nesting_engine_cfr_sort_key_precompute_perf.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_cfr_sort_key_precompute_perf.yaml`

---

## DoD

- [x] `sort_components(...)` decorated sortot hasznal, es a tie-break hash komponensenkent egyszer keszul.
- [x] Uj unit teszt megvan es zold: `cfr_sort_key_precompute_*`.
- [x] `scripts/check.sh` futtatja: `cargo test --manifest-path rust/nesting_engine/Cargo.toml cfr_sort_key_`.
- [x] `./scripts/check.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_cfr_sort_key_precompute_perf.md` PASS.
