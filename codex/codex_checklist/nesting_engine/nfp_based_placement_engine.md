# Codex Checklist — nfp_based_placement_engine

**Task slug:** `nfp_based_placement_engine`  
**Canvas:** `canvases/nesting_engine/nfp_based_placement_engine.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_based_placement_engine.yaml`

---

## DoD

- [x] `nfp/ifp.rs` implementálva + unit tesztek (spec 6.1, 6.2; 4.1).
- [x] `nfp/cfr.rs` implementálva (union + difference + canonicalize + sort) + unit tesztek (spec 9.1, 10.1, 10.2, 10.3).
- [x] `nfp/cache.rs` bővítve: seed-mentes `shape_id()` + `MAX_ENTRIES` cap + determinisztikus `clear_all()` (spec 2, 14.6).
- [x] `placement/nfp_placer.rs` stub kiváltva: deterministic ordering + CFR-vertex candidate + nudge + first-feasible + wrapper contract (spec 2, 7.2, 11.1, 11.3, 12, 15.2).
- [x] Multi-sheet cache scope: a greedy wrapper egy run-szintű NFP cache példányt tart és ad tovább az NFP placernek (spec 3.3, 14.4).
- [x] Új F0–F3 v2 fixture-ek létrehozva (`noholes`, explicit `spacing_mm`).
- [x] `scripts/check.sh` bővítve F0–F3 + determinism(3x) + functional + rotation + no-worse-than-BLF ellenőrzésekkel.
- [x] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_based_placement_engine.md`.
