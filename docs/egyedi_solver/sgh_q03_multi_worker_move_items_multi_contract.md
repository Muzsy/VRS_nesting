# SGH-Q03 multi-worker move_items_multi contract

## Decision

SGH-Q03 extends `VrsSeparator` with deterministic multi-worker search in `separator.rs` while preserving SGH-Q02 behavior for `worker_count <= 1`.

Key decisions:
- `VrsSeparatorConfig` gains `worker_count` and `seed` (defaults: `1`, `0`).
- `worker_count=0` is normalized to `1` (no panic, backward-compatible).
- `worker_count>1` runs N workers from the same master snapshot per iteration.
- Worker 0 is baseline-compatible (single-worker target selection), workers 1..N use deterministic seeded shuffle.
- Master commits only if candidate improves raw loss, or ties raw loss and improves weighted loss.

## Source Sparrow feature mapping

Reference source used from local clone:
- `.cache/sparrow/src/optimizer/separator.rs` → `move_items_multi()` (Algorithm 10)
- `.cache/sparrow/src/optimizer/worker.rs` → `move_items()` (Algorithm 5)

Mapping:
- Sparrow worker fan-out from one master snapshot → VRS `run_worker_iteration(...)` per worker
- Worker-specific move order randomization → VRS deterministic `deterministic_shuffle(..., worker_seed)`
- Best-worker-wins merge → VRS stable worker candidate ranking and conditional commit

## VRS implementation summary

Production change is limited to:
- `rust/vrs_solver/src/optimizer/separator.rs`

Main additions:
- `SeparatorWorker` and `WorkerCandidate` private structs
- Deterministic worker RNG (`DeterministicRng`) and Fisher-Yates shuffle helper
- Candidate tie-break comparator (raw loss, weighted loss, accepted moves, worker_id, placement ordering)
- Multi-worker branch inside `VrsSeparator::run`
- `VrsCollisionTracker` and `LossSnapshot` made clonable to support worker snapshots

## Config semantics

`VrsSeparatorConfig` new fields:
- `worker_count: usize` default `1`
- `seed: u64` default `0`

Semantics:
- `worker_count <= 1` uses baseline path.
- `worker_count == 0` is normalized to `1`.
- For `worker_count > 1`, each worker gets seed:
  - `seed ^ mix(iteration) ^ mix(worker_id)`
- Same input + same `seed` + same `worker_count` => deterministic output and diagnostics.

## Worker model

Each worker:
- Starts from cloned master layout (`WorkingLayout`) and tracker (`VrsCollisionTracker`)
- Computes its own deterministic move-target order
- Attempts separator moves independently
- Returns candidate layout + tracker + metrics (`raw_loss`, `weighted_loss`, attempted/accepted/rollback)
- Does not mutate shared state

Master behavior:
- Builds N worker candidates from identical master state
- Deterministically ranks candidates
- Commits only improving candidate

## Determinism and seed contract

Determinism guarantees:
- `deterministic_shuffle` is pure given `(colliders, seed)`
- Worker seed is deterministic from `(config.seed, iteration, worker_id)`
- Tie-break uses stable ordering including placement ordering fallback
- Unit test `multi_worker_same_seed_is_deterministic` asserts bit-identical output/diagnostics

## Candidate selection and tie-break contract

Worker selection order (ascending / better first):
1. Lower `raw_loss`
2. Lower `weighted_loss`
3. Higher `moves_accepted`
4. Lower `worker_id`
5. Stable placement ordering comparison

Commit rule:
- Commit if `candidate.raw_loss < master.raw_loss`
- Or if `raw_loss` equal and `candidate.weighted_loss < master.weighted_loss`

## Rollback and GLS weight handling

Rollback logic from SGH-Q02 remains active:
- Failed local move restores loss-state via `restore_but_keep_weights`
- GLS weights are preserved and updated by existing multiplicative SGH-Q02 formula

Master-level no-improvement iteration:
- Keeps current master placement state
- Applies one GLS update on master tracker

## Tests and acceptance gates

Implemented SGH-Q03-focused tests:
- `separator_worker_count_one_backward_compatible`
- `separator_worker_count_zero_normalized_to_one`
- `multi_worker_same_seed_is_deterministic`
- `worker_seed_shuffle_smoke_distinct_and_deterministic`
- `dense_fixture_three_worker_not_worse_than_single_worker`
- `dense_fixture_three_worker_output_no_violations_if_zero_loss`
- `worker_candidate_tiebreak_is_deterministic`

Mandatory gates executed in task report:
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml separator`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q03_multi_worker_move_items_multi.md`

## Remaining quality gaps after SGH-Q03

Status update:
- F09 (`move_items_multi`) moves from `MISSING` to `PARTIAL/FULL(rectangular scope)` on deterministic multi-worker search
- Not in SGH-Q03 scope and still open:
  - Full exploration/compression orchestration (F11/F12/F13/F14)
  - Continuous rotation and smooth loss model (F01/F05/F06)
  - CDE collision backend for irregular parity (F04 full)

## Next task: SGH-Q04

SGH-Q04 remains the next task:
- Exploration/compression phase orchestration
- Infeasible pool and disruption loop
- Phase-level time-budget orchestration
