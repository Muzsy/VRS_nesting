# Codex Checklist — nesting_engine_spatial_index_rtree_and_sweepline_self_intersect

**Task slug:** `nesting_engine_spatial_index_rtree_and_sweepline_self_intersect`  
**Canvas:** `canvases/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.yaml`

---

## DoD

- [x] `rust/nesting_engine/Cargo.toml` bővítve `geo` dependency-vel, repo pin stílus szerint.
- [x] `polygon_self_intersects()` brute-force O(N^2) implementációja geo sweep-line megoldásra cserélve.
- [x] Self-intersect viselkedés változatlan: `STATUS_SELF_INTERSECT` reject marad.
- [x] `feasibility/narrow.rs` broad-phase RTree query-t használ a teljes lineáris szűrés helyett.
- [x] Bevezetve `PlacedIndex` (Vec + RTree), és `can_place` az új index API-t használja.
- [x] Narrow-phase előtt explicit determinisztikus rendezés megmaradt.
- [x] `placement/blf.rs` átállt `PlacedIndex` state-re.
- [x] Tesztek lefedik a self-intersect reject és a determinism regressziót.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md` PASS.
- [x] Report AUTO_VERIFY blokk és `.verify.log` elkészült.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS.
