# Checklist — SGH-Q26 Single-sheet Sparrow validation test suite, revised with LV8-derived gate

## Scope / hygiene

- [x] Read `AGENTS.md`, Codex docs, Q25-R6 report, and relevant Sparrow/adapter/test/DXF files.
- [x] Record `git status --porcelain=v1` and `git diff --name-only` before editing.
- [x] Record pre-existing dirty files.
- [x] Do not edit unrelated files.
- [x] Do not modify solver production code unless a test-infra issue makes it unavoidable and the report explains it.
- [x] Do not tune the solver to pass Q26.

## Test suite structure

- [x] Create `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs`.
- [x] Use the public crate boundary, preferably `vrs_solver::adapter::solve` and `serde_json::from_value::<SolverInput>`.
- [x] Add reusable helpers for requested instance count, output diagnostics, single-sheet assertions, and deterministic output comparison.
- [x] Ensure every positive Rust fixture uses `solver_profile=jagua_optimizer_phase1_outer_only`.
- [x] Ensure every positive Rust fixture uses `optimizer_pipeline=sparrow_cde`.
- [x] Ensure every positive Rust fixture uses `collision_backend=cde`.
- [x] Ensure every positive Rust fixture uses exactly one stock with `quantity=1`.
- [x] Ensure every positive Rust fixture asserts `status == "ok"`.
- [x] Ensure every positive Rust fixture asserts all placements are on `sheet_index == 0`.

## Required Rust tests

- [x] Add `q26_single_sheet_tiny_rectangles_all_placed`.
- [x] Add `q26_single_sheet_requires_90_degree_rotation_all_placed`.
- [x] Add `q26_single_sheet_strict_cde_irregular_l_shape_mix_all_placed`.
- [x] Add `q26_single_sheet_medium_rect_mix_all_placed`.
- [x] Add `q26_single_sheet_medium_mixed_rotations_all_placed`.
- [x] Add `q26_single_sheet_serious_synthetic_40_to_80_instances_all_placed`.
- [x] Add `q26_single_sheet_deterministic_same_seed_same_output`.
- [x] Add `q26_single_sheet_negative_overcapacity_reports_partial_with_diagnostics`.

## Diagnostic assertions

- [x] Assert `optimizer_diagnostics.pipeline_used == "sparrow_cde"` on positive fixtures.
- [x] Assert `sparrow_invoked == Some(true)`.
- [x] Assert `sparrow_converged == Some(true)`.
- [x] Assert `sparrow_native_model_active == Some(true)`.
- [x] Assert `sparrow_native_tracker_active == Some(true)`.
- [x] Assert `sparrow_old_core_used == Some(false)`.
- [x] Assert `sparrow_compression_passes == Some(0)`.
- [x] Assert `loss_bbox_proxy_used_as_primary == Some(false)`.
- [x] Assert `collision_backend_diagnostics.backend_used == "cde_adapter"`.
- [x] Assert `collision_backend_diagnostics.bbox_fallback_queries == 0`.

## Fixture levels

- [x] Level 1 tiny rectangle fixture is easy and deterministic.
- [x] Level 2 90-degree rotation-required fixture is deterministic and all placed.
- [x] Level 2 irregular L-shape/CDE fixture uses `outer_points` and all placed.
- [x] Level 3 medium rectangle mix has 15–30 instances and all placed.
- [x] Level 3 medium mixed-rotation fixture has 15–35 instances and all placed.
- [x] Level 4A serious synthetic fixture has 40–80 instances, one sheet, and all placed.
- [x] Negative overcapacity fixture honestly returns partial/unsupported with diagnostics.
- [x] No synthetic positive fixture requires near-perfect density or Nest&Cut-level optimization.

## LV8-derived one-sheet validation

- [x] Create `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py`.
- [x] Use real files from `samples/real_work_dxf/0014-01H/lv8jav`.
- [x] Ignore backup files like `*.dxf~`.
- [x] Parse filename quantities such as `_28db`, `_20db`, etc., or use existing repo helper.
- [x] Build a deterministic subset with total selected quantity between 40 and 80 instances.
- [x] Prefer broad coverage across multiple LV8 part types.
- [x] Use exactly one 1500×3000 stock/sheet with quantity 1.
- [x] Use spacing/margin appropriate for project validation, default `spacing_mm=10.0`, `margin_mm=10.0` unless existing repo rules require another value.
- [x] Run via `scripts/run_real_dxf_sparrow_pipeline.py` or the closest existing repo-native DXF runner.
- [x] Assert status `ok`.
- [x] Assert `unplaced_count == 0`.
- [x] Assert `placements_count == selected_instance_count`.
- [x] Assert all placements are on sheet 0 / first sheet.
- [x] Assert no `sheet_002.dxf` artifact exists.
- [x] Assert native Sparrow/CDE diagnostics if present in produced solver output.
- [x] Write `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/lv8_derived_subset_manifest.json` with selected files and quantities.
- [x] Do not use first-sheet 191 or full 276 LV8 as acceptance.
- [x] Do not call this a benchmark.

## Smoke scripts

- [x] Create/update `scripts/smoke_sgh_q26_single_sheet_validation_suite.py`.
- [x] Smoke verifies Rust integration test file existence.
- [x] Smoke verifies required Rust test names.
- [x] Smoke verifies single-sheet-only fixture contract.
- [x] Smoke verifies diagnostics assertions are present.
- [x] Smoke verifies `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py` exists.
- [x] Smoke verifies the LV8-derived smoke references the real LV8 directory.
- [x] Smoke verifies the LV8-derived smoke enforces 40–80 selected instances.
- [x] Smoke verifies the LV8-derived smoke enforces status ok, unplaced 0, one 1500×3000 stock, and no `sheet_002.dxf`.
- [x] Smoke verifies no first-sheet 191 / full-276 / multisheet acceptance wording.
- [x] Smoke verifies no compression wiring or legacy-core regression in Q26 files.
- [x] Smoke verifies report sections and PASS tokens.

## Existing small real-DXF one-sheet smoke

- [x] Run `python3 scripts/smoke_real_dxf_sparrow_pipeline.py`.
- [x] Record whether it passed or explain exact missing dependency / failure.
- [x] Keep this separate from the LV8-derived one-sheet validation.

## Report

- [x] Create `codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md`.
- [x] Include all required Q26 report sections.
- [x] Include changed file list.
- [x] Include exact command results.
- [x] Include PASS tokens only if all gates support them.
- [x] Include failure diagnostics for any failed fixture.
- [x] Include LV8 selected source files, selected quantities, total instances, sheet size, spacing/margin, command, output metrics, and artifact list.

## Verification

- [x] Run `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`.
- [x] Run `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`.
- [x] Run `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation -- --nocapture`.
- [x] Run `python3 scripts/smoke_sgh_q26_single_sheet_validation_suite.py`.
- [x] Run `python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py`.
- [x] Run `python3 scripts/smoke_real_dxf_sparrow_pipeline.py`.
- [x] Run `./scripts/check.sh`.
- [x] Run `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md`.

## Closure note

- Rust suite: 8/8 green; `cargo test --lib` 454/454 green.
- LV8-derived gate: 63 instances (11 LV8 types) on one 1500x3000 sheet, status ok, unplaced 0, sheet 0 only, no `sheet_002.dxf`.
- LV8 parts consumed via committed normalized derivatives (`samples/real_work_dxf/0014-01H/lv8jav_normalized/`); raw `lv8jav` files are not importable by the strict-layer `dxf_v1` pipeline (documented in the report).
- No production solver / pipeline code changed.
