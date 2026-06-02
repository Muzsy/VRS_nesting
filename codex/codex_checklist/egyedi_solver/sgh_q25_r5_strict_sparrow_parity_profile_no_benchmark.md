# Checklist — SGH-Q25-R5 Strict Sparrow parity profile

## Scope / hygiene

- [x] Read `AGENTS.md`, Codex docs, Q25-R4 report, and relevant upstream Sparrow files.
- [x] Record `.cache/sparrow` commit hash.
- [x] Record `git status --porcelain=v1` before editing.
- [x] Record `git diff --name-only` before editing.
- [x] List pre-existing dirty files separately.
- [x] Do not modify out-of-scope files.
- [x] End with `OUT_OF_SCOPE_NEW_CHANGES: NONE` or mark `REVISE_SCOPE_BLOCKED`.

## Strict profile / policy

- [x] Introduce explicit strict parity profile, preferably `SparrowStrictParity`.
- [x] Introduce explicit touching policy, preferably `CdeTouchingPolicy::SparrowStrict` and `CdeTouchingPolicy::VrsTouchAllowed`.
- [x] Ensure strict parity is the path used for Sparrow parity claims.
- [x] Ensure VRS touch-allowed behavior is explicitly named non-parity mode.
- [x] Ensure strict mode does not silently downgrade raw CDE touching collisions to `NoCollision`.
- [x] Add tests for pair touching and boundary touching strict behavior.

## Upstream budgets / limits

- [x] Add strict constants for separator 50 / 25 / 3.
- [x] Add strict constants for LBF 1000 / 0 / 3.
- [x] Add strict constants for separator loop 200 / 3.
- [x] Set strict worker count to 3.
- [x] Disable instance-count budget downscaling in strict profile.
- [x] Keep fast/performance downscaling only in explicit non-parity mode, if retained.

## Worker ordering

- [x] Strict worker pass shuffles all colliding items with worker RNG.
- [x] Remove strict-mode worker-index bias: no worst-first, reverse, least-loss-first.
- [x] Preserve best-worker load-back by total weighted loss.
- [x] Add test for RNG-shuffle-only ordering semantics.

## Separator loop

- [x] Replace strict hard-coded `no_improve_limit = 6` with 200.
- [x] Replace strict hard-coded `strike_limit = 4` with 3.
- [x] Add test proving strict loop limits are upstream parity values.

## Exploration / disruption

- [x] Keep fixed-sheet model; do not add strip shrinking/widening.
- [x] Keep infeasible pool sorted by raw loss.
- [x] Use max consecutive failed attempts = 10 in strict profile.
- [x] Use normal-distribution-like biased restore with stddev 0.25, not seed+attempt modulo better-half.
- [x] Select random pair from large-item candidate pool, not always the two largest items.
- [x] Use 0.75 convex-hull-area percentile idea as closely as local shapes allow.
- [x] Keep contained-item relocation.
- [x] Keep cross-sheet / rotation kicks only as documented fixed-sheet extensions.
- [x] Add tests for biased restore and random large-item pair selection.

## Regression prevention

- [x] No `WorkingLayout` in `optimizer/sparrow`.
- [x] No `VrsCollisionTracker` in `optimizer/sparrow`.
- [x] No compression phase added.
- [x] No bbox/AABB/proxy ranking added to separation or LBF.
- [x] No LV8 quality benchmark acceptance added.

## Report

- [x] Add all required Q25-R5 report sections.
- [x] Include exact PASS tokens only when source and tests prove them.
- [x] Explicitly document what remains fixed-sheet adaptation and why.
- [x] Include changed file list and build/test/gate results.

## Verification

- [x] Run `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`.
- [x] Run `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`.
- [x] Run `python3 scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py`.
- [x] Run `./scripts/check.sh`.
- [x] Run `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`.
