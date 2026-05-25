# SGH-05 Move operators contract

## Purpose

SGH-05 implements rollback-safe move execution operators (`try_reinsert`, `try_transfer`, `try_swap`, `resolve_by_transfers`) inside `rust/vrs_solver/src/optimizer/moves.rs`. These operators are the internal algorithmic building blocks for a future local-search improvement phase (SGH-06+). They are not yet wired into the optimizer pipeline; they expose a testable API only.

All operators share the same invariant: accepted output must be violation-free (`find_violations() == []`). Failure always leaves the caller's data unchanged.

---

## Current moves.rs gap

Before SGH-05, `moves.rs` contained only:
- `CandidateMove` enum skeleton (Place / Move / Reinsert / Rotate variants) with `serde` derive
- 3 serialization unit tests

No execution logic, no collision repair, no commit/rollback discipline.

---

## SparrowGH bp_moves.rs mapping

| SparrowGH concept | VRS SGH-05 equivalent |
|---|---|
| `try_transfer(item, bin)` | `MoveExecutor::try_transfer(placements, instance_id, to_sheet, ...)` |
| `try_swap(a, b)` | `MoveExecutor::try_swap(placements, id_a, id_b, ...)` |
| `try_reinsert(item, pos)` | `MoveExecutor::try_reinsert(placements, instance_id, to_sheet, rot, ...)` |
| `resolve_placeable` / transfer loop | `MoveExecutor::resolve_by_transfers(placements, src_sheets, dst_sheets, budget, ...)` |
| Collision repair via LBF + separator | `lbf_clear_on_sheet` + `run_separator_fix` |
| Rollback via snapshot | Caller slice is never mutated; `None` return = rollback |

SparrowGH direct-copy is BLOCKED (no compatible license). The above is an independent reimplementation using the VRS separator/working layer.

---

## Move execution API

```rust
pub struct MoveExecutor<'a> {
    parts: &'a [Part],
    sheets: &'a [SheetShape],
}

pub struct MoveDiagnostics {
    pub attempted: usize,
    pub committed: usize,
    pub rolled_back: usize,
    pub separator_attempts: usize,
    pub separator_successes: usize,
    pub commit_gate_rejections: usize,
    pub last_reason: String,
}

pub enum MoveFailureReason {
    UnknownInstanceId,
    InvalidSheetIndex,
    UnsupportedRotation,
    NoValidSeedPlacement,
    SeparatorDidNotConverge,
    CommitGateRejected,
    PlacementCountMismatch,
    InstanceSetMismatch,
}
```

All operator methods take `&[Placement]` (borrow) and return `Option<Vec<Placement>>`:
- `Some(new_placements)` — operator succeeded; caller decides whether to adopt the result.
- `None` — operator failed; the caller's original slice is unchanged (rollback-safe by design).

`MoveDiagnostics` is caller-owned and accumulates across multiple calls.

---

## Reinsert operator

```rust
pub fn try_reinsert(
    &self,
    placements: &[Placement],
    instance_id: &str,
    to_sheet: usize,
    rotation_deg: i64,
    diag: &mut MoveDiagnostics,
) -> Option<Vec<Placement>>
```

Steps:
1. Validate `to_sheet < sheets.len()`, `instance_id` exists, `rotation_deg` is supported.
2. Seed the item at bbox-min origin of `to_sheet` with `rotation_deg`.
3. Build new placements: all items except the target + the seed.
4. Run `VrsSeparator` scoped to `to_sheet` via `run_separator_fix`.
5. Full commit gate: count, instance set, sheet bounds, `find_violations`.
6. Return `Some(result)` on success, `None` on any failure.

Failure cases: `UnknownInstanceId`, `InvalidSheetIndex`, `UnsupportedRotation`, `NoValidSeedPlacement`, `SeparatorDidNotConverge`, `CommitGateRejected`.

---

## Transfer operator

```rust
pub fn try_transfer(
    &self,
    placements: &[Placement],
    instance_id: &str,
    to_sheet: usize,
    explicit_rotation: Option<i64>,
    diag: &mut MoveDiagnostics,
) -> Option<Vec<Placement>>
```

Three-path priority:

1. **Explicit rotation path**: if `explicit_rotation` is provided, seed at origin with that rotation and run separator on `to_sheet`.
2. **LBF clear path**: find best collision-free LBF candidate on `to_sheet` (y asc, x asc) using `generate_candidates_with_sheets`. No separator needed.
3. **Origin seed + separator**: seed at origin (first fitting rotation) and run separator on `to_sheet`.

All paths apply the full commit gate before returning. Source sheet is unaffected (item removal only reduces potential violations there).

---

## Swap operator

```rust
pub fn try_swap(
    &self,
    placements: &[Placement],
    instance_id_a: &str,
    instance_id_b: &str,
    diag: &mut MoveDiagnostics,
) -> Option<Vec<Placement>>
```

**Same-sheet swap**: deterministic no-op success — returns `placements.to_vec()` unchanged. Counts as `committed`. This is the documented and tested behavior.

**Cross-sheet swap**:
1. Seed A at origin of B's old sheet (tries B's rotation for A if supported).
2. Seed B at origin of A's old sheet (tries A's rotation for B if supported).
3. Run separator scoped to `{sheet_a, sheet_b}`.
4. Full commit gate.

---

## Resolve-by-transfers helper

```rust
pub fn resolve_by_transfers(
    &self,
    placements: Vec<Placement>,
    source_sheets: &[usize],
    dest_sheets: &[usize],
    budget: usize,
    diag: &mut MoveDiagnostics,
) -> Vec<Placement>
```

Deterministic order:
- Source sheets ascending.
- Items on each source sheet: area descending, then `instance_id` ascending.
- Destination sheets ascending.

Per attempt:
- Skip items already moved off the source sheet in this pass.
- Decrement budget before each `try_transfer` call.
- On first successful transfer per item, move to next item.
- Failed attempts are rollback-safe; no partial invalid state escapes.

Returns the updated placements (may be unchanged if all attempts fail or budget=0).

---

## Commit/rollback gates

### Private commit gate (`commit_gate_ok`)

Called after every separator run before accepting any result:

```
1. new_placements.len() == original_count
2. instance_id set unchanged
3. all sheet_index < sheets.len()
4. find_violations(new_placements, parts, sheets).is_empty()
```

### Private separator runner (`run_separator_fix`)

```
WorkingLayout::new(placements, vec![], sheets.len(), 0)
VrsSeparator::new(config { allowed_sheet_indices }).run(working, parts, sheets)
→ accept only if best_loss == 0.0 || converged
→ AND validate_for_commit(parts, sheets).is_ok()
→ increment separator_successes on accept
```

### Rollback guarantee

All public operators take `placements: &[Placement]`. The original slice is never mutated. On `None` return, the caller's data is unchanged. This is a structural guarantee, not a runtime rollback.

---

## Diagnostics

`MoveDiagnostics::summary()` format:

```
attempted=N committed=N rolled_back=N sep_attempts=N sep_ok=N commit_reject=N last_reason=<str>
```

`last_reason` holds the last failure reason string (or `"committed"` on the last successful move). Multiple calls accumulate all counters.

---

## Determinism rules

- `generate_candidates_with_sheets` is deterministic (sorted, EPS-deduped).
- `VrsSeparator` is deterministic (no RNG, index-based tiebreaking).
- All sorting in `resolve_by_transfers` uses stable keys.
- Same input placements + same move call → same output (verified by `deterministic_smoke` test).

---

## Scope exclusions

SGH-05 explicitly excludes:
- External SparrowGH backend or vendor/submodule.
- `io.rs` / `SolverOutput` / `SolverInput` contract changes.
- `adapter.rs` changes.
- `initializer.rs` or `sheet_elimination.rs` pipeline integration.
- `score.rs` objective rewrite.
- Python runner or exact validator changes.
- Solution pool / perturbation / multi-restart.
- Continuous rotation.
- Cavity-prepack.
- Automatic pipeline wiring of move operators.

Only `rust/vrs_solver/src/optimizer/moves.rs` was modified in production code.

---

## Preparation for SGH-06

SGH-06 (solution pool / perturbation / local search loop) can build directly on SGH-05:

- `MoveExecutor` provides the three canonical move operators needed for a local search loop.
- `MoveDiagnostics` exposes attempt/commit/rollback/separator counters to guide parameter tuning.
- `resolve_by_transfers` is the natural first-phase recovery helper for infeasible multi-sheet layouts after perturbation.
- The `allowed_sheet_indices` separator scoping (established in SGH-04) is already wired into each operator, enabling targeted repair in SGH-06 multi-sheet optimization.
- The commit/rollback discipline guarantees that SGH-06 can chain move operators without risk of accumulating invalid state.
