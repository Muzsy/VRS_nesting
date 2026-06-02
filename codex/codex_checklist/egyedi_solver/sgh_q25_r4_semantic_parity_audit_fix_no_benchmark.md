# Checklist — SGH-Q25-R4 Semantic parity audit/fix

## Scope / hygiene

- [x] Read `AGENTS.md`, Codex docs, Q25-R3 report, and relevant upstream Sparrow files.
- [x] Record `.cache/sparrow` commit hash.
- [x] Record `git status --porcelain=v1` before editing.
- [x] Record `git diff --name-only` before editing.
- [x] List pre-existing dirty files separately.
- [x] Do not modify out-of-scope files.
- [x] End with `OUT_OF_SCOPE_NEW_CHANGES: NONE` or mark `REVISE_SCOPE_BLOCKED`.

## Coordinate convention

- [x] Document that `evaluate_sample(x, y, rot)` receives rect-min coordinates.
- [x] Ensure `UniformBBoxSampler` emits rect-min coordinates.
- [x] Ensure `search_placement` passes rect-min coordinates.
- [x] Add explicit `rect_min_x` and `rect_min_y` sample-space fields to `ScoredPlacement`.
- [x] Ensure `LBFEvaluator` fills sample-space fields from `rmx/rmy`.
- [x] Ensure `SeparationEvaluator` fills sample-space fields from `rmx/rmy`.
- [x] Ensure `CoordinateDescent` mutates rect-min coordinates, not anchor coordinates.
- [x] Ensure `BestSamples` deduplicates in sample-space rect-min coordinates, not anchor coordinates.
- [x] Add a rotated/non-90° regression test for anchor-vs-rect-min mismatch.

## LBF Invalid semantics

- [x] Ensure `LBFEvaluator` returns no colliding `ScoredPlacement`.
- [x] Remove `is_clear: false` from `lbf_evaluator.rs`.
- [x] Remove artificial collision-ranking branch from LBF evaluator.
- [x] Ensure `LBFBuilder` places only clear candidates.
- [x] Ensure unresolved/no-clear cases are recorded honestly.
- [x] Ensure fixed-sheet bootstrap remains outside `LBFBuilder`.
- [x] Add a test proving colliding LBF candidate is invalid/rejected.

## Fixed-sheet adaptation honesty

- [x] Report fixed-sheet bootstrap as fixed-sheet separator bootstrap, not LBF parity.
- [x] Do not present infeasible bootstrap placements as constructive LBF success.
- [x] Add/keep test coverage for unresolved bootstrap outside LBF.

## Report correction

- [x] Add `Q25_R3_REPORT_CLAIM_CORRECTION` section.
- [x] Explicitly say whether Q25-R3 LBF collision-invalid claim matched the source.
- [x] If mismatch existed, state exact file/function fixed.
- [x] State whether coordinate convention issue was real and how it was fixed.

## Regression prevention

- [x] No `WorkingLayout` in `optimizer/sparrow`.
- [x] No `VrsCollisionTracker` in `optimizer/sparrow`.
- [x] No compression phase added.
- [x] No bbox/AABB/proxy ranking added to separation or LBF.
- [x] No LV8 quality benchmark acceptance added.

## Verification

- [x] Run `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`.
- [x] Run `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`.
- [x] Run `python3 scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py`.
- [x] Run `./scripts/check.sh`.
- [x] Run `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`.
