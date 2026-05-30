# SGH-Q23 — Full Sparrow parity cutover (fixed-sheet) — design & status

Status: **REVISE** (production path established and CDE-first; medium-CDE
convergence gate not yet met — precise remaining cutover work below).

See also: [`sgh_q23_sparrow_reference_map.md`](./sgh_q23_sparrow_reference_map.md)
(the `.cache/sparrow` → VRS port map this design builds on).

---

## 1. What `sparrow_cde` is

A new **production** optimizer pipeline, selected by:

```json
{ "optimizer_pipeline": "sparrow_cde" }
```

(`OptimizerPipelineKind::SparrowCde` in `rust/vrs_solver/src/io.rs`). It is the
intended production Sparrow path for fixed-sheet nesting. It reuses the Q22/Q22R1
`SparrowSeparationKernel` (explicit `SparrowState`, collision graph, GLS weights,
`search_position` relocation, accept/rollback, best feasible/infeasible
incumbents) but is wired in the adapter as **CDE-first and legacy-quarantined**:

| Property | `sparrow_cde` (production) | `sparrow_experimental` (Q22) |
|---|---|---|
| Geometry backend | **forced** `Cde` regardless of `collision_backend` input | caller-chosen (bbox or cde) |
| LBF / finite-candidate fallback | **forbidden** (`allow_lbf_fallback=false`) | config-dependent |
| Legacy fallback on failure | **never** — returns `unsupported`/partial with full diagnostics | n/a |
| `pipeline_used` label | `sparrow_cde` | `sparrow_experimental` |

Both pipelines now share one driver, `run_sparrow_pipeline` in
`rust/vrs_solver/src/adapter.rs`, so diagnostics preservation (Q22R1) is
identical for both.

## 2. CDE/Jagua as geometry source of truth

`sparrow_cde` forces `CollisionBackendKind::Cde`:

- collision existence ← `CdeCollisionBackend` (jagua-rs `CDEngine`),
- boundary validity ← `CdeCollisionBackend::placement_within_sheet`,
- final commit ← `WorkingLayout::validate_and_commit_with_backend(.., Cde)`,
- unsupported/timeout ← preserves full `optimizer_diagnostics` **and**
  `collision_backend_diagnostics` (Q22R1 helpers `run_sparrow_pipeline` →
  `_unsupported_output_with_full_diag`),
- CDE query/engine metrics ← `cde_observability` thread-local counters surfaced
  in `collision_backend_diagnostics`.

bbox is **not** a collision source of truth here. If `collision_backend: "bbox"`
is requested together with `sparrow_cde`, the adapter ignores it and uses CDE
(test: `sparrow_cde_forces_cde_backend_even_when_bbox_requested`).

## 3. Query reduction — AABB broad-phase pruning (this cut)

The documented Q22R1 blocker is that the CDE adapter is `PerCallOnly`: every pair
/ boundary query builds a fresh `CDEngine` (`cde_adapter.rs::query_pair` /
`query_boundary` → `CDEngine::new`). Q23 introduces the first real query
reduction:

- **AABB broad-phase pre-check** in `CdeAdapter::query_pair`
  (`rust/vrs_solver/src/optimizer/cde_adapter.rs`): if the two prepared shapes'
  axis-aligned bounding boxes are strictly separated on any axis, the pair is
  resolved as `NoCollision` **without** building a `CDEngine`. This is the rule
  the canvas mandates: *"AABB separated → skip exact pair query and count as
  broadphase_pruned; AABB never produces positive collision truth."*
- Counter `broadphase_pruned` added to `cde_observability::CdeCounters` and
  surfaced as `cde_broadphase_pruned` in `CollisionBackendDiagnosticsOutput`.

Measured effect (bench `--quick`, see measurements):

| fixture | cde queries | engine builds | broadphase pruned | prune rate |
|---|---:|---:|---:|---:|
| tiny | 96 | 71 | 25 | 26% |
| two_rect_overlap | 464 | 255 | 209 | 45% |
| medium_10_to_20_items | 11236 | 7650 | 3586 | 32% |

Broad-phase pruning is real and measurable, and it never asserts a positive
collision (unit tests `cde_q23_broadphase_prunes_separated_rects_without_engine_build`
and `cde_q23_broadphase_does_not_prune_overlapping_rects`).

## 4. Fixed-sheet adaptation (inherited from Q22)

Hard constraints: inside the fixed sheet (CDE Exterior hazard) and no pairwise
collision (CDE). Spacing/margin is handled by geometry preprocessing upstream.
Primary objective: place all required items; the seed places every fittable
instance at the sheet origin (intentional overlap) and the separation loop
resolves it. Items that can never fit are `PART_NEVER_FITS_STOCK`. Multi-sheet
minimisation remains **HOLD** (Q19) — single fixed-sheet CDE is the Q23 target.

## 5. Acceptance result (honest)

Production `sparrow_cde` + CDE outcome accounting (`--quick`, seed 1):

| fixture | status | converged | runtime |
|---|---|---|---|
| tiny | ok | true | 0.23 s |
| two_rect_overlap | ok | true | 0.80 s |
| boundary_recovery | ok | true | 0.004 s |
| medium_10_to_20_items | **unsupported** | **false** | **25 s** |

3 / 4 production fixtures converge. The **medium CDE acceptance gate is not met**:
the fixture does not converge and runs ~25 s (no hang — the kernel terminates on
its budget — but it does not reach feasibility). Per the Q23 contract this is a
**REVISE**, not a weak PASS.

## 6. Why medium CDE still fails — precise remaining cutover work

AABB broad-phase removes ~⅓ of engine builds, but the dominant cost remains the
**7650 per-call `CDEngine::new` builds** at ~3 ms each. The remaining cutover
items (the real Q18B/Q23 "CDE scale" work) are:

1. **Solve-scoped decision caches** keyed by stable transform signatures:
   - prepared-geometry cache (one `SPolygon` per (part, rotation)),
   - pair decision cache + boundary decision cache (memoise CDE verdicts),
   - dirty invalidation on item move (only the moved item's rows recompute —
     mirrors Sparrow `CollisionTracker::register_item_move`).
   This needs a stateful CDE backend (interior mutability or a `&mut` cache
   threaded through `collision_severity.rs`, `search_position.rs`,
   `separator.rs`), because the `CollisionBackend` trait is `&self`.
2. **Incremental collision-graph update** instead of the current full O(n²)
   pair sweep in `CollisionGraphSnapshot::from_tracker`.
3. **Active-set pair filtering** (only re-query pairs whose AABBs are near).
4. **Sparrow Algorithm 5/10 parity**: move every colliding item per pass across
   parallel workers, not a single worst-weighted target per iteration.
5. **Exploration/compression strip-shrink analogue** for fixed sheets
   (Algorithm 12/13), beyond the single separation loop.

Items 1–3 are the throughput-critical work; without them, medium CDE cannot meet
the convergence gate under the quick cap.

## 7. Legacy quarantine

- `legacy_multisheet` is the default only when no pipeline is requested; it is
  not reachable from `sparrow_cde`.
- `phase_optimizer` is explicit opt-in (`pipeline_used == "phase_optimizer"`).
- `sparrow_cde` never falls back to either; a failure is `unsupported` with full
  diagnostics. Smoke `production_sparrow_no_legacy_fallback` and
  `legacy_pipeline_requires_explicit_opt_in` enforce this.

## 8. Files touched

- `rust/vrs_solver/src/io.rs` — `OptimizerPipelineKind::SparrowCde`,
  `cde_broadphase_pruned` output field.
- `rust/vrs_solver/src/adapter.rs` — `run_sparrow_pipeline` shared driver,
  `SparrowCde` routing (CDE-first), `sparrow_optimizer_diag_from` label param,
  broadphase field in 3 diag constructors, 4 new tests.
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` — AABB broad-phase prune in
  `query_pair`, 2 new tests.
- `rust/vrs_solver/src/optimizer/cde_observability.rs` — `broadphase_pruned`
  counter + `inc_broadphase_pruned`.
- `rust/vrs_solver/src/optimizer/collision_backend.rs` — pre-existing engine-build
  test updated to an overlapping pair (broad-phase aware).
- `scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py`,
  `scripts/bench_sgh_q23_full_sparrow_parity_cutover.py`.
- `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`, this doc, and the Q23
  report + measurements.
