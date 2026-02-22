# Codex Checklist — nesting_engine_polygon_pipeline_fixes

**Task slug:** `nesting_engine_polygon_pipeline_fixes`  
**Canvas:** `canvases/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_polygon_pipeline_fixes.yaml`

---

## DoD

- [x] A polygon pipeline canvasban a futtatasi peldak helyes repo-relativ binaris utvonalat hasznalnak.
- [x] Van uj, determinisztikus unit teszt `SELF_INTERSECT` esetre (bow-tie outer polygon).
- [x] `SELF_INTERSECT` esetben a pipeline nem crashel, `self_intersect` statuszt es diagnostikait ad.
- [x] A "never constructed" warningot okozo, nem konstrualt enum ag megszunt / kod igazitas megtortent.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.md` PASS.
- [x] Report + checklist teljesen kitoltve (DoD -> Evidence + Advisory + AUTO_VERIFY frissitve).

## Lokalis ellenorzesek

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS (8 test)
