# SGH-Q23R1 — Production Sparrow cutover implementation (design & status)

Status: **REVISE** — substantial implementation landed (solve-scoped CDE
cache, strategy B), medium CDE convergence + 80% engine-build-reduction gates
not yet met. Builds on Q23 (see
[`sgh_q23r1_sparrow_reference_delta.md`](./sgh_q23r1_sparrow_reference_delta.md)).

## Implemented

### Solve-scoped CDE cache (run.md §1, strategy B)
`rust/vrs_solver/src/optimizer/cde_adapter.rs` — thread-local `QUERY_CACHE`:
- prepared-geometry cache (`Rc<CdePreparedShape>` keyed by part-geometry hash +
  exact f64 transform): fixed items' `SPolygon`s built once, shared across search;
- pair decision cache + boundary decision cache (memoised CDE verdicts);
- `reset_query_cache()` called at every CDE solve scope (paired with
  `cde_observability::reset()` in `adapter.rs`);
- bounded by `CACHE_ENTRY_CAP` (eviction counted as `cache_invalidations`).

`CdeCollisionBackend::placement_overlaps`/`placement_within_sheet`
(`collision_backend.rs`) now route through `cached_query_pair` /
`cached_query_boundary`; a cache hit returns the verdict with **no `CDEngine::new`**.
On a miss the per-call `CdeAdapter::query_pair` runs (AABB broad-phase first, then
engine build) and the verdict is memoised.

Correctness: CDE verdicts are pure functions of (geometry, transform, config);
the key hashes full part geometry + exact transform bits, so id-only collisions
are impossible (test `cde_q23r1_cache_key_includes_geometry_not_just_id`). Reset
per solve.

### Metrics (run.md §3)
`CdeCounters` + `CollisionBackendDiagnosticsOutput` gained:
`cde_cache_pair_hits/misses`, `cde_cache_boundary_hits/misses`,
`cde_cache_prepared_hits/misses`, `cde_cache_invalidations` (alongside Q23's
`cde_broadphase_pruned`, `cde_engine_builds`).

### Legacy quarantine (run.md §7) — retained from Q23
`sparrow_cde` forces CDE, `allow_lbf_fallback=false`, never invokes
`phase_optimizer`/`legacy_multisheet`, preserves full diagnostics on failure.
Covered by smoke `production_sparrow_no_legacy_fallback` and adapter tests.

## Measured (medium_10_to_20_items, sparrow_cde + CDE)

| metric | Q23 | R1 | gate |
|---|---:|---:|---|
| status | unsupported | unsupported | ok |
| iterations | 5 | 8 | — |
| pairs init→final | 66→28 | 66→10 | →0 |
| raw loss init→final | 1320→560 | 1320→200 | →0 |
| engine builds | 7650 | 4246 (−45%) | ≤1530 (−80%) |
| cache pair hit rate | — | 76% | — |
| runtime | ~25 s | ~9.7 s | no timeout |

Hard gates met: no timeout/hang, no bbox/LBF fallback, CDE oracle, cache +
graph metrics present, engine-build reduction positive. **Not met:** ≥80% engine
reduction and full convergence.

## NOT implemented (remaining cutover → REVISE)

1. Single-engine-multi-hazard existence query (the ≥80% lever).
2. Probe-cost reduction via the same single-engine path.
3. Incremental collision graph (still O(n²) snapshot).
4. Multi-target Sparrow pass (Algorithm 5/10).
5. Fixed-sheet exploration/compression (Algorithm 12/13 analogue).
6. `sparrow_cde` as normal-run production default (serde-default flip breaks
   legacy/API contract tests; needs a dedicated production run-config switch).

## Files touched
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` — cache + cached query helpers + 3 tests
- `rust/vrs_solver/src/optimizer/cde_observability.rs` — cache counters
- `rust/vrs_solver/src/optimizer/collision_backend.rs` — backend routes via cache
- `rust/vrs_solver/src/io.rs` — 7 cache diag fields
- `rust/vrs_solver/src/adapter.rs` — cache reset wiring + 3 diag constructors
- `scripts/smoke_sgh_q23r1_production_sparrow_cutover.py`,
  `scripts/bench_sgh_q23r1_production_sparrow_cutover.py`
- `docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md`, this doc, report + measurements
