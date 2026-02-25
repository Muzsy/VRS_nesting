# Codex Checklist — nfp_concave_integer_union

**Task slug:** `nfp_concave_integer_union`  
**Canvas:** `canvases/nesting_engine/nfp_concave_integer_union.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_integer_union.yaml`

---

## DoD

- [x] `rust/nesting_engine/src/nfp/concave.rs` nem használ `FloatOverlay` / `i_overlay::float::*` importot.
- [x] A concave stable baseline union integer-only útvonalon fut (`i_overlay::core::overlay::Overlay`).
- [x] A union kimenete továbbra is `clean_polygon_boundary()` után tér vissza.
- [x] Concave fixture regressziók PASS (`rust/nesting_engine/tests/nfp_regression.rs`).
- [x] Guard regresszió teszt védi a float overlay visszacsúszást (`rust/nesting_engine/tests/nfp_no_float_overlay.rs`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md` PASS.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression --test nfp_no_float_overlay` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md` futtatva.
