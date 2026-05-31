# SGH-Q24R3 — Native Sparrow lifecycle parity without compression

You are working in the VRS_nesting repository.

This is a **coding-first Sparrow parity task**. The production `sparrow_cde` path must match the current local `.cache/sparrow` / jagua_rs/Sparrow lifecycle **except for compression**.

Do not spend this task on compression. Do not drift into bbox rhetoric. Do not turn this into a benchmark campaign. Code the missing solver behavior.

## Controlling rule

Implement the current jagua_rs/Sparrow exploration/separation/search/tracker lifecycle in VRS fixed-sheet form. Compression is intentionally excluded for now.

Compression rationale:

- Sparrow's compression is valuable for strip-packing because the strip dimension is the objective.
- VRS is fixed-sheet multisheet nesting; compression is mainly useful later on the last partially used sheet.
- Therefore default `sparrow_cde` must not rely on compression to pass Q24R3.

## Mandatory reference reading

Before coding, read the current local Sparrow clone:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

Skim only for context, not as an implementation target in this task:

```text
.cache/sparrow/src/optimizer/compress.rs
```

If `.cache/sparrow` is missing, run:

```bash
./scripts/ensure_sparrow.sh
```

Then read current VRS code:

```text
codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
scripts/smoke_sgh_q24r2_native_sparrow_core_port.py
```

## Audited starting point

Q24R2 is accepted only as a skeleton lifecycle port:

- `SparrowSeparationKernel::run` exists.
- `exploration_phase`, `separate`, `move_items_multi`, `worker_move_items`, `compression_phase`, `finalize` exist.
- Production `sparrow_cde` forces CDE and avoids legacy fallback.

But Q24R2 is still insufficient:

- medium CDE 12 items does not have to converge in Q24R2;
- initial solution is still all-at-origin/first-sheet/first-rotation;
- tracker/loss is still not full native CDE collision quantification;
- search depth is toy-sized in production config;
- exploration is structural but weak under CDE;
- state/problem/layout is still adapter-heavy;
- compression exists but is not useful to focus on now.

## Required work

### 1. Write a reference map first

Create:

```text
docs/egyedi_solver/sgh_q24r3_sparrow_reference_map.md
```

Map each current `.cache/sparrow` function to the VRS equivalent you will implement or modify:

```text
optimizer::optimize
LBFBuilder::construct
exploration_phase
Separator::separate
Separator::move_items_multi
SeparatorWorker::move_items
search::search_placement
CollisionTracker
SPSolution/SPProblem save/restore
```

This map must include file paths and function names. It must explicitly mark `compress.rs` as out of Q24R3 scope.

### 2. Complete the fixed-sheet Sparrow state/problem model

Implement either a split module tree or explicit types inside `sparrow.rs`.

Preferred split:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/problem.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
```

Acceptable non-split implementation must still define equivalent concepts:

```rust
FixedSheetSparrowProblem
FixedSheetSparrowLayout
FixedSheetPlacementKey
FixedSheetSparrowSolution
FixedSheetSparrowTracker
FixedSheetSeparator
FixedSheetSeparatorWorker
```

Hard requirements:

- stable placement identity or rigorous index/key mapping;
- layout + tracker snapshot/restore as one coherent state;
- move/update lifecycle equivalent to Sparrow remove/place/register;
- worker load from master snapshot;
- rollback preserving GLS memory where Sparrow does;
- no layout/tracker/CDE-session mismatch.

### 3. Replace the all-origin seed

Replace `build_sparrow_seed_layout` or wrap it with a Sparrow-compatible fixed-sheet initial solution builder.

The seed builder must:

- behave like Sparrow's constructive initial solution role;
- be deterministic for the same seed;
- respect sheet availability and rotation policy;
- distribute instances across sheets/regions better than all at origin;
- preserve all fittable instances;
- support future/warm-start input if already available in repo structures;
- never be used as final fallback success.

Allowed seed approaches:

- LBF-like fixed-sheet construction;
- coarse grid/spread over sheets;
- size/area-sorted constructive placement;
- overlap-allowed fallback only when constructive non-overlap placement cannot place all fittable items.

Forbidden:

- using legacy row/cursor solver as final production solver;
- emitting a seed as success without Sparrow separation and final CDE validation;
- dropping hard instances.

### 4. Make CDE tracker/loss decisive

For production `sparrow_cde`, the tracker must quantify the actual CDE geometry problem.

Implement or adapt:

- CDE-backed pair collision collection/evaluation;
- CDE-backed item-vs-sheet/container violation quantification;
- per-pair and per-boundary raw loss;
- weighted loss through GLS;
- item-level weighted loss;
- tracker save/restore preserving weights;
- efficient update after item move;
- full final CDE validation before success.

Bbox is allowed only for broad-phase/candidate pruning/diagnostics. It must not be the primary CDE separation loss.

If exact jagua-rs quantification functions are not directly reusable, implement a documented fixed-sheet equivalent and record the delta in the report.

### 5. Restore Sparrow search placement behavior under CDE

Upgrade or wrap `search_position_for_target` so production CDE search has real Sparrow-like depth.

Required components:

- sheet/container-wide sampling;
- focused sampling around the current placement;
- BestSamples/top retention with deterministic dedupe;
- coordinate descent on multiple retained samples;
- final finer coordinate descent on the best sample;
- continuous rotation refinement where allowed;
- worker-specific deterministic RNG;
- CDE-backed weighted separation evaluator.

Production config must no longer rely on toy values solely to avoid timeout. If CDE search becomes too expensive, implement active-set/session support.

### 6. Add active-set/session support as needed

Add enough support to make real CDE search affordable:

- target-specific active hazard set;
- sheet-local hazard filtering;
- spatial/proximity prefilter before expensive CDE checks;
- candidate session reuse within worker/search scope;
- cached transforms/shapes where safe;
- final full validation across all items/sheets.

Do not replace final CDE truth with an active-set shortcut.

### 7. Make exploration operational under CDE

Keep the Q24R2 shape, but make it effective.

Required:

- bounded infeasible pool sorted by raw/weighted CDE loss;
- biased restore toward better pool entries;
- repeated restore/disrupt/separate attempts;
- best feasible and best infeasible tracking;
- at least two real disruption strategies:
  - one large-item/offending-item strategy;
  - one sheet/cluster redistribution strategy.

The medium CDE hard gate must pass because this lifecycle actually works, not because tests are weakened.

### 8. Gate compression out of default production Q24R3

Default production `sparrow_cde` lifecycle for this task:

```text
constructive seed -> exploration/separation/search -> final full CDE validation
```

Compression may remain as dormant code or explicit config, but:

- it must not run by default in Q24R3 smoke;
- it must not be counted as a PASS deliverable;
- it must not consume the main diff;
- it must not be required to solve medium CDE;
- diagnostics should make it clear that compression was skipped/gated.

### 9. Add/update diagnostics only to prove real behavior

Expose only what is needed for verification, for example:

- Q24R3 production compression disabled/skipped flag;
- CDE loss source used by tracker;
- active-set/full-validation query counts;
- search depth actually used;
- exploration pool/disruption counts;
- seed builder strategy.

Diagnostics are not the deliverable; code behavior is.

## Hard verification gates

Add this smoke script:

```text
scripts/smoke_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.py
```

It must check at minimum:

```text
medium_10_to_20_items / sparrow_cde / forced CDE
status: ok
placed: 12/12
sparrow_converged: true
final collision pairs: 0
final boundary violations: 0
no bbox fallback
no LBF/legacy fallback
compression disabled or zero default passes
search_position calls/samples > 0
CDE backend used
```

Then run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.py
./scripts/check.sh
```

Do not claim PASS if any gate fails or is not run.

## Full LV8 is not a Q24R3 PASS gate

Do not make the task fail only because full LV8/276 is not solved yet.

However, do not break the path toward:

```text
276 / 276 instances
2 × 1500 × 3000 sheets
CDE-valid
zero overlap
zero boundary violation
```

Optional: include a tiny LV8 subset smoke if it is cheap and already supported.

## Report

Create:

```text
codex/reports/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.md
```

Required sections:

1. PASS or REVISE.
2. Sparrow reference files read from `.cache/sparrow`.
3. Function-by-function Sparrow → VRS map.
4. Rust files changed.
5. Seed builder changes.
6. State/problem/tracker changes.
7. CDE loss quantification changes.
8. Search depth and active-set/session changes.
9. Exploration changes.
10. Explicit compression status: disabled/gated/out of scope.
11. Test outputs.
12. Medium CDE hard-gate result.
13. Remaining gaps toward full LV8.

## PASS criteria

PASS only if:

- `.cache/sparrow` was read or an honest blocker was reported;
- production `sparrow_cde` still forces CDE;
- no legacy/LBF/row-cursor final fallback is used;
- fixed-sheet Sparrow state/problem/tracker lifecycle is complete enough to map to current Sparrow excluding compression;
- initial seed is no longer all-origin only;
- worker-master and all-colliding-item worker logic remain active;
- CDE-backed tracker/loss is primary;
- search depth is meaningful under CDE;
- active-set/session support keeps CDE search affordable without weakening truth;
- exploration solves medium CDE 12/12;
- compression is disabled/gated and not used as default Q24R3 crutch;
- full final CDE validation gates success;
- required build/test/smoke/check evidence is in the report.

## Automatic REVISE

Mark REVISE if:

- main work is docs/reports/scripts/diagnostics only;
- main work is compression;
- main work is bbox-removal rhetoric;
- medium CDE convergence is deferred again;
- search depth is reduced instead of made affordable;
- tracker loss remains bbox/surrogate primary for CDE;
- success can bypass full CDE validation;
- hard instances are dropped silently;
- `.cache/sparrow` was not read;
- tests were not run and no blocker is given.
