# SGH-01 WorkingLayout state contract

Document date: 2026-05-24. Describes the design, rules, and invariants of
`WorkingLayout` as introduced in SGH-01.

---

## Purpose

`WorkingLayout` is a transient, in-process layout state used by the VRS
optimizer's separator-driven search loop (SGH-02 and later).  It exists to give
the search algorithm a place to temporarily hold colliding or boundary-violating
placements — which arise during GLS-based item movement — without polluting the
accepted layout state.

Before SGH-01, the VRS optimizer had no explicit concept of an "infeasible working
state".  All optimizer state (`LayoutState`) was required to be valid at all
times.  `repair.rs` avoided infeasible states entirely by only ever placing items
into valid candidate positions.  A separator cannot operate this way: it must
move items through infeasible positions to escape local minima.

`WorkingLayout` fills that gap.

---

## Relationship to LayoutState and SolverOutput

```
SolverInput
    │
    ▼
WorkingLayout          ← search / separator operates here (violations OK)
    │
    │  validate_and_commit()     ← calls find_violations(); rejects if non-empty
    ▼
(Vec<Placement>, Vec<Unplaced>)  ← clean, violation-free pairs
    │
    ├─→ LayoutState              ← internal post-commit state (optimizer bookkeeping)
    └─→ io::SolverOutput         ← JSON output contract (Python runner / exact validator)
```

Key differences:

| Type | Violations allowed? | Used for |
|---|---|---|
| `WorkingLayout` | YES | Search state during separator loop |
| `LayoutState` | NO | Internal optimizer bookkeeping after commit |
| `io::SolverOutput` | NO | Accepted JSON output; Python exact validator gate |

There is **no implicit conversion** from `WorkingLayout` to `LayoutState` or
`SolverOutput`.  The only path is through `validate_and_commit`, which rejects
any violation.

---

## Infeasible working state rules

1. **Storage is unchecked.** `WorkingLayout::new()` and direct field mutation
   do not validate placements.  The caller may store overlapping or out-of-bounds
   placements freely.

2. **Violation types** (mirroring `repair::ViolationType`):
   - `Overlap` — bbox of placement overlaps another valid placement on the same sheet.
   - `BoundaryOrSheet` — placement is outside the sheet boundary, or `sheet_index`
     is out of range.

3. **The separator may produce infeasible intermediate states.**  Each call to
   `snapshot()` followed by `rollback` (restoring a previous snapshot) is the
   standard undo mechanism.

4. **All infeasible states must be resolved before commit.**  `validate_and_commit`
   is the gate; it is not optional.

---

## Commit gate

```rust
pub fn validate_and_commit(
    self,
    parts: &[Part],
    sheets: &[SheetShape],
) -> Result<(Vec<Placement>, Vec<Unplaced>), WorkingCommitError>
```

Internally calls `repair::find_violations(placements, parts, sheets)`.

- If the violation list is empty → returns `Ok((placements, unplaced))`.
- If any violation exists → returns `Err(WorkingCommitError::Violations(diag))`
  where `diag` carries `violation_count`, `overlap_count`, and `boundary_count`.

`validate_for_commit` is the non-consuming variant for inspection without
committing.

**Important:** `validate_and_commit` consumes `self`.  If rollback may be needed,
call `snapshot()` before `validate_and_commit`.

---

## Forbidden implicit conversions

The following patterns are **forbidden** and must not be added in any future task:

```rust
// FORBIDDEN: impl From<WorkingLayout> for LayoutState
// FORBIDDEN: impl From<WorkingLayout> for SolverOutput
// FORBIDDEN: any method that returns LayoutState without calling find_violations
// FORBIDDEN: any method that builds SolverOutput from WorkingLayout directly
```

All output from `WorkingLayout` must pass through `validate_and_commit` or
`validate_for_commit` + explicit construction.

---

## Snapshot / rollback contract

```rust
let snap = working_layout.snapshot();   // full clone
// ... mutate working_layout ...
if commit_failed {
    working_layout = snap;              // restore
}
```

`snapshot()` returns `Self` (full `Clone`).  It is allocation-cheap for small
layouts (< 300 placements in Phase 1).  The separator loop should snapshot before
each item move and restore on failure.

Invariant: after restore, `working_layout` is byte-identical to the state at
the time of `snapshot()`.  This is guaranteed by `#[derive(Clone)]` on
`Placement` and `Unplaced` (which contain only primitive types and `String`).

---

## Preparation for SGH-02 VrsSeparator

`WorkingLayout` provides exactly the primitives the SGH-02 `VrsSeparator` will need:

| SGH-02 need | Provided by WorkingLayout |
|---|---|
| Store temporarily colliding placements | `placements: Vec<Placement>` without validation |
| Roll back to pre-move state | `snapshot()` / reassignment |
| Check if current state is feasible | `validate_for_commit()` returns `Ok(_)` iff no violations |
| Commit best feasible state | `validate_and_commit()` → clean pairs |
| Diagnostic counts for GLS book-keeping | `WorkingCommitDiagnostics.overlap_count`, `.boundary_count` |

The `VrsSeparator` will add a `VrsCollisionTracker` that caches weighted pair
losses on top of `WorkingLayout`.  The tracker is separate from `WorkingLayout`
to keep this type minimal and free of GLS-specific state.
