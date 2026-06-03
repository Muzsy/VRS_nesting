# SGH-Q26 Single-sheet Sparrow validation test suite — revised with explicit LV8-derived one-sheet gate

## Why this task exists

Q25-R6 closed the known strict Sparrow parity gaps for the native fixed-sheet core:
strict touching policy, upstream-like budgets, worker ordering, separator limits, convex-hull disruption, and upstream mapping.

The next step is not another porting/refactor task. The next step is a serious validation suite that proves the native `sparrow_cde` path works across increasingly demanding **single-sheet** cases.

The previous Q26 draft was too soft on the "serious" level. This revised Q26 makes the high-end single-sheet validation explicit:

```text
Level 4B: LV8-derived 40–80 instance real-DXF single-sheet validation
Source: samples/real_work_dxf/0014-01H/lv8jav
Sheet: 1500×3000, quantity=1
Goal: status ok, all selected instances placed on sheet 0, no sheet_002, strict native Sparrow/CDE diagnostics
Not a goal: first-sheet-191, full-276, utilization benchmark, multisheet benchmark
```

This is still **not** a 191-piece first-sheet benchmark and not the full 276-piece LV8 benchmark. It is a correctness/stability gate using real LV8 geometry at a materially harder size than toy fixtures.

## Required outcome

After SGH-Q26 the repo must contain a staged validation suite for the production `sparrow_cde` path:

```text
Level 0: strict parity invariants remain guarded.
Level 1: tiny/easy single-sheet solves place all requested instances on sheet 0.
Level 2: rotation/irregular/strict-CDE cases place all requested instances on sheet 0.
Level 3: medium synthetic single-sheet cases place all requested instances on sheet 0.
Level 4A: serious synthetic 40–80 instance one-sheet fixture passes deterministically.
Level 4B: LV8-derived 40–80 instance real-DXF one-sheet validation passes through the existing DXF pipeline.
Level 5: existing small real-DXF one-sheet smoke remains covered.
```

The suite must be deterministic, auditably one-sheet-only, and must assert the correct diagnostics: native Sparrow active, native tracker active, old core not used, compression inactive, CDE backend active, no bbox fallback.

## Scope classification

This is a **test-suite task**.

Allowed implementation work:

- add Rust integration tests;
- add JSON fixture files if needed;
- add a deterministic LV8-derived fixture manifest if needed;
- add a Python LV8-derived one-sheet smoke using the existing repo DXF pipeline;
- add/extend a Q26 smoke script that validates the new test suite, the LV8-derived smoke, and report;
- add the Q26 report/checklist artifacts.

Not allowed:

- solver algorithm changes to make tests pass;
- benchmark-driven tuning;
- first-sheet-191 or full-276 LV8 gate;
- multisheet fixture gate;
- compression work;
- lowering strict Sparrow parity constraints;
- reintroducing legacy VRS core paths into `optimizer/sparrow`.

If a Q26 test fails because the solver has a real bug, the correct output is **FAIL with exact failing fixture and diagnostics**, not silent solver rewriting.

## Source of truth

Read before editing:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
rust/vrs_solver/Cargo.toml
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
rust/vrs_solver/src/optimizer/sparrow/tests.rs
scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py
scripts/smoke_real_dxf_sparrow_pipeline.py
scripts/run_real_dxf_sparrow_pipeline.py
samples/dxf_demo/stock_rect_1000x2000.dxf
samples/dxf_demo/part_arc_spline_chaining_ok.dxf
samples/dxf_demo/part_arc_heavy_ok.dxf
samples/real_work_dxf/test_dxf/L-alak-BodyPad.dxf
samples/real_work_dxf/test_dxf/Macskanyelv-BodyPad.dxf
samples/real_work_dxf/test_dxf/Negyzet_120x120-BodyPad.dxf
samples/trial_run_quality/fixtures/circles_dense_pack/stock.dxf
samples/trial_run_quality/fixtures/lshape_rect_mix/stock.dxf
samples/trial_run_quality/fixtures/triangles_rotation_pair/stock.dxf
samples/real_work_dxf/0014-01H/lv8jav
samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf
```

Do not invent APIs. If a fixture route is not realistically usable, document it and use the closest existing repo path instead.

## Scope hygiene gate

At task start run:

```bash
git status --porcelain=v1
git diff --name-only
```

Report:

```text
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
```

Do not revert unrelated dirty files. Only fail the task if your own changes create new out-of-scope diffs.

## Hard exclusions

Do not:

- add or wire compression;
- use LV8 first-sheet-191 or full-276 as an acceptance criterion;
- require more than one sheet in any new Q26 fixture;
- change the solver to pass tests unless the bug is a narrow test-infra issue and is explicitly reported;
- change strict profile budgets/limits/touching policy from Q25-R6;
- introduce `WorkingLayout`, `VrsCollisionTracker`, bbox/AABB/proxy ranking, or legacy fallback into `optimizer/sparrow`;
- weaken validation to allow partial result on positive fixtures;
- hide a failing fixture behind `PASS_WITH_NOTES`;
- call the LV8-derived 40–80 validation a benchmark or optimize utilization against it.

## Required implementation details

### 1. Add a dedicated Rust integration validation suite

Create:

```text
rust/vrs_solver/tests/sparrow_single_sheet_validation.rs
```

This test file must use the public crate boundary where possible:

```rust
use vrs_solver::adapter;
use vrs_solver::io::SolverInput;
```

It may construct `SolverInput` through `serde_json::from_value` to avoid fragile struct boilerplate.

Every positive fixture must set:

```json
"contract_version": "v1",
"solver_profile": "jagua_optimizer_phase1_outer_only",
"optimizer_pipeline": "sparrow_cde",
"collision_backend": "cde",
"stocks": [{"id": "S", "quantity": 1, "width": ..., "height": ...}],
"margin_mm": 0.0
```

Every positive fixture must assert:

```text
status == "ok"
metrics.unplaced_count == 0
metrics.placed_count == requested_count
all placements have sheet_index == 0
metrics.sheet_count_used == 1
optimizer_diagnostics.pipeline_used == "sparrow_cde"
optimizer_diagnostics.sparrow_invoked == Some(true)
optimizer_diagnostics.sparrow_converged == Some(true)
optimizer_diagnostics.sparrow_native_model_active == Some(true)
optimizer_diagnostics.sparrow_native_tracker_active == Some(true)
optimizer_diagnostics.sparrow_old_core_used == Some(false)
optimizer_diagnostics.sparrow_compression_passes == Some(0)
optimizer_diagnostics.loss_bbox_proxy_used_as_primary == Some(false)
collision_backend_diagnostics.backend_used == "cde_adapter"
collision_backend_diagnostics.bbox_fallback_queries == 0
```

The suite must also include a negative overcapacity test. That test must assert partial/unsupported is reported honestly with diagnostics; it must not require all items to place.

### 2. Required Rust test names and fixture intent

Add these tests, or equivalent names only if the report explains a repo constraint:

```text
q26_single_sheet_tiny_rectangles_all_placed
q26_single_sheet_requires_90_degree_rotation_all_placed
q26_single_sheet_strict_cde_irregular_l_shape_mix_all_placed
q26_single_sheet_medium_rect_mix_all_placed
q26_single_sheet_medium_mixed_rotations_all_placed
q26_single_sheet_serious_synthetic_40_to_80_instances_all_placed
q26_single_sheet_deterministic_same_seed_same_output
q26_single_sheet_negative_overcapacity_reports_partial_with_diagnostics
```

Fixture guidance:

- **Tiny rectangles:** 2–4 rectangles on a 200×200 or 300×300 sheet.
- **90° rotation required:** include at least one part that only fits when 90° is allowed, e.g. `width > sheet.width`, `height < sheet.width`, rotated height fits sheet height.
- **Irregular L-shape mix:** use `outer_points` on at least one L-shaped or concave part and at least one rectangle. Keep density modest enough that it should place reliably.
- **Medium rect mix:** 15–30 instances, 45–65% rough area utilization, all on one sheet.
- **Medium mixed rotations:** 15–35 instances with `[0, 90]` and at least one `[0, 45, 90]` candidate domain; do not make 45° mandatory unless you prove it is deterministic.
- **Serious synthetic:** 40–80 instances on a single sheet, roughly 55–75% area utilization. This must be harder than the tiny/medium tests but not a near-perfect packing benchmark.
- **Determinism:** run the same serious or medium fixture twice with the same seed and compare status, placements count, unplaced count, and exact ordered placement records within a small epsilon.
- **Negative overcapacity:** area or dimensions make all instances impossible on one sheet; expect partial/unsupported with diagnostics, not silent `ok`.

Important: Do **not** create synthetic fixtures that require Nest&Cut-level optimization to pass. This is a solver correctness/stability suite, not final industrial density benchmarking.

### 3. Required LV8-derived 40–80 instance one-sheet validation

Create a dedicated Python smoke:

```text
scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py
```

This smoke must use the repo's existing real-DXF pipeline, not a fake synthetic substitute:

```text
scripts/run_real_dxf_sparrow_pipeline.py
samples/real_work_dxf/0014-01H/lv8jav/*.dxf
```

Required project contract:

```json
{
  "version": "dxf_v1",
  "name": "q26_lv8_derived_single_sheet_validation",
  "seed": 0,
  "time_limit_s": 300,
  "units": "mm",
  "spacing_mm": 10.0,
  "margin_mm": 10.0,
  "stocks": or "stocks_dxf": exactly one 1500×3000 stock with quantity 1,
  "parts_dxf": deterministic LV8 subset totaling 40–80 instances
}
```

Implementation requirements:

- Use only real LV8 DXF part files from `samples/real_work_dxf/0014-01H/lv8jav`.
- Ignore backup files such as `*.dxf~`.
- Parse quantity from filename `..._<N>db...` or use an existing repo helper if available.
- Build a deterministic subset totaling **40–80 instances**.
- Prefer broad coverage across many LV8 part types rather than repeating only one easy part.
- Do not use the full 191 first-sheet set.
- Do not use the full 276 package.
- One 1500×3000 sheet only.
- Use `optimizer_pipeline=sparrow_cde` / CDE path if the pipeline contract supports explicit solver options; otherwise assert the produced solver input contains those options.
- Assert report/output status is `ok`.
- Assert `unplaced_count == 0`.
- Assert `placements_count == selected_instance_count`.
- Assert every placement is on sheet 0 / first sheet.
- Assert no second sheet artifact is produced: no `sheet_002.dxf`.
- Assert native Sparrow diagnostics if present in produced `solver_output.json`.
- Emit a compact JSON/markdown manifest of selected source files and quantities under:

```text
rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/lv8_derived_subset_manifest.json
```

If the existing real-DXF pipeline cannot currently create a 1500×3000 stock without a stock DXF fixture, the task must create the smallest valid repo-native stock fixture or documented project JSON contract needed for this smoke. Do not skip the LV8-derived gate merely because the old small real-DXF smoke uses `stock_rect_1000x2000.dxf`.

If `ezdxf` or another declared DXF dependency is missing in the environment, report the exact dependency failure. This may be `PASS_WITH_NOTES` only if all non-DXF gates pass and the repo's existing `scripts/check.sh` already treats the same missing dependency as acceptable. Otherwise the task is FAIL.

### 4. Optional JSON fixtures for Rust tests

If the integration tests become too large, create small fixture files under:

```text
rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/
```

Allowed fixture files:

```text
tiny_rectangles.json
rotation_90_required.json
irregular_l_shape_mix.json
medium_rect_mix.json
medium_mixed_rotations.json
serious_synthetic_single_sheet.json
negative_overcapacity.json
lv8_derived_subset_manifest.json
```

Every Q26 JSON solver fixture must contain exactly one stock entry with `quantity: 1`.

If inline Rust JSON fixtures are clearer and smaller, fixture files are optional except for `lv8_derived_subset_manifest.json`, which is required when the LV8-derived smoke runs.

### 5. Add a Q26 static smoke script

Create/update:

```text
scripts/smoke_sgh_q26_single_sheet_validation_suite.py
```

The script must be benchmark-free. It must statically verify:

- the Rust integration test file exists;
- all required Rust test names exist;
- the LV8-derived smoke script exists;
- the LV8-derived smoke references the real LV8 directory;
- the LV8-derived smoke enforces 40–80 selected instances;
- the LV8-derived smoke enforces one 1500×3000 stock, status `ok`, `unplaced_count == 0`, no `sheet_002.dxf`;
- the tests route through `optimizer_pipeline: "sparrow_cde"` and `collision_backend: "cde"`;
- all positive fixtures use a single stock quantity 1 and assert sheet index 0 / `sheet_count_used == 1`;
- the test file asserts native model/tracker flags and old core false;
- the test file asserts compression passes 0;
- the negative overcapacity test exists;
- report sections and PASS tokens are present;
- no Q26 file introduces first-sheet-191 / full-276 / multisheet acceptance wording;
- no Q26 file introduces compression wiring or legacy-core strings.

The smoke may run no solver itself; the actual solver execution is handled by `cargo test --test sparrow_single_sheet_validation` and `python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py`.

### 6. Existing small real-DXF one-sheet coverage

This task should not remove the existing small real-DXF smoke:

```bash
python3 scripts/smoke_real_dxf_sparrow_pipeline.py
```

This covers one simple real DXF stock and one real DXF part through the repo’s existing `dxf_v1` path. The report must record this as **small real-DXF one-sheet smoke**, separate from the **LV8-derived one-sheet validation**.

### 7. Report requirements

Create/update:

```text
codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
```

Required sections:

```text
SGH-Q26_STATUS
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
VALIDATION_LEVELS_IMPLEMENTED
SINGLE_SHEET_FIXTURE_AUDIT
STRICT_PARITY_INVARIANT_AUDIT
NATIVE_SPARROW_DIAGNOSTICS_AUDIT
SERIOUS_SYNTHETIC_SINGLE_SHEET_AUDIT
LV8_DERIVED_SINGLE_SHEET_AUDIT
REAL_DXF_ONE_SHEET_SMOKE_AUDIT
NEGATIVE_FIXTURE_AUDIT
LEGACY_CORE_REGRESSION_GATE
BUILD_TEST_RESULTS
```

Required PASS tokens, only if true:

```text
Q26_SINGLE_SHEET_SUITE: IMPLEMENTED
VALIDATION_LEVELS: MICRO_TO_LV8_DERIVED_SINGLE_SHEET
POSITIVE_FIXTURES: ALL_REQUIRE_STATUS_OK
SHEET_SCOPE: SINGLE_SHEET_ONLY
NATIVE_SPARROW_FLAGS: ASSERTED
COMPRESSION_STATUS: DEFERRED_ONLY
LEGACY_CORE_STATUS: NOT_REINTRODUCED
LV8_DERIVED_SINGLE_SHEET_VALIDATION: PASS
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE
FIRST_SHEET_191_STATUS: NOT_USED
FULL_276_STATUS: NOT_USED
REAL_DXF_ONE_SHEET_SMOKE: RUN_OR_EXPLAINED
OUT_OF_SCOPE_NEW_CHANGES: NONE
```

The LV8 audit section must include:

```text
LV8 source directory
selected source DXF files
per-file selected quantity
total selected instances
sheet size
spacing/margin
command run
status
placements_count
unplaced_count
sheet artifact list
native Sparrow/CDE diagnostics summary
```

### 8. Mandatory verification commands

Run and record:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation -- --nocapture
python3 scripts/smoke_sgh_q26_single_sheet_validation_suite.py
python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py
python3 scripts/smoke_real_dxf_sparrow_pipeline.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
```

If the LV8-derived smoke fails because the solver cannot place 40–80 real LV8 instances on one sheet, do not tune the solver inside this task. Mark SGH-Q26 as FAIL and include exact diagnostics. The next task will then be a solver bugfix/quality task based on that evidence.
