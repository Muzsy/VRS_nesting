# SGH-Q04 phase orchestration contract

## Decision

SGH-Q04 bevezeti az első VRS-natív exploration/compression orchestration réteget. Ez nem teljes Sparrow-parity, hanem rectangular Phase 1 orchestration foundation, amely későbbi Sparrow-quality feature-ök alapja lesz.

## Source Sparrow feature mapping

| Sparrow feature | VRS adaptation | Status |
|---|---|---|
| Algorithm 12: exploration_phase() | ExplorationPhase | PARTIAL |
| Algorithm 13: compression_phase() | CompressionPhase | PARTIAL |
| InfeasibleSolutionPool | InfeasibleSolutionPool | PARTIAL |
| LargeItemSwapDisruption | LargeItemSwapDisruption | PARTIAL |
| Phase budget/time management | PhaseBudget | PARTIAL |

## VRS adaptation boundary

Tilos ebben a taskban:
- BPP phase loop / sheet elimination iteratív loop
- continuous rotation / RotationPolicy
- smooth LossModel / pole penetration
- CollisionBackend / CDE backend
- DXF/preflight módosítás
- IO contract módosítás
- Python runner módosítás

## Public API

```rust
// Phase API (phase.rs)
PhaseConfig { seed, worker_count, exploration_budget, compression_budget, ... }
PhaseBudget { max_iterations, time_limit_s }
PhaseDiagnostics { phase_type, iterations_run, stop_reason, best_score, ... }
PhaseResult { layout, score, initial_score, best_score, diagnostics, unplaced }
PhaseOptimizer::run(layout, parts, sheets) -> PhaseResult

// Exploration (explore.rs)
ExplorationPhase::new(config) -> Self
ExplorationPhase::run(layout, parts, sheets) -> (WorkingLayout, PhaseDiagnostics)
InfeasibleSolutionPool::new(capacity) -> Self
InfeasibleSolutionPool::push(candidate) / best() / len()
LargeItemSwapDisruption::try_disrupt(layout, parts, sheets, iteration) -> Option<Vec<Placement>>

// Compression (compress.rs)
CompressionPhase::new(config) -> Self
CompressionPhase::run(layout, parts, sheets) -> (WorkingLayout, PhaseDiagnostics)
```

## PhaseConfig and budgets

- `seed: i64` — deterministic RNG seed
- `worker_count: usize` — passed to VrsSeparatorConfig
- `exploration_budget: PhaseBudget` — max_iterations + time_limit_s
- `compression_budget: PhaseBudget` — max_iterations + time_limit_s
- `pool_capacity: usize` — infeasible pool bound
- `disruption_top_percentile: f64` — top % of items for disruption
- `disruption_max_attempts: usize` — max disruption attempts

## ExplorationPhase contract

- Preserves feasible incumbent (never returns worse score than input)
- Stores infeasible candidates in bounded pool (loss-ascending order)
- Uses VrsSeparator for collision resolution
- Deterministic tie-break on pool ordering
- LargeItemSwapDisruption on stuck state (5 consecutive no-improvement)

## InfeasibleSolutionPool contract

- Capacity-bounded (pool_capacity)
- Loss-ascending ordering with stable tie-break
- Feasible candidates never stored (only infeasible)
- Public API: push(), best(), len(), drain()

## LargeItemSwapDisruption contract

- Selects top-percentile large items by area
- Deterministic pair selection (seed + iteration)
- Uses MoveExecutor::try_swap for rollback-safe perturbation
- Only commits if resulting layout is violation-free

## CompressionPhase contract

- Only score-non-worsening candidates commit
- Accepted output always find_violations == empty
- Returns original incumbent if no improvement found
- Deterministic iteration order

## Determinism and seed contract

- Identical input + seed + config → bit-identical output
- PhaseConfig::deterministic_default() provides baseline deterministic config
- Worker shuffle uses seed via deterministic PRNG

## Score/no-downgrade contract

- Exploration: best_score <= initial_score (feasible incumbent preserved)
- Compression: best_score <= initial_score (no downgrade)
- If no improvement, original layout returned unchanged

## Validation and commit gates

- All accepted layouts pass find_violations check
- validate_for_commit called before any layout acceptance
- No implicit conversion from WorkingLayout to accepted output

## Tests and acceptance gates

1. PhaseConfig default/budget smoke
2. InfeasibleSolutionPool capacity + loss ordering + deterministic tie-break
3. Exploration preserves feasible incumbent
4. Exploration stores infeasible candidate without accepting infeasible output
5. LargeItemSwapDisruption selects top-percentile large items deterministically
6. Compression no-downgrade: best_score <= initial_score or unchanged baseline
7. Compression accepted output find_violations == empty
8. Full PhaseOptimizer same seed determinism
9. Phase budget stop reason
10. F11-F14 parity update documented in report

## Remaining quality gaps after SGH-Q04

| Gap | Status | Next task |
|---|---|---|
| F11 exploration/compression orchestration | PARTIAL → PARTIAL | SGH-Q05 |
| F12 infeasible solution pool | PARTIAL | SGH-Q05 |
| F13 disruption loop | PARTIAL → PARTIAL+ | SGH-Q05 |
| F14 per-phase time budget | PARTIAL | SGH-Q05 |
| Continuous rotation | MISSING | SGH-Q07 |
| Smooth LossModel | MISSING | SGH-Q06 |
| CDE backend | MISSING | SGH-Q08 |

## Next task: SGH-Q05

SGH-Q05 will address:
- BPP phase loop / sheet elimination orchestration
- Multi-phase iteration with sheet elimination
- Integration with existing PhaseOptimizer foundation
