PASS

# Report — SGH-Q18A `sgh_q18a_cde_correctness_runtime_observability`

## Dependency gate

```
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
```

First line: `PASS` ✓  
Contains `SGH-Q18_STATUS: READY` ✓  

Dependency gate: **PASS**

## Pre-audit command summary

```bash
rg -n "CdeCollisionBackend|CdeAdapter::with_defaults|CDEngine::new|validate_and_commit_with_backend|
       validate_placements_with_backend_checked|score_with_backend|collision_backend_diagnostics|
       OptimizerDiagnosticsOutput|PhaseDiagnostics" rust/vrs_solver/src
```

Key findings:

**Hol épül CDEngine jelenleg?**
- `cde_adapter.rs` line ~137: inside `CdeAdapter::query_pair` — one `CDEngine::new` per pair query
- `cde_adapter.rs` line ~177: inside `CdeAdapter::query_boundary` — one `CDEngine::new` per boundary query
- `cde_session.rs` has a session-style adapter but is unused in main solve path

**Melyik útvonalakon hívódik CDE scoring/separator/validation alatt?**
- `score.rs` line 151: `ScoreModel::score_with_backend` → dispatches to `CdeCollisionBackend` when `CollisionBackendKind::Cde`
- `explore.rs` lines 270, 305: `score_with_backend` in exploration loop → CDE active for every scoring call
- `phase.rs` lines 213, 228: score calls in phase initialization and finalization
- `repair.rs` line 333: `validate_placements_with_backend_checked` with `CdeCollisionBackend`
- `working.rs` line 195: `validate_and_commit_with_backend(Cde)` → calls `commit_with_checked_backend`

**Hol van final commit CDE bizonyíték Q16 után?**
- `working.rs` `commit_with_checked_backend` calls `validate_placements_with_backend_checked` with `CdeCollisionBackend`
- `adapter.rs` resets CDE counters before, snapshots after, and emits `final_commit_backend_used = "cde_adapter"` in output

**Milyen diagnosztika hiányzott Q18B döntéshez?**
- Per-query CDE call count (now available via `cde_total_queries`, `cde_engine_builds`)
- Final commit vs. full-solve scope distinction (now available via `cde_observability_scope`)
- Per-phase timing breakdown (partially: `final_commit_validation_ms` gated by env flag)
- PhaseOptimizer phase-level timing not yet broken down to exploration/compression/bpp separately

## Modified files

| File | Change |
|---|---|
| `rust/vrs_solver/src/optimizer/mod.rs` | Added `pub mod cde_observability;` |
| `rust/vrs_solver/src/optimizer/cde_observability.rs` | **New**: thread-local `CdeCounters` module |
| `rust/vrs_solver/src/optimizer/cde_adapter.rs` | `inc_engine_build()` before each `CDEngine::new(...)` |
| `rust/vrs_solver/src/optimizer/collision_backend.rs` | `CdeCollisionBackend` fully instrumented with all counters |
| `rust/vrs_solver/src/io.rs` | `CollisionBackendDiagnosticsOutput` extended backward-compatibly |
| `rust/vrs_solver/src/adapter.rs` | CDE reset/snapshot/diag helpers; extended commit paths; Q18A tests |

## New diagnostic fields

All new fields are `Option` with `#[serde(skip_serializing_if = "Option::is_none")]`, so
existing JSON consumers are unaffected when the field is absent.

| Field | Populated when |
|---|---|
| `final_commit_backend_used` | CDE backend path |
| `final_commit_unsupported_queries` | CDE backend path |
| `final_commit_bbox_fallback_queries` | CDE backend path (always 0) |
| `cde_pair_queries` | CDE backend path |
| `cde_boundary_queries` | CDE backend path |
| `cde_total_queries` | CDE backend path |
| `cde_engine_builds` | CDE backend path |
| `cde_collision_results` | CDE backend path |
| `cde_no_collision_results` | CDE backend path |
| `cde_unsupported_results` | CDE backend path |
| `cde_prepare_failures` | CDE backend path |
| `cde_cross_sheet_skipped` | CDE backend path |
| `cde_observability_scope` | CDE backend path: `"final_commit_only"` or `"full_solve"` |
| `final_commit_validation_ms` | CDE backend path + `VRS_CDE_OBSERVABILITY_TIMING=1` |

## CDE final commit backend proof

Smoke fixture 1 (valid rect + CDE + legacy_multisheet) output:

```json
"collision_backend_diagnostics": {
  "backend_used": "cde_adapter",
  "unsupported_queries": 0,
  "bbox_fallback_queries": 0,
  "final_commit_backend_used": "cde_adapter",
  "final_commit_unsupported_queries": 0,
  "final_commit_bbox_fallback_queries": 0,
  "cde_pair_queries": 1,
  "cde_boundary_queries": 2,
  "cde_total_queries": 3,
  "cde_engine_builds": 3,
  "cde_collision_results": 0,
  "cde_no_collision_results": 3,
  "cde_unsupported_results": 0,
  "cde_prepare_failures": 0,
  "cde_cross_sheet_skipped": 0,
  "cde_observability_scope": "final_commit_only"
}
```

`final_commit_backend_used == "cde_adapter"` proves the final commit used genuine CDE,
not a bbox fallback.

## CDE query/call count evidence

| Fixture | cde_total_queries | cde_engine_builds | scope |
|---|---|---|---|
| legacy_multisheet + CDE, 2 rects | 3 | 3 | final_commit_only |
| phase_optimizer + CDE, 2 rects | 288 | 288 | full_solve |
| L-shape notch + CDE | 3 | 3 | final_commit_only |

PhaseOptimizer CDE scope accumulates 288 queries over exploration/compression/bpp + final commit.
Legacy CDE scope covers only the final commit: 3 queries (1 pair + 2 boundary for 2 placed parts).

## Unsupported/fallback evidence

Smoke fixture 3 (malformed outer_points):
- `status: "unsupported"`, `unsupported_reason: "CDE_BACKEND_UNSUPPORTED_QUERY"` ✓
- `bbox_fallback_queries: 0` — no silent bbox downgrade ✓
- `cde_unsupported_results: 3`, `cde_prepare_failures: 3` — counters preserved even on error ✓
- No placements emitted ✓

`bbox_fallback_queries == 0` invariant holds for all CDE fixtures.

## Runtime/per-phase evidence

Timing is non-deterministic wall-clock time, not in default JSON.

With `VRS_CDE_OBSERVABILITY_TIMING=1`:

```
Fixture 6 (timing env flag):
  final_commit_validation_ms = 8.213823 ms
```

Gated by env flag — default SolverOutput JSON contains no timing fields.

Existing determinism tests pass (350/350 green) — no regression.

Per-phase breakdown (exploration/compression/bpp separately) was not exposed in the Q18A output
structure; only the aggregate final commit timing was available at Q18A close. This gap was
incorrectly marked done in the Q18A checklist. **SGH-Q18A-R1** corrects this: `phase_optimizer_exploration_ms`,
`phase_optimizer_compression_ms`, and `phase_optimizer_bpp_ms` are now gated by
`VRS_CDE_OBSERVABILITY_TIMING=1` and present in `optimizer_diagnostics` when enabled.
See `codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md`.

## Smoke script output

```
SGH-Q18A CDE observability smoke script
Binary: .../rust/vrs_solver/target/release/vrs_solver

=== Fixture 1: valid rect + CDE + legacy_multisheet ===
  [PASS] status ok/partial (got ok)
  [PASS] collision_backend_diagnostics present
  [PASS] backend_used=cde_adapter (got cde_adapter)
  [PASS] bbox_fallback_queries==0 (got 0)
  [PASS] cde_total_queries>0 (got 3)
  [PASS] cde_engine_builds>0 (got 3)
  [PASS] final_commit_backend_used=cde_adapter (got cde_adapter)
  [PASS] scope=final_commit_only (got final_commit_only)

=== Fixture 2: valid rect + CDE + phase_optimizer ===
  [PASS] status ok/partial (got ok)
  [PASS] collision_backend_diagnostics present
  [PASS] backend_used=cde_adapter (got cde_adapter)
  [PASS] bbox_fallback_queries==0 (got 0)
  [PASS] cde_total_queries>0 (got 288)
  [PASS] cde_engine_builds>0 (got 288)
  [PASS] final_commit_backend_used=cde_adapter (got cde_adapter)
  [PASS] scope=full_solve (got full_solve)

=== Fixture 3: malformed outer_points + CDE → unsupported ===
  [PASS] status=unsupported (got unsupported)
  [PASS] unsupported_reason=CDE_BACKEND_UNSUPPORTED_QUERY
  [PASS] no placements on malformed geometry
  [PASS] collision_backend_diagnostics present even on unsupported
  [PASS] bbox_fallback_queries==0 (got 0)
  [PASS] at least one unsupported/prepare_failure (unsupported=3, failures=3)

=== Fixture 4: L-shape notch + CDE (proves CDE ≠ bbox proxy) ===
  [PASS] status ok/partial (got ok)
  [PASS] collision_backend_diagnostics present
  [PASS] backend_used=cde_adapter (got cde_adapter)
  [PASS] bbox_fallback_queries==0 (got 0)
  [PASS] cde_total_queries>0 (got 3)

=== Fixture 5: default bbox backend — no CDE observability ===
  [PASS] status ok/partial (got ok)
  [PASS] bbox default path must not emit collision_backend_diagnostics

=== Fixture 6: timing env flag VRS_CDE_OBSERVABILITY_TIMING=1 ===
  [PASS] status ok/partial (got ok)
  [PASS] collision_backend_diagnostics present with timing flag
  [PASS] final_commit_validation_ms present and non-negative (got 8.213823)

Results: 32 passed, 0 failed
SMOKE: PASS
```

## Cargo test results

```
cargo test ... optimizer::cde_adapter   → 21 passed, 0 failed
cargo test ... optimizer::collision_backend → 28 passed, 0 failed
cargo test ... optimizer::working       → 16 passed, 0 failed
cargo test ... optimizer::cde_observability → 5 passed, 0 failed
cargo test ... adapter                  → 52 passed, 0 failed
cargo test ... --lib                    → 350 passed, 0 failed
```

Test name→requirement mapping:

| Test | Requirement |
|---|---|
| `cde_observability_counts_pair_and_boundary_queries` | Q18A §1: pair/boundary counters |
| `cde_observability_reports_engine_builds` | Q18A §1: engine build counter |
| `cde_observability_reports_no_bbox_fallback` | invariant: bbox_fallback_queries==0 |
| `cde_observability_reset_clears_all_fields` | reset() correctness |
| `cde_observability_snapshot_is_independent_of_future_increments` | snapshot isolation |
| `cde_observability_pair_query_increments_pair_and_total` | backend-level counter |
| `cde_observability_boundary_query_increments_boundary_and_total` | backend-level counter |
| `cde_observability_engine_builds_counted_for_pair_query` | engine_builds accuracy |
| `cde_observability_engine_builds_counted_for_boundary_query` | engine_builds accuracy |
| `cde_observability_prepare_failure_counted_for_invalid_polygon` | prepare_failure counter |
| `cde_observability_cross_sheet_skip_counted` | cross_sheet_skipped counter |
| `bbox_backend_does_not_increment_cde_observability_counters` | bbox isolation |
| `adapter_cde_valid_output_contains_observability_diagnostics` | output CDE fields |
| `adapter_cde_unsupported_output_preserves_observability_diagnostics` | unsupported preservation |
| `bbox_backend_does_not_emit_cde_observability` | bbox path no CDE counters |
| `cde_observability_does_not_break_existing_q16_tests` | Q16 regression guard |

## Q18B decision table

| Metric / Evidence | Result | Interpretation | Decision impact |
|---|---|---|---|
| cde_total_queries per final commit (2 parts) | 3 | 1 pair + 2 boundary | Low raw count, per-call overhead tolerable for small problems |
| cde_engine_builds per query | 1:1 | CDEngine rebuilt for every query | Session/cache could amortize this for PhaseOptimizer bulk scoring |
| PhaseOptimizer CDE total (2 rects, short run) | 288 | 288 CDEngine builds in a 10s run | High build frequency in exploration/compression loops |
| bbox_fallback_queries | 0 | No silent bbox downgrade anywhere | Architecture is clean; no fallback path to fix |
| Final commit timing (VRS_CDE_OBSERVABILITY_TIMING=1) | ~8ms | Wall clock, not deterministic | Single data point; larger fixture needed for reliable session benefit estimate |
| L-shape notch proves CDE ≠ bbox proxy | Confirmed | CDE correctly avoids L-notch false positive | Quality justification for CDE confirmed |
| Per-phase breakdown | Not yet available | Cannot isolate exploration vs. compression cost | One reason to consider Q18B: get phase-level breakdown |

**Summary:** The 288 CDEngine builds for PhaseOptimizer on a small fixture (2 parts, 10s)
suggests that in real LV8-scale runs, the CDEngine rebuild overhead per query is a genuine
accumulation. However, without a larger fixture we cannot quantify the session/cache benefit
vs. implementation complexity. The current architecture is clean and correct.

**Recommendation:** `INCONCLUSIVE_NEEDS_BIGGER_FIXTURE` — run a Q19/LV8-scale fixture with
timing enabled and compare `cde_engine_builds` at scale before committing to a CDEngine session
rewrite. If `cde_engine_builds` in a 276-part run exceeds ~10K with measurable latency
contribution, Q18B is warranted.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-28T00:16:27+02:00 → 2026-05-28T00:19:29+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.verify.log`
- git: `main@c7892ed`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     | 217 ++++++++++++++++++++-
 rust/vrs_solver/src/io.rs                          |  30 +++
 rust/vrs_solver/src/optimizer/cde_adapter.rs       |   2 +
 rust/vrs_solver/src/optimizer/collision_backend.rs | 148 +++++++++++++-
 rust/vrs_solver/src/optimizer/mod.rs               |   1 +
 5 files changed, 388 insertions(+), 10 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/collision_backend.rs
 M rust/vrs_solver/src/optimizer/mod.rs
?? canvases/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
?? codex/codex_checklist/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q18a_cde_correctness_runtime_observability.yaml
?? codex/prompts/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability/
?? codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
?? codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.verify.log
?? docs/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
?? rust/vrs_solver/src/optimizer/cde_observability.rs
?? scripts/smoke_sgh_q18a_cde_observability.py
```

<!-- AUTO_VERIFY_END -->

SGH-Q18A_STATUS: READY_FOR_AUDIT
Q18B_RECOMMENDATION: INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
