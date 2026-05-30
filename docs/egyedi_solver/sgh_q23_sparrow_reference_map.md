# SGH-Q23 — Sparrow reference map (`.cache/sparrow` → VRS)

This document maps the **local** `.cache/sparrow` reference implementation
(`git`-cloned, gitignored, present locally) onto the VRS fixed-sheet solver. It
is the basis for the Q23 full-Sparrow-parity cutover. All paths below are real
paths inspected in this run; do not treat this as a generic summary.

Sparrow paper reference embedded in the source: Andries & Wauters,
*"Sparrow: an algorithm for irregular strip packing"*,
https://doi.org/10.48550/arXiv.2509.13329 (algorithm numbers cited below are the
ones the source code itself annotates).

---

## 1. Sparrow repository structure and real entrypoints

```text
.cache/sparrow/src/
  main.rs                         CLI entry; parses input, calls optimizer::optimize
  lib.rs, config.rs, consts.rs    SparrowConfig, ExplorationConfig, CompressionConfig, GLS/CD consts
  optimizer/
    mod.rs                        optimize()  — Algorithm 11 (top-level explore→compress)
    lbf.rs                        LBFBuilder   — initial constructive layout (Left-Bottom-Fill)
    separator.rs                  Separator    — Algorithm 9 separate(), move_item, change_strip_width
    worker.rs                     SeparatorWorker — Algorithm 5/10 move_items (per-worker parallel)
    explore.rs                    exploration_phase — Algorithm 12 (shrink-on-feasible + disrupt)
    compress.rs                   compression_phase — Algorithm 13 (compact feasible incumbent)
  sample/
    search.rs                     search_placement — Algorithm 6 / Figure 7 (sample + refine)
    coord_descent.rs              refine_coord_desc — coordinate descent local refinement
    best_samples.rs               BestSamples — top-k unique sample retention
    uniform_sampler.rs            UniformBBoxSampler, convert_sample_to_closest_feasible
  eval/
    sample_eval.rs                SampleEval {Clear,Collision,Invalid}, SampleEvaluator trait
    sep_evaluator.rs              SeparationEvaluator — Algorithm 7 (CDE-backed eval w/ upper bound)
    lbf_evaluator.rs              LBFEvaluator — clear/invalid eval for constructive phase
    specialized_jaguars_pipeline.rs  SpecializedHazardCollector (early-terminating jagua query)
  quantify/
    tracker.rs                    CollisionTracker — Algorithm 1/8 (pair/container loss + GLS weights)
    pair_matrix.rs                PairMatrix — dense per-pair (loss,weight) storage
    overlap_proxy.rs              overlap_area_proxy — Algorithm 3 (pole/circle penetration proxy)
    mod.rs                        quantify_collision_poly_poly (Alg 4), quantify_collision_poly_container
  util/                           terminator, listener, svg exporter, assertions
```

Geometry truth is **jagua-rs** throughout: `jagua_rs::probs::spp` (Strip Packing
Problem) entities `SPInstance`/`SPProblem`/`SPSolution`/`SPPlacement`, and
`Layout::cde()` returns the `CDEngine` used for every collision query.

---

## 2. Main solve loop — `optimizer/mod.rs::optimize` (Algorithm 11)

1. Build an initial solution: `LBFBuilder::new(..).construct()` unless a warm-start
   `SPSolution` is supplied.
2. **Exploration phase** (`exploration_phase`) under its own time budget, starting
   from a `Separator` seeded with the LBF layout.
3. **Compression phase** (`compression_phase`) under its own budget, starting from
   the final exploration solution and `Separator` state.
4. Report `ReportType::Final` and return the compressed `SPSolution`.

The strip width is the optimized objective: exploration repeatedly **shrinks** the
strip and re-separates; compression fine-shrinks a feasible incumbent.

---

## 3. Feasibility problem lifecycle

Sparrow deliberately allows **infeasible (overlapping) intermediate states**. The
`SPProblem` always holds *all* items placed; feasibility = "total collision loss
== 0". State is carried by:

- `SPProblem` (placements + strip width), `save()`/`restore()` snapshots.
- `CollisionTracker` (`quantify/tracker.rs`): per-pair and per-container **loss**
  (overlap proxy) and **GLS weight**, plus `save()`/`restore_but_keep_weights()`.
- Incumbents: exploration keeps a vector of feasible solutions (one per achieved
  width) and a sorted pool of infeasible solutions (`infeas_sol_pool`).

---

## 4. Separation procedure — `optimizer/separator.rs::separate` (Algorithm 9)

```text
min_loss_sol = (prob.save(), ct.save()); min_loss = ct.total_loss()
while n_strikes < strike_limit && !killed:
    while n_iter_no_improvement < iter_no_imprv_limit:
        move_items_multi()                     # parallel workers, Alg 10
        loss = ct.total_loss()
        if loss == 0: record + break 'outer    # fully separated
        elif loss < min_loss: record new best; reset no-improve if >2% better
        else: n_iter_no_improvement += 1
        ct.update_weights()                    # GLS, Alg 8 — EVERY iteration
    if no substantial improvement this strike: n_strikes += 1 else reset
    rollback(min_loss_sol)                     # restore placements, KEEP weights
return min_loss_sol                            # feasible if found, else least-infeasible
```

`move_items_multi` (Algorithm 10): clone the master solution to each
`SeparatorWorker`, run them in parallel (rayon) with different RNG orderings, then
keep the worker with lowest **weighted** total loss; discard the rest.

---

## 5. search_position / transform candidate sampling — `sample/search.rs::search_placement` (Algorithm 6 / Figure 7)

Per colliding item (worker.rs `move_items`, Algorithm 5):

1. Seed `BestSamples` (top-k, k = `n_coord_descents`) with the current transform
   evaluated.
2. **Focused sampling**: `n_focussed_samples` from a `UniformBBoxSampler` around
   the item's current bbox.
3. **Container sampling**: `n_container_samples` from a sampler over the whole
   container bbox.
4. **First refinement**: coordinate-descend *each* retained best sample
   (`prerefine_cd_config`).
5. **Final refinement**: take the single best and coordinate-descend it finer
   (`final_refine_cd_config`).

Returns `(Option<(DTransformation, SampleEval)>, n_evals)`. Default sample budget
(`config.rs`): container 50, focused 25, coord-descents 3.

---

## 6. Coordinate descent / local refinement — `sample/coord_descent.rs`

`refine_coord_desc` runs a CD with axes {Horizontal, Vertical, ForwardDiag,
BackwardDiag, Wiggle(rotation)}. Each `ask()` yields two candidates ±step on the
active axis; `tell()` keeps the better, multiplies step by `CD_STEP_SUCCESS=1.1`
on improve / `CD_STEP_FAIL=0.5` on fail, and picks a new random axis on failure.
Stops when both translation steps and (if enabled) the rotation step fall below
their limits. `Wiggle` (rotation) is only enabled when
`item.allowed_rotation == RotationRange::Continuous`.

Constants (`consts.rs`): `PRE_REFINE_CD_TL_RATIOS=(0.25,0.02)`,
`SND_REFINE_CD_TL_RATIOS=(0.01,0.001)`, rotation steps 5°→1° then 0.5°→0.05°.

---

## 7. Move acceptance / rejection / rollback

- `SeparatorWorker::move_item`: remove + re-place item, `register_item_move` on the
  tracker. A `debug_assert` enforces that **weighted** loss never increases for the
  moved item (search returns the argmin of the weighted eval).
- Worker selection in `move_items_multi` keeps the global lowest weighted loss.
- `separate` keeps `min_loss_sol` by **raw** total loss and rolls back to it at the
  end of each strike. `rollback` restores placements and, with a tracker snapshot,
  uses `restore_but_keep_weights` so GLS memory survives.

---

## 8. Collision graph representation and update — `quantify/tracker.rs` + `pair_matrix.rs`

The "collision graph" is materialised as a dense `PairMatrix` of `CTEntry{loss,
weight}` per ordered item pair, plus a `container_collisions` vector per item.
`CollisionTracker::recompute_loss_for_item` re-queries the CDE
(`l.cde().collect_poly_collisions`) only for the **moved** item and rewrites that
item's row — i.e. an **incremental** per-item update, not a full rebuild. Total /
per-item / weighted loss are simple sums over the matrix.

---

## 9. GLS / pair weights / penalty update — `tracker.rs::update_weights` (Algorithm 8) + `consts.rs`

```text
max_loss = max loss over all entries
for each entry e:
    if e.loss == 0:  e.weight *= GLS_WEIGHT_DECAY (0.95)            # decay toward 1
    else:            e.weight *= MIN_INC + (MAX_INC-MIN_INC)*(e.loss/max_loss)
    e.weight = max(e.weight, 1.0)                                   # floor at 1
GLS_WEIGHT_MIN_INC_RATIO=1.2, GLS_WEIGHT_MAX_INC_RATIO=2.0
```

Weighted loss = weight × loss; the search minimises weighted loss so that
persistently-colliding pairs get escalating pressure (guided local search).

---

## 10. Exploration phase — `optimizer/explore.rs::exploration_phase` (Algorithm 12)

```text
while !killed:
    local_best = sep.separate()
    if total_loss == 0:          # feasible at current width
        record feasible; shrink strip by shrink_step (0.1%); clear infeasible pool
    else:                        # could not separate
        insert into sorted infeas_sol_pool (by loss)
        if pool >= max_conseq_failed_attempts: break
        pick a solution (normal-dist biased to best) and disrupt_solution()
```

`disrupt_solution` swaps two large (top convex-hull-area percentile) items and
drags items contained by the swapped ones into the freed space — a structured
kick to escape stagnation.

---

## 11. Compression phase — `optimizer/compress.rs::compression_phase` (Algorithm 13)

Repeatedly tries to shrink the feasible incumbent strip by `r_shrink` at a random
split position, re-separates, and keeps the result if still feasible. The shrink
ratio decays (time-based or failure-based) until it drops below a floor.

---

## 12. CDE / jagua-rs engine usage

- `Separator`/workers each hold a full `SPProblem` whose `Layout` owns a live
  `CDEngine`. Moving an item mutates the layout (`remove_item`/`place_item`),
  which **incrementally** updates the engine's hazard quadtree — there is no
  per-query engine rebuild.
- `SeparationEvaluator` (Algorithm 7) queries the live engine via
  `collect_poly_collisions_in_detector_custom` with an **upper bound** so a
  candidate is abandoned early once its quantified loss exceeds the current best
  (`early_terminate`). Surrogate poles (`SPSurrogate`) give a cheap first pass.
- `CDEConfig` default: `quadtree_depth=4`, `cd_threshold=16`, surrogate poles
  `[(64,0.0),(16,0.8),(8,0.9)]`.

This live, incrementally-updated, upper-bounded engine is the single biggest
architectural difference from VRS (see §14/§16).

---

## 13. Diagnostics / benchmark structure

`util/listener.rs` reports `ReportType` events (ExplFeas/ExplImproving/ExplInfeas/
CmprFeas/Final); `separate` logs evals/s, evals/move, moves/s. `src/bench.rs` +
`tests/tests.rs` drive the benchmark instances under `data/input/`.

---

## 14. What must change for fixed-sheet / multi-sheet nesting

| Sparrow (strip packing) | VRS (fixed sheet) |
|---|---|
| Objective = minimise strip **width** (continuous) | Objective = place all required items inside fixed-size sheet(s); minimise **sheet count** |
| `change_strip_width` shrinks a 1-D container | Sheet bounds are fixed; "compression" = compactness/utilisation inside a fixed rect, not width shrink |
| Exploration shrinks until infeasible | Exploration = separate the seeded overlap on a fixed sheet; if infeasible → item is `unplaced`/spills to next sheet |
| Single open strip | Multi-sheet: per-sheet collision graphs, cross-sheet moves, sheet elimination |
| Boundary = left/right strip walls + floor | Boundary = arbitrary sheet polygon (`SheetShape`, possibly irregular), via CDE Exterior hazard |

---

## 15. Explicit VRS mapping — Sparrow concept → VRS file/type/function

| Sparrow | VRS equivalent (today) |
|---|---|
| `optimizer::optimize` (Alg 11) | `optimizer/phase.rs::PhaseOptimizer::run` (explore→compress→bpp) and, for the Sparrow mode, `optimizer/sparrow.rs::SparrowSeparationKernel::run` |
| `LBFBuilder` | `optimizer/initializer.rs::build_initial_layout_with_rotation_context`; Sparrow seed = `sparrow.rs::build_sparrow_seed_layout` (all items at sheet origin, overlaps intentional) |
| `Separator` / `separate` (Alg 9) | `optimizer/separator.rs::VrsCollisionTracker` + `optimizer/sparrow.rs` separation loop; `optimizer/separator.rs` legacy `VrsSeparator` |
| `SeparatorWorker::move_items` (Alg 5/10) | `sparrow.rs` per-iteration "pick worst weighted target → search_position → accept/rollback" (single-target, single-worker — see deviations) |
| `search_placement` (Alg 6) | `optimizer/search_position.rs::search_position_for_target` |
| `refine_coord_desc` | `optimizer/search_position.rs` coordinate-descent refinement (`TransformCandidate`) |
| `BestSamples` | top-k retention inside `search_position.rs` |
| `SeparationEvaluator` (Alg 7) | `optimizer/collision_severity.rs` (oracle-probe severity) + `optimizer/collision_backend.rs` (`CollisionBackend` trait) |
| `CollisionTracker` (Alg 1/8) | `optimizer/separator.rs::VrsCollisionTracker` (pair/boundary loss + GLS weights, `update_weights`, `restore_but_keep_weights`) |
| `PairMatrix` | dense pair storage inside `VrsCollisionTracker`; graph snapshot = `sparrow.rs::CollisionGraphSnapshot` |
| `quantify_collision_*` (Alg 3/4) | `optimizer/loss_model.rs::LossModelKind` + `collision_severity.rs` overlap proxy |
| `exploration_phase` (Alg 12) | `optimizer/explore.rs` (phase optimizer); **not yet** width-shrink-equivalent in Sparrow mode |
| `compression_phase` (Alg 13) | `optimizer/compress.rs` (phase optimizer); fixed-sheet compaction |
| live `CDEngine` via `Layout::cde()` | `optimizer/cde_adapter.rs::CdeAdapter` (**per-call** `CDEngine::new`), `optimizer/collision_backend.rs::CdeCollisionBackend`, `optimizer/cde_session.rs` (capability = `PerCallOnly`) |
| `SPInstance/SPProblem/SPSolution` | `optimizer/working.rs::WorkingLayout` (+ `validate_and_commit_with_backend`) |

---

## 16. Intentional deviations and why they are required

1. **Per-call CDE vs live engine.** jagua-rs 0.6.4 as integrated by VRS has no
   "tentative query" API and `HazardEntity::PlacedItem` needs a SlotMap key from a
   full jagua layout VRS does not own (`cde_session.rs` documents this as
   `PerCallOnly`). Sparrow's live, incrementally-updated engine is the source of
   its throughput. **Consequence:** every VRS CDE query rebuilds a `CDEngine`
   (`cde_adapter.rs::query_pair`/`query_boundary` → `CDEngine::new`), which is the
   documented reason medium CDE fixtures time out (Q22R1). Closing this is the
   central Q23 cutover work (query reduction / session caching).

2. **Fixed sheet, no strip width.** VRS cannot shrink a continuous strip; the
   exploration/compression objective is re-expressed as sheet-count minimisation
   (multi-sheet) + intra-sheet compactness. Width-shrink Algorithm 12/13 parity is
   replaced, not copied.

3. **Single-target / single-worker separation (current Sparrow mode).** `sparrow.rs`
   moves one worst-weighted item per iteration rather than Sparrow's all-colliding-
   items-per-iteration across parallel workers. This is a simplification to keep the
   loop deterministic and debuggable; full Algorithm 5/10 parity (move every
   colliding item per pass; multi-worker argmin) is a remaining cutover item.

4. **Overlap quantification.** Sparrow uses a pole/circle penetration proxy
   (Algorithm 3). VRS `LossModelKind` currently offers bbox-area and severity
   proxies; the pole proxy is not a 1:1 port (jagua `SPSurrogate` poles are not
   exposed through the VRS adapter boundary).

5. **Deterministic seeding.** VRS uses explicit `u64` seeds threaded per call
   instead of Sparrow's `Xoshiro256PlusPlus` worker forking, to keep single-thread
   determinism for the fixed-sheet contract.
