# SGH-Q24R9 — Exact upstream-style tracker/evaluator/search semantics

`SGH-Q24R9_STATUS: PASS`

`STATIC_NATIVE_ARCHITECTURE_GATE: PASS`
`STATIC_EXACT_SEMANTICS_GATE: PASS`
`RUNTIME_MEDIUM_CDE_GATE: PASS`
`RUNTIME_LV8_12TYPES_X1_GATE: PASS`
`ROTATION_WIGGLE_GATE: PASS`
`RUNTIME_LV8_191_PROGRESS_GATE: PASS (explicit 191 partial)`

Provided smoke: **95 passed, 0 failed, 2 partial notes → `SMOKE: PASS_WITH_EXPLICIT_191_PARTIAL`**.

Q24R9 replaces the remaining Q24R8 **proxy** core semantics with CDE-truth /
tracker-driven semantics, while preserving the native architecture
(`SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution`) and keeping
compression out of scope.

## 1. Upstream → local parity map (`.cache/sparrow` read)

Read: `.cache/sparrow/src/quantify/{tracker.rs,mod.rs}`,
`.cache/sparrow/src/eval/{sample_eval.rs,sep_evaluator.rs,lbf_evaluator.rs}`,
`.cache/sparrow/src/sample/{search.rs,best_samples.rs,coord_descent.rs,uniform_sampler.rs}`,
`.cache/sparrow/src/optimizer/{worker.rs,separator.rs,explore.rs}`.

| Upstream (jagua_rs/Sparrow) | Native (`optimizer/sparrow/mod.rs`) |
|---|---|
| `quantify_collision_poly_poly` (Alg 4) | `quantify_collision_poly_poly_native` — **CDE-truth resolution-distance probe** (bracket-double + binary-refine, every step via `CdeAdapter::query_pair`) |
| `quantify_collision_poly_container` | `quantify_collision_poly_container_native` — CDE-truth clearance probe via `query_boundary` |
| `CollisionTracker` (Alg 8 GLS) | `SparrowCollisionTracker` — authority: `pair_loss/pair_weight/container_loss/container_weight/item_raw_loss/item_weighted_loss/total_*_loss/colliding_indices/snapshot/restore_keep_weights/update_weights_gls/register_item_move` |
| `SampleEval` / `SampleEvaluator` (Alg 7) | `SampleEval {Clear,Collision,Invalid}` + `SampleEvaluator` trait |
| `SeparationEvaluator` | `SeparationEvaluator` — CDE session decides clear/collision; **tracker GLS weights** (`pair_weight`/`container_weight`) scale the ordering; **`upper_bound` early termination** (clear dominates collision; running-loss prune) |
| `LBFEvaluator` / `LBFBuilder` | `LBFEvaluator` + `LBFBuilder` (CDE-clear bottom-left fill for small instances; deterministic shelf for dense) |
| `BestSamples` (upper-bound, unique) | `BestSamples` |
| `UniformBBoxSampler` | `UniformBBoxSampler` |
| `refine_coord_desc` + `CDAxis::Wiggle` | `refine_coord_desc` with a nonzero **rotation-wiggle** axis (`rotation_step`, ±deg) gated by `continuous_rotation` |
| `search_placement` (Alg 6) | `native_search_placement` — current + focused + global + two-stage coord descent |
| `SeparatorWorker` / `move_items` (Alg 5) | `SeparatorWorker` / `run_worker_pass` — **weighted-loss-only acceptance** |
| `Separator::separate/move_items_multi` (Alg 9/10) | `separate` / `move_items_multi` worker competition + best-worker load-back |

## 2. Files changed

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs   (+~435/-65)  semantics rewrite
rust/vrs_solver/src/optimizer/cde_adapter.rs   (+19)        translate_prepared() probe helper
```

## 3. Proof: bbox-proxy loss is no longer primary; CDE/hazard quantification is primary

Q24R8 pair/container loss was `overlap_proxy = ix*iy` / `outside_proxy = bbox - inside_x*inside_y`.
Q24R9 deletes those. The tracker's authoritative loss is now a **CDE resolution
distance**: the colliding pair/container is CDE-confirmed (`CdeCandidateSession` /
`query_boundary`), and the magnitude is the minimal translation that clears it,
found by `probe_resolution` (bracket-double + binary-refine) where **every probe
step is a CDE `query_pair`/`query_boundary`** on a `translate_prepared` shape. bbox
is used only for the centroid/direction hint and as broad-phase ordering — never as
the loss magnitude.

Static gate confirms (all PASS): `quantify_collision_poly_poly_native` contains no
`overlap_proxy`/`ix * iy`/`candidate.max_x.min(fixed.max_x)`/`candidate.min_x.max(fixed.min_x)`
and does contain `query_pair`; `quantify_collision_poly_container_native` contains no
`outside_proxy`/`inside_x`/`inside_y`/`bbox -`/`candidate.max_x.min(sheet.max_x)`/`bbox_area(candidate)`
and does contain `query_boundary`.

## 4. Evaluator is tracker/GLS-driven (not local ad-hoc weights)

`SeparationEvaluator` holds `tracker: &SparrowCollisionTracker`. `score_candidate`
scales each CDE-confirmed hazard by `tracker.pair_weight(target, j)` and the
boundary by `tracker.container_weight(target)`, and uses `upper_bound` to early-
reject dominated samples (a colliding candidate can never beat a clear incumbent;
running loss is pruned against the bound). The Q24R8 local-weight invention
`1.0_f64.max(base).min(base + 1.0)` is removed (static gate PASS).

## 5. Worker acceptance tightened

`run_worker_pass` accepts a move only when the moved item's **weighted collision
loss does not increase** (`new_w <= old_w + 1e-9`). The loose
`new_total < old_total || new_pairs < old_pairs` fallback (which could worsen an
item's local damage when the global pair count happened to drop) is removed (static
gate PASS).

## 6. Rotation-aware coordinate descent

`refine_coord_desc` adds a `rotation_step` (±degrees, nonzero) wiggle axis when the
instance permits continuous/free rotation (`SPInstance.continuous_rotation`, derived
from the resolved rotation policy). The Q24R8 `[(step, 0.0, 0.0); 6]` all-zero
fallback is removed. Diagnostic `search_rotation_wiggle` counts executed nonzero
rotation steps. Unit test `coord_descent_rotation_wiggle_executes_for_continuous_rotation`
drives a continuous fixture and asserts `search_rotation_wiggle > 0`. Orthogonal
fixtures keep their discrete rotation set (wiggle disabled).

## 7. Runtime metrics

Medium CDE (`sparrow_cde`, 12×30×20, 2 sheets, seed 5, tl 30): **status ok, 0.7s,
12/12, converged, final pairs 0, boundary 0, compression 0, no bbox fallback.**

LV8 12 types × 1 (real polygons, 1500×3000, cde, seed 11, tl 45): **status ok, 9.4s,
12/12, converged, final pairs 0, boundary 0.**

Rotation wiggle: static gate PASS + unit test PASS.

## 8. Dense 191 first-sheet (seed 17, tl 90, cap 240) vs Q24R8

```text
metric              Q24R8 baseline      Q24R9
status              partial             partial
validated           39                  46     (HARD gate: >39 → PASS)
initial_raw         381928              22707  (CDE-distance scale, not bbox-area)
final_raw           216263              10403  (< initial ✓)
initial_pairs       202                 181
final_pairs         152                 147    (< initial ✓)
runtime             ~127s               ~135s  (< 240s cap)
accepted moves      3                   5
cde activity        —                   6221   (> 100 ✓)
```

All **hard** dense bars pass: real runtime (135s), real search/worker activity,
accepted>0, CDE activity>100, `final_raw < initial_raw`, `final_pairs < initial_pairs`,
`validated 46 > 39`, explicit `partial` with `sparrow_dense_partial_reason =
time_budget_exhausted` and 145 unresolved instance IDs surfaced.

The two **soft** targets (final pairs ≤120, validated ≥60) remain partial notes
(smoke `PASS_WITH_EXPLICIT_191_PARTIAL`).

### Blocker for the soft 60/120 targets

The first-sheet vector is geometrically over-capacity for a single 1500×3000 sheet:
`Lv8_11612_6db` (2522×733) appears ×3, and even rotated (733×2522) three of them
need 3×733 = 2199 mm of width > 1500 mm — they cannot co-reside on one sheet without
overlap. Combined with `Lv8_07921_50db` (227×120)×33 and `Lv8_15348_6db` (600×290)×4,
a fully collision-free single-sheet placement of all 191 does not exist, so a clean
subset well above ~46 is not reachable by translation/rotation separation alone.
Reaching ≥60 would require a tighter 2D constructive packer (skyline/maxrects-style
gap filling) — out of scope for this semantics task and deliberately not faked.

## 9. Architecture + compression preserved

`run_sparrow_pipeline` still constructs `SparrowProblem` and calls
`SparrowOptimizer::solve` (static gate PASS); no `WorkingLayout` / `VrsCollisionTracker`
/ `SparrowSeparationKernel` / `PhaseOptimizer` / `MultiSheetManager` /
`search_position_for_target` / `build_constructive_seed_layout` in production
`optimizer/sparrow`. Compression stays disabled: `enable_compression: false`,
`sparrow_compression_passes == 0` on every runtime gate.

## 10. Build / test evidence

```text
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release  → green (dead-code warnings only)
cargo test  --manifest-path rust/vrs_solver/Cargo.toml --lib      → 433 passed; 0 failed
  new/updated native tests: native_tracker_quantified_loss_is_not_binary_count,
  coord_descent_rotation_wiggle_executes_for_continuous_rotation, worker competition, determinism
python3 scripts/smoke_sgh_q24r9_...py  → 95 passed, 0 failed, 2 partial → PASS_WITH_EXPLICIT_191_PARTIAL
./scripts/check.sh  → see AUTO_VERIFY block below
```

## 11. Known remaining gaps toward full parity

- Dense separation throughput is CDE-session-bound (≈190-hazard sessions); only a
  few worker passes complete within tl=90, so most of `validated` comes from the
  deterministic shelf seed. A spatial broad-phase that safely bounds session
  hazards, or surrogate-pole quantification, would raise dense throughput.
- The search-candidate *ordering* still uses an AABB-penetration magnitude scaled by
  tracker GLS weights (CDE owns the colliding set + the authoritative tracker loss);
  upstream uses a surrogate overlap-area proxy in the evaluator too.
- Workers run sequentially (deterministic), not via rayon.
- 191 single-sheet remains an explicit honest partial (see §8 blocker).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T23:05:06+02:00 → 2026-05-31T23:08:10+02:00 (184s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.verify.log`
- git: `main@cd70aa9`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/cde_adapter.rs |  19 ++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs | 481 +++++++++++++++++++++++----
 2 files changed, 435 insertions(+), 65 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q24R9_EXACT_UPSTREAM_STYLE_TRACKER_EVALUATOR_SEARCH_SEMANTICS_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.yaml
?? codex/prompts/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics/
?? codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md
?? codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.verify.log
?? scripts/smoke_sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.py
```

<!-- AUTO_VERIFY_END -->
