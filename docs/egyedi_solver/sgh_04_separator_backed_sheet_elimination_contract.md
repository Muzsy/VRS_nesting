# SGH-04 Separator-backed sheet elimination contract

## Purpose

SGH-04 upgrades `SheetEliminationEngine` with a SparrowGH-style bin-reduction pattern inside the VRS Rust optimizer. The elimination attempt removes items from one target sheet, redistributes them to lower-index sheets with deterministic LBF clear reinsertion, and falls back to `WorkingLayout` + `VrsSeparator` when clear reinsertion fails.

Accepted output remains strict: no violations, sheet count reduced, and full rollback on any gate failure.

## Current SheetElimination V1 gap

Before SGH-04, `sheet_elimination.rs` used a simple non-target-sheet reinsert loop:

- target sheet selection was weakest-sheet heuristics (area/count tie-broken by index), not explicitly `max+1` contract reducing;
- redistribution used only clear candidate placement;
- no `WorkingLayout` / `VrsSeparator` fallback for displaced items;
- diagnostics did not expose displaced/LBF/separator/rejection counters.

This could miss elimination opportunities and did not explicitly enforce lower-index-only receiving sheets for `sheet_count_used` reduction safety.

## SparrowGH bin-reduction mapping

SGH-04 maps the key SparrowGH `bp_explore.rs` pattern to VRS:

- **sheet/bin elimination attempt**: choose one used sheet and remove its items;
- **largest-first redistribution**: sort displaced queue deterministically;
- **clear LBF attempt first**: reuse existing receiving sheets before opening spread;
- **separator repair fallback**: run separator on working state when clear reinsert fails;
- **commit/rollback discipline**: only accept valid, reducing layouts; otherwise restore snapshot.

Excluded in SGH-04: solution pool, perturbation, transfer/swap operators, external backend.

## VRS sheet_count_used constraint

`compute_sheet_count_used()` contract is:

```rust
max(sheet_index) + 1
```

This is not distinct-sheet-count. Therefore SGH-04 must eliminate the highest used sheet to guarantee that successful redistribution can strictly reduce `sheet_count_used` without unsafe reindexing.

## Target sheet selection V2

SGH-04 target rule:

- `target_sheet = max(placement.sheet_index)`.

Rationale:

- if all displaced items are moved to sheets `< target_sheet`, then the highest used index decreases;
- no sheet reindexing is needed;
- no silent non-reducing attempt is accepted by commit gate.

## Receiving sheet restriction

Redistribution is restricted to:

```text
sheet_index < target_sheet
```

SGH-04 enforces this in both phases:

- LBF clear reinsertion filters candidates to lower-index sheets only;
- separator fallback config uses optional `allowed_sheet_indices` filter;
- commit gate rejects any `sheet_index >= target_sheet` in separator output.

## LBF reinsertion V2

Displaced queue ordering:

```text
area desc -> max_dim desc -> instance_id asc
```

Per-item clear reinsert is LBF-scored with deterministic key:

```text
used receiving sheet first -> lower y -> lower x -> lower sheet_index
```

Implementation uses existing VRS helpers:

- `generate_candidates_with_sheets()`
- `rect_within_boundary()`
- `dims_for_rotation()`
- `placement_anchor_from_rect_min()`
- `PlacedBbox::overlaps()`
- `bbox_from_placement()`

## Separator-backed fallback V1

When LBF clear reinsertion fails for a displaced item:

1. choose deterministic seed receiving sheet from allowed lower-index sheets (max estimated free area);
2. add seed placement;
3. build `WorkingLayout`;
4. run `VrsSeparator::run()` with `allowed_sheet_indices=Some(lower_sheets)`;
5. accept only if:
   - `best_loss == 0.0` or `converged == true`,
   - `validate_for_commit(parts, sheets)` passes,
   - no placement uses `sheet_index >= target_sheet`,
   - `find_violations()` is empty.

Failure in any gate path triggers elimination-attempt rollback.

## Commit/rollback gates

Commit conditions for elimination attempt:

- all displaced items reinserted;
- final placements use only sheets `< target_sheet`;
- `find_violations()` is empty;
- `sheet_count_used_after < sheet_count_used_before`;
- placement count invariant preserved.

On any failure:

- reject attempt;
- rollback to pre-attempt snapshot;
- keep original placements/unplaced output.

Partial success is not allowed.

## Diagnostics

`SheetEliminationDiagnostics` SGH-04 fields include:

- displaced item count;
- LBF reinsertion successes;
- separator fallback attempts/successes/failures;
- commit-gate rejection count;
- target/higher sheet reuse rejection count;
- receiving sheet count.

`summary()` includes all SGH-04 counters for auditability.

## Scope exclusions

SGH-04 explicitly does not include:

- external SparrowGH backend or vendor/submodule;
- `io.rs` / solver output contract changes;
- Python runner or exact validator changes;
- `adapter.rs` changes;
- `score.rs` objective rewrite;
- `moves.rs` transfer/swap execution;
- solution pool / perturbation / multi-restart;
- continuous rotation;
- unsafe sheet reindexing.

## Preparation for SGH-05

SGH-04 establishes the safe elimination/redistribution baseline for SGH-05:

- separator candidate sheet scoping is now explicit via optional allowed-sheet filter;
- elimination diagnostics expose where clear vs separator recovery succeeds/fails;
- commit/rollback gates already enforce strict accepted-output safety;
- this creates a stable boundary for future transfer/swap move operator integration.
