# Codex Checklist — nesting_engine_spacing_margin_bin_offset_model

**Task slug:** `nesting_engine_spacing_margin_bin_offset_model`  
**Canvas:** `canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_spacing_margin_bin_offset_model.yaml`

---

## DoD

- [x] `pipeline_v1` tamogatja az optional `spacing_mm` mezot, legacy fallback: spacing=kerf ha spacing hianyzik.
- [x] Part inflate a pipeline-ban kizarolag `inflate_delta=spacing/2` alapjan fut (margin nem resze).
- [x] Stock usable outer offset: `bin_offset=spacing/2 - margin` (pozitiv esetben outer no).
- [x] Stock hole/defect akadaly: `inflate_delta=spacing/2` alapjan tagul (margin nelkul).
- [x] `nesting_engine_v2` input tamogatja az optional `sheet.spacing_mm` mezot, effective spacing fallback `kerf_mm`-bol.
- [x] A `nest` rect-bin szamitas `bin_offset` alapjan tortenik, es kulon unit teszt fedi a `margin < spacing/2` esetet.
- [x] Python shapely stock fallback tamogatja a `bin_offset` modellt (pozitiv esetet is), es a tesztek frissultek.
- [x] Doksi szinkron megtortent (`docs/dxf_nesting_app_4_...`, `docs/nesting_engine/io_contract_v2.md`, POC mintak).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md` PASS.
- [x] `codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.verify.log` letrejott.

## Lokalis ellenorzesek

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` PASS.
- [x] `python3 -m pytest -q tests/test_geometry_offset.py` PASS.
