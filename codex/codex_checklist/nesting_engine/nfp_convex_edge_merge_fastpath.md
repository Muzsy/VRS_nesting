# Codex Checklist — nfp_convex_edge_merge_fastpath

**Task slug:** `nfp_convex_edge_merge_fastpath`  
**Canvas:** `canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_convex_edge_merge_fastpath.yaml`

---

## DoD

- [x] `compute_convex_nfp()` az edge-merge implementációt hívja (nem a hull-t).
- [x] `compute_convex_nfp_reference()` a hull implementáció (átnevezve, logikailag változatlan).
- [x] A meglévő fixture regressziós teszt (`fixture_library_passes`) PASS marad.
- [x] Új cross-check teszt: `edge_merge_equals_hull_on_all_fixtures()` PASS.
- [x] Párhuzamos élek (`cross == 0`) collinear merge kezelése unit teszttel igazolt.
- [x] Determinisztikus output: azonos input kétszer azonos NFP csúcslista.
- [x] `cross_product_i128()` az egyetlen szorzási útvonal a merge komparátorban.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md` PASS.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md` futtatva.
