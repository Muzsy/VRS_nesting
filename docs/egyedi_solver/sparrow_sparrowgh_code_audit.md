# Sparrow / SparrowGH code audit

Audit date: 2026-05-24. All source files retrieved from live public repos; no invented paths or APIs.

---

## Source repositories and pinned refs

| Alias | URL | Commit | Cloned to |
|---|---|---|---|
| JeroenGar/sparrow | https://github.com/JeroenGar/sparrow | a4bfbbe0bf864a7eaf136f9d06456155b1163195 | /tmp/vrs_sparrow_audit/JeroenGar_sparrow/ |
| coroush/sparrow | https://github.com/coroush/sparrow | 5df9ce15960f262545169f989ff1068b5f038c9c | /tmp/vrs_sparrow_audit/coroush_sparrow/ |
| coroush/sparrow-grasshopper | https://github.com/coroush/sparrow-grasshopper | 0c9a13622e9a63caa693a7271d36e28826f2899d | /tmp/vrs_sparrow_audit/coroush_sparrow_grasshopper/ |

**coroush/sparrow-grasshopper note:** The `sparrow` subdir inside the GH repo is an empty git submodule (no Rust source present). The GH plugin itself is C# only. All BPP algorithm source audited in this document comes from the `coroush/sparrow` Rust repository.

---

## License and attribution

| Repo | LICENSE path | License | Copyright |
|---|---|---|---|
| JeroenGar/sparrow | LICENSE | MIT | Copyright (c) 2025 Jeroen Gardeyn, KU Leuven |
| coroush/sparrow | LICENSE | MIT | Copyright (c) 2025 Jeroen Gardeyn, KU Leuven (same header) |
| coroush/sparrow-grasshopper | NOT_FOUND | UNKNOWN | — |

**License decision:**
- `JeroenGar/sparrow` and `coroush/sparrow`: MIT — algorithmic patterns may be studied and reimplemented in VRS. Direct code copy is permissible but not planned; reimplementation inside VRS is the target path.
- `coroush/sparrow-grasshopper` C# plugin: no LICENSE found → **direct-copy BLOCKED** per `LICENSE_REQUIRED` rule. Since the BPP algorithms are in `coroush/sparrow` (MIT), this does not block the migration — only the C# wrapper code is affected.

---

## Original Sparrow architecture summary

JeroenGar/sparrow is a **strip-packing (SPP)** solver for irregular 2D parts. Core primitives:

- **Backend:** `jagua-rs` — NFP/CDT geometry, `Layout`, `SPProblem`/`SPInstance`, continuous rotation, `CollisionDetectionEngine`.
- **Separator (`optimizer/separator.rs`):** Algorithm 9 from arXiv:2509.13329. `Separator` holds `SPProblem` + `CollisionTracker` + parallel `SeparatorWorker`s. Inner loop: `move_items_multi()` → each worker runs `move_items()` (shuffle colliding items, `search_placement` via `SeparationEvaluator`) → pick worker with lowest `get_total_weighted_loss()` → restore best. Outer loop: strike-based (`strike_limit`, `iter_no_imprv_limit`). On zero loss: break and return. `update_weights()` implements GLS (Algorithm 8).
- **Exploration (`optimizer/explore.rs`):** Compression/shrink loop; not directly relevant to BPP but informative about solution pool structure.
- **`CollisionTracker` (`quantify/tracker.rs`):** `PairMatrix` of `CTEntry { loss, weight }` + per-item container collision. `recompute_loss_for_item()` uses jagua-rs `collect_poly_collisions`. `register_item_move()` updates index map. `update_weights()` GLS weight step.
- **Stopping:** terminator trait; time-budget aware.

---

## SparrowGH/coroush BPP architecture summary

coroush/sparrow extends JeroenGar/sparrow with a **bin packing (BPP)** layer (`src/bp_optimizer/`). Geometry backend: same `jagua-rs`. BPP types: `BPInstance`, `BPProblem`, `BPSolution`, `Layout`, `LayKey`.

### Phase 1 — FFD + LBF construction (`bp_lbf.rs`, `BpLbfBuilder`)

Items sorted largest-first by `ChAreaTimesDiameter` / `ChArea` / `ExactArea`. For each item:

1. **Pass 1 (fast):** collision-free LBF in each open bin (`LBFEvaluator`, 800 container samples, 3 coord descents). On success: place + `separate_bin()`.
2. **Pass 2 (fallback):** snapshot → place at origin in most-available bin → `separate_bin_feasible()` (1 strike). On success: keep. On fail: restore snapshot.
3. **Pass 3:** open new bin (cheapest available stock), place, `separate_bin()`.

### Phase 2 — Bin reduction (`bp_explore.rs`, `bin_reduction_phase`)

Outer loop until `n_bins == lower_bound` or time up or `MAX_CONSECUTIVE_FAILURES=15`:

- **Select:** `select_candidate_bin()` = lowest utilization bin, skipping `failed_bins` set (QW-3).
- **Remove layout:** `prob.remove_layout(bin_to_remove)`. Displaced items sorted largest-first.
- **Redistribute (QW-1):** `try_lbf_into_any_bin()` — LBF clear placement. Fallback: most-available bin + origin seed.
- **Separate (QW-2):** `separate_single_bin()` only for bins that received items.
- **Success path:** QW-4 compaction (LBF reinsertion largest-first), update incumbent, reset `failed_bins`.
- **Fail path:** `resolve_by_transfers()` (budget-limited inter-bin moves), then compaction. If still fail: mark bin as failed, increment `consecutive_failures`.
- **Perturbation (AC-3):** after `PERTURB_AFTER_FAILURES` failures, probabilistically restore from solution pool and call `perturb_swap_between_bins()` (swap large items between two bins + re-separate).
- **Solution pool:** `POOL_MAX=5` alternative incumbents at current best bin count. Reset on each successful reduction.

### BinSeparator (`bp_separator.rs`)

Direct adaptation of JeroenGar separator for `BPInstance`/`Layout`:
- `BinSepWorker`: cloned `Layout` + `CollisionTracker` + `Xoshiro256PlusPlus`.
- `move_items()`: shuffle colliding items (by `ct.get_loss(pk) > 0`), `search_placement` with `SeparationEvaluator`.
- `move_items_multi()`: `par_iter_mut()` via rayon, each worker runs from master snapshot; pick worker with lowest `get_total_weighted_loss()`.
- Outer loop: same strike/iter_no_imprv structure as original.
- `rollback()`: restore snapshot + `restore_but_keep_weights()`.

### Move operators (`bp_moves.rs`)

- `try_transfer(from, to, pik)`: remove item from `from_bin`, place in `to_bin` at old `d_transf`, `separate_single_bin(to_bin)`. Returns feasibility.
- `try_swap(bin_a, pik_a, bin_b, pik_b)`: cross-place both items, separate both. Returns `feas_a && feas_b`.
- `resolve_by_transfers(infeasible_bins, all_bins, budget)`: outer loop over infeasible bins + inner over items; tries transfer to each other bin; on success checks if source is now feasible/empty. Budget-limited.

### CollisionTracker (`quantify/tracker.rs`)

- `PairMatrix<CTEntry { loss, weight }>` + `container_collisions: Vec<CTEntry>`.
- `recompute_loss_for_item()`: `collect_poly_collisions` → for each collision entity: `quantify_collision_poly_poly` or `quantify_collision_poly_container`.
- `update_weights()`: Algorithm 8 — max_loss scan; no-collision entries decay × `GLS_WEIGHT_DECAY`, collision entries × proportional factor in `[GLS_WEIGHT_MIN_INC_RATIO, GLS_WEIGHT_MAX_INC_RATIO]`.
- `restore_but_keep_weights()`: copy loss + keys from snapshot, keep weights from live state.
- `save() / CTSnapshot = CollisionTracker`.

---

## File-by-file audit

### coroush/sparrow

| File | Repo | Ref | Key types/functions | VRS relevance | Porting risk |
|---|---|---|---|---|---|
| `src/bp_optimizer/mod.rs` | coroush/sparrow | 5df9ce15 | `bp_optimize()`, `export_bp_svg()`, `validate_items_fit_bins()` | Entry point pattern | Low — VRS has own entry |
| `src/bp_optimizer/bp_lbf.rs` | coroush/sparrow | 5df9ce15 | `BpLbfBuilder`, `construct()`, `find_lbf_placement()`, `separate_bin_feasible()`, `separate_bin()`, `most_available_bin()`, `cheapest_available_bin_id()` | FFD+LBF construction template | Medium — geometry layer differs |
| `src/bp_optimizer/bp_separator.rs` | coroush/sparrow | 5df9ce15 | `BinSeparator`, `BinSepWorker`, `separate()`, `move_items()`, `move_items_multi()`, `rollback()` | Core separator pattern | High — needs jagua-rs BPP types |
| `src/bp_optimizer/bp_explore.rs` | coroush/sparrow | 5df9ce15 | `bin_reduction_phase()`, `select_candidate_bin()`, `try_lbf_into_any_bin()`, `compact_bin()`, `most_available_bin()`, `perturb_swap_between_bins()`, `pick_large_item_pk()` | Bin reduction loop template | Medium |
| `src/bp_optimizer/bp_moves.rs` | coroush/sparrow | 5df9ce15 | `separate_single_bin()`, `try_transfer()`, `try_swap()`, `resolve_by_transfers()` | Move operator templates | Medium |
| `src/quantify/tracker.rs` | coroush/sparrow | 5df9ce15 | `CollisionTracker`, `CTEntry`, `update_weights()`, `recompute_loss_for_item()`, `register_item_move()`, `restore_but_keep_weights()` | GLS collision tracking | High — central to separator |

### JeroenGar/sparrow

| File | Repo | Ref | Key types/functions | VRS relevance | Porting risk |
|---|---|---|---|---|---|
| `src/optimizer/separator.rs` | JeroenGar/sparrow | a4bfbbe0 | `Separator`, `SeparatorWorker`, `separate()`, Algorithm 9 | Original separator reference | High |
| `src/optimizer/explore.rs` | JeroenGar/sparrow | a4bfbbe0 | Compression/exploration loop | Solution pool pattern reference | Low |

---

## Algorithmic components

| Component | Source | Algorithm ref | Status |
|---|---|---|---|
| GLS collision loss | `quantify/tracker.rs` | Algorithm 1, arXiv:2509.13329 | Audited |
| GLS weight update | `update_weights()` | Algorithm 8, arXiv:2509.13329 | Audited |
| Separation loop | `BinSeparator::separate()` | Algorithm 9, arXiv:2509.13329 | Audited |
| LBF placement | `LBFEvaluator` + `search_placement` | Lower-left heuristic | Referenced (not read in full) |
| FFD construction | `BpLbfBuilder::construct()` | First-Fit Decreasing | Audited |
| Bin reduction | `bin_reduction_phase()` | BPP-specific | Audited |
| Solution pool + perturbation | Pool in `bin_reduction_phase()`, `perturb_swap_between_bins()` | AC-3 analog | Audited |
| Inter-bin move ops | `bp_moves.rs` | transfer / swap / resolve | Audited |
| Compaction | `compact_bin()` | LBF reinsertion | Audited |

---

## What is directly reusable

Nothing from Sparrow/SparrowGH should be directly copied verbatim into VRS production code. The algorithms, patterns, and data structure designs may be reimplemented:

- **Algorithmic patterns:** GLS weight update, strike-based separator loop, largest-first item sorting, snapshot/rollback pattern, solution pool structure.
- **Structural patterns:** `CollisionTracker` design (pair matrix + container vector + weighted loss), `rollback()` + `restore_but_keep_weights()`, `select_candidate_bin()` heuristic, `resolve_by_transfers()` budget logic.
- **References:** arXiv:2509.13329 is the canonical paper; VRS implementations should cite it.

---

## What must be reimplemented VRS-style

The VRS optimizer works with rectangular `Rect`-bbox geometry (not `jagua-rs` NFP/polygon), Python-side exact validation, and its own IO contract (`Placement`, `Unplaced`, `SheetShape`). All of the following must be VRS-native reimplementations, not ports of Sparrow's jagua-rs types:

- **Infeasible working state:** VRS `LayoutState` has no colliding working layout concept. A new `WorkingLayout` or extended `LayoutState` with optional `colliding: Vec<PlacedItem>` must be added.
- **CollisionTracker equivalent:** Currently absent in VRS. VRS `repair.rs` uses `find_violations()` (bbox overlap scan, O(n²)) with no weighted GLS loss. A weighted pair-loss tracker using VRS `PlacedBbox` must be built.
- **Separator:** VRS `repair.rs` is not a separator. A proper GLS separator for VRS (using `PlacedBbox` collision quantification, weight updates, multi-pass with rollback) must be implemented.
- **LBF evaluator:** VRS `initializer.rs` uses `generate_candidates_with_sheets()` + bbox collision check. A Lower-Left / LBF evaluator that scores positions must be added.
- **Move operators:** VRS `moves.rs` is a pure data skeleton. Execution logic for transfer-between-sheets, intra-sheet reinsert, and swap must be built.
- **Solution pool and perturbation:** No analog in VRS. Must be implemented around `LayoutState` snapshots.

---

## What must not be copied/adopted

- No vendoring of Sparrow Rust crates (jagua-rs, collision detection, etc.) into VRS production.
- No external SparrowGH benchmark backend — VRS exact validator is the only acceptance gate.
- No direct use of SparrowGH C# code (no license).
- No relaxation of the exact validator requirement for accepted output.
- No continuous rotation in the initial migration scope (VRS supports 0/90/180/270° only in Phase 1; continuous rotation is a later phase).

---

## Gaps and uncertainties

1. **`src/sample/search.rs`, `src/eval/lbf_evaluator.rs`, `src/eval/sep_evaluator.rs`** were not read in full during this audit. These contain the concrete placement search logic (`search_placement`, `SampleConfig`, `LBFEvaluator`, `SeparationEvaluator`). Their VRS equivalents must be designed for SGH-02/SGH-03.
2. **`src/config.rs`** not read — `BinPackConfig`, `ItemSortKey`, `SeparatorConfig` field details assumed from usage in audited files.
3. **SparrowGH license** is unknown — direct-copy BLOCKED. Since algorithmic content is in `coroush/sparrow` (MIT), this does not affect the reimplementation path.
4. **VRS `optimizer/boundary.rs`, `candidates.rs`, `score.rs`, `multisheet.rs`** were referenced but not audited in full here; their design is known from JG-19/JG-20 work.
5. **Continuous rotation:** Sparrow supports continuous rotation; VRS Phase 1 does not. The migration plan covers 0/90/180/270° initially.

---

## Evidence appendix

```
JeroenGar/sparrow  commit: a4bfbbe0bf864a7eaf136f9d06456155b1163195
  LICENSE: MIT, Copyright (c) 2025 Jeroen Gardeyn, KU Leuven
  Audited: src/optimizer/separator.rs, src/quantify/tracker.rs (referenced explore.rs)

coroush/sparrow  commit: 5df9ce15960f262545169f989ff1068b5f038c9c
  LICENSE: MIT, Copyright (c) 2025 Jeroen Gardeyn, KU Leuven (same header)
  Audited: src/bp_optimizer/mod.rs, bp_lbf.rs, bp_separator.rs, bp_explore.rs, bp_moves.rs
           src/quantify/tracker.rs

coroush/sparrow-grasshopper  commit: 0c9a13622e9a63caa693a7271d36e28826f2899d
  LICENSE: NOT_FOUND — direct-copy BLOCKED
  Audited: README_dev.md, README.md (no algorithmic Rust source present; sparrow subdir is empty submodule)

VRS files audited:
  rust/vrs_solver/src/optimizer/mod.rs
  rust/vrs_solver/src/optimizer/state.rs
  rust/vrs_solver/src/optimizer/moves.rs
  rust/vrs_solver/src/optimizer/stopping.rs
  rust/vrs_solver/src/optimizer/repair.rs
  rust/vrs_solver/src/optimizer/initializer.rs
  rust/vrs_solver/src/optimizer/sheet_elimination.rs
  vrs_nesting/nesting/instances.py (validate_multi_sheet_output)
```
