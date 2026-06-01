SGH-Q25-R1_STATUS: PASS

# SGH-Q25-R1 Semantic Sparrow Core Parity Fix

## Meta

- Task slug: `sgh_q25_r1_semantic_sparrow_core_parity_fix`
- Canvas: `canvases/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r1_semantic_sparrow_core_parity_fix.yaml`
- Upstream Sparrow commit: `c95454e390276231b278c879d25b39708398b7d3`
- Compression scope: `DEFERRED_COMPRESSION_ONLY`

## Changed Files

- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs`
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/mod.rs`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
- `rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs`
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs`
- `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs`
- `rust/vrs_solver/src/optimizer/sparrow/separator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs`
- `codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`

## Runtime Evidence

- `.cache/sparrow` exists; upstream commit recorded as `c95454e390276231b278c879d25b39708398b7d3`.
- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`: PASS; build completed with existing Rust warnings.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`: PASS, `433 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 107.26s`.
- `python3 scripts/smoke_sgh_q25_r1_semantic_sparrow_core_parity_fix.py`: PASS, `PASS=47 FAIL=0 WARN=0`.
- `./scripts/check.sh`: PASS; Python unit tests `376 passed`, mypy success, Sparrow IO validation PASS, DXF/geometric smokes PASS, nesting validator PASS, deterministic smokes PASS, final marker `[DONE] smoketest OK`.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`: see `AUTO_VERIFY` block below.

## Semantic Mapping

| Upstream file | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| eval/specialized_jaguars_pipeline.rs | Stateful hazard collector with loss cache, upper bound, hazard records, and early termination | rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs | `SpecializedCdeHazardCollector` stores target, tracker weights, fixed shapes, sheet shape, hazards, accumulated loss, bound, and early termination flag | PORTED | Local CDE session returns a batch result; collection is real and loss pruning happens while accumulating returned hazards | `reload`, `add_pair`, `add_container`, `collect_poly_collisions_in_detector_custom` |
| eval/sep_evaluator.rs | Algorithm 7 candidate scoring through collector reload, CDE hazard collection, upper-bound pruning, clear/collision/invalid result | rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs | `SeparationEvaluator::score_candidate` prepares the candidate, reloads collector with the bound, collects hazards, returns clear or quantified collision | PORTED | Sheet fit clipping remains fixed-sheet boundary logic before CDE query | No `hazard_extent_depth`, no `ox.min(oy)`, collector call in scoring |
| quantify/overlap_proxy.rs | `overlap_area_proxy` over surrogate poles with epsilon decay | rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs | Implements upstream pole-pair overlap proxy with epsilon decay and generated jagua surrogates | PORTED | Prepared VRS shapes generate surrogates on demand | `overlap_area_proxy` |
| quantify/mod.rs | Pair loss is `overlap_area_proxy + epsilon^2`, square root, shape penalty | rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs and tracker.rs | `quantify_collision_poly_poly` plus `calc_shape_penalty`; tracker calls it only after CDE-confirmed collision | PORTED | Collision existence remains local CDE truth | `quantify_collision_poly_poly_native` delegates to overlap-proxy quantifier |
| quantify/mod.rs | Container loss uses outside/intersection-area loss and shape penalty | rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs and tracker.rs | `quantify_collision_poly_container` implements upstream bbox-intersection container loss and shape penalty | ADAPTED_FIXED_SHEET | Container is a fixed VRS sheet shape; CDE decides boundary violation before quantification | `quantify_collision_poly_container_native` |
| quantify/tracker.rs | Tracker stores pair/container raw losses and GLS weights | rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs | Pair and boundary loss maps/vectors store overlap-proxy raw loss, pair/container weights, total weighted loss, and GLS updates | PORTED | Local keys are layout indices, not upstream `PItemKey` | `pair_loss`, `boundary_loss`, `pair_weight`, `boundary_weight`, `update_weights` |
| quantify/pair_matrix.rs | Pair-matrix boundary preserved | rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs | Module remains as mapped boundary; active tracker uses hash-keyed local pairs | ADAPTED_FIXED_SHEET | Hash-keyed layout pairs match fixed-sheet local layout indexing | `SparrowCollisionTracker::pair_loss` |
| sample/search.rs | Search placement uses upper-bound best-sample flow and coordinate descent | rust/vrs_solver/src/optimizer/sparrow/sample/search.rs | Native search builds fixed-sheet CDE session, evaluates focused/global samples, and refines via coordinate descent | ADAPTED_FIXED_SHEET | Searches current sheet first and then other fixed sheets | `native_search_placement` |
| eval/lbf_evaluator.rs | LBF evaluator rejects CDE collisions and ranks clear bottom-left candidates | rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs | Clear candidates are ranked by bottom-left score; colliding samples remain explicit collision samples for fixed-sheet unresolved seed states | ADAPTED_FIXED_SHEET | Fixed sheets cannot expand strip width, so unresolved construction states stay explicit for separator | `LBFEvaluator::score_candidate` |
| optimizer/lbf.rs | LBF construction uses `search_placement + LBFEvaluator`; no shelf/AABB recovery | rust/vrs_solver/src/optimizer/sparrow/lbf.rs | `LBFBuilder::search_placement` uses CDE sessions, `UniformBBoxSampler`, `BestSamples`, and `LBFEvaluator`; recovery shortcut removed | ADAPTED_FIXED_SHEET | No upstream strip expansion; if no clear fixed-sheet candidate exists, the best CDE-scored candidate remains visible to separation | No `fixed_sheet_recovery_candidate`, no `candidate_penalty` |
| optimizer/worker.rs | Move acceptance by moved item weighted loss non-increase | rust/vrs_solver/src/optimizer/sparrow/worker.rs | Worker snapshots the tracker, updates moved item, accepts only when new weighted loss does not increase | PORTED | Sequential local worker execution is retained; competition semantics are preserved | `run_worker_pass` |
| optimizer/separator.rs | Best worker load-back by total weighted loss and strike loop by loss improvement | rust/vrs_solver/src/optimizer/sparrow/separator.rs | Worker candidates are selected by minimum `weighted_loss`, raw loss and pair count are tie-breakers only | PORTED | Workers are sequential in this local implementation | `move_items_multi`, `separate` |
| optimizer/explore.rs | Large-item disruption includes contained-item relocation | rust/vrs_solver/src/optimizer/sparrow/explore.rs | After swap, items geometrically contained by moved large items are translated into the opened fixed-sheet space and clamped | ADAPTED_FIXED_SHEET | Relocation targets the old fixed-sheet placement instead of upstream mutable strip space | `relocate_practically_contained_items`, `practically_contained_items` |
| optimizer/explore.rs | Compression remains excluded | rust/vrs_solver/src/optimizer/sparrow/optimizer.rs | No compression phase is called from native `sparrow_cde` solve path | DEFERRED_COMPRESSION_ONLY | Task scope excludes compression | `excluded_phase_passes` remains zero |

## Removed Proxy Paths

- Removed `fixed_sheet_recovery_candidate` production LBF path.
- Removed `candidate_penalty` and AABB-overlap recovery scoring from LBF.
- Removed bbox/extent penetration ranking from `SeparationEvaluator`.
- Replaced default tracker quantification with overlap-proxy plus shape-penalty functions.
- Added real specialized collector state and collection path.
- Added contained-item relocation after large-item exploration swaps.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-01T21:19:37+02:00 → 2026-06-01T21:22:39+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.verify.log`
- git: `main@fe3921f`
- módosított fájlok (git status): 19

**git diff --stat**

```text
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |  73 +++-----
 .../sparrow/eval/specialized_cde_pipeline.rs       | 138 ++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/explore.rs   | 193 +++++++++++++++++++++
 .../src/optimizer/sparrow/fixed_sheet.rs           | 151 ----------------
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       |  71 +-------
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |  21 +++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../optimizer/sparrow/quantify/overlap_proxy.rs    | 140 ++++++++++++++-
 .../src/optimizer/sparrow/quantify/tracker.rs      | 147 ++--------------
 .../src/optimizer/sparrow/sample/search.rs         |   1 +
 rust/vrs_solver/src/optimizer/sparrow/separator.rs |  37 +++-
 11 files changed, 556 insertions(+), 417 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs
 M rust/vrs_solver/src/optimizer/sparrow/explore.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/overlap_proxy.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/separator.rs
?? README_SGH_Q25_R1_SEMANTIC_SPARROW_CORE_PARITY_FIX_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r1_semantic_sparrow_core_parity_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix/
?? codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md
?? codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.verify.log
?? scripts/smoke_sgh_q25_r1_semantic_sparrow_core_parity_fix.py
```

<!-- AUTO_VERIFY_END -->
