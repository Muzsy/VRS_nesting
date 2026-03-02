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

## 5. References

- `docs/nesting_engine/tolerance_policy.md` (SCALE, contour winding, touching policy)
- `docs/nesting_engine/json_canonicalization.md` (determinism reference)

## 6. Timeout-Bound Determinism Policy

The placement flow supports two stop modes:

- `wall_clock` (default): cutoff driven by `time_limit_sec` wall-clock checks.
- `work_budget`: deterministic operation-budget cutoff inside BLF and NFP search loops.

For `work_budget` mode, a hard wall-clock safety guard is still applied:

- hard guard threshold = `time_limit_sec + hard_timeout_grace_sec`
- if the hard guard is reached, the run stops even if work budget remains.

This keeps runaway scenarios bounded while allowing deterministic stop behavior under normal load.

Implication:

- In wall-clock mode near the time-limit boundary, small scheduler/CPU jitter can change whether a final placement
  attempt is completed before cutoff.
- In such timeout-bound runs, run-to-run placement count or hash drift can appear even with
  identical input and seed.

Policy alignment:

- Determinism guarantees are strict for non-timeout-bound runs.
- Timeout-bound runs are best-effort and should be labeled explicitly in benchmark/report tooling.
