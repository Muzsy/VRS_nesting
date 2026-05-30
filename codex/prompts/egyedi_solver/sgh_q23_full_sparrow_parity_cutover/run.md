# Runner — SGH-Q23 full Sparrow parity cutover

You are working in the `VRS_nesting` repository.

This is not a bbox-removal task. This is a full Sparrow-parity cutover task.

## Target

Implement or harden a production solver path that behaves like the actual local `.cache/sparrow` implementation, adapted to fixed-sheet nesting.

The target behavior is:

```text
Sparrow-style infeasible-state feasibility solving
collision graph
GLS/pair-weight search memory
search_position sampling/refinement
coordinate descent
a separation lifecycle
exploration/compression where applicable
jagua-rs/CDE-backed geometry truth
fixed-sheet objective adaptation
full diagnostics and benchmark evidence
```

Bbox restrictions are only a consequence of this goal, not the central objective.

## Step 0 — mandatory local Sparrow audit

`.cache/sparrow` is gitignored but present locally. Use it as the reference.

If missing:

```text
first line: BLOCKED
reason: .cache/sparrow missing
```

Do not proceed from memory.

Run and inspect:

```bash
find .cache/sparrow -maxdepth 4 -type f | sed -n '1,320p'
rg -n "search_position|separation|separate|compression|exploration|Guided|GLS|collision|CDE|jagua|position|coordinate|descent|sample|worker|move|feasibility|penalty|weight" .cache/sparrow
```

Create:

```text
docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
```

This document must map actual local Sparrow source paths/types/functions to VRS equivalents and list intentional deviations for fixed-sheet nesting.

## Step 1 — audit current VRS Sparrow path

Read at least:

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/cde_session.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/loss_model.rs
rust/vrs_solver/src/optimizer/phase.rs
scripts/smoke_sgh_q22_sparrow_kernel.py
scripts/bench_sgh_q22_sparrow_kernel.py
codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
```

Write a short blocker summary into the Q23 report before implementation.

## Step 2 — production Sparrow path

Create or harden a clear production path, preferably:

```text
optimizer_pipeline = "sparrow_cde"
```

Equivalent naming is acceptable only if unambiguous.

This must be the intended new production solver path. Old solvers may remain only as explicit legacy/debug comparisons.

## Step 3 — implement the Sparrow parity contract

Implement or align the following, using `.cache/sparrow` as the guide:

```text
1. SparrowState lifecycle with intentional infeasible states
2. backend-confirmed collision graph
3. GLS/pair-weight update and persistence across restore/rollback
4. target selection from weighted collision graph
5. search_position as the primary relocation mechanism
6. top-k coordinate descent/refinement
7. backend-oracle evaluate_transform scoring
8. move accept/reject/rollback rules
9. stagnation handling: weight update / disruption / restart
10. best feasible and best infeasible incumbent tracking
11. exploration/compression lifecycle where applicable
12. fixed-sheet objective adaptation
13. solve-scoped CDE/Jagua session/cache and active-set query reduction
14. complete diagnostics on success and failure
```

Do not submit a PASS if this is merely the old solver with a new label.

## Step 4 — CDE/Jagua production geometry backend

Production Sparrow must use CDE/Jagua as geometry source-of-truth.

Required:

```text
collision existence from active backend
boundary validity from active backend
final commit from active backend
unsupported/timeout preserves optimizer diagnostics
CDE/Jagua query/session/cache metrics visible
```

Implement query reduction as part of the cutover:

```text
prepared geometry cache
transformed placement cache
pair decision cache
boundary decision cache
dirty invalidation when item moves
active-set pair filtering
incremental collision graph update
```

AABB/bbox may be used only as broad-phase pruning, never as positive collision truth.

## Step 5 — fixed-sheet adaptation

Document and implement the adaptation from Sparrow strip-packing to our fixed sheet nesting:

```text
hard constraints:
  inside fixed sheet
  no collision
  geometry/preprocessing handles spacing/margin

primary objective:
  place all required items for fixture/problem contract
  minimize sheet count when multi-sheet is active

secondary objective:
  compactness / utilization / reduced spread
```

For Q23, fixed single-sheet CDE medium fixture must not timeout. Full multi-sheet minimization may remain HOLD only if fixed single-sheet production Sparrow/CDE is clean.

## Step 6 — legacy quarantine

Production Sparrow path cannot silently fallback to old solver logic.

Required:

```text
legacy_multisheet explicit opt-in only
phase_optimizer explicit opt-in only
bbox backend explicit debug/legacy only
LBF finite-candidate fallback forbidden in production Sparrow/CDE
old solver cannot silently solve failed Sparrow/CDE cases
```

A production Sparrow/CDE failure must return unsupported/partial with complete diagnostics.

## Step 7 — smoke, benchmark, verify

Create/update:

```text
scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py
scripts/bench_sgh_q23_full_sparrow_parity_cutover.py
```

Smoke must fail on CDE failure unless the fixture is explicitly named unsupported-diagnostics.

Minimum smoke fixtures:

```text
tiny_cde_must_converge
overlap_two_rects_cde_must_separate
boundary_recovery_cde_must_recover
continuous_rotation_rescue_cde
medium_10_to_20_items_cde_must_not_timeout
production_sparrow_uses_backend_oracle_evaluation
production_sparrow_no_legacy_fallback
production_sparrow_preserves_full_diagnostics_on_failure
legacy_pipeline_requires_explicit_opt_in
```

Benchmark must count all outcomes in denominators: ok, partial, unsupported, timeout, error.

Run:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_session
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py
python3 scripts/bench_sgh_q23_full_sparrow_parity_cutover.py --quick
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
```

## Report

Create:

```text
docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
docs/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.verify.log
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.json
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.md
```

First line: `PASS`, `REVISE`, or `BLOCKED`.

PASS final markers:

```text
SGH-Q23_STATUS: READY_FOR_AUDIT
SPARROW_PRODUCTION_STATUS: FULL_SPARROW_PARITY_FIXED_SHEET|CDE_FIRST_PARTIAL_READY_WITH_EXPLICIT_GAPS
LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY
Q19_STATUS: HOLD
```

Use `FULL_SPARROW_PARITY_FIXED_SHEET` only if the implementation is genuinely aligned with local Sparrow and fixed-sheet acceptance passes. Otherwise report `REVISE`, unless all production gates pass and remaining gaps are explicitly non-blocking.
