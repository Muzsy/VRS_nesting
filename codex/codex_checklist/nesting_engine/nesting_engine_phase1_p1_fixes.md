# Codex Checklist — nesting_engine_phase1_p1_fixes

**Task slug:** `nesting_engine_phase1_p1_fixes`  
**Canvas:** `canvases/nesting_engine/nesting_engine_phase1_p1_fixes.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_phase1_p1_fixes.yaml`

---

## DoD

- [x] `scripts/validate_nesting_solution.py` overlap ellenorzest vegez minden placement-parra (AABB, optional i_overlay narrow-phase).
- [x] `scripts/validate_nesting_solution.py` OOB ellenorzest vegez (`sheet` hatar + `margin_mm` figyelembevetel).
- [x] `poc/nesting_engine/invalid_overlap_fixture.json` letezik es validatorra non-zero exittel bukik.
- [x] `scripts/check.sh` tartalmazza a validator FAIL smoke lepest (invalid overlap fixture, elvart non-zero).
- [x] `scripts/check.sh` tartalmazza a validator PASS smoke lepest (baseline output, elvart zero).
- [x] `offset_stock_geometry`: env nelkul (`VRS_OFFSET_ALLOW_SHAPELY_FALLBACK` off) Rust hibanal `GeometryOffsetError` dobodik.
- [x] `offset_stock_geometry`: env on eseten (`VRS_OFFSET_ALLOW_SHAPELY_FALLBACK=1`) WARNING log + Shapely fallback.
- [x] `tests/test_geometry_offset.py` tartalmazza a ket uj stock fallback tesztet (env OFF/ON ag).
- [x] Rust `nest` stdout outputbol az `elapsed_sec` el van tavolitva (`meta` csak determinism hash).
- [x] `vrs_nesting/runner/nesting_engine_runner.py` runner-level idomerest (`elapsed_sec`) artifact metaadatban tarol.
- [x] `docs/nesting_engine/io_contract_v2.md` dokumentalja, hogy `meta.elapsed_sec` runner-level adat.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_phase1_p1_fixes.md` PASS.
- [x] `codex/reports/nesting_engine/nesting_engine_phase1_p1_fixes.verify.log` letrejott.
