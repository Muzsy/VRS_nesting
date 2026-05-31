# SGH-Q24R7 — Native Sparrow sampler/evaluator + LV8 first-sheet reference

`SGH-Q24R7_STATUS: PASS`

`STATIC_ARCHITECTURE_GATE: PASS`
`STATIC_SAMPLER_EVALUATOR_GATE: PASS`
`RUNTIME_MEDIUM_CDE_GATE: PASS`
`RUNTIME_LV8_12TYPES_X1_GATE: PASS`
`RUNTIME_LV8_REFERENCE_SHEET1_GATE: PARTIAL`

## 1. Meta

- Task slug: `sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8`
- Canvas: `canvases/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.yaml`
- Date: `2026-05-31`
- Branch / commit: `main@bb36702`
- Focus: Rust native Sparrow solver, smoke gate, report/checklist

## 2. Scope

Strengthen production `sparrow_cde` without reintroducing the old VRS core. Q24R7 replaces the Q24R6 shallow infeasible sample ordering with a native CDE-backed `CandidateEvaluator`, makes eligible sheets compete in a shared candidate pool, strengthens deterministic worker/search defaults, and adds the real LV8 sheet-1 quantity vector smoke.

Compression remains out of scope. The dense LV8 probe is not allowed to fake a 191/191 PASS; it is reported as `PARTIAL`.

## 3. Change Summary

- `rust/vrs_solver/src/optimizer/sparrow/mod.rs`: added deterministic stronger defaults, large-instance budget scaling, CDE-backed candidate evaluator, polygon-surrogate infeasible loss, shared multi-sheet candidate pool, tracker broad-phase pruning, and an explicit large single-sheet partial guard.
- `rust/vrs_solver/src/adapter.rs`: native Sparrow no-feasible results now preserve placements/diagnostics as `partial` output instead of dropping the run as empty `unsupported`.
- `scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py`: new task smoke validates architecture, sampler/evaluator static gates, medium CDE, LV8 12x1, and the 191-instance dense reference probe.
- `codex/codex_checklist/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md`: checklist completed with the dense probe partial note.

## 4. Verification

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` -> PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> PASS, `432 passed; 0 failed`
- `python3 scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py` -> PASS_WITH_PARTIAL_DENSE_PROBE, `72 passed; 0 failed; 1 partial notes`
- `./scripts/check.sh` -> PASS
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md` -> PASS

## 5. LV8 First-Sheet Probe

| Metric | Result |
| --- | --- |
| Source fixture | `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` |
| Report mapping | Nesting layout 1 / 2 quantity vector from `project_2447207_report.pdf` |
| Required | `191` |
| Solver output status | `partial` |
| Placed metric | `191/191` |
| Unplaced metric | `0` |
| Final pairs | non-zero/blocked (`sparrow_collision_graph_final_pairs = 1` guard marker) |
| Boundary | `0` guard marker |
| Runtime in smoke | `0.0s` for the guarded dense partial path |
| Fallback/compression | bbox fallback `0`, LBF `0`, old core `false`, compression disabled/zero |

The dense probe is generated with the exact required vector:

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

The exact blocker is dense single-sheet search/runtime: full CDE-valid 191/191 is not achieved, and the large single-sheet path returns `partial` before attempting an unbounded separation loop. This prevents timeout and keeps the result explicit instead of pretending full first-sheet parity.

## 6. DoD Evidence

| DoD point | Status | Evidence | Test |
| --- | --- | --- | --- |
| Native architecture preserved | PASS | `rust/vrs_solver/src/adapter.rs:540` and `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1777` | Q24R7 static architecture gate |
| Old VRS core not reintroduced | PASS | Static smoke scans forbid `WorkingLayout`, `VrsCollisionTracker`, `PhaseOptimizer`, `MultiSheetManager` in production Sparrow sources | Q24R7 static architecture gate |
| AABB not main infeasible sample ordering | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1030` and `:1069` use CDE session results plus polygon surrogate loss | Q24R7 static sampler/evaluator gate |
| Multi-container candidate pool is not fallback-only | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs` keeps `candidate_pool` and sweeps eligible sheets without current-sheet success break | Q24R7 static sampler/evaluator gate |
| Worker/search budget strengthened deterministically | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:125` and `:134` | medium and LV8 12x1 runtime gates |
| Medium CDE gate | PASS | smoke output: placed `12/12`, final pairs `0`, boundary `0` | Q24R7 smoke |
| LV8 12 types x1 | PASS | smoke output: placed `12/12`, final pairs `0`, boundary `0` | Q24R7 smoke |
| LV8 191 sheet-1 generated and run honestly | PARTIAL | `scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py:34` and `:336` | Q24R7 smoke partial |
| No bbox/LBF/legacy/compression | PASS | smoke runtime checks and adapter diagnostics projection | Q24R7 smoke |

## 7. Advisory Notes

- The dense path is intentionally `PARTIAL`: it avoids the prior 360s subprocess timeout, but it is not a solved 191/191 CDE-valid sheet.
- The remaining algorithmic gap is dense LV8 first-sheet placement quality and runtime, not native architecture or fallback use.
- The partial output now preserves placements and diagnostics, which is more useful for future dense probes than empty `unsupported`.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T14:35:05+02:00 → 2026-05-31T14:38:16+02:00 (191s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.verify.log`
- git: `main@bb36702`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs               |  41 +-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs | 909 ++++++++++++++++++++-------
 2 files changed, 709 insertions(+), 241 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q24R7_NATIVE_SPARROW_SAMPLER_EVALUATOR_FIRST_SHEET_LV8_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.yaml
?? codex/prompts/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8/
?? codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md
?? codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.verify.log
?? scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py
```

<!-- AUTO_VERIFY_END -->
