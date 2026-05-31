# SGH-Q24R6 — Native Sparrow tracker + search parity hardening

`SGH-Q24R6_STATUS: PASS`

`STATIC_ARCHITECTURE_GATE: PASS`
`STATIC_TRACKER_SEARCH_WORKER_GATE: PASS`
`RUNTIME_MEDIUM_CDE_GATE: PASS`
`RUNTIME_LV8_12TYPES_X1_GATE: PASS`

Q24R6 hardens the native Sparrow core delivered by the Q24R5 architectural
cutover. The architecture is preserved (production `sparrow_cde` still runs
`SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution`), and the core is
now a real Sparrow separation/search engine: CDE-truth *quantified* tracker loss,
multi-sheet/rotation search, real multi-worker competition with best-worker
load-back, and deeper exploration. Compression stayed out of scope. The old VRS
core was not reintroduced.

## 1. Reference material read

Current project files: `codex/reports/egyedi_solver/sgh_q24r5_*.md` (+ `.verify.log`),
`scripts/smoke_sgh_q24r5_*.py`, `rust/vrs_solver/src/adapter.rs`, `.../io.rs`,
`.../optimizer/sparrow/mod.rs`, `.../optimizer/cde_adapter.rs`,
`.../optimizer/collision_severity.rs`, `.../optimizer/loss_model.rs`.

`.cache/sparrow` reference (algorithm/model truth):

```text
.cache/sparrow/src/optimizer/mod.rs        (Alg 11 optimize)
.cache/sparrow/src/optimizer/separator.rs  (Alg 9 separate; Alg 10 move_items_multi worker-master)
.cache/sparrow/src/optimizer/worker.rs     (Alg 5 worker move_items; load/move_item)
.cache/sparrow/src/optimizer/explore.rs    (exploration)
.cache/sparrow/src/sample/search.rs        (Alg 6 search_placement)
.cache/sparrow/src/quantify/tracker.rs     (Alg 8 GLS tracker; quantified loss)
.cache/sparrow/src/quantify/mod.rs         (quantify_collision_poly_poly / _container)
.cache/sparrow/src/eval/sep_evaluator.rs   (Alg 7 sample evaluation)
```

`.cache/sparrow/src/optimizer/compress.rs` skimmed only — compression confirmed
out of scope (default `sparrow_cde` is zero-pass).

## 2. Files changed

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs   rewritten/hardened (~+977/-254; 1915 lines)
rust/vrs_solver/src/adapter.rs                 native diag projection wired to new search/worker/quant fields
scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py   (provided gate; placed in tree)
```

No `io.rs` change was needed — the new evidence maps onto existing
`OptimizerDiagnosticsOutput` fields (`search_position_*`, `sparrow_workers`,
`sparrow_worker_*`, `sparrow_multi_target_*`, `sparrow_topk_target_count`,
`collision_severity_*`) plus the Q24R5 native flags.

## 3. Tracker quantification (count-only → CDE-truth resolution distance)

Q24R5 stored `pair_loss = 1.0` / `boundary_loss[i] = 1.0` (binary count). Q24R6
stores a **CDE-truth quantified separation/clearance distance**:

- collision **existence** is still decided only by the CDE (`CdeCandidateSession`
  for the same-sheet pair set, `CdeAdapter::query_boundary` for the container);
- the stored **magnitude** is the minimal translation distance to clear,
  estimated by a `bracket`-doubling + `binary_refine` probe
  (`probe_pair_resolution_distance`, `probe_boundary_resolution_distance`) where
  **every probe step is resolved by the CDE** — bbox/AABB never decides a probe
  step;
- `total_weighted_loss = Σ raw_quantified × GLS_weight`; `weighted_loss_for_item`
  sums the quantified touching records for an item; `colliding_indices` orders
  offenders worst-first by weighted loss;
- unsupported geometry is treated honestly as a large hard violation
  (`BIG_UNSUPPORTED_LOSS`), never as no-collision;
- `update_after_move` / `snapshot` / `restore_keep_weights` / `final_validation`
  retained; incremental updates and quantified pair/boundary queries are counted
  into the diagnostics (`native_tracker_incremental_updates`,
  `quantified_pair_queries`, `quantified_boundary_queries`, `unsupported_queries`).

Unit-proof: `native_tracker_quantified_loss_is_not_binary_count` asserts a deep
overlap yields a strictly larger loss than a shallow overlap, and neither equals
`1.0`.

## 4. Search (multi-sheet, multi-rotation, refined)

`native_search_placement` now evaluates candidates **across every eligible
sheet** (`for sheet_idx in 0..sheets.len()`), all allowed rotations, with:

- current-placement candidate + **focused** jitter samples (current sheet);
- a container-wide **global** grid on each eligible sheet;
- **coord**inate-**descent** refinement of the best candidate;
- the current sheet is searched first; other sheets are swept only when no clear
  spot is found there (bounds candidate volume — keeps LV8 within budget).

Scoring: a candidate is CDE-`is_clear()` (score 0, the authoritative target) or
ordered by a cheap continuous geometric penetration magnitude
(`aabb_penetration` + boundary spill). The colliding **set** is always CDE-decided;
the AABB magnitude only *orders* infeasible samples — it never decides collision
truth and is never the authoritative loss (that remains the CDE-truth tracker
probe, which drives every accept/reject + GLS update). Search diagnostics
(`search_global_samples`, `search_focused_samples`, `search_refined_samples`,
`search_coord_descent_steps`, `search_unsupported_samples`,
`search_cross_sheet_calls`, `search_best_eval`) are reported truthfully.

## 5. Worker competition (Alg 5/10 native port)

`move_items_multi` spawns `worker_count` (default 2) `WorkerCandidate`s from the
**same master state**: each worker clones the layout + CDE tracker, gets a
worker-unique deterministic seed and target ordering (worst-first / shuffled /
reversed), and runs `run_worker_pass` — a greedy move batch accepting a move only
when it lowers that item's CDE-truth weighted loss (rollback via
`restore_keep_weights` otherwise). `compare_worker_candidates` selects the
min-weighted-loss worker deterministically (tie → raw loss → index) and
`load_best_worker` loads it back into the master, discarding the rest. GLS weights
are updated on the master between iterations (Alg 9 strike / no-improvement loop).

Worker diagnostics reported: `worker_count`, `worker_passes`,
`worker_candidates_evaluated`, `worker_commits`, `worker_rollbacks`,
`worker_best_loss`, `multi_target_items_attempted/accepted/rejected`,
`topk_target_count`.

## 6. Exploration / disruption (no compression)

`disrupt` is deeper than the previous single largest-item swap, combining:
(a) largest-pair position swap, (b) **cross-sheet relocation** of the highest-loss
item to a randomized in-bounds anchor on another eligible sheet, and (c) an
**alternate-rotation kick** of the highest-loss item. Pool insert (least-infeasible),
biased restore from the better half, then disrupt. No strip-shrink, no compression
(`compression_passes == 0`, `enable_compression = false`).

## 7. Rotation-aware constructive seed (LV8 enabler)

`build_native_constructive_seed` is now rotation-aware (`fitting_rotation`): a part
that is oversized at 0° (LV8 `Lv8_11612_6db` is 2522×733 vs a 1500×3000 sheet) is
seeded at a rotation under which it fits (90°), instead of being dropped. Unit-proof:
`constructive_seed_is_rotation_aware_for_oversized_at_zero`.

## 8. Runtime evidence

Medium CDE (`sparrow_cde`, bbox requested → CDE forced, 12×30×20, 2 sheets, seed 5, tl 30):

```text
status ok (1.3s)   placed 12/12   converged true
final pairs 0   boundary 0   backend cde_adapter   bbox_fallback 0   lbf 0   compression 0
workers 2   worker_candidates_evaluated 20   search_calls 20   search_samples 360
native_tracker_incremental_updates 20   native_model_active true   old_core_used false
```

LV8 12 types × 1 (real outer polygons up to 520 verts, sheet 1500×3000, cde backend, seed 11, tl 45):

```text
status ok (6.3s)   placed 12/12   converged true
final pairs 0   boundary 0   backend cde_adapter   bbox_fallback 0   lbf 0
workers 2   worker_candidates_evaluated 18   search_calls 18   incremental_updates 18
```

The oversized-at-0° part is placed (rotated), proving rotation-aware seeding +
multi-rotation search.

## 9. Smoke / build / test evidence

```text
python3 scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py
  → static architecture gate: PASS
  → static tracker/search/worker hardening gate: PASS (count-only patterns gone; quantified probe present; multi-sheet; worker snapshot/competition/load-back; diag fields)
  → runtime medium CDE gate: PASS
  → runtime LV8 12 types x1 gate: PASS
  → Results: 79 passed, 0 failed — SMOKE: PASS

cargo build --manifest-path rust/vrs_solver/Cargo.toml --release   → green (warnings only)
cargo test  --manifest-path rust/vrs_solver/Cargo.toml --lib       → 432 passed; 0 failed
  (native tests incl. quantified-loss gradient, rotation-aware seed, worker competition active, determinism)
./scripts/check.sh                                                  → see AUTO_VERIFY block below
```

## 10. Acceptance checklist

- Q24R5 native architecture preserved ✔ (static gate)
- production `sparrow_cde` remains native ✔
- tracker loss no longer binary count-only ✔ (CDE-truth resolution distance; gradient unit test)
- search considers multiple eligible sheets/containers ✔
- worker snapshot / competition / best-worker load-back exists ✔
- medium CDE passes without fallback/compression ✔
- LV8 12 type × 1 attempted and passes ✔
- evidence is real (runtime + tests), not only docs ✔

## 11. Known remaining gaps toward full jagua_rs/Sparrow parity

- Search-candidate *ordering* uses an AABB penetration proxy for infeasible
  samples (CDE still decides the set + the authoritative tracker loss); Sparrow
  uses a polygon-surrogate overlap-area proxy — a closer port would adopt a
  surrogate/pole-of-inaccessibility magnitude in search too.
- Workers run sequentially (deterministic), not in parallel threads (Sparrow uses
  rayon); behaviour is equivalent, throughput is single-threaded.
- LV8 is exercised at 12 types × 1 (low density); full LV8 276 acceptance and
  last-sheet compression remain explicit non-goals/out of scope.
- Cross-sheet search is a fallback (only when the current sheet has no clear
  spot) to bound candidate volume; a full always-on multi-container sampler is a
  later step.

## 12. Compression statement

Compression remained disabled and out of scope: `enable_compression = false`,
no compression phase runs, `sparrow_compression_passes == 0` on the default
production `sparrow_cde` path. It was not used to pass any gate.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T13:05:52+02:00 → 2026-05-31T13:08:48+02:00 (176s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.verify.log`
- git: `main@fc6bed0`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs               |   52 +-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs | 1179 +++++++++++++++++++++-----
 2 files changed, 977 insertions(+), 254 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q24R6_NATIVE_SPARROW_TRACKER_SEARCH_PARITY_HARDENING_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.yaml
?? codex/prompts/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening/
?? codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.md
?? codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.verify.log
?? scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py
```

<!-- AUTO_VERIFY_END -->
