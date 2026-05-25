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

Post-Q05R contract (canonical):

```
PhaseResult.score = ScoreModel::score(final_returned_layout)
PhaseResult.best_score = PhaseResult.score.total_cost
```

Both `PhaseResult` fields always refer to the same (final returned) layout. There is no cross-phase minimum: the Q05R correction removed the old formula that took the minimum of exploration, compression, BPP and initial scores. If best-seen scores during exploration or compression are needed, consult the per-phase `PhaseDiagnostics.best_score` fields — they are not surfaced in `PhaseResult`.

`best_seen_score` (minimum across all phases) is currently not part of `PhaseResult`. If it is needed in the future, it must be introduced as a separate field (e.g. `best_seen_score`) with an explicit contract.

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

## BppPhaseDiagnostics fields (Q05R)

| Field | Type | Meaning |
|---|---|---|
| `initial_sheet_count` | `usize` | `compute_sheet_count_used` before BPP loop |
| `final_sheet_count` | `usize` | `compute_sheet_count_used` after BPP loop |
| `attempts` | `usize` | total `SheetEliminationEngine::run()` calls |
| `successful_eliminations` | `usize` | attempts that passed the commit gate |
| `failed_eliminations` | `usize` | attempts that failed the commit gate |
| `rollback_count` | `usize` | same as `failed_eliminations` (implicit clone-based rollback) |
| `stop_reason` | `String` | reason the outer loop terminated |
| `initial_score` | `f64` | `ScoreModel::score` of the input layout before BPP |
| `best_score` | `f64` | **BPP-local diagnostic.** Score of the last successfully committed incumbent; equals `initial_score` if no eliminations. This is not the same as `PhaseResult.best_score` — it is a within-BPP tracking value only. |
| `per_attempt` | `Vec<SheetEliminationDiagnostics>` | one entry per `SheetEliminationEngine::run()` call; `attempts == per_attempt.len()` invariant |

### Per-attempt audit role

`per_attempt` is the audit trail: for each BPP attempt it records which sheet was targeted (`selected_sheet`), how many items were displaced, LBF/separator outcomes, and the internal stop reason. Useful for diagnosing why an elimination failed or what path was taken.

## PhaseResult.score and PhaseResult.best_score semantics (Q05R)

- `PhaseResult.score` = `ScoreModel::score(final_returned_layout)`.
- `PhaseResult.best_score` = `PhaseResult.score.total_cost`.

Both fields always refer to the same layout (the one returned). There is no optimistic claim. If best-seen scores during exploration or compression are needed for analysis, consult the per-phase `PhaseDiagnostics.best_score` fields.

If a future task wants to expose "best score seen across all phases" in `PhaseResult`, it must introduce a separate field (e.g. `best_seen_score`) with an explicit contract — it should not reuse `best_score`.

### PhaseResult.improved() semantics (Q05R)

Because `PhaseResult.best_score == PhaseResult.score.total_cost` after Q05R, `PhaseResult.improved()` is equivalent to:

```
final_score.total_cost < initial_score
```

i.e. it returns `true` if and only if the final returned layout has a strictly lower score than the initial layout passed to `PhaseOptimizer::run()`. It does not compare against exploration/compression intermediates.

## Remaining quality gaps

| Gap | Status | Next task |
|---|---|---|
| Continuous rotation (RotationPolicy) | MISSING | SGH-Q07 |
| Smooth LossModel / pole penetration | MISSING | SGH-Q06 |
| CDE backend | MISSING | SGH-Q08 |
| BPP with non-rectangular sheets | PARTIAL | needs irregular sheet provider |
| Sheet cost weighting in BPP decision | MISSING | requires cost model |
