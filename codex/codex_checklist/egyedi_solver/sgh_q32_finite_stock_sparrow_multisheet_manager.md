# Codex checklist — sgh_q32_finite_stock_sparrow_multisheet_manager

## Kötelező workflow

- [ ] Elolvastam: `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`.
- [ ] Elolvastam a Q32 canvas-t.
- [ ] Felderítettem a valós kódot: `io.rs`, `adapter.rs`, `sheet.rs`, `optimizer/sparrow/*`, `optimizer/score.rs`.
- [ ] Rögzítettem a reportban, hogy a régi `optimizer/multisheet.rs` legacy/Phase1 manager, nem production Sparrow finite-stock megoldás.
- [ ] Rögzítettem a reportban a Q31 base-shape cache jelenlegi állapotát.
- [ ] Git status / dirty state rögzítve a reportban.

## Pipeline / IO contract

- [ ] `OptimizerPipelineKind::SparrowCdeMultisheet` létezik.
- [ ] Serde snake_case név: `sparrow_cde_multisheet`.
- [ ] A meglévő `sparrow_cde` út nem tört el.
- [ ] Az adapterben külön `sparrow_cde_multisheet` ág van.
- [ ] A multisheet path nem fallbackel legacy solverre.
- [ ] A multisheet path CDE backendet használ.
- [ ] `OptimizerDiagnosticsOutput` tartalmazza a kötelező `sparrow_ms_*` optional mezőket.

## Új Sparrow-native finite-stock manager

- [ ] Létrejött: `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs`.
- [ ] Exportálva van a `rust/vrs_solver/src/optimizer/sparrow/mod.rs`-ből.
- [ ] Nem importál `WorkingLayout`-ot.
- [ ] Nem importál `VrsCollisionTracker`-t.
- [ ] Nem használja a régi `optimizer/multisheet.rs` production megoldásként.
- [ ] Nem használ Python `multi_sheet_wrapper.py`-t.
- [ ] Nem köt be compressiont.
- [ ] Heterogén rectangle stock poolt kezel.
- [ ] Original expanded sheet index mapping stabil.
- [ ] Candidate sheet subseteket generál és rangsorol.
- [ ] Kisebb / jobb sheet használatot preferál.
- [ ] Full stock pool fallback candidate van.

## Sparrow-core integráció

- [ ] A manager `SparrowProblem::from_solver_input` + `SparrowOptimizer::solve` core-t használ.
- [ ] Selected sheet subsetre futtatott attempt működik.
- [ ] Output placement sheet index visszamappelődik original expanded sheet indexre.
- [ ] Q31 `SPInstance.base_shape: Rc<CdeBaseShape>` cache megmaradt.
- [ ] `prepare_base_shape_native` nincs visszatolva search/LBF/tracker hot pathba.
- [ ] A core strict CDE/tracker útja megmaradt.

## Partial sanitize / unplaced

- [ ] `ok` output csak `final_pairs == 0` és `boundary_violations == 0` mellett lehetséges.
- [ ] `partial` outputban nincs collisionos placement.
- [ ] `partial` outputban nincs boundary-sértő placement.
- [ ] Collision graph / conflict cluster alapú sanitize vagy ejection-repair van.
- [ ] Több removal candidate van, nem csak az első ütköző item.
- [ ] Explicit unplaced reason létezik stock exhaustion esetben.
- [ ] `PART_NEVER_FITS_STOCK` kezelt.
- [ ] `STOCK_EXHAUSTED_PARTIAL` vagy `INSUFFICIENT_STOCK_CAPACITY` reportolva van.

## Utilization / sheet usage

- [ ] `used_sheet_indices` unique placement sheet indexekből számolódik.
- [ ] `used_sheet_count` nem `max(sheet_index)+1`.
- [ ] `used_sheet_area` unique used sheetek területösszege.
- [ ] `placed_part_area` számolva.
- [ ] `utilization_pct = 100 * placed_part_area / used_sheet_area`.
- [ ] Heterogén/gapped sheet index esetet teszt fedi.

## LV8 full276 runner / artifactok

- [ ] `rust/vrs_solver/tests/fixtures/sgh_q32_finite_stock_multisheet/full_276_lv8_derived.json` létrejött.
- [ ] Full276 fixture 12 part type-ot tartalmaz.
- [ ] Full276 fixture total quantity = 276.
- [ ] A fixture a `samples/real_work_dxf/0014-01H/lv8jav_normalized/` normalizált DXF-ekből készült.
- [ ] A fő Sparrow core nem kap `holes_points`-ot.
- [ ] `scripts/run_sgh_q32_finite_stock_multisheet_lv8.py` létezik.
- [ ] Runner case01/case02/case03 inputokat létrehozta.
- [ ] Runner mindhárom output JSON-t létrehozta.
- [ ] Summary JSON létrejött.
- [ ] Markdown benchmark report létrejött.

## Case 01 — 2×1500×3000 acceptance

- [ ] `status == ok`.
- [ ] `placed_count == 276`.
- [ ] `unplaced_count == 0`.
- [ ] `sparrow_ms_final_pairs == 0`.
- [ ] `sparrow_ms_boundary_violations == 0`.
- [ ] `sparrow_ms_used_sheet_count <= 2`.
- [ ] `sparrow_ms_utilization_pct > 0`.

## Case 02 — 3×1500×3000 acceptance

- [ ] `status == ok`.
- [ ] `placed_count == 276`.
- [ ] `unplaced_count == 0`.
- [ ] `sparrow_ms_final_pairs == 0`.
- [ ] `sparrow_ms_boundary_violations == 0`.
- [ ] `sparrow_ms_used_sheet_count <= 2`.
- [ ] `sparrow_ms_used_sheet_area <= 9000000.0`.
- [ ] `sparrow_ms_utilization_pct > 0`.

## Case 03 — mixed stock acceptance

- [ ] Case03 vagy OK gate szerint PASS, vagy korrekt stock-exhausted partial szerint PASS.
- [ ] Ha OK: `status == ok`, `placed_count == 276`, `unplaced_count == 0`, `final_pairs == 0`, `boundary_violations == 0`.
- [ ] Ha partial: `status == partial`, `placed_count > 0`, `unplaced_count > 0`, `sparrow_ms_stock_exhausted == true`, `used_sheet_count == 3`, `final_pairs == 0`, `boundary_violations == 0`, explicit unplaced list.
- [ ] Case03 nem PASS collisionos partiallal.
- [ ] Case03 nem PASS üres unplaced listás partiallal.

## Smoke / Rust tesztek

- [ ] `scripts/smoke_sgh_q32_finite_stock_multisheet.py` létezik.
- [ ] Smoke statikus invariánsokat ellenőriz.
- [ ] Smoke artifact gate-eket ellenőriz.
- [ ] `rust/vrs_solver/tests/sparrow_finite_stock_multisheet.rs` létezik.
- [ ] Rust teszt fedi enum deserializációt.
- [ ] Rust teszt fedi heterogén stock mappinget.
- [ ] Rust teszt fedi unique used sheet countot.
- [ ] Rust teszt fedi synthetic max-2-used-sheet stratégiát.
- [ ] Rust teszt fedi partial sanitize/unplaced reason logikát.
- [ ] Rust teszt fedi Q31 cache invariánst.

## Verifikáció

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` PASS.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` PASS.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_finite_stock_multisheet` PASS.
- [ ] `python3 scripts/run_sgh_q32_finite_stock_multisheet_lv8.py` PASS.
- [ ] `python3 scripts/smoke_sgh_q32_finite_stock_multisheet.py` PASS.
- [ ] `./scripts/check.sh` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md` PASS.

## Report

- [ ] Report Standard v2 szerint készült.
- [ ] DoD → Evidence Matrix path + line bizonyítékokkal kitöltve.
- [ ] Case01/Case02/Case03 eredmények szerepelnek.
- [ ] Acceptance gates külön táblázatban szerepelnek.
- [ ] Kötelező marker sorok megvannak:
  - [ ] `Q32_STATUS:`
  - [ ] `Q32_CASE01_STATUS:`
  - [ ] `Q32_CASE02_STATUS:`
  - [ ] `Q32_CASE03_STATUS:`
  - [ ] `Q32_CASE01_PLACED:`
  - [ ] `Q32_CASE02_PLACED:`
  - [ ] `Q32_CASE03_PLACED:`
  - [ ] `Q32_CASE01_USED_SHEETS:`
  - [ ] `Q32_CASE02_USED_SHEETS:`
  - [ ] `Q32_CASE03_USED_SHEETS:`
  - [ ] `Q32_CASE01_FINAL_PAIRS:`
  - [ ] `Q32_CASE02_FINAL_PAIRS:`
  - [ ] `Q32_CASE03_FINAL_PAIRS:`
  - [ ] `Q32_CASE03_UNPLACED:`
  - [ ] `Q32_FINAL_VERDICT:`
