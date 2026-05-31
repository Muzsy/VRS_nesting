PASS

# SGH-Q24R2 native Sparrow core port implementation

SGH-Q24R2_STATUS: READY_FOR_AUDIT
NATIVE_LIFECYCLE_STATUS: IMPLEMENTED (orchestration → separator strike loop → worker-master → worker move_items(all colliding) → exploration pool/disruption → compression restore/pressure/separate/accept)
MAIN_CODE_CHANGE: rust/vrs_solver/src/optimizer/sparrow.rs (solver lifecycle), NOT cde_adapter-only
MEDIUM_BBOX_NATIVE_LIFECYCLE: ok 12/12 (converges via the new lifecycle)
MEDIUM_CDE_PERF: executes within budget (~7.7s, no hang); convergence at this scale is the deferred LV8-style perf gate, not a Q24R2 gate
Q19_STATUS: HOLD

> `PASS` is claimed on the Q24R2 terms: this is a **coding-first native lifecycle
> port**, and "full LV8 convergence is not a required PASS gate; native lifecycle
> implementation is" (run.md). The real Sparrow lifecycle now lives in
> `optimizer/sparrow.rs`: Algorithm 11 orchestration, Algorithm 9 separator
> strike/no-improvement loop, Algorithm 10 worker-master `move_items_multi`,
> Algorithm 5 worker `move_items` over ALL currently colliding items, Algorithm 12
> exploration pool + biased restore + large-item disruption, and Algorithm 13
> compression restore→pressure→separate→accept. The old one-loop + grid-restart +
> primitive (x−1/y−1) compression functions were **removed**. 434 lib tests pass
> (incl. 3 new native-lifecycle unit tests) and the structural smoke is 21/21.

## 1) Original Sparrow files inspected (`.cache/sparrow`)
`src/optimizer/mod.rs` (Alg 11), `src/optimizer/separator.rs` (Alg 9 `separate`,
Alg 10 `move_items_multi`), `src/optimizer/worker.rs` (Alg 5 `move_items`),
`src/optimizer/explore.rs` (Alg 12), `src/optimizer/compress.rs` (Alg 13),
`src/sample/search.rs` (Alg 6), `src/quantify/tracker.rs` (Alg 8).

## 2) Sparrow → VRS mapping (after this port)

| Original Sparrow | VRS implementation (this run) | status |
|---|---|---|
| Alg 11 `optimize` (mod.rs) | `SparrowSeparationKernel::run` orchestration: build initial → `exploration_phase` → `compression_phase` → final validation/`finalize` | IMPLEMENTED |
| Alg 9 `Separator::separate` | `SparrowSeparationKernel::separate` — strike/no-improvement loop, min-loss incumbent, GLS update every iter, rollback preserving GLS | IMPLEMENTED |
| Alg 10 `move_items_multi` | `SparrowSeparationKernel::move_items_multi` — workers load master, run, best-by-weighted-loss loaded back | IMPLEMENTED |
| Alg 5 worker `move_items` | `SparrowSeparationKernel::worker_move_items` — processes ALL `tracker.colliding_indices()` in worker order; accept iff moved item's weighted loss not increased; rollback preserves GLS | IMPLEMENTED |
| Alg 6 `search_placement` | `optimizer/search_position.rs::search_position_for_target` — container grid + focused samples + top-k retention + coordinate-descent refinement | PARITY (reused) |
| Alg 8 tracker/`update_weights` | `optimizer/separator.rs::VrsCollisionTracker` — `colliding_indices`, `update_placement`, `update_weights`, `snapshot_loss`/`restore_but_keep_weights` | PARITY (reused) |
| Alg 12 exploration | `SparrowSeparationKernel::exploration_phase` — bounded infeasible pool (sorted by raw loss), biased restore (top-half), `disrupt_large_items` (large-item position swap), repeated separate under budget | IMPLEMENTED |
| Alg 13 compression | `SparrowSeparationKernel::compression_phase` — restore incumbent → compaction pressure → `separate` → accept iff feasible & objective improved → rollback + decay | IMPLEMENTED |

## 3) Exact Rust files changed
- `rust/vrs_solver/src/optimizer/sparrow.rs` — **main deliverable**: new
  `separate`, `move_items_multi`, `worker_move_items`, `exploration_phase`,
  `disrupt_large_items`, `compression_phase`; `run` rewritten as Alg 11
  orchestration; native-lifecycle diagnostics; deadline guard in the worker pass;
  worker count = 2 (multiple deterministic workers). **Removed** the orphaned old
  lifecycle: `build_grid_spread_seed_layout`, `run_fixed_sheet_compression`,
  `top_target_indices`, `worker_is_better_than_master`, `run_worker_pass`.
- (No meaningful change this run to `cde_adapter.rs`/`cde_observability.rs` — per
  run.md those must not be the main deliverable.)

## 4) PASS-requirement checklist (run.md §"PASS requirements")
| # | requirement | status | evidence |
|---|---|---|---|
| 1 | Real lifecycle code in `optimizer/sparrow.rs` | ✓ | new separate/move_items_multi/worker_move_items/exploration_phase/compression_phase |
| 2 | Orchestration: initial → exploration → compression → validation | ✓ | `run()` |
| 3 | Separator strike/no-improvement loop | ✓ | `separate()` + `separator_strikes`/`separator_no_improvement_iters` |
| 4 | Worker-master `move_items_multi` | ✓ | `move_items_multi()` + `worker_master_loads` |
| 5 | Worker `move_items` over ALL colliding items | ✓ | `worker_move_items` uses `tracker.colliding_indices()`; `worker_colliding_items_seen>1` (unit test) |
| 6 | Search: container + focused + BestSamples + two-stage CD | ✓ | `search_position_for_target` (global grid + focused + top-k coord descent); non-trivial budget |
| 7 | Exploration pool + biased restore + real large-item disruption | ✓ | `exploration_phase` + `disrupt_large_items`; unit test asserts `exploration_pool_inserts/restores>=1`, `exploration_disruptions_large_item_swap>=1` |
| 8 | Compression restore/pressure/separate/accept | ✓ | `compression_phase`; unit test asserts `compression_separation_calls>=1`, objective non-worsening |
| 9 | Tracker save/restore/update supports lifecycle | ✓ | `snapshot_loss`/`restore_but_keep_weights`/`update_placement`/`colliding_indices` |
| 10 | Minimal compile/smoke evidence | ✓ | 434 lib tests pass; smoke 21/21 |

## 5) Native-lifecycle unit tests (in-process proof of code existence)
- `sparrow_q23r3_multi_target_and_incremental_graph_are_diagnosed` — worker-master
  over all colliding items (`worker_master_loads>1`, `worker_colliding_items_seen>1`,
  `separator_invocations>=1`).
- `sparrow_q24r2_exploration_and_compression_lifecycle_are_diagnosed` — medium
  converges; `separator_invocations>=1`, `compression_passes>=1`,
  `compression_separation_calls>=1`, objective non-worsening.
- `sparrow_q24r2_exploration_pool_and_disruption_fire_on_infeasible` — impossible
  fixture: `separator_strikes>=1`, `exploration_pool_inserts>=1`,
  `exploration_pool_restores>=1`, `exploration_disruptions_large_item_swap>=1`.

## 6) Tests / commands run
- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` → ok.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **434 passed, 0 failed**.
- `python3 scripts/smoke_sgh_q24r2_native_sparrow_core_port.py` → **21 passed, 0 failed** (SMOKE: PASS).
  - tiny/two_rect CDE converge via native lifecycle; medium (sparrow_experimental+bbox,
    same `run_sparrow_pipeline`) converges 12/12; medium CDE executes within budget
    (~7.7 s, no hang); impossible → `unsupported` with full diagnostics, no fallback.
- `.cache/sparrow` inspected (§1).

## 7) Honest scope notes
- The native lifecycle is the ACTIVE production path (the old one-loop/grid-restart/
  primitive-compression functions were deleted, not left as the active path).
- Medium **CDE** (12 items) does not converge within an 8 s budget; this is the
  query-bound CDE perf wall documented in Q24R1 (collect_poly_collisions over many
  candidates), explicitly NOT a Q24R2 PASS gate. The native lifecycle converges the
  same medium with the cheap bbox backend, confirming the algorithm (not the
  geometry backend) is correct.
- Search parity reuses `search_position_for_target`; its container/focused/top-k/
  coord-descent components are active (non-trivial budget from Q24).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T06:15:51+02:00 → 2026-05-31T06:18:47+02:00 (176s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.verify.log`
- git: `main@abaec17`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/sparrow.rs | 754 +++++++++++++++++++------------
 1 file changed, 455 insertions(+), 299 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow.rs
?? README_SGH_Q24R2_NATIVE_SPARROW_CORE_PORT_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r2_native_sparrow_core_port.yaml
?? codex/prompts/egyedi_solver/sgh_q24r2_native_sparrow_core_port/
?? codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
?? codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.verify.log
?? scripts/smoke_sgh_q24r2_native_sparrow_core_port.py
```

<!-- AUTO_VERIFY_END -->
