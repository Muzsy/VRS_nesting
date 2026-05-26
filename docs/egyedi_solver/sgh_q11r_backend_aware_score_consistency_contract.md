# SGH-Q11R Contract — Backend-aware score consistency + candidate evaluation

## Purpose

SGH-Q11R closes the remaining post-Q11 consistency gaps where backend-aware validation existed but scoring or candidate selection could still be driven by bbox-only decisions.

## Contract

### Score policy

Every Q11R-scope decision or diagnostic score that depends on the selected collision backend must use:

```rust
score_with_backend(..., &config.collision_backend)
```

This applies to:

- `PhaseOptimizer::run()` initial/final/result/best score.
- `ExplorationPhase::run()` initial/incumbent score.
- `CompressionPhase::run()` initial/incumbent score.
- Phase1 adapter `score_breakdown`.

`CollisionBackendKind::Bbox` remains backward-compatible and delegates to the legacy bbox score semantics.

### Separator candidate policy

`VrsSeparator::find_best_candidate_for_target()` must not rank exact-backend candidates with bbox-only overlap decisions.

- Bbox: keep the current fast bbox candidate path.
- JaguaPolygonExact: build a candidate `Placement`, check sheet containment through `placement_within_sheet`, and check pair collisions through `placement_overlaps` against relevant placements.
- NoCollision: zero candidate loss.
- Collision: backend-confirmed collision gets surrogate loss magnitude.
- Unsupported: candidate reject / hard invalid, never NoCollision and never silent bbox fallback.
- CDE: candidate reject / hard invalid until real CDE support exists.

### Sheet elimination policy

`SheetEliminationEngine` must carry the selected `CollisionBackendKind`.

- `new(...)` defaults to Bbox.
- `new_with_rotation_context(...)` defaults to Bbox.
- `new_with_backend_and_rotation_context(...)` accepts an explicit backend.
- `BppPhase::run()` must call the explicit constructor with `config.collision_backend`.
- Sheet elimination commit/fallback/LBF candidate checks must not silently downgrade exact or CDE validation to bbox.

## Non-goals

- No CDE full implementation.
- No exact backend as global default.
- No hole/cavity semantics.
- No DXF/preflight refactor.
- No full polygon penetration-depth loss implementation.
- No `legacy_multisheet` default replacement.
- No breaking JSON output change.

## Verification gate

Q11R is not PASS until these commands are green in a local repo with Rust tooling installed:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::explore
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
```

Only after green verification may the report be updated to `PASS` and `SGH-Q12_STATUS: READY`.
