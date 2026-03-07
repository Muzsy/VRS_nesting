# Codex Checklist — part_in_part_pipeline

**Task slug:** `part_in_part_pipeline`  
**Canvas:** `canvases/nesting_engine/part_in_part_pipeline.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_part_in_part_pipeline.yaml`

---

## DoD

- [x] Új CLI kapcsoló elérhető: `--part-in-part off|auto`, default `off`.
- [x] `--part-in-part off` esetben baseline út változatlan marad.
- [x] `auto` módban BLF cavity-aware candidate generation fut a placed hole geometriákból.
- [x] `hole_collapsed` / outer-only (`holes=[]`) forrás cavity-source-ként ignorálva van.
- [x] Elkészült az F3-2 fixture: `poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json`.
- [x] A fixture-en igazolt különbség: `off -> sheets_used=2`, `auto -> sheets_used=1`.
- [x] Rust unit tesztek (`blf_part_in_part_` prefix) PASS.
- [x] Új CLI smoke script PASS és be van kötve a `scripts/check.sh` gate-be.
- [x] `docs/nesting_engine/architecture.md` és `docs/nesting_engine/tolerance_policy.md` szinkronizálva.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/part_in_part_pipeline.md` lefuttatva.
