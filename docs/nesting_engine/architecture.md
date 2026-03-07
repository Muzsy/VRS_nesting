# Nesting Engine Architecture

## 1. Module map and responsibilities

The crate is organized so nominal geometry handling and inflated feasibility logic stay separated.

- `geometry/`
  - Current: SCALE conversions, polygon types, offset operations, and the nominal->inflated pipeline orchestrator.
  - Responsibility: pure geometry transforms (`mm <-> i64`, `inflate_part`, pipeline diagnostics).
- `nesting/` (planned)
  - Responsibility: high-level nesting flow orchestration across candidate generation and feasibility checks.
- `feasibility/` (planned)
  - Responsibility: collision/touching checks and acceptance/rejection decisions on inflated geometry.
- `placement/` (planned)
  - Responsibility: candidate placement search strategy and deterministic ordering rules.
- `multi_bin/` (planned)
  - Responsibility: multi-sheet bin handling and sheet-level assignment flow.
- `export/` (planned)
  - Responsibility: output generation from nominal geometry (DXF/export-facing representation).

## 2. Non-negotiable nominal vs inflated rule

```
A solver feasibility engine CSAK inflated geometriaval dolgozik.
DXF export MINDIG nominalis geometriabol tortenik.
Ez a kulonbseg soha nem keveredhet.
```

Implementation implication:
- The `inflate-parts` pipeline exists only to produce feasibility geometry.
- Nominal points are preserved for downstream export responsibilities.

## 3. Inflate pipeline flow

```text
Python DXF importer (nominal points)
  -> JSON stdio request (pipeline_v1)
  -> Rust nesting_engine inflate-parts
  -> inflate_part() + diagnostics (hole_collapsed/self_intersect/error)
  -> inflated geometry for feasibility engine
```

The pipeline does not mutate export-side nominal definitions.

## 4. Rotation determinism policy (placement)

Placement rotation in `rust/nesting_engine/src/placement/blf.rs` must be platform-stable:

- Orthogonal rotations (0/90/180/270) stay integer-only shortcuts.
- Non-orthogonal rotations must use fixed-point LUT values from `geometry/trig_lut.rs`.
- `TRIG_SCALE = 1_000_000_000` is used for `SIN_Q/COS_Q` coefficients.
- Rotation math uses i128 intermediates:
  - `x' = round_div(x * cos_q - y * sin_q, TRIG_SCALE)`
  - `y' = round_div(x * sin_q + y * cos_q, TRIG_SCALE)`
- Rounding is explicit deterministic half-away-from-zero (`round_div_i128`), not runtime `f64` trig/round.

This keeps the placement output byte-stable across CPU architectures (x86_64, arm64) for identical input.

## 5. DXF curve polygonization policy (nominal truth-layer prep)

The Python DXF importer is the nominal geometry truth-layer input for downstream solver/export flows.
Curve handling must stay policy-locked and deterministic across ARC/SPLINE/ELLIPSE entities.

Source-of-truth policy constants:

- `vrs_nesting/geometry/polygonize.py`
  - `ARC_TOLERANCE_MM = 0.2`
  - `CURVE_FLATTEN_TOLERANCE_MM = ARC_TOLERANCE_MM`
  - `ARC_POLYGONIZE_MIN_SEGMENTS = 12`
- `vrs_nesting/dxf/importer.py`
  - `CHAIN_ENDPOINT_EPSILON_MM = 0.2` (separate policy concept from curve flatten tolerance)

Importer contract:

- ARC polygonization (`arc_to_points`) uses the curve tolerance policy above.
- SPLINE/ELLIPSE flattening (`curve_entity.flattening(flatten_tol)`) is derived from the same
  curve tolerance policy.
- Endpoint chaining epsilon is used only for segment stitching/ring closure and is not a flatten
  precision knob, even if its numeric value currently matches.

Fixture coverage policy:

- Real DXF curve regression fixtures live under `samples/dxf_demo/`.
- Positive fixtures must remain non-self-intersecting after polygonization.
- Negative self-intersecting curve fixtures must fail deterministically with importer error code
  `DXF_INVALID_RING`.

## 6. Search layer (F2-4 Simulated Annealing)

F2-4 introduces an optional deterministic search layer on top of the existing constructive placers.

Activation and compatibility rules:

- The default `nest` behavior remains unchanged.
- Search is opt-in via `--search sa`; without it, the engine runs the constructive baseline only.
- Supported SA CLI flags are:
  - `--search none|sa`
  - `--sa-iters <u64>`
  - `--sa-temp-start <u64>`
  - `--sa-temp-end <u64>`
  - `--sa-seed <u64>`
  - `--sa-eval-budget-sec <u64>`
- SA-specific flags are rejected unless `--search sa` is active.

Current implementation map:

- `rust/nesting_engine/src/search/sa.rs`
  - deterministic SA core
  - deterministic PRNG (`SplitMix64`)
  - neighborhood operators (`swap`, `move`, `rotate`)
  - integer-only acceptance rule
  - global time-limit clamp + deadline guard
- `rust/nesting_engine/src/main.rs`
  - CLI parsing
  - `SaSearchConfig` construction
  - `--search none|sa` dispatch
- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - `PartOrderPolicy`
  - sheet-by-sheet constructive evaluation entry point

State and evaluation model:

- SA state consists of:
  - part order permutation
  - per-part rotation-choice index
- Candidate states are evaluated by running the existing constructive placement flow via
  `greedy_multi_sheet(...)`, not by a separate geometry engine.
- Cost is encoded lexicographically as integer score:
  1. fewer unplaced instances
  2. fewer sheets used
  3. better fill / fewer leftover placements

Order-sensitivity contract:

- `PartOrderPolicy::ByArea` preserves the historical baseline behavior.
- `PartOrderPolicy::ByInputOrder` allows SA-provided order to reach the placer unchanged.
- SA evaluation uses `ByInputOrder`; non-SA baseline flow uses `ByArea`.

Determinism contract:

- PRNG is local and seed-driven (`SplitMix64`), no external/random crate is involved.
- Tie-breaks are total and deterministic:
  - lower cost wins
  - on equal cost, lexicographically earlier state wins
- Acceptance uses integer arithmetic only; no floating-point probability logic is used.

Search result contract:

- SA returns the best already-evaluated constructive result.
- The search does not perform an extra final constructive rerun after the best state is chosen.
- This is required so the global evaluation budget remains hard-bounded by the configured SA limits.

## 7. Timeout-Bound Determinism Policy

The placement flow supports two stop modes:

- `wall_clock` (default): cutoff driven by `time_limit_sec` wall-clock checks.
- `work_budget`: deterministic operation-budget cutoff inside BLF and NFP search loops.

For SA (`--search sa`), the engine forces `work_budget` mode when no explicit
`NESTING_ENGINE_STOP_MODE` is set.

For `work_budget` mode, a hard wall-clock safety guard is still applied:

- hard guard threshold = `time_limit_sec + hard_timeout_grace_sec`
- if the hard guard is reached, the run stops even if work budget remains.

SA also applies its own global search budget:

- `eval_budget_sec` bounds one constructive evaluation
- the hard SA budget model is `1 + iters` evaluations:
  - `1` initial evaluation
  - `iters` in-loop candidate evaluations
- effective SA iterations are clamped as:
  - `max_evals = floor(time_limit_sec / eval_budget_sec)`
  - `max_iters = max_evals.saturating_sub(1)`
  - `effective_iters = min(requested_iters, max_iters)`
- `0` iterations are valid and mean:
  - the initial constructive evaluation is returned as the final SA result

This keeps runaway scenarios bounded while allowing deterministic stop behavior under normal load.

Implication:

- In wall-clock mode near the time-limit boundary, small scheduler/CPU jitter can change whether a final placement
  attempt is completed before cutoff.
- In such timeout-bound runs, run-to-run placement count or hash drift can appear even with
  identical input and seed.

Policy alignment:

- Determinism guarantees are strict for non-timeout-bound runs.
- Timeout-bound runs are best-effort and should be labeled explicitly in benchmark/report tooling.

## 8. Part-in-part pipeline policy (F3-2)

F3-2 introduces an opt-in cavity-aware extension in the BLF placer only.

Activation and scope:

- `nest` gets `--part-in-part off|auto`.
- Default is `off`, so baseline behavior stays unchanged when the flag is omitted.
- `auto` enables extra cavity candidate generation in BLF before the global grid scan.
- This iteration does not introduce hole-aware NFP/CFR; hybrid gating remains unchanged
  (`--placer nfp` still falls back to BLF when holes or `hole_collapsed` are present).

Cavity source and validation rules:

- Cavity candidates are generated only from already placed polygons' `inflated_polygon.holes`.
- Outer-only / `hole_collapsed`-like sources (`holes=[]`) are ignored as cavity sources.
- Candidate anchors are deterministic and hole-geometry-based (bbox/vertex + deterministic nudges),
  so off-grid cavity placements can be reached.
- Every cavity candidate is validated through the existing `can_place()` narrow-phase.
- If no cavity candidate is feasible, the original global BLF grid-scan path runs unchanged.

## 9. References

- `docs/nesting_engine/tolerance_policy.md` (SCALE, contour winding, touching policy)
- `docs/nesting_engine/json_canonicalization.md` (determinism reference)
- `canvases/nesting_engine/simulated_annealing_search.md` (F2-4 feature intent / task-level design)
- `canvases/nesting_engine/arc_spline_polygonization_policy.md` (F3-1 curve policy intent)
- `canvases/nesting_engine/part_in_part_pipeline.md` (F3-2 feature intent / task-level design)
