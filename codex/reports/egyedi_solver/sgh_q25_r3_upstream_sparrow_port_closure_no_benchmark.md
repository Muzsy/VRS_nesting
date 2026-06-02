# SGH-Q25-R3 — Upstream Sparrow core port closure (no benchmark focus)

SGH-Q25-R3_STATUS: PASS

## UPSTREAM_COMMIT

`.cache/sparrow` HEAD: `c95454e390276231b278c879d25b39708398b7d3`

## PRE_TASK_GIT_STATUS

`git status --porcelain=v1` at task start:

```
?? README_SGH_Q25_R3_UPSTREAM_SPARROW_PORT_CLOSURE_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark/
?? scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py
```

`git diff --name-only` at task start: (empty — no tracked-file modifications)

Baseline: the Q25-R2 work is committed as `1d3a30c` ("feat(sparrow): complete
upstream Sparrow core semantic port with full algorithmic parity"). The working
tree was clean except for the R3 task package.

## PRE_TASK_DIRTY_FILES

Only untracked files, all within the allowed Q25-R3 task/report scope (the task
package copied into place before coding began):

- README_SGH_Q25_R3_UPSTREAM_SPARROW_PORT_CLOSURE_PACKAGE.md
- canvases/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
- codex/codex_checklist/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
- codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.yaml
- codex/prompts/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark/run.md
- scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py

## PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES

NONE. The working tree had no tracked-file modifications and no untracked files
outside the allowed Q25-R3 task scope at task start.

## TASK_CHANGED_FILES

All within the allowed scope (`rust/vrs_solver/src/optimizer/sparrow/**` +
`rust/vrs_solver/src/optimizer/cde_adapter.rs`):

- `rust/vrs_solver/src/optimizer/cde_adapter.rs` — exposed the specialized-pipeline
  primitives (`begin_specialized_collection`, `candidate_poles_and_area`,
  `n_candidate_edges`, `collect_pole_hazards`, `collect_edge_hazards`,
  `collect_containment_hazards`, `SpecializedCollectionCtx`, `CandidatePole`) so the
  pole pre-pass / bit-reversed edges / containment orchestration lives in the
  sparrow pipeline; added `prepare_base_shape_native` + `transform_base_to_candidate`
  (build each search candidate by a rigid transform of a once-prepared base shape,
  POI computed once — upstream `shape_buff.transform_from`); added
  `convex_hull_area_and_diameter` for the LBF ordering; pre-generate the surrogate
  for placed/fixed shapes so quantification reuses it.
- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs` —
  `collect_poly_collisions_in_detector_custom` now runs the three upstream phases
  itself: pole pre-pass (area threshold `shape.area * 0.5 / PI`), bit-reversed edge
  traversal, containment pass, all with loss-bound early termination.
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs` — builds the
  candidate via `transform_base_to_candidate` (base shape) instead of rebuilding.
- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs` — implements
  `SampleEvaluator` (so the shared `search_placement` drives LBF construction) and
  builds candidates from the base shape.
- `rust/vrs_solver/src/optimizer/sparrow/sample/uniform_sampler.rs` — rewritten to
  the upstream range-based sampler: `RotEntry { rot, x_range, y_range }`,
  none/discrete/continuous rotations (`ROT_N_SAMPLES = 16`), valid-range
  intersection, random sampling (`random_in_range`).
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs` — shared generic
  `search_placement` (Algorithm 6): reference candidate, focused sampler,
  container-wide sampler, `BestSamples` (item-min-dim threshold), pre + final
  coordinate descent; `native_search_placement` wraps it per eligible fixed sheet.
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs` — `LBFBuilder` only: upstream
  `convex_hull_area × diameter` ordering, `search_placement` + `LBFEvaluator`,
  clear-only acceptance, honest `unresolved` recording, uniform (non-density) seed
  phase budget; no `width*height*diagonal`, no `instances.len() >= 100`, no embedded
  bootstrap.
- `rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs` — owns
  `build_native_constructive_seed` and the explicitly-named
  `fixed_sheet_separator_bootstrap` (the infeasible bootstrap for unresolved items,
  outside `LBFBuilder`).
- `rust/vrs_solver/src/optimizer/sparrow/mod.rs` — re-export wiring for the new
  adapter items.

The quantify overlap-area module was left unchanged: because placed/fixed shapes
now carry a surrogate generated once in `prepare_shape_native`, its existing
quantifier reuses that surrogate (no per-pair regeneration) without edits.

Task/report files: this report + its `.verify.log`, plus the R3 task package
(README/canvas/checklist/goal-yaml/prompt/smoke) copied in before coding.

## OUT_OF_SCOPE_NEW_CHANGES

NONE. `git status --porcelain=v1` shows only the 9 tracked files above (all under
`rust/vrs_solver/src/optimizer/sparrow/**` or the allowed
`rust/vrs_solver/src/optimizer/cde_adapter.rs`) plus the R3 task/report package. No
file outside the allowed scope was modified. (`cde_session.rs`,
`cde_observability.rs`, `collision_severity.rs` were in scope but needed no change.)

## PORT_CLOSURE_MAPPING_TABLE

Upstream file | Upstream behavior | Local file/function | Status | Allowed deviation | Evidence
--- | --- | --- | --- | --- | ---
eval/specialized_jaguars_pipeline.rs | `collect_poly_collisions_in_detector_custom`: pole pre-pass (area threshold `shape.area*0.5/PI`), bit-reversed edge traversal, containment pass, loss-bound early termination | sparrow/eval/specialized_cde_pipeline.rs `collect_poly_collisions_in_detector_custom` + cde_adapter session primitives | PORTED | candidate poles come from the same overlap-area surrogate (VRS prepared shape); touching post-policy applied per hazard | smoke pole/area_threshold/bit_reversal/containment checks PASS; sparrow tests
eval/specialized_jaguars_pipeline.rs | `SpecializedHazardCollector`: incremental weighted loss, `loss_bound`, `early_terminate` | sparrow/eval/specialized_cde_pipeline.rs `SpecializedCdeHazardCollector` (impl `SpecializedHazardSink`) | PORTED | none | smoke collector checks PASS
eval/sep_evaluator.rs | `SeparationEvaluator::evaluate_sample` (Alg 7): reload+bound, early-term dominated, score from collector weighted loss | sparrow/eval/sep_evaluator.rs `score_candidate` | PORTED | bbox-in-sheet is a fit gate only; candidate built by rigid transform of base shape | smoke banned-ranking checks PASS
eval/lbf_evaluator.rs | `LBFEvaluator::evaluate_sample`: clear → left-bottom loss, collision → Invalid | sparrow/eval/lbf_evaluator.rs `evaluate_sample`/`score_lbf_candidate` | PORTED | CDE batch-query verdict (same clear/collision result) | LBF places only clear (sparrow tests)
quantify/mod.rs + quantify overlap-area module | overlap-area quantification + shape penalty (Alg 3/4) | sparrow/quantify overlap-area module | PORTED | poles reuse the persistent surrogate | smoke overlap-area-quantifier/shape_penalty checks PASS; deep>shallow loss test
quantify/tracker.rs | `CollisionTracker`: pair/container loss, GLS weights (Alg 8), item/total weighted loss, moved-item update, collision extraction | sparrow/quantify/tracker.rs `SparrowCollisionTracker` | ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS | dense layout-index pair keys instead of slotmap `PItemKey` (VRS owns no jagua layout); GLS constants match upstream | snapshot/restore + incremental tests; tracker token checks PASS
sample/uniform_sampler.rs | `UniformBBoxSampler`: rotation entries with valid x/y ranges, none/discrete/continuous (16 samples), bbox∩container, random sampling | sparrow/sample/uniform_sampler.rs `UniformBBoxSampler` | PORTED | valid range is rect-min-in-fixed-sheet (vs strip) | smoke rot_entries/ROT_N_SAMPLES=16/continuous/discrete/intersect-range/random checks PASS
sample/search.rs | `search_placement` (Alg 6): ref candidate, focused + container samplers, `BestSamples`, two-stage coord descent, rotation wiggle | sparrow/sample/search.rs `search_placement` | PORTED | wrapped once per eligible fixed sheet, best-across-sheets (multisheet, not a sampler/refinement change) | smoke focused/container/BestSamples/two-stage/ref checks PASS
sample/coord_descent.rs | `refine_coord_desc` ask/tell: random axis, success/fail step scaling, rotation wiggle | sparrow/sample/coord_descent.rs | PORTED | item-min-dim steps; configured wiggle step; generous safety round cap | smoke coord-descent checks; rotation-wiggle test
sample/best_samples.rs | `BestSamples`: N best by eval, similarity dedup, upper bound | sparrow/sample/best_samples.rs | PORTED | dedup also keyed on sheet index | smoke BestSamples checks; determinism test
optimizer/lbf.rs | `LBFBuilder::construct/find_placement`: `convex_hull_area×diameter` order, `search_placement`+`LBFEvaluator`, clear-only, strip-expand on no-fit | sparrow/lbf.rs `LBFBuilder` + sparrow/fixed_sheet.rs `fixed_sheet_separator_bootstrap` | ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS | fixed sheets cannot expand: no-clear items are recorded unresolved and seeded by a separately-named bootstrap outside the builder (never reported as LBF success); seed phase gets a uniform (non-density) time share | smoke LBF banned-shortcut + ordering + unresolved + bootstrap-not-in-LBF checks PASS
optimizer/worker.rs | `SeparatorWorker::move_items/move_item` (Alg 5): move colliding items, accept only if moved-item weighted loss does not increase | sparrow/worker.rs `run_worker_pass` | PORTED | sequential workers (perf limitation, identical competition semantics) | smoke worker weighted-loss / no-pair-count checks PASS; worker-competition test
optimizer/separator.rs | `Separator::separate` (Alg 9) + `move_items_multi` (Alg 10): strike/no-improve on total loss, best worker by total weighted loss, GLS updates | sparrow/separator.rs | PORTED | no `change_strip_width`; pair count is a tie-breaker/diagnostic only | smoke separator weighted-loss checks PASS
optimizer/explore.rs | `exploration_phase` (Alg 12), `disrupt_solution`, `practically_contained_items` | sparrow/explore.rs | ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS | no strip shrink (fixed sheet): repeated separation + infeasible pool + biased restore + disrupt; CDE+POI contained relocation | smoke pool/restore + contained checks PASS
optimizer/mod.rs | `optimize` (Alg 11): LBF seed → exploration → (compression) | sparrow/optimizer.rs `solve` | ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS | compression deferred; final fixed-sheet validation/projection | feasible-solve test
optimizer/compress.rs | `compression_phase` | (not ported) | DEFERRED_COMPRESSION_ONLY | out of scope per task | smoke "compression remains excluded" PASS

Every non-compression row is `PORTED` or `ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS`;
none is left as an open semantic gap.

## FIXED_SHEET_DEVIATIONS_WITH_NO_SEMANTIC_LOSS

Every deviation is an unavoidable consequence of fixed multisheet (vs an infinite
strip) and does not change core semantics:

1. **Tracker pair indexing** — VRS owns no jagua `Layout`/`PItemKey`, so the
   pair/container loss + GLS weights are keyed by dense layout indices instead of
   the upstream triangular `PItemKey` matrix. Same loss model, same GLS update
   constants; only the key type differs.
2. **Multisheet search wrapper** — upstream searches one strip; VRS runs the
   identical `search_placement` (sampler + evaluator + two-stage coord descent) once
   per eligible fixed sheet and keeps the best-across-sheets. The per-sheet search
   logic is unchanged.
3. **LBF no-clear handling** — upstream widens the strip when an item has no clear
   placement; fixed sheets cannot widen, so such items are recorded `unresolved` and
   given an in-bounds start by `fixed_sheet_separator_bootstrap` (outside
   `LBFBuilder`, never reported as LBF success). The LBF constructive path itself
   accepts clear placements only.
4. **Uniform seed-phase time share** — the seed phase gets a uniform fraction of the
   solve budget (same for every instance count — not a density branch), mirroring
   upstream's explore/compress phase split, so the separator/exploration phases run.
5. **Sequential workers** — worker competition is identical; only execution is
   sequential rather than rayon-parallel (a performance limitation).
6. **No strip operations** — `change_strip_width` / strip shrinking have no
   fixed-sheet equivalent; exploration drives repeated separation with an
   infeasible-solution pool + biased restore + disruption instead.

## DEFERRED_COMPRESSION_ONLY

Compression (`.cache/sparrow/src/optimizer/compress.rs`) remains explicitly out of
scope and disabled. It is the only deferred upstream module.

## BUILD_TEST_RESULTS

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` → OK.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → `433 passed; 0 failed`.
- `python3 scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py`
  → all code-level closure gates PASS (pole pre-pass + area threshold +
  bit-reversed + containment; LBF convex-hull×diameter, no banned shortcuts,
  bootstrap outside LBF; range-based sampler with 16 continuous samples + random
  sampling; two-stage refinement; worker/separator/explore semantics).
- `./scripts/check.sh` → see the auto-verify block.
- `./scripts/verify.sh --report …` → see the auto-verify block + `.verify.log`.

No LV8 dense quality gate was added; runtime checks are not-broken guardrails only.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-02T21:43:54+02:00 → 2026-06-02T21:46:59+02:00 (185s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.verify.log`
- git: `main@1d3a30c`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 343 +++++++++++++++------
 .../src/optimizer/sparrow/eval/lbf_evaluator.rs    |  27 +-
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |   5 +-
 .../sparrow/eval/specialized_cde_pipeline.rs       |  88 +++++-
 .../src/optimizer/sparrow/fixed_sheet.rs           |  64 ++++
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       | 230 +++++++-------
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   6 +-
 .../src/optimizer/sparrow/sample/search.rs         | 324 +++++++++++--------
 .../optimizer/sparrow/sample/uniform_sampler.rs    | 132 +++++---
 9 files changed, 828 insertions(+), 391 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/uniform_sampler.rs
?? README_SGH_Q25_R3_UPSTREAM_SPARROW_PORT_CLOSURE_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark/
?? codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
?? codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.verify.log
?? scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py
```

<!-- AUTO_VERIFY_END -->
