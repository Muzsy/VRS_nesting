# SGH-Q25-R2 — Complete upstream Sparrow core semantic port

SGH-Q25-R2_STATUS: PASS

## UPSTREAM_COMMIT

`.cache/sparrow` HEAD: `c95454e390276231b278c879d25b39708398b7d3`

## PRE_TASK_GIT_STATUS

`git status --porcelain=v1` at task start:

```
?? README_SGH_Q25_R2_COMPLETE_UPSTREAM_SPARROW_CORE_SEMANTIC_PORT_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/
?? scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py
```

`git diff --name-only` at task start: (empty — no tracked-file modifications)

## PRE_TASK_DIRTY_FILES

Only untracked files, all within the allowed Q25-R2 task/report scope (the task package
copied into place before coding began):

- README_SGH_Q25_R2_COMPLETE_UPSTREAM_SPARROW_CORE_SEMANTIC_PORT_PACKAGE.md
- canvases/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
- codex/codex_checklist/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
- codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.yaml
- codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/run.md
- scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py

## PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES

NONE. The working tree had no tracked-file modifications and no untracked files outside
the allowed Q25-R2 task scope at task start.

## TASK_CHANGED_FILES

Implementation (all within the allowed Q25-R2 scope
`rust/vrs_solver/src/optimizer/sparrow/**` + the allowed CDE adapter support file):

- `rust/vrs_solver/src/optimizer/cde_adapter.rs` — added the bounded/visitor
  collection API (`CdeCandidateSession::collect_poly_collisions_custom`, the
  `SpecializedHazardSink` trait, the `SinkAdapter` `HazardCollector`, and a
  bit-reversal edge order). Allowed support file (required for upstream-style
  hazard collection / early termination). The legacy `query` batch helper is
  retained for the LBF/tracker non-search paths only.
- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs` — the
  collector now accumulates tracker-weighted loss during collection via the
  visitor sink (no post-`query` batch loop).
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs` — Algorithm 7:
  reload + loss-bound, early-terminate dominated samples, `Clear { 0.0 }` /
  `Collision { collector loss }` only (no bbox ranking).
- `rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs` — pure
  (diag-free) `*_value` quantify functions for the visitor path.
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs` — GLS
  `update_weights` aligned to upstream constants and clean either/or
  decay-or-increase; stale resolution-distance terminology removed.
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs` — LBF accepts only `Clear`
  placements; no-clear instances recorded as unresolved; a clearly-named
  fixed-sheet seeding adaptation (`seed_unresolved_on_fixed_sheets`) replaces the
  removed least-infeasible "success" path.
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs` — faithful
  ask/tell coordinate-descent port (CDAxis, success/fail step multipliers, random
  axis reselection, rotation wiggle).
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs` — passes item min-dim
  to coordinate descent; comment cleanup.
- `rust/vrs_solver/src/optimizer/sparrow/separator.rs` — raw-total-loss-primary
  strike loop (Algorithm 9); weighted-loss best-worker selection with pair count
  as a tie-breaker/diagnostic only.
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs` — owns `exploration_phase`
  (Algorithm 12, fixed-sheet adaptation: infeasible pool + biased restore +
  disrupt) in addition to disrupt/contained relocation.
- `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs` — `solve` delegates the
  exploration loop to `explore::exploration_phase`.
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs` — removed the dead
  resolution-distance probe-step config fields.
- `rust/vrs_solver/src/optimizer/sparrow/mod.rs` — re-export wiring
  (`SpecializedHazardSink`, `quantify::overlap_proxy::*`).

Task/report files: this report + its `.verify.log`, plus the task package
(README/canvas/checklist/goal-yaml/prompt/smoke) copied in before coding.

## OUT_OF_SCOPE_NEW_CHANGES

NONE. `git diff --name-only` lists only the 13 tracked files above, all under
`rust/vrs_solver/src/optimizer/sparrow/**` or the explicitly-allowed
`rust/vrs_solver/src/optimizer/cde_adapter.rs`. No file outside the allowed scope
was modified. (`cde_session.rs`, `cde_observability.rs`, `collision_severity.rs`
were available in scope but did not need changes.)

## BUILD_TEST_RESULTS

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` → OK.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → `433 passed; 0 failed`.
- `python3 scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py`
  → all code-level gates PASS (collector-not-post-query, evaluator bound, LBF
  no-least-infeasible, search/coord/worker/separator/explore checks). The only
  smoke assertion gated on this report is the mapping-table header, satisfied below.
- `./scripts/check.sh` → exit 0 (pytest, mypy, sparrow IO + DXF/geometry smokes,
  determinism, VRS solver validator smoke). See the auto-verify block.
- `./scripts/verify.sh --report …` → PASS; log written to
  `…/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.verify.log`.

No dense-LV8 quality acceptance was added; runtime checks are not-broken regressions only.

## SEMANTIC_MAPPING_TABLE

Upstream file | Upstream type/function | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence
--- | --- | --- | --- | --- | --- | --- | ---
eval/specialized_jaguars_pipeline.rs | `collect_poly_collisions_in_detector_custom`, `SpecializedHazardCollector` | populate collector during CDE traversal; per-edge loss-bound early termination | optimizer/cde_adapter.rs, sparrow/eval/specialized_cde_pipeline.rs | `CdeCandidateSession::collect_poly_collisions_custom` rides jagua `collect_collisions` edge-by-edge into `SinkAdapter`; `SpecializedCdeHazardCollector` accumulates tracker-weighted loss on the fly and stops when bound exceeded | PORTED | candidate session uses no surrogate, so the upstream pole pre-pass is skipped (perf-only fail-fast, identical hazard set); VRS touching post-policy applied per hazard | smoke "specialized collector is not post-query-only batch accumulation" PASS; sparrow lib tests
eval/sep_evaluator.rs | `SeparationEvaluator::evaluate_sample` (Alg 7) | reload+bound, early-term dominated, score from collector weighted loss only | sparrow/eval/sep_evaluator.rs | `score_candidate`: reload(loss_bound) → bounded collect → `None` (dominated) / `Clear{0.0}` / `Collision{collector loss}` | PORTED | bbox-in-sheet is a broad-phase fit gate only, never ranking | smoke banned-proxy checks PASS; sep tests
eval/lbf_evaluator.rs | `LBFEvaluator::evaluate_sample` | clear → left-bottom positional loss, any collision → Invalid | sparrow/eval/lbf_evaluator.rs | `score_lbf_candidate`: CDE batch verdict → Clear with LBF positional loss, collision rejected for LBF acceptance | PORTED | uses the `CdeCandidateSession` batch query (boolean verdict) instead of `detect_*_collision`; same clear/collision result | LBF construct only accepts clear (sparrow tests)
eval/sample_eval.rs | `SampleEval` + `Ord` | Clear<Collision<Invalid, loss ordering | sparrow/eval/sample_eval.rs | identical enum + `Ord` | PORTED | none | compiles/tests
quantify/mod.rs | `quantify_collision_poly_poly`, `quantify_collision_poly_container`, `calc_shape_penalty` (Alg 4) | sqrt(overlap-proxy+ε²)·penalty pairs; outside-area·penalty container | sparrow/quantify/overlap_proxy.rs | same formulas; `*_value` (pure) + diag-counting wrappers | PORTED | container outside-area computed from prepared-shape bbox (upstream also uses `s.bbox`) | smoke "overlap_area_proxy"/"shape penalty" PASS; quantified-loss-not-binary test
quantify/overlap_proxy.rs | `overlap_area_proxy` (Alg 3) | pole pairwise penetration-decay × min radius × π | sparrow/quantify/overlap_proxy.rs | same algorithm over surrogate poles | PORTED | poles generated on the fly from a shape clone (VRS prepared shapes don't persist a surrogate) | deep>shallow loss gradient test
quantify/tracker.rs | `CollisionTracker` (loss records, GLS weights, `update_weights` Alg 8, `get_*_loss`, `register_item_move`) | store pair/container raw loss + GLS weights; item/total weighted loss; moved-item update; collision-item extraction | sparrow/quantify/tracker.rs | `SparrowCollisionTracker` with `pair_loss`/`pair_weight`/`boundary_loss`/`boundary_weight`, `update_weights` (upstream constants, clean either/or), `update_after_move`, `colliding_indices`, item/total weighted loss | ADAPTED_FIXED_SHEET | indexing by dense layout-index pairs (`HashMap`) instead of slotmap `PItemKey` triangular matrix — VRS owns no jagua layout/`PItemKey` | snapshot/restore + incremental-update tests; GLS constants match `consts.rs`
quantify/pair_matrix.rs | `PairMatrix` triangular store | pairwise loss/weight storage | sparrow/quantify/{pair_matrix.rs,tracker.rs} | `pair_loss`/`pair_weight` HashMaps keyed `(min,max)` | ADAPTED_FIXED_SHEET | dense (usize,usize) keys instead of `PItemKey` triangular matrix | same indexing reason as tracker
sample/search.rs | `search_placement` (Alg 6) | focused + container-wide sampling, BestSamples, 2-stage coord descent | sparrow/sample/search.rs | `native_search_placement`: focused-around-current + grid + container-wide, BestSamples, pre+final coord descent | PORTED | searches across all eligible fixed sheets / rotations (upstream is one strip) | smoke search checks PASS; worker-competition test
sample/coord_descent.rs | `refine_coord_desc` + ask/tell `CoordinateDescent` | random/det axis, ±2 candidates, success/fail step scaling, rotation wiggle, step-limit stop | sparrow/sample/coord_descent.rs | faithful ask/tell `CoordinateDescent`, `CDAxis`, `CD_STEP_SUCCESS`/`FAIL`, per-stage `CDConfig`, wiggle | PORTED | steps from item min-dim; honors configured wiggle step; generous safety round cap | rotation-wiggle test (`search_rotation_wiggle>0`)
sample/best_samples.rs | `BestSamples` | N best by eval, similarity dedup, upper bound | sparrow/sample/best_samples.rs | same: sorted by eval, dedup by x/y/rot/sheet, `upper_bound` | PORTED | similarity also keyed on sheet index | smoke best-samples checks; determinism test
sample/uniform_sampler.rs | `UniformBBoxSampler` | uniform in-bbox samples honoring rotation fit | sparrow/sample/uniform_sampler.rs | per-sheet rect-min sampler with rotation-fit narrowing, deterministic grid + random | PORTED | per-fixed-sheet sampling instead of single strip | sampling drives clear-placement tests
optimizer/lbf.rs | `LBFBuilder::construct/find_placement` (Alg, strip expand on no-fit) | only-clear placement; expand strip when none | sparrow/lbf.rs | `construct` accepts only clear; no-clear → `unresolved`; `seed_unresolved_on_fixed_sheets` (named adaptation) installs an in-bounds infeasible seed | PORTED + ADAPTED_FIXED_SHEET | fixed sheets cannot expand, so unresolved items get a named infeasible seed for the separator (never reported as LBF success) | smoke "no least-infeasible" + "unresolved" PASS; all-placed + rotation-aware-seed tests
optimizer/worker.rs | `SeparatorWorker::move_items/move_item` (Alg 5) | move colliding items; accept only if moved-item weighted loss does not increase | sparrow/worker.rs | `run_worker_pass`: iterate tracker colliding items, search, accept iff moved-item weighted loss ≤ old, else rollback | PORTED | sequential workers (perf limitation, not a semantic change) | smoke worker checks; worker-competition test
optimizer/separator.rs | `Separator::separate` (Alg 9) + `move_items_multi` (Alg 10) | strike/no-improve loop on total loss; best worker by total weighted loss; GLS updates | sparrow/separator.rs | raw-total-loss strike loop, weighted-loss best-worker load-back, `update_weights` between iters | PORTED + ADAPTED_FIXED_SHEET | no `change_strip_width`; sequential worker competition; pair count is tie-breaker/diagnostic only | smoke separator checks PASS
optimizer/explore.rs | `exploration_phase` (Alg 12), `disrupt_solution`, `practically_contained_items` | pool infeasible, biased restore, large-item disruption, contained relocation | sparrow/explore.rs | `exploration_phase` (infeasible pool + biased restore + disrupt), large-item swap, CDE+POI contained relocation, cross-sheet/rotation kicks | ADAPTED_FIXED_SHEET | no strip shrink (fixed sheet); biased restore via deterministic better-half index; contained relocation is the fixed-sheet equivalent | smoke pool/restore + contained checks PASS
optimizer/mod.rs | `optimize` (Alg 11) | LBF seed → exploration → (compression) | sparrow/optimizer.rs | `solve`: LBF+seed → `exploration_phase` → final CDE validation; compression excluded | PORTED + ADAPTED_FIXED_SHEET | compression deferred; final fixed-sheet validation/projection | feasible-solve test
optimizer/compress.rs | `compression_phase` | post-feasible compaction | (not ported) | — | DEFERRED_COMPRESSION_ONLY | out of scope per task | smoke "compression remains excluded" PASS

No non-compression `REVISE` rows: every core module is either `PORTED` or
`ADAPTED_FIXED_SHEET` with a concrete fixed-sheet reason (single strip → fixed
multi-sheet, slotmap `PItemKey` → dense layout index, rayon parallel workers →
sequential workers, strip expansion → named infeasible seed).

## DEFERRED_COMPRESSION_ONLY

Compression (`.cache/sparrow/src/optimizer/compress.rs`) remains explicitly out of scope
and disabled per task definition.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-01T23:30:16+02:00 → 2026-06-01T23:33:19+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.verify.log`
- git: `main@da12cd0`
- módosított fájlok (git status): 21

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 174 ++++++++++++++-
 .../src/optimizer/sparrow/diagnostics.rs           |   6 -
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |  41 ++--
 .../sparrow/eval/specialized_cde_pipeline.rs       |  77 ++++---
 rust/vrs_solver/src/optimizer/sparrow/explore.rs   |  56 +++++
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       | 106 ++++++++-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   3 +-
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |  40 +---
 .../optimizer/sparrow/quantify/overlap_proxy.rs    |  31 ++-
 .../src/optimizer/sparrow/quantify/tracker.rs      |  66 +++---
 .../src/optimizer/sparrow/sample/coord_descent.rs  | 241 ++++++++++++++++-----
 .../src/optimizer/sparrow/sample/search.rs         |   8 +-
 rust/vrs_solver/src/optimizer/sparrow/separator.rs |  16 +-
 13 files changed, 667 insertions(+), 198 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs
 M rust/vrs_solver/src/optimizer/sparrow/explore.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/separator.rs
?? README_SGH_Q25_R2_COMPLETE_UPSTREAM_SPARROW_CORE_SEMANTIC_PORT_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/
?? codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
?? codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.verify.log
?? scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py
```

<!-- AUTO_VERIFY_END -->
