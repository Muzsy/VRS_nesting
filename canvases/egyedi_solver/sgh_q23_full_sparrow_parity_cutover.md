# SGH-Q23 — Full Sparrow parity cutover for fixed-sheet nesting

## Mission

This is not a bbox-removal task.

This is a **full Sparrow-parity cutover task**: implement a production solver path whose algorithmic behavior follows the local `.cache/sparrow` repository as closely as possible, adapted to our fixed rectangular sheet / multi-sheet nesting problem.

The goal is not:

```text
"make the current solver a bit less bbox-based"
```

The goal is:

```text
"make the production solver operate like Sparrow: infeasible-state feasibility solving, collision graph, GLS memory, search_position sampling/refinement, separation lifecycle, exploration/compression, jagua-rs/CDE geometry backend, and fixed-sheet objective adaptation."
```

Any bbox limitation is only a consequence of this parity target. Do not center the task around bbox. Center it around **Sparrow algorithmic equivalence**.

## Local reference requirement

The local Sparrow reference repository exists at:

```text
.cache/sparrow
```

It is gitignored and may not appear in this task package. The agent executing this task must use the local clone as the primary reference. Do not proceed from memory. Do not use generic internet summaries as a substitute for the local source.

If `.cache/sparrow` is missing:

```text
first line: BLOCKED
reason: .cache/sparrow missing
```

No production code changes in that case.

## Dependency gate

Required prior reports:

```text
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
```

Expected state:

```text
Q21R1: PASS / READY_FOR_AUDIT
Q22R1: PASS as diagnostic hardening, but only TESTABLE_WITH_CDE_MICRO for full Sparrow goal
```

This Q23 task exists because Q22R1 proved the kernel exists but is not yet full production Sparrow/CDE.

## Step 0 — mandatory Sparrow reference map

Before implementation, inspect `.cache/sparrow` and create:

```text
docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
```

This is not optional documentation. It is the basis for the port.

Minimum sections:

```text
1. Sparrow repository structure and real entrypoints
2. Main solve loop
3. Feasibility problem lifecycle
4. Separation procedure
5. search_position / transform candidate sampling
6. coordinate descent / local refinement
7. move acceptance / rejection / rollback
8. collision graph representation and update strategy
9. GLS / pair weights / penalty update logic
10. exploration phase
11. compression phase
12. CDE / jagua-rs engine/session usage
13. diagnostics / benchmark structure
14. what must change for fixed-sheet / multi-sheet nesting
15. explicit VRS mapping: Sparrow concept -> VRS file/type/function
16. intentional deviations and why they are required
```

Use concrete source paths and names from `.cache/sparrow`. Example command set:

```bash
find .cache/sparrow -maxdepth 4 -type f | sed -n '1,320p'
rg -n "search_position|separation|separate|compression|exploration|Guided|GLS|collision|CDE|jagua|position|coordinate|descent|sample|worker|move|feasibility|penalty|weight" .cache/sparrow
```

If direct code is copied, preserve license headers and document the copied source and rationale. Prefer architecture-level porting unless direct copying is clearly appropriate and license-compatible.

## Current VRS state to audit

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

Write a short pre-implementation blocker summary into the Q23 report before coding.

## Production target

Create or harden a production solver path. Preferred explicit name:

```text
optimizer_pipeline = "sparrow_cde"
```

Equivalent name is acceptable only if it is unambiguous and documented.

This production path must be the intended new solver path. Existing old solvers may remain only as explicit legacy/debug comparison, not as production fallback.

## Sparrow parity contract

PASS requires all of these to be true or explicitly implemented to the maximum extent possible with exact blockers documented as `REVISE` rather than weak `PASS`.

### 1. Explicit Sparrow state lifecycle

The production path must operate through a Sparrow-style state, not through a renamed legacy/phase optimizer.

Required properties:

```text
SparrowState owns placements / transforms / item status
state may be infeasible during search
collision graph is part of the state or derived incrementally from state
GLS/pair weights are attached to the search memory
best feasible incumbent tracked
best infeasible incumbent tracked
rollback/restore preserves intended Sparrow memory such as GLS weights
final output can only come from backend-valid state
```

### 2. Collision graph and weighted target selection

The production path must use a backend-confirmed collision graph to drive moves.

Required:

```text
node = item instance / boundary violation candidate
edge = backend-confirmed item-pair collision or boundary violation
edge fields include severity and GLS/penalty weight
weighted score drives target/pair selection
repeated/stagnating collisions update weights
```

Do not select targets only from legacy bbox/candidate heuristics.

### 3. search_position parity

`search_position` must be the primary relocation/search mechanism.

Required:

```text
global sampling
focused sampling around incumbent transform
top-k transform candidates
coordinate descent / local refinement
rotation refinement governed by rotation policy
backend-oracle evaluation
unsupported candidate rejection
stable deterministic seed behavior
```

The report must compare our implementation to the local Sparrow `search_position` behavior and explain any differences.

### 4. Move acceptance / rollback / separation loop

Required:

```text
candidate transforms are evaluated using Sparrow/CDE oracle evaluation
accepted moves improve weighted separation objective or follow documented Sparrow-style acceptance rule
rejected moves cannot corrupt incumbent state
rollback restores placements but preserves intended search memory
stagnation triggers GLS weight update / disruption / restart, not legacy fallback
separation loop iterates until feasible, budget exhausted, or documented partial state
```

### 5. Exploration/compression structure

Production path must not be only a single separation loop if `.cache/sparrow` shows a broader exploration/compression lifecycle.

Implement or explicitly align:

```text
exploration budget / attempts / restarts
compression / compacting phase for feasible incumbent
fixed-sheet adaptation of compression objective
incumbent management across attempts
```

If full exploration/compression cannot be completed in this task, report `REVISE` with exact remaining work. Do not pretend parity.

### 6. jagua-rs/CDE geometry backend

The production Sparrow path must be CDE/Jagua-first.

Required:

```text
collision existence from active backend
boundary validity from active backend
final commit from active backend
unsupported/timeout paths preserve full optimizer diagnostics
CDE/Jagua query/session/cache metrics visible
```

### 7. Fixed-sheet adaptation

Sparrow is strip-packing oriented; VRS is fixed-sheet / multi-sheet nesting.

Implement and document the adaptation:

```text
hard constraints:
  inside fixed sheet
  no collision
  required spacing/margin represented by geometry/preprocessing

primary objective:
  place all required items for the current sheet/problem contract
  minimize sheet count when multi-sheet is active

secondary objective:
  compactness / used extent / utilization
  avoid spread that makes later sheet reduction harder
```

For this Q23 acceptance, fixed single-sheet CDE medium fixture must work. Full multi-sheet minimization may be `HOLD` only if fixed single-sheet CDE is production-clean and documented.

## CDE scaling requirements

Q22R1 proved:

```text
sparrow_experimental + cde works only on tiny fixture
medium CDE is unsupported / timeout
```

Q23 must address this as part of the real Sparrow cutover, not as an optional optimization.

Required:

```text
solve-scoped CDE/Jagua session/cache or equivalent query reduction
prepared geometry cache
transformed placement cache
pair decision cache
boundary decision cache
dirty invalidation when an item moves
active-set pair filtering
incremental collision graph update
query budget diagnostics
```

AABB/bbox may be used only as broad-phase pruning:

```text
AABB separated -> skip exact pair query and count as broadphase_pruned
AABB overlaps / uncertain -> CDE/Jagua decides
AABB never produces positive collision truth
```

## Legacy quarantine

Legacy code may remain physically present, but production path must be isolated.

Required:

```text
legacy_multisheet explicit opt-in only
phase_optimizer explicit opt-in only
bbox backend explicit debug/legacy only
LBF/finite candidate fallback forbidden in production Sparrow/CDE
old solver cannot silently solve failed Sparrow/CDE cases
```

A failure in production Sparrow/CDE must return:

```text
unsupported / partial with full diagnostics
```

not fallback success from old code.

## Bbox rule as consequence, not mission

This task is not centered on bbox. However, because full Sparrow/CDE parity is the target, these guardrails follow:

```text
bbox may be broad-phase prereject / quick reject / diagnostics / legacy debug
bbox may not be collision source-of-truth in production Sparrow/CDE
bbox may not be final validation
bbox may not be the semantic loss identity
bbox may not be fallback when CDE is slow
```

If the only successful solver path is bbox, the report must be `REVISE`.

## Required smoke and benchmark

Create/update:

```text
scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py
scripts/bench_sgh_q23_full_sparrow_parity_cutover.py
```

Minimum smoke fixtures:

```text
1. tiny_cde_must_converge
2. overlap_two_rects_cde_must_separate
3. boundary_recovery_cde_must_recover
4. continuous_rotation_rescue_cde
5. medium_10_to_20_items_cde_must_not_timeout
6. medium_10_to_20_items_cde_must_converge_or_document_partial_by_contract
7. production_sparrow_uses_backend_oracle_evaluation
8. production_sparrow_no_legacy_fallback
9. production_sparrow_preserves_full_diagnostics_on_failure
10. legacy_pipeline_requires_explicit_opt_in
```

No CDE failure skip except tests explicitly named unsupported-diagnostics.

Minimum benchmark matrix:

```text
pipelines:
  sparrow_cde / production Sparrow
  previous sparrow_experimental only as comparison if still present
  phase_optimizer only as comparison, not acceptance

backends:
  cde
  jagua_polygon_exact if available
  bbox only as debug comparison, not acceptance

fixtures:
  tiny
  2-rect overlap
  boundary recovery
  10-20 item medium
  30 item synthetic if feasible under quick cap
```

All outcomes count in denominator:

```text
ok
partial
unsupported
timeout
error
```

Do not render numeric 0 as `-` in markdown.

## Performance / correctness acceptance

Minimum PASS target:

```text
medium_10_to_20_items + production Sparrow + cde:
  no timeout under quick cap
  status ok OR well-defined partial accepted by fixture contract
  sparrow_converged true for fixtures that require full convergence
  all diagnostics preserved
  backend oracle evaluation active
  no legacy fallback
```

Metrics required in JSON and markdown:

```text
status
runtime_ms
placed_count / required_count
sparrow_converged
sparrow_iterations
moves_attempted / accepted / rejected
collision graph initial/final pairs
best feasible loss
best infeasible loss
CDE engine/session builds
cache hits / misses / invalidations
active-set pairs considered
broadphase pruned pairs
CDE pair queries
CDE boundary queries
search_position calls / samples / refinements
GLS weight updates
fallback counters
```

## Verification commands

Run at least:

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

## Report outputs

Create:

```text
docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
docs/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.verify.log
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.json
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.md
```

First line must be exactly one of:

```text
PASS
REVISE
BLOCKED
```

PASS final markers:

```text
SGH-Q23_STATUS: READY_FOR_AUDIT
SPARROW_PRODUCTION_STATUS: FULL_SPARROW_PARITY_FIXED_SHEET|CDE_FIRST_PARTIAL_READY_WITH_EXPLICIT_GAPS
LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY
Q19_STATUS: HOLD
```

Use `FULL_SPARROW_PARITY_FIXED_SHEET` only if the implementation is genuinely aligned with the local Sparrow reference and fixed-sheet acceptance passes. Otherwise use `REVISE` or `CDE_FIRST_PARTIAL_READY_WITH_EXPLICIT_GAPS` only if all explicitly scoped acceptance gates pass and remaining gaps are non-production-blocking.

If the implementation cannot complete the full cutover in one run, the correct outcome is `REVISE` with a precise cutover blocker list and measurements, not a weak PASS.
