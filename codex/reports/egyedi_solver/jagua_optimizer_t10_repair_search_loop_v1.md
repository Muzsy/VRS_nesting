PASS

# Report — JG-10 `jagua_optimizer_t10_repair_search_loop_v1`

## Dependency evidence

- `codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md` exists, first line `PASS`, contains `JG-10_STATUS: READY`.
- `vrs_nesting/runner/vrs_solver_runner.py` contains `validation_status`, `validation_error`, `utilization` fields added in JG-09.
- `scripts/smoke_jagua_exact_validation_bridge.py` exists (JG-09 bridge artifact).

## Real code audit

| File | Finding |
|---|---|
| `optimizer/moves.rs` | `CandidateMove` skeleton present; translate/reinsert captured via candidate coordinates |
| `optimizer/state.rs` | `LayoutState` / `PlacementTransform` present; JG-10 uses `io::Placement` directly (no LayoutState conversion in V1) |
| `optimizer/initializer.rs` | `build_initial_layout()` + `bbox_from_placement()` confirmed; `bbox_from_placement` re-used by repair for placed-bbox tracking |
| `optimizer/candidates.rs` | `generate_candidates()` deterministic (sorted sheet_idx → y → x); `PlacedBbox::overlaps()` rect-rect check confirmed |
| `adapter.rs` Phase 1 branch | `build_initial_layout()` → `run_repair()` → `(p, u, _rd)` pipeline confirmed |
| JG-09 runner exact validation path | `_validate_contract_fields()` wrapped in try/except; `validation_status=pass/fail` written to `runner_meta.json` |

## Repair design decision

**DEVIATION from LayoutState**: JG-10 V1 operates directly on `Vec<io::Placement>` / `Vec<io::Unplaced>` rather than converting to `LayoutState`. Rationale: Phase 1 rectangular items carry all needed geometry in their bbox; LayoutState conversion adds overhead without benefit at this stage. LayoutState integration is deferred to JG-11+ score-based optimizer.

**No RNG**: determinism achieved via sorted candidate generation and sorted repair queue (area desc → instance_id asc). No `rand` crate dependency added.

## Implemented files

| File | Status |
|---|---|
| `rust/vrs_solver/src/optimizer/stopping.rs` | NEW — `StoppingPolicy`: `max_iterations` + `time_limit_s`; `StopReason`: Converged / MaxIterations / TimeLimit; 5 unit tests |
| `rust/vrs_solver/src/optimizer/repair.rs` | NEW — `find_violations()`, `run_repair()`, `ViolationType`, `RepairDiagnostics`; 9 unit tests |
| `rust/vrs_solver/src/optimizer/mod.rs` | MODIFIED — `pub mod repair; pub mod stopping;` added |
| `rust/vrs_solver/src/adapter.rs` | MODIFIED — Phase 1 branch: `build_initial_layout()` → `run_repair()` pipeline |
| `rust/vrs_solver/src/io.rs` | MODIFIED — `#[derive(Clone)]` added to `Placement` and `Unplaced` for repair test code |
| `scripts/smoke_jagua_repair_search_v1.py` | NEW — 12 checks |

## StoppingPolicy

- `StoppingPolicy::new(max_iterations, time_limit_s)` — starts internal `Instant`.
- `tick()` → increments iteration counter, returns `should_stop()`.
- `should_stop()` → true if `iteration >= max_iterations` OR `elapsed_s() >= time_limit_s`.
- `stop_reason()` → `TimeLimit` if time exceeded (checked first), else `MaxIterations`, else `Converged`.
- Used in adapter: `StoppingPolicy::new(256, repair_time_s)` where `repair_time_s = input.time_limit_s.max(1.0)`.
- Unit tests: `test_max_iterations_stops`, `test_time_limit_zero_stops`, `test_converged_reason`, `test_max_iter_reason`, `test_iteration_counter`.

## RepairEngine

### find_violations

Sequential scan over `placements`. For each placement:
1. Check `bbox_from_placement()` → if sheet_index out-of-range or not `rect_inside_sheet_shape()` → `BoundaryOrSheet`.
2. Check overlap vs all previously accepted bboxes → `Overlap`.
Returns `Vec<(index, ViolationType)>`.

### run_repair

1. `find_violations()` → `violation_indices: HashSet<usize>`.
2. Split placements: valid (not in violation_indices) vs `repair_queue`.
3. Non-`PART_NEVER_FITS_STOCK` unplaced items added to `repair_queue`.
4. `repair_queue` sorted: area desc → instance_id asc (deterministic).
5. Build `placed_bboxes` from valid placements.
6. For each repair item:
   - `policy.should_stop()` → if true: push `REPAIR_STOPPED` reason.
   - `policy.tick()`.
   - `generate_candidates(&placed_bboxes, sheets)` → candidate (sheet_idx, x, y) list.
   - Try each candidate × allowed_rotation:
     - `bbox_from_rotation()` → boundary check → overlap check → if valid: place and break.
   - If no candidate succeeded: push `REPAIR_FAILED` unplaced.

### Diagnostics

`RepairDiagnostics`: `overlap_detected`, `boundary_detected`, `attempts`, `successes`, `failures`, `stopped_by_policy`, `stop_reason` (string).

## Repair attempt/success/fail metrics (from unit tests)

| Test scenario | attempts | successes | failures |
|---|---|---|---|
| No violations | 0 | 0 | 0 |
| Overlap repaired | ≥1 | 1 | 0 |
| Boundary repaired | ≥1 | 1 | 0 |
| Repair failed (no room) | ≥1 | 0 | 1 |
| Policy stops mid-repair | ≥1 | 0 | 0 (stopped_by_policy=1+) |

All 9 repair unit tests cover these scenarios deterministically.

## Cargo build and test results

```
cargo build --manifest-path rust/vrs_solver/Cargo.toml
→ PASS (exit 0)

cargo test --manifest-path rust/vrs_solver/Cargo.toml
→ 49 passed; 0 failed; 0 ignored
  (includes: 5 stopping tests, 9 repair tests, all pre-existing tests)
```

## Smoke results: smoke_jagua_repair_search_v1.py

```
=== JG-10 Repair Search V1 Smoke ===
Check 1: Rust repair unit tests (cargo test optimizer::repair)     PASS
Check 2: Rust stopping unit tests (cargo test optimizer::stopping) PASS
Check 3: Integration valid fixture → runner exit 0                 PASS
Check 4: validation_status=pass (JG-09 bridge active with repair)  PASS
Check 5: metrics fields present (duration_sec, placements_count…)  PASS (5 fields)
Check 6: Overlap evidence — bridge rejects overlapping layout      PASS
Check 7: Boundary evidence — bridge rejects out-of-sheet layout    PASS
Check 8: Regression smoke_jagua_initial_construction.py (JG-08)   PASS
Check 9: Regression smoke_jagua_exact_validation_bridge.py (JG-09) PASS

=== RESULTS: 12 PASS, 0 FAIL ===
OVERALL: PASS
```

## Contract invariants confirmed

- `SolverOutput` v1 contract not broken; `Metrics` fields unchanged.
- `jagua-rs` types do not appear in public VRS output or runner contract.
- Invalid layout cannot pass as success: exact validation bridge (`validate_multi_sheet_output`) is the final gate; any overlap or out-of-sheet placement raises `ValueError` before `validation_status=pass` is written.
- Every instance is either placed or in `unplaced` with an explicit reason (`PART_NEVER_FITS_STOCK` / `NO_CAPACITY` / `REPAIR_FAILED` / `REPAIR_STOPPED`). Silent geometry loss: none.
- Rust Metrics backward-compatible: no fields removed or renamed.

## Globális progress checklist

`canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-10 szakasza: `[x] Kész`.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T00:38:12+02:00 → 2026-05-24T00:41:15+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.verify.log`
- git: `main@d05f964`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     | 32 +++++++++++-----------
 rust/vrs_solver/src/adapter.rs                     | 12 ++++++--
 rust/vrs_solver/src/io.rs                          |  4 +--
 rust/vrs_solver/src/optimizer/mod.rs               |  2 ++
 4 files changed, 30 insertions(+), 20 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/mod.rs
?? canvases/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t10_repair_search_loop_v1.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1/
?? codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
?? codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.verify.log
?? rust/vrs_solver/src/optimizer/repair.rs
?? rust/vrs_solver/src/optimizer/stopping.rs
?? scripts/smoke_jagua_repair_search_v1.py
```

<!-- AUTO_VERIFY_END -->

JG-11_STATUS: READY
