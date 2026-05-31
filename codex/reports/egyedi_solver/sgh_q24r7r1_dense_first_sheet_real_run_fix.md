# SGH-Q24R7-R1 — Dense first-sheet real-run fix

`SGH-Q24R7R1_STATUS: PASS`

`STATIC_ARCHITECTURE_GATE: PASS`
`STATIC_DENSE_GUARD_GATE: PASS`
`RUNTIME_MEDIUM_CDE_GATE: PASS`
`RUNTIME_LV8_12TYPES_X1_GATE: PASS`
`RUNTIME_LV8_REFERENCE_SHEET1_REAL_RUN_GATE: PASS`
`RUNTIME_LV8_REFERENCE_SHEET1_FIT_GATE: PARTIAL`

## 1. Meta

- Task slug: `sgh_q24r7r1_dense_first_sheet_real_run_fix`
- Canvas: `canvases/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r7r1_dense_first_sheet_real_run_fix.yaml`
- Date: `2026-05-31`
- Focus: repair Q24R7 dense LV8 first-sheet probe so it is a real bounded native Sparrow CDE run, not an early guarded partial.

## 2. Change Summary

- Removed the production early `SparrowSolveResult` return for `instances >= 100` and one sheet.
- Replaced the skip with bounded dense behavior inside the native lifecycle: constructive seed, native tracker build, separation loop, worker competition, native search, CDE candidate/session queries, and final CDE validation diagnostics.
- Added backward-compatible dense diagnostics: `sparrow_dense_guard_used`, `sparrow_dense_real_run`, `sparrow_dense_partial_reason`, `sparrow_dense_validated_placements`, `sparrow_dense_unresolved_instances`, and `sparrow_dense_final_validation_ran`.
- Preserved production `sparrow_cde` native architecture; no legacy/LBF/bbox/compression path was introduced.

## 3. Verification

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` -> PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> PASS, `432 passed; 0 failed`
- `python3 scripts/smoke_sgh_q24r7r1_dense_first_sheet_real_run_fix.py` -> PASS_WITH_DENSE_FIT_PARTIAL, `72 passed; 0 failed; 1 partial notes`
- `./scripts/check.sh` -> PASS
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md` -> PASS

## 4. Dense LV8 Reference Sheet-1 Probe

| Metric | Result |
| --- | ---: |
| Source fixture | `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` |
| Stock sheets | `1` |
| Required instances | `191` |
| Solver status | `partial` |
| Output placement metric | `191/191` seed/output placements, not treated as solved |
| CDE-validated placements | `36` |
| Unresolved/colliding instances | `155` |
| Unplaced output count | `0` |
| Runtime | `9.908s` |
| Initial final-pair sample | `96` |
| Final collision pairs | `178` |
| Boundary violations | `0` |
| Initial raw/weighted loss | `5477.485879469028 / 5477.485879469028` |
| Final raw/weighted loss | `9098.819368203358 / 9098.819368203358` |
| Iterations | `3` |
| Exploration iterations | `1` |
| Search calls | `6` |
| Search samples | `74` |
| Worker passes | `3` |
| Worker candidates evaluated | `6` |
| CDE activity proof | `cde_batch_candidate_queries=368`, `cde_batch_collisions_returned=552`, smoke aggregate `718` |
| Dense guard used | `false` |
| Dense real run | `true` |
| Dense final validation ran | `true` |
| Dense partial reason | `unresolved_collisions` |
| Compression passes | `0` |
| LBF fallback used | `0` |
| Old core used | `false` |
| BBox fallback queries | `0` |

Top unresolved instance ids, first 20:

```text
LV8_00035_28db__0002
LV8_00035_28db__0003
LV8_00035_28db__0004
LV8_00035_28db__0005
LV8_00035_28db__0006
LV8_00035_28db__0007
LV8_00035_28db__0008
LV8_00035_28db__0009
LV8_00035_28db__0010
LV8_00035_28db__0011
LV8_00035_28db__0012
LV8_00035_28db__0013
LV8_00035_28db__0014
LV8_00035_28db__0015
LV8_00035_28db__0016
LV8_00035_28db__0017
LV8_00035_28db__0018
LV8_00035_28db__0019
LV8_00035_28db__0020
LV8_00035_28db__0021
```

## 5. LV8 First-Sheet Quantity Vector

```text
LV8_01170_10db=10
LV8_02048_20db=7
LV8_02049_50db=50
Lv8_07919_16db=13
Lv8_07920_50db=12
Lv8_07921_50db=33
Lv8_15435_10db=10
Lv8_11612_6db=3
Lv8_15348_6db=4
Lv8_10059_10db=10
LV8_00035_28db=28
LV8_00057_20db=11
TOTAL=191
```

## 6. DoD Evidence

| DoD point | Status | Evidence |
| --- | --- | --- |
| Native architecture preserved | PASS | Static smoke: `SparrowProblem`, `SparrowOptimizer::solve`, `SparrowCollisionTracker`, `SparrowSolution` present |
| Old VRS core not reintroduced | PASS | Static smoke forbids `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, `MultiSheetManager` in production Sparrow sources |
| Dense shortcut removed | PASS | Static dense guard gate found no pre-search `SparrowSolveResult` return and no `instances.len()>=100&&sheets.len()==1` shortcut |
| Dense probe real run | PASS | Runtime: `10.1s`, `sparrow_iterations=3`, `search_calls=6`, `search_samples=74`, `worker_candidates=6`, CDE query activity non-zero |
| Dense final validation diagnostics | PASS | `sparrow_dense_final_validation_ran=true`, final pairs `178`, boundary `0`, partial reason `unresolved_collisions` |
| Honest dense partial semantics | PASS | Solver status `partial`; `placed_count=191` is not used as solved count; `sparrow_dense_validated_placements=36`, unresolved count `155` |
| Medium CDE gate | PASS | Smoke: placed `12/12`, final pairs `0`, boundary `0` |
| LV8 12 types x1 gate | PASS | Smoke: placed `12/12`, final pairs `0`, boundary `0` |
| No bbox/LBF/legacy/compression | PASS | `bbox_fallback_queries=0`, `sparrow_lbf_fallback_used=0`, `sparrow_old_core_used=false`, `sparrow_compression_passes=0` |

## 7. Advisory Notes

- The 191 first-sheet fit remains `PARTIAL`; this task proves a real bounded native CDE run rather than solving the full dense layout.
- The dense path intentionally caps expensive CDE session breadth so the first-sheet probe completes within the smoke cap while still producing non-zero search, worker, and CDE diagnostics.
- Further Q24 work should improve dense placement quality and full all-pairs validation throughput; compression remains out of scope here.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T19:55:48+02:00 → 2026-05-31T19:58:49+02:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.verify.log`
- git: `main@34ad380`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs               |  16 ++
 rust/vrs_solver/src/io.rs                    |  12 ++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs | 250 ++++++++++++++++++++++-----
 3 files changed, 239 insertions(+), 39 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q24R7R1_DENSE_FIRST_SHEET_REAL_RUN_FIX_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r7r1_dense_first_sheet_real_run_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix/
?? codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md
?? codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.verify.log
?? scripts/smoke_sgh_q24r7r1_dense_first_sheet_real_run_fix.py
```

<!-- AUTO_VERIFY_END -->
