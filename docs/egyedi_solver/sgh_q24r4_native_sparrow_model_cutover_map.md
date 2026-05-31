# SGH-Q24R4 — Native Sparrow model cutover map

Maps the Q24R3 production solver-core concepts (old VRS core model) to the Q24R4
native Sparrow replacement, and records which old code becomes legacy-only /
removed from the production `sparrow_cde` path. Compression stays out of scope.

## Cutover table

| Q24R3 / old core concept | Q24R4 native replacement | disposition |
|---|---|---|
| `optimizer::working::WorkingLayout` (production layout truth) | `sparrow::SparrowLayout` (Vec<`SparrowPlacement`> indexed by `SPInstance`) | WorkingLayout → legacy-only (LegacyMultisheet/PhaseOptimizer pipelines); removed from `sparrow_cde` |
| `crate::io::Placement` as internal placement | `sparrow::SparrowPlacement { instance_idx, sheet_index, x, y, rotation_deg }` | `crate::io::Placement` → output projection only |
| `optimizer::separator::VrsCollisionTracker` | `sparrow::SparrowCollisionTracker` (owns pair/boundary records + GLS weights; CDE-backed via `cde_adapter` primitives) | VrsCollisionTracker → legacy-only; removed from `sparrow_cde` |
| `SparrowState` wrapping `WorkingLayout`+`VrsCollisionTracker` | native `sparrow::SparrowState` owning `SparrowLayout`+`SparrowCollisionTracker`+weights+incumbents | rewritten native |
| `build_constructive_seed_layout` → `WorkingLayout` | native constructive `SparrowSolution` builder on `SparrowLayout` | rewritten native |
| `run_sparrow_pipeline` seed step (`build_*` → `WorkingLayout::new`) | `SparrowProblem::from_solver_input(input, sheets, rotation_context, pre_unplaced)` | rewritten — no `WorkingLayout::new` in the production branch |
| `search_position::search_position_for_target(&WorkingLayout, …)` | native `sparrow` search over `SparrowLayout`+`SparrowCollisionTracker` (reuses `cde_adapter::{prepare_shape_native, CdeCandidateSession}` — NOT `WorkingLayout`) | native search (cannot call the WorkingLayout-typed function) |
| final `WorkingLayout::validate_and_commit_with_backend` | native final full CDE validation in `SparrowCollisionTracker` + `SparrowSolution::to_output_projection()` → `crate::io::Placement` | rewritten native; projection at the boundary |
| `SparrowSeparationKernel::run` | `sparrow::SparrowOptimizer::solve(problem) -> SparrowSolution` (build → exploration/separation/search → final CDE validation) | renamed/rewritten native |

## Reusable low-level primitives (allowed — not the old core)
- `cde_adapter::prepare_shape_native(part, x, y, rot)` (added Q24R4),
  `prepare_shape_from_sheet`, `CdeCandidateSession::{build,query}`,
  `CdeAdapter::{query_pair,query_boundary}`, `reset_query_cache`.
- `collision_backend::{extract_polygon_from_part, transform_polygon,
  polygons_collide, polygon_within_sheet_pts}`.
- `item::{Part, expand_instances_with_policy, can_fit_any_stock_with_policy,
  dims_for_rotation, placement_anchor_from_rect_min}`; `sheet::SheetShape`;
  `boundary::rect_within_boundary`; `rotation_policy::RotationResolveContext`.

These let the native tracker/search do CDE collision truth WITHOUT
`WorkingLayout` / `VrsCollisionTracker`.

## Static gate (smoke) shape
The Q24R4 smoke scans `optimizer/sparrow/` (dir) else `optimizer/sparrow.rs`:
- requires tokens: `SparrowProblem`, `SPInstance`, `SparrowLayout`,
  `SparrowSolution`, `SparrowCollisionTracker`, `SparrowOptimizer`;
- forbids tokens (non-test): `WorkingLayout`, `VrsCollisionTracker`,
  `PhaseOptimizer`, `MultiSheetManager`, `build_initial_layout_with_rotation_context`;
- `run_sparrow_pipeline` must not contain `WorkingLayout::new` etc. and must
  reference `SparrowProblem`/`from_solver_input`.

## Compression
Out of scope (Q24R3 `enable_compression=false` default retained). Native lifecycle
default = constructive seed → exploration/separation/search → final CDE validation.
