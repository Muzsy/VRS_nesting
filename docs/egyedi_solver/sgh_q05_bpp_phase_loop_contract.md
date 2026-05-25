# SGH-Q05 BPP phase loop contract

## Purpose

SGH-Q05 introduces an iterative BPP (Bin Packing Problem) phase loop that wraps the existing `SheetEliminationEngine` and integrates it as the third stage of `PhaseOptimizer::run()`. The primary goal is sheet-count reduction: fewer sheets used = lower material cost and better packing efficiency.

## Connection: SheetEliminationEngine → BppPhase → PhaseOptimizer

```
PhaseOptimizer::run(layout, parts, sheets)
  -> ExplorationPhase::run(...)        // GLS-based position improvement
  -> CompressionPhase::run(...)        // rotation-based score improvement
  -> BppPhase::run(...)                // iterative sheet elimination
  -> final PhaseResult
```

`BppPhase` does not recurse into `PhaseOptimizer`. It only calls `SheetEliminationEngine::run()` repeatedly.

`SheetEliminationEngine` (SGH-04, `sheet_elimination.rs`) provides a single-pass attempt: remove the highest-index sheet, redistribute displaced items to lower-index sheets (LBF + separator fallback), commit or rollback. `BppPhase` wraps this with an outer loop.

## Commit/rollback invariants

Every successful BPP iteration satisfies:
- `elim_diag.successful_eliminations > 0`
- `new_sheet_count < incumbent_sheet_count`
- `find_violations(new_placements) == []`
- `new_placements.len() == incumbent_placements.len()` (placement count invariant)
- `instance_ids(new_placements) == instance_ids(incumbent_placements)` (instance set invariant)

If any condition fails, the incumbent is unchanged (implicit rollback via pre-call clone) and the loop stops.

`SheetEliminationEngine` already performs its own internal commit/rollback — if elimination fails internally it returns the original placements. `BppPhase` adds an outer safety check as an additional gate.

## Score vs sheet-count decision rule

BPP phase is sheet-count-first:
- A result is committed only if `sheet_count_used` strictly decreases.
- Score comparison is not used in the BPP commit gate (sheet count takes priority).
- After the full pipeline, `PhaseResult.score` is the actual score of the final BPP output.
- `PhaseResult.best_score` = `min(final_score, compression_best, exploration_best, initial_score)`.

This ensures no optimistic claim: `best_score` is always achievable by the returned layout or a layout seen during exploration/compression.

## Budget and loop termination

The outer loop stops when:
1. `successful_eliminations >= bpp_max_eliminations` (default 16) → `stop_reason = "max_eliminations_reached"`
2. `elapsed >= bpp_budget.time_limit_s` (default 30s) → `stop_reason = "time_limit"`
3. `incumbent_sheet_count <= 1` → `stop_reason = "single_sheet_reached"`
4. Elimination attempt fails → `stop_reason = "elimination_failed"`

The inner `StoppingPolicy` for each pass gets `bpp_budget.max_iterations` and `f64::MAX` time limit (time controlled by the outer loop).

## Determinism contract

- Identical input + `PhaseConfig` → bit-identical output.
- `SheetEliminationEngine` is deterministic (LBF ordering is stable, separator uses a fixed seed via `VrsSeparatorConfig::default()`).
- No random state introduced by `BppPhase` beyond what `SheetEliminationEngine` already provides.
- Test: `same_seed_bpp_phase_determinism` verifies bit-identical placements for two runs.

## PhaseConfig additions (SGH-Q05)

```rust
pub bpp_budget: PhaseBudget,       // default: PhaseBudget::new(16, 30.0)
pub bpp_max_eliminations: usize,   // default: 16
```

`bpp_budget.max_iterations` = max iterations passed to each inner `StoppingPolicy`.
`bpp_budget.time_limit_s` = wall-clock limit for the entire BPP phase loop (0.0 = no limit).
`bpp_max_eliminations` = max successful eliminations before stopping.

## Remaining quality gaps

| Gap | Status | Next task |
|---|---|---|
| Continuous rotation (RotationPolicy) | MISSING | SGH-Q07 |
| Smooth LossModel / pole penetration | MISSING | SGH-Q06 |
| CDE backend | MISSING | SGH-Q08 |
| BPP with non-rectangular sheets | PARTIAL | needs irregular sheet provider |
| Sheet cost weighting in BPP decision | MISSING | requires cost model |
