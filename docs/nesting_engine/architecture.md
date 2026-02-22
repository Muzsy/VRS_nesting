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

## 4. References

- `docs/nesting_engine/tolerance_policy.md` (SCALE, contour winding, touching policy)
- `docs/nesting_engine/json_canonicalization.md` (determinism reference)
