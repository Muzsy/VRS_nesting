# SGH-Q24R5 — Architectural native Sparrow cutover

`SGH-Q24R5_STATUS: PASS`

`STATIC_CUTOVER_GATE: PASS`
`RUNTIME_MEDIUM_CDE_GATE: PASS`

This run completes the cutover that Q24R4 deferred. Production `sparrow_cde` no
longer runs on `WorkingLayout` / `VrsCollisionTracker` / `SparrowSeparationKernel`.
It runs on a native Sparrow model (`SparrowProblem` → `SparrowOptimizer::solve` →
`SparrowSolution` → boundary projection). No fake wrappers, no re-enabled legacy,
no compression, no LBF/bbox fallback. The medium CDE gate still converges 12/12.

## 1. Reference material read

`.cache/sparrow` (native algorithm/model truth):

```text
.cache/sparrow/src/optimizer/mod.rs        (Alg 11 optimize; problem/optimizer shape)
.cache/sparrow/src/optimizer/separator.rs  (Alg 9 separate strike/no-improve loop)
.cache/sparrow/src/optimizer/worker.rs     (Alg 5/10 move_items_multi worker-master)
.cache/sparrow/src/optimizer/explore.rs    (Alg 12 exploration pool/restore/disrupt)
.cache/sparrow/src/sample/search.rs        (Alg 6 search_placement; focused+global samples)
.cache/sparrow/src/quantify/tracker.rs     (Alg 8 GLS tracker, weighted loss, update_weights)
```

VRS side (what is being replaced / the I/O boundary):

```text
rust/vrs_solver/src/adapter.rs                    (run_sparrow_pipeline driver)
rust/vrs_solver/src/optimizer/sparrow.rs          (DELETED legacy core)
rust/vrs_solver/src/optimizer/cde_adapter.rs      (prepare_shape_native, CdeCandidateSession)
rust/vrs_solver/src/optimizer/working.rs          (old WorkingLayout/VrsCollisionTracker — no longer on sparrow path)
rust/vrs_solver/src/optimizer/separator.rs        (old kernel — no longer on sparrow path)
rust/vrs_solver/src/optimizer/search_position.rs  (old search — no longer on sparrow path)
rust/vrs_solver/src/io.rs                          (diagnostics contract)
```

`.cache/sparrow/src/optimizer/compress.rs` was skimmed only; compression stays out
of scope (default `sparrow_cde` is zero-pass — see §8).

## 2. Files changed

```text
rust/vrs_solver/src/optimizer/sparrow.rs       DELETED  (-1916)  legacy core removed from production path
rust/vrs_solver/src/optimizer/sparrow/mod.rs   ADDED    (+1196)  native Sparrow core + native unit tests
rust/vrs_solver/src/adapter.rs                 MODIFIED          run_sparrow_pipeline cut over to native dataflow
rust/vrs_solver/src/io.rs                       MODIFIED (+17)   6 native-model proof diagnostic fields
scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py  ADDED  static+runtime gate
```

`optimizer/mod.rs` net-unchanged vs HEAD: `pub mod sparrow;` now resolves to the
new `sparrow/` directory module instead of the deleted `sparrow.rs` file.

## 3. Old-core files/functions removed from the production path

- `rust/vrs_solver/src/optimizer/sparrow.rs` (the entire legacy module:
  `SparrowSeparationKernel`, `build_constructive_seed_layout`, the
  `WorkingLayout`-based `SparrowConfig`/`SparrowDiagnostics`, all legacy tests) is
  **deleted**.
- `run_sparrow_pipeline` no longer calls `build_constructive_seed_layout(...)`,
  `WorkingLayout::new(...)`, `SparrowSeparationKernel::new(...).run(...)`, nor
  `layout.validate_and_commit_with_backend(...)`.
- The legacy diagnostics builder `sparrow_optimizer_diag_from(&sparrow::SparrowDiagnostics, ...)`
  is **replaced** by `native_sparrow_diag_to_output(&sparrow::SparrowDiagnostics, ...)`
  reading the native diagnostics struct.
- `WorkingLayout` / `VrsCollisionTracker` / `search_position::search_position_for_target`
  still exist in the crate (used by other pipelines: legacy multisheet, phase
  optimizer, compression), but they are **not reachable from production `sparrow_cde`**.

## 4. Native types introduced (`optimizer/sparrow/mod.rs`)

```text
DeterministicRng                  SplitMix64-style, seed-controlled
SparrowConfig + from_solver_input native config (time budget, backend, rotation ctx, seed,
                                  focused_samples/global_grid_n/coord_descent_steps; compression OFF)
SparrowDiagnostics                native diagnostics incl. native_model_active / native_tracker_active /
                                  old_core_used / native_problem_instances / tracker rebuild+incremental counts
SPInstance                        native expanded instance (idx, instance_id, part_id, part, allowed_rotations_deg)
SparrowContainer                  native fixed-sheet container set
SparrowRotationDomain             resolved rotation domain per instance
SparrowProblem + from_solver_input  one-way I/O conversion; never-fit → pre_unplaced (no silent drops)
SparrowPlacement                  native placement (NOT crate::io::Placement; no Placement stored inside)
SparrowLayout                     native layout keyed by instance index; snapshot/restore
SparrowCollisionTracker           native CDE-backed tracker (see §6)
TrackerSnapshot                   transient-loss snapshot (GLS weights preserved across restore)
SparrowState                      layout + tracker + best feasible/infeasible incumbents
SparrowSolution + to_solver_projection  projects to Vec<crate::io::Placement> ONLY at the output boundary
SparrowSolveResult                solution + projected placements + unplaced + feasible + diagnostics
SparrowOptimizer + new + solve    native solve: constructive seed → separate/worker/search/exploration →
                                  final native CDE validation
```

Native vertical slice in `solve`/`separate`/`disrupt`: constructive seed builder,
native `separate` over `SparrowLayout + SparrowCollisionTracker`, native worker
move loop over all colliding items, CDE-scored native candidate search (focused
samples + global grid + coordinate descent), GLS `update_weights`, best
feasible/infeasible tracking, exploration pool/restore/disrupt, and final full CDE
validation.

## 5. Proof: `run_sparrow_pipeline` no longer creates `WorkingLayout`

The production dataflow (`adapter.rs::run_sparrow_pipeline`) is exactly the allowed
boundary shape:

```rust
use crate::optimizer::sparrow::{SparrowConfig, SparrowOptimizer, SparrowProblem};
// ...
let config  = SparrowConfig::from_solver_input(time_limit, backend_kind, rotation_context, seed);
let problem = SparrowProblem::from_solver_input(&input.parts, sheets, rotation_context, pre_unplaced, config.clone())?;
let optimizer = SparrowOptimizer::new(config);
let result  = optimizer.solve(problem);
// result.feasible / result.placements / result.unplaced / result.diagnostics
//   placements are SparrowSolution::to_solver_projection(...) produced inside solve
```

Static gate confirms the function body contains none of
`WorkingLayout::new`, `SparrowSeparationKernel`, `build_constructive_seed_layout`,
`PhaseOptimizer`, `MultiSheetManager`, `build_initial_layout_with_rotation_context`,
and does contain `SparrowProblem`/`from_solver_input` + `SparrowOptimizer` + `.solve`
(see §9 static output, all PASS).

## 6. Proof: `VrsCollisionTracker` not used by production `sparrow_cde`

`SparrowCollisionTracker` is a standalone native tracker. It:

- owns pair collision records (`pair_loss` keyed by `(i,j)`), boundary/container
  violation records (`boundary_loss` per item), and GLS weights
  (`pair_weight` / `boundary_weight`);
- computes raw loss, weighted loss, and per-item weighted loss;
- exposes colliding/offending item indices;
- supports full rebuild (`build`), update-after-move for one item
  (`update_after_move` → `recompute_item`), and snapshot/restore that preserves GLS
  weights (`snapshot` / `restore_keep_weights`);
- exposes final full CDE validation (`final_validation`).

Collision **truth** is the jagua_rs CDE engine: shapes are prepared via
`cde_adapter::prepare_shape_native` (never `prepare_shape_from_placement`) and
queried via `CdeCandidateSession` / `CdeAdapter::query_boundary`. AABB is used only
as the no-collision broad-phase prune already inside the CDE adapter; it never
produces positive collision truth. The static gate confirms the production
`optimizer/sparrow` sources contain no `VrsCollisionTracker` and no `WorkingLayout`
(see §9, all PASS). The string `crate::io::Placement` appears only in `mod.rs` at the
output-projection boundary (allowed by the gate).

Because the native tracker is CDE-backed for **every** requested backend, the
sparrow pipeline always resets and surfaces the CDE observability counters and
reports `backend_used == "cde_adapter"` (the jagua_rs polygon-exact CDE engine).
The pre-cutover test `sparrow_pipeline_final_commit_uses_selected_backend` (which
asserted a `WorkingLayout` commit honored a non-CDE backend) was updated to assert
this native reality — this is an architecture-driven test update, not a re-enabling
of legacy.

## 7. Native-model diagnostics added (`io.rs` `OptimizerDiagnosticsOutput`)

```rust
sparrow_native_model_active: Option<bool>             // true on production native solve
sparrow_native_tracker_active: Option<bool>           // true
sparrow_old_core_used: Option<bool>                   // false
sparrow_native_problem_instances: Option<usize>       // native expanded instance count
sparrow_native_tracker_full_rebuilds: Option<usize>
sparrow_native_tracker_incremental_updates: Option<usize>
```

All are `#[serde(skip_serializing_if = "Option::is_none")]`; they are set by the
native projection `native_sparrow_diag_to_output(...)` and left `None` on the
non-sparrow (phase optimizer / legacy) constructors.

## 8. Medium CDE gate (still passing, no compression)

Fixture: `optimizer_pipeline = sparrow_cde`, `collision_backend = bbox` (production
forces CDE), 12× 30×20 parts, 2× 200×200 sheets, seed 5, `time_limit_s = 20`.

Native solve output (`vrs_solver --input … --output …`, ~0.5 s):

```text
status                ok
placed_count          12        (12/12)
pipeline_used         sparrow_cde
sparrow_converged     true
final collision pairs 0
final boundary viol.  0
backend_used          cde_adapter   (even though bbox requested)
bbox_fallback_queries 0
lbf_fallback          0
compression_passes    0            (compression disabled by default config)
native_model_active   true
native_tracker_active true
old_core_used         false
native_problem_instances 12
```

Compression explicitly stayed out of scope: `SparrowConfig::from_solver_input` sets
`enable_compression: false`, and `solve` never runs a compression phase, so
`sparrow_compression_passes == 0` on the default production path.

## 9. Smoke output — `scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py`

```text
=== static native Sparrow architecture gate ===
  [PASS] production optimizer/sparrow sources exist
  [PASS] native concept present: SparrowProblem / SPInstance / SparrowPlacement /
         SparrowLayout / SparrowSolution / SparrowCollisionTracker /
         SparrowOptimizer / SparrowSolveResult
  [PASS] no WorkingLayout / VrsCollisionTracker / SparrowSeparationKernel /
         search_position_for_target / build_constructive_seed_layout / PhaseOptimizer /
         MultiSheetManager / build_initial_layout_with_rotation_context in sources
  [PASS] crate::io::Placement not used as internal native layout type
  [PASS] run_sparrow_pipeline found for static scan
  [PASS] run_sparrow_pipeline does not use WorkingLayout::new / SparrowSeparationKernel /
         build_constructive_seed_layout / PhaseOptimizer / MultiSheetManager /
         build_initial_layout_with_rotation_context
  [PASS] run_sparrow_pipeline constructs native SparrowProblem
  [PASS] run_sparrow_pipeline calls native SparrowOptimizer::solve

=== runtime medium CDE native cutover gate ===
  [PASS] status ok (0.5s)        [PASS] placed 12/12
  [PASS] pipeline_used == sparrow_cde
  [PASS] sparrow_converged == true
  [PASS] final collision pairs == 0   [PASS] final boundary violations == 0
  [PASS] CDE backend used even when bbox requested
  [PASS] no bbox fallback queries     [PASS] no LBF fallback
  [PASS] compression disabled/gated or zero default passes
  [PASS] native model diagnostic active == true
  [PASS] native tracker diagnostic active == true
  [PASS] old core diagnostic used == false

========================================================================
Results: 40 passed, 0 failed
SMOKE: PASS
```

## 10. Build / test / check evidence

```text
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release   → green (warnings only)
cargo test  --manifest-path rust/vrs_solver/Cargo.toml --lib       → 429 passed; 0 failed
  - includes 7 new native tests in optimizer::sparrow::tests:
      from_solver_input_expands_instances_with_stable_indices
      from_solver_input_projects_never_fits_to_pre_unplaced
      native_tracker_cde_detects_overlap_and_separation
      native_tracker_update_after_move_resolves_collision_incrementally
      native_tracker_snapshot_restore_preserves_gls_weights
      native_optimizer_solve_feasible_projects_all_placements
      native_optimizer_solve_is_deterministic_for_same_seed
python3 scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py → 40 passed, SMOKE: PASS
./scripts/check.sh                                                  → exit 0 ([DONE] smoketest OK)
```

The 11 fewer lib tests vs the prior 433 baseline are exactly the legacy tests that
lived inside the deleted `sparrow.rs` (they exercised the removed `WorkingLayout` /
`SparrowSeparationKernel` core); native coverage for production types is restored by
the 7 new `optimizer::sparrow::tests`.

## 11. Compression statement

Compression remained disabled and out of scope. It was not hardened, not ported, and
not used to pass acceptance. Default production `sparrow_cde` runs with
`enable_compression = false` and reports `sparrow_compression_passes == 0`.

## 12. PASS justification

- Production `sparrow_cde` runs on native `SparrowProblem` / `SparrowLayout` /
  `SparrowSolution` / `SparrowCollisionTracker` / `SparrowOptimizer`. ✔
- `run_sparrow_pipeline` does not construct `WorkingLayout`. ✔ (static gate)
- Production `optimizer/sparrow` uses neither `VrsCollisionTracker` nor
  `WorkingLayout`. ✔ (static gate)
- `SparrowPlacement` is native, not `crate::io::Placement`. ✔
- Native tracker owns loss/GLS/pair/boundary state. ✔
- CDE remains decisive collision truth. ✔
- Q24R3 medium CDE gate still passes without compression. ✔
- Static anti-hybrid smoke passes. ✔
- Build/test/check evidence exists. ✔

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T12:22:01+02:00 → 2026-05-31T12:24:55+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.verify.log`
- git: `main@810435e`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs | 380 +++++++++++++++++++++--------------------
 rust/vrs_solver/src/io.rs      |  17 ++
 2 files changed, 209 insertions(+), 188 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
D  rust/vrs_solver/src/optimizer/sparrow.rs
A  rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q24R5_ARCHITECTURAL_NATIVE_SPARROW_CUTOVER_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r5_architectural_native_sparrow_cutover.yaml
?? codex/prompts/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover/
?? codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.md
?? codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.verify.log
?? scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py
```

<!-- AUTO_VERIFY_END -->
