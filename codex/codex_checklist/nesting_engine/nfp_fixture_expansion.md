# Codex Checklist — nfp_fixture_expansion

**Task slug:** `nfp_fixture_expansion`  
**Canvas:** `canvases/nesting_engine/nfp_fixture_expansion.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_fixture_expansion.yaml`

---

## DoD

- [x] `convex.rs`-ben `#[cfg(test)]` blokk létezik legalább 5 unit teszttel.
- [x] `test_not_convex_returns_err` PASS.
- [x] `test_empty_polygon_returns_err` PASS.
- [x] `test_collinear_merge_no_extra_vertices` PASS (4 csúcs).
- [x] `test_determinism` PASS.
- [x] `test_rect_rect_known_nfp` PASS.
- [x] 5 új fixture JSON létrehozva a `poc/nfp_regression/` alatt.
- [x] Minden fixture bemeneti poligonra teljesül: `is_convex` + `is_ccw`.
- [x] Minden új fixture `expected_nfp` hull-módszerrel előállítva és kézzel ellenőrizve.
- [x] `fixture_library_passes` PASS (7 fixture).
- [x] `edge_merge_equals_hull_on_all_fixtures` PASS (7 fixture).
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md` PASS.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` futtatva.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` futtatva.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md` futtatva.
