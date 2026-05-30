# SGH-Q23R1 — Sparrow reference delta (what Q23 missed, what R1 implemented)

Builds on [`sgh_q23_sparrow_reference_map.md`](./sgh_q23_sparrow_reference_map.md).
This delta is scoped to the per-call-CDE blocker that left Q23 at `REVISE`.

## The Q23 blocker, in Sparrow terms

Local Sparrow (`.cache/sparrow`) never rebuilds its collision engine per query:
`SPProblem.layout` owns a live `CDEngine` (`Layout::cde()`), and a move mutates it
incrementally (`remove_item`/`place_item`). The separation evaluator
(`src/eval/sep_evaluator.rs`, Algorithm 7) queries that live engine with an
upper-bounded, early-terminating collector (`SpecializedHazardCollector`), and the
collision tracker (`src/quantify/tracker.rs`) recomputes only the moved item's row
(`register_item_move`). So a candidate evaluation is cheap: no engine construction,
surrogate poles for fast reject, early exit once the loss bound is exceeded.

VRS (jagua-rs 0.6.4, `cde_session.rs` = `PerCallOnly`) had no live engine: every
`CdeCollisionBackend::placement_overlaps` / `placement_within_sheet` built a fresh
`CDEngine` (`cde_adapter.rs::query_pair`/`query_boundary` → `CDEngine::new`). Q23
measured 7650 engine builds / 25 s on the medium fixture → `unsupported`.

## What R1 implemented (this run)

R1 takes run.md **strategy B**: *"VRS-side solve-scoped exact/CDE cache with dirty
invalidation while keeping CDE adapter calls behind cache misses."*

| Sparrow concept | R1 VRS realisation |
|---|---|
| Live engine, no per-candidate rebuild | Solve-scoped **decision cache** (`cde_adapter.rs::QUERY_CACHE`): pair + boundary verdicts memoised; a hit returns the verdict with **no `CDEngine::new`**. |
| Cached transformed shapes | **Prepared-geometry cache** (`Rc<CdePreparedShape>` by part-geometry + transform): the fixed items' `SPolygon`s are built once and shared across the whole search. |
| Incremental tracker (`register_item_move`) | Transform-keyed cache is self-invalidating: a moved item produces new transform keys, so stale entries become unreachable (documented dirty-invalidation; explicit eviction only bounds memory). |
| Surrogate fast-reject | **AABB broad-phase** (Q23, retained): AABB-separated pairs resolve `NoCollision` with no build. |
| Engine/query visibility | Diagnostics: `cde_engine_builds`, `cde_broadphase_pruned`, `cde_cache_{pair,boundary,prepared}_{hits,misses}`, `cde_cache_invalidations`. |

Correctness: a CDE verdict is a pure function of `(part geometry, transform,
backend config)`. The cache key hashes the part's full geometry (id + dims +
outer polygon) plus exact f64 transform bits, so two parts sharing an id but
differing geometrically can never collide on a cached verdict (unit test
`cde_q23r1_cache_key_includes_geometry_not_just_id`). The cache is reset per
CDE solve scope.

## Measured effect (medium_10_to_20_items, sparrow_cde + CDE)

| metric | Q23 baseline | R1 |
|---|---:|---:|
| status | unsupported | unsupported |
| sparrow iterations | 5 | 8 |
| collision pairs initial→final | 66→28 | 66→10 |
| raw loss initial→final | 1320→560 (58%) | 1320→200 (85%) |
| cde engine builds | 7650 | 4246 (−45%) |
| cde total queries | 11236 | 27350 |
| cache pair hits / misses | — | 20043 / 6253 (76% hit) |
| runtime | ~25 s | ~9.7 s |

The cache makes each iteration far cheaper (more iterations + far lower residual
loss in less wall time), but does **not** yet meet the R1 gates: engine-build
reduction is 45% (gate ≥80%) and the fixture does not reach feasibility.

## What R1 did NOT finish (precise remaining cutover → still REVISE)

1. **Single-engine-multi-hazard existence query** — the larger structural win:
   build one `CDEngine` per candidate evaluation holding all fixed items as
   `Hole` hazards (+ sheet as `Exterior`) and query the candidate once via
   `collect_poly_collisions`, instead of N pairwise builds. Needs a CDE-specific
   batched path through `eval_with_severity_backend` (currently `&dyn
   CollisionBackend`, backend-agnostic) and per-hazard touching post-policy. This
   is what would take engine builds well past the 80% gate.
2. **Probe-cost reduction** — `run_pair_probe`/`run_boundary_probe` directional
   bracket+binary search still issues many (cached but partly distinct) queries
   for severity; needs the single-engine path too.
3. **Incremental collision graph** — `CollisionGraphSnapshot::from_tracker` is
   still an O(n²) rebuild per refresh.
4. **Multi-target Sparrow pass** — kernel still moves one worst-weighted target
   per iteration (not Algorithm 5/10 all-colliding-items-per-pass).
5. **Fixed-sheet exploration/compression** (Algorithm 12/13 analogue).
6. **Production default routing** — `sparrow_cde` is selectable + quarantined but
   not yet the normal-run default (flipping the serde default breaks unrelated
   legacy/API contract tests; needs a dedicated production run-config switch).
