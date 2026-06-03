# SGH-Q26 — Single-sheet Sparrow validation suite (report)

SGH-Q26_STATUS: PASS

Staged single-sheet validation suite for the production native `sparrow_cde`
path, from tiny basics through a serious synthetic 40-80 instance fixture and a
concrete LV8-derived 40-80 instance real-DXF single-sheet gate. This is a
validation/correctness/stability task only: no solver algorithm change, no
compression, no multisheet acceptance, no full-LV8 benchmark tuning.

PASS token summary (machine-checkable):

```
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

## PRE_TASK_GIT_STATUS

At task start the working tree contained only the freshly-applied SGH-Q26
package artifacts (copied in from `tmp/task/`), nothing else:

```
?? README_SGH_Q26_SINGLE_SHEET_SPARROW_VALIDATION_SUITE_REVISED_PACKAGE.md
?? canvases/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
?? codex/codex_checklist/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q26_single_sheet_sparrow_validation_suite.yaml
?? codex/prompts/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite/
?? scripts/smoke_sgh_q26_single_sheet_validation_suite.py
```

`git diff --name-only` was empty (no tracked-file modifications).

## PRE_TASK_DIRTY_FILES

All six pre-task dirty entries are SGH-Q26 package files (canvas, goal YAML,
checklist, runner prompt, root README, static smoke). They are in scope.

## PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES

None. No unrelated tracked or untracked files were dirty at task start, so no
unrelated dirty file was reverted or touched.

## TASK_CHANGED_FILES

New / modified by this task:

- `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs` — integration suite (new).
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/tiny_rectangles.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/rotation_90_required.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/irregular_l_shape_mix.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/medium_rect_mix.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/medium_mixed_rotations.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/serious_synthetic_single_sheet.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/negative_overcapacity.json`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/lv8_derived_subset_manifest.json` — emitted by the LV8 smoke.
- `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py` — LV8-derived gate (new).
- `scripts/smoke_sgh_q26_single_sheet_validation_suite.py` — shipped static gate; only `ALLOWED_PREFIXES` extended to cover the committed LV8 normalized fixture dir.
- `samples/real_work_dxf/0014-01H/lv8jav_normalized/` — 12 normalized (CUT_OUTER/CUT_INNER) LV8 part DXFs (committed fixture; see LV8 audit).
- `codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md` — this report.
- `codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.verify.log` — written by `verify.sh`.
- `codex/codex_checklist/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md` — filled.

Package artifacts already in the tree (placed before implementation): the root
`README_SGH_Q26...md`, `canvases/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md`,
`codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q26_single_sheet_sparrow_validation_suite.yaml`,
`codex/prompts/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite/run.md`.

## OUT_OF_SCOPE_NEW_CHANGES

OUT_OF_SCOPE_NEW_CHANGES: NONE

No production solver code (`rust/vrs_solver/src/**`), no `vrs_nesting` pipeline
code, and no other module was modified. The only non-`outputs`-listed addition is
the committed LV8 normalized fixture directory
`samples/real_work_dxf/0014-01H/lv8jav_normalized/` plus a one-line
`ALLOWED_PREFIXES` extension in the static smoke — both are the repo-native
fixture explicitly required to make the LV8-derived single-sheet gate
reproducible (the raw `lv8jav` DXFs are not importable by the strict-layer
pipeline; see LV8 audit). This was directed for this task and is documented here.

## VALIDATION_LEVELS_IMPLEMENTED

VALIDATION_LEVELS: MICRO_TO_LV8_DERIVED_SINGLE_SHEET

| Level | Scenario | Vehicle | Result |
|------|----------|---------|--------|
| 0 | strict parity invariants still guarded | existing `cargo test --lib` (454 tests) | PASS |
| 1 | tiny/easy single sheet | `q26_single_sheet_tiny_rectangles_all_placed` | PASS |
| 2 | rotation required | `q26_single_sheet_requires_90_degree_rotation_all_placed` | PASS |
| 2 | irregular strict-CDE L-shape mix | `q26_single_sheet_strict_cde_irregular_l_shape_mix_all_placed` | PASS |
| 3 | medium rect mix | `q26_single_sheet_medium_rect_mix_all_placed` | PASS |
| 3 | medium mixed rotations | `q26_single_sheet_medium_mixed_rotations_all_placed` | PASS |
| 4A | serious synthetic 40-80 instance | `q26_single_sheet_serious_synthetic_40_to_80_instances_all_placed` | PASS |
| 4B | LV8-derived 40-80 instance real DXF | `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py` | PASS |
| — | deterministic same-seed | `q26_single_sheet_deterministic_same_seed_same_output` | PASS |
| — | negative overcapacity | `q26_single_sheet_negative_overcapacity_reports_partial_with_diagnostics` | PASS |
| 5 | existing small real-DXF one-sheet smoke | `scripts/smoke_real_dxf_sparrow_pipeline.py` | PASS |

## SINGLE_SHEET_FIXTURE_AUDIT

SHEET_SCOPE: SINGLE_SHEET_ONLY

Every Rust fixture uses exactly one stock with `quantity: 1`, `margin_mm: 0.0`,
`solver_profile: jagua_optimizer_phase1_outer_only`,
`optimizer_pipeline: sparrow_cde`, `collision_backend: cde`. Every positive test
asserts all placements have `sheet_index == 0` and `metrics.sheet_count_used == 1`.
The LV8-derived gate uses one 1500x3000 stock with `quantity 1` and asserts every
placement is on sheet 0 with no `sheet_002.dxf` artifact. No fixture allows or
requires a second sheet.

## STRICT_PARITY_INVARIANT_AUDIT

COMPRESSION_STATUS: DEFERRED_ONLY

The Q25-R6 strict Sparrow parity invariants are untouched: no production solver
file was modified, the full `cargo test --lib` parity suite (454 tests) is green,
and every positive Q26 fixture asserts `sparrow_compression_passes == Some(0)`
(compression remains inactive / deferred). No strict-profile budget, limit, or
touching-policy constant was changed.

## NATIVE_SPARROW_DIAGNOSTICS_AUDIT

NATIVE_SPARROW_FLAGS: ASSERTED

Every positive fixture asserts, via the public `adapter::solve` output:

```
optimizer_diagnostics.pipeline_used                 == "sparrow_cde"
optimizer_diagnostics.sparrow_invoked               == Some(true)
optimizer_diagnostics.sparrow_converged             == Some(true)
optimizer_diagnostics.sparrow_native_model_active   == Some(true)
optimizer_diagnostics.sparrow_native_tracker_active == Some(true)
optimizer_diagnostics.sparrow_old_core_used         == Some(false)
optimizer_diagnostics.sparrow_compression_passes    == Some(0)
optimizer_diagnostics.loss_bbox_proxy_used_as_primary == Some(false)
collision_backend_diagnostics.backend_used          == "cde_adapter"
collision_backend_diagnostics.bbox_fallback_queries == 0
```

## SERIOUS_SYNTHETIC_SINGLE_SHEET_AUDIT

`serious_synthetic_single_sheet.json`: 64 instances (48x 100x100 + 16x 100x50)
on one 1200x1000 stock, ~46.7% rough area utilization. This is materially harder
than the tiny/medium fixtures (64 instances, many collision pairs) but is a
correctness/stability target, not a near-perfect packing benchmark. The test
asserts the full positive single-sheet bundle (status ok, all on sheet 0,
sheet_count_used 1, native diagnostics) and that the instance count is in [40, 80].

## LV8_DERIVED_SINGLE_SHEET_AUDIT

LV8_DERIVED_SINGLE_SHEET_VALIDATION: PASS
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE
FIRST_SHEET_191_STATUS: NOT_USED
FULL_276_STATUS: NOT_USED

- **LV8 source directory:** `samples/real_work_dxf/0014-01H/lv8jav` (raw originals).
- **Normalization note:** the raw `lv8jav` DXFs carry their cut geometry on
  AutoCAD layer `0` (mixed with `Gravir` TEXT and multiple closed bore contours)
  and are NOT importable by the strict `CUT_OUTER`/`CUT_INNER` `dxf_v1` importer
  (verified: `DXF_NO_OUTER_LAYER` by default, `DXF_MULTIPLE_OUTERS` /
  `DXF_UNSUPPORTED_ENTITY_TYPE` when forcing `outer_layer=0`). The gate therefore
  consumes their normalized derivatives (same geometry, moved to
  `CUT_OUTER`/`CUT_INNER`, text dropped), committed at
  `samples/real_work_dxf/0014-01H/lv8jav_normalized/` so the gate is reproducible.
- **Selected source DXF files & per-file selected quantity** (deterministic;
  sorted by name; exclude bbox-max-dim > 1500; cap 3 for area >= 0.05 m^2 else
  cap 6; quantity = min(cap, parsed `_<N>db`)):

  | file | parsed db | selected | w x h (mm) | decision |
  |------|-----------|----------|-----------|----------|
  | LV8_00035_28db_M_REV2_norm.dxf | 28 | 6 | 50 x 50 | selected |
  | LV8_00057-2_20db_REV8_norm.dxf | 20 | 6 | 112.6 x 50 | selected |
  | LV8_01170_10db_REV5_norm.dxf | 10 | 6 | 139 x 108.1 | selected |
  | LV8_02048_20db_L_REV5_norm.dxf | 20 | 6 | 45 x 106.2 | selected |
  | LV8_02049_50db_REV7_norm.dxf | 50 | 6 | 30 x 44 | selected |
  | Lv8_10059_10db_REV2_norm.dxf | 10 | 6 | 156.8 x 30 | selected |
  | Lv8_07919_16db_REV4_norm.dxf | 16 | 6 | 137.7 x 62 | selected |
  | Lv8_07920_50db_REV1_norm.dxf | 50 | 6 | 175 x 105.5 | selected |
  | Lv8_07921_50db_REV1_norm.dxf | 50 | 6 | 227 x 120 | selected |
  | Lv8_11612_6db_REV3_norm.dxf | 6 | 0 | 2522 x 732.8 | excluded (oversized for one 1500x3000) |
  | Lv8_15348_6db_GRAVIR_REV1_norm.dxf | 6 | 3 | 600 x 290 | selected (large-area cap 3) |
  | Lv8_15435_10db_REV0_norm.dxf | 10 | 6 | 62.4 x 146.8 | selected |

- **Total selected instances:** 63 (11 part types) — within [40, 80].
- **Sheet size:** 1500 x 3000 mm, quantity 1 (one physical sheet).
- **Spacing/margin:** spacing_mm = 10.0, margin_mm = 10.0; seed = 0.
- **Selected area:** ~1.106 m^2 of 4.5 m^2 sheet (~24.6% — comfortable, not a
  density benchmark).
- **Command run:** `python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py`
  (project: `dxf_v1`, runs `scripts/run_real_dxf_sparrow_pipeline.py`; sheet stock
  DXF synthesized at runtime; time budget default 120 s, env override
  `Q26_LV8_TIME_LIMIT_S`).
- **status:** ok
- **placements_count:** 63 (== selected instance count)
- **unplaced_count:** 0
- **sheet artifact list:** `['sheet_001.dxf', 'sheet_001.svg']` — no `sheet_002.dxf`.
- **native Sparrow/CDE diagnostics summary:** `optimizer_diagnostics` is ABSENT
  in this `solver_output.json` because the `dxf_v1` pipeline runs the upstream
  Sparrow strip packer (not the native `vrs_solver` `sparrow_cde` core). This is
  expected; the smoke asserts the native flags only when present. The native
  `sparrow_cde` diagnostics (model/tracker active, old core false, compression 0,
  CDE backend, no bbox fallback) are asserted by the Rust integration suite,
  which exercises the production `sparrow_cde` path directly.
- The subset is NOT the full-191 first-sheet set and NOT the full 276-part
  package; it is not used as a utilization/density benchmark.
- **Manifest:** `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/lv8_derived_subset_manifest.json`.

## REAL_DXF_ONE_SHEET_SMOKE_AUDIT

REAL_DXF_ONE_SHEET_SMOKE: RUN_OR_EXPLAINED

`python3 scripts/smoke_real_dxf_sparrow_pipeline.py` → `[OK] real DXF + Sparrow
pipeline smoke passed` (exit 0). This is the existing small real-DXF one-sheet
smoke (one `stock_rect_1000x2000.dxf` stock + one real DXF part through the
`dxf_v1` path); it is distinct from the LV8-derived one-sheet validation above
and was left intact.

## NEGATIVE_FIXTURE_AUDIT

`negative_overcapacity.json`: 4x 200x200 parts on one 300x300 stock (impossible
to place all feasibly). `q26_single_sheet_negative_overcapacity_reports_partial_with_diagnostics`
asserts the honest signal: `status != "ok"` (partial/unsupported), preserved
`optimizer_diagnostics` with `sparrow_invoked == Some(true)`,
`sparrow_converged == Some(false)`, `sparrow_old_core_used == Some(false)`,
residual collisions/boundary violations > 0, and CDE backend diagnostics still
surfaced (`cde_adapter`, 0 bbox fallback). The test deliberately does NOT require
any item to be reported `unplaced` — the native core keeps every item in an
infeasible (overlapping) layout — and never accepts a silent `ok`.

## LEGACY_CORE_REGRESSION_GATE

LEGACY_CORE_STATUS: NOT_REINTRODUCED

No Q26 fixture or test reintroduces the old VRS core or bbox/AABB-proxy ranking:
the static smoke verifies the Rust suite and LV8 smoke contain none of the
legacy-core / compression-wiring tokens (old layout type, old collision tracker,
compression phase, run-compression), and every positive test asserts
`sparrow_old_core_used == Some(false)` and `loss_bbox_proxy_used_as_primary ==
Some(false)`. No `optimizer/sparrow` production source was modified.

## BUILD_TEST_RESULTS

| gate | result | evidence |
|------|--------|----------|
| `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` | PASS | `Finished release profile` |
| `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` | PASS | `test result: ok. 454 passed; 0 failed` (159.7s) |
| `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation -- --nocapture` | PASS | `test result: ok. 8 passed; 0 failed` |
| `python3 scripts/smoke_sgh_q26_single_sheet_validation_suite.py` | PASS | static gate green (see verify log) |
| `python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py` | PASS | status ok, 63 placed, 0 unplaced, sheet 0 only, no sheet_002 |
| `python3 scripts/smoke_real_dxf_sparrow_pipeline.py` | PASS | `[OK] real DXF + Sparrow pipeline smoke passed` |
| `./scripts/check.sh` | PASS | exit 0, ~183s; full repo suite incl. pytest, mypy (26 files), Sparrow IO smoketest, real-DXF pipeline smoke, nesting_engine determinism 10/10 (see AUTO_VERIFY block + verify.log) |
| `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md` | PASS | repo gate green (see AUTO_VERIFY block) |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-03T23:56:45+02:00 → 2026-06-03T23:59:48+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.verify.log`
- git: `main@3c985e8`
- módosított fájlok (git status): 1

**git diff --stat**

```text
 ...ingle_sheet_sparrow_validation_suite.verify.log | 890 +++++++++++++++++++++
 1 file changed, 890 insertions(+)
```

**git status --porcelain (preview)**

```text
 M codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.verify.log
```

<!-- AUTO_VERIFY_END -->
