REVISE

# Report — SGH-Q23R1 Production Sparrow cutover implementation

SGH-Q23R1_STATUS: REVISE
SPARROW_PRODUCTION_STATUS: PARTIAL_WITH_EXPLICIT_BLOCKERS
PRODUCTION_DEFAULT_STATUS: LEGACY_STILL_DEFAULT_REVISE
CDE_SESSION_STATUS: STATEFUL_SESSION_OR_CACHE_ACTIVE
INCREMENTAL_GRAPH_STATUS: PARTIAL_REVISE
LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY
MEDIUM_CDE_STATUS: NOT_CONVERGED_REVISE
Q19_STATUS: HOLD

> `REVISE` — but NOT report-only. R1 implemented the run.md §1 strategy-B
> solve-scoped CDE cache (decision + prepared-geometry) with full metrics and
> tests. On the medium fixture this cut engine builds 7650→4246 (−45%), raised
> the cache pair-hit rate to 76%, took residual collision pairs 66→28 → 66→10
> and raw loss 1320→560 → 1320→200, and runtime 25 s → 9.7 s. The hard R1 gates
> (≥80% engine reduction, full convergence, production-default flip) are not yet
> met — the remaining structural lever (single-engine-multi-hazard query) and the
> default-routing change are documented as precise blockers below.

## 1) Meta
* **Task slug:** `sgh_q23r1_production_sparrow_cutover_implementation`
* **Canvas:** `canvases/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md`
* **Run date:** 2026-05-30
* **Branch / commit:** main (uncommitted, on top of `a3b5a5a`)
* **Reference delta:** `docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md`
* **Design doc:** `docs/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md`

## 2) Reference gate
`.cache/sparrow` present. Reference delta written, focused on the per-call-CDE
blocker (Sparrow's live `CDEngine` + incremental tracker vs VRS `PerCallOnly`).

## 3) Implemented (real code, not a report)

### Solve-scoped CDE cache — run.md §1 strategy B
`cde_adapter.rs` thread-local `QUERY_CACHE`: prepared-geometry cache
(`Rc<CdePreparedShape>`), pair decision cache, boundary decision cache, keyed by
**full part geometry hash + exact f64 transform bits** (pure-function correct;
id-only collisions impossible). `reset_query_cache()` wired to every CDE solve
scope. `CdeCollisionBackend` routes through `cached_query_pair`/
`cached_query_boundary`; a hit returns the verdict with **no `CDEngine::new`**.
Bounded by `CACHE_ENTRY_CAP` (evictions → `cache_invalidations`).

### Metrics — run.md §3
`cde_cache_{pair,boundary,prepared}_{hits,misses}`, `cde_cache_invalidations`
added to `CdeCounters` and `CollisionBackendDiagnosticsOutput` (with Q23's
`cde_engine_builds`, `cde_broadphase_pruned`).

### Legacy quarantine — run.md §7
`sparrow_cde` forces CDE, no LBF/bbox/legacy fallback, full diagnostics on
failure (Q23 + R1 tests).

## 4) Measured — medium_10_to_20_items / sparrow_cde / CDE

| metric | Q23 baseline | R1 | R1 gate | met |
|---|---:|---:|---|:--:|
| status | unsupported | unsupported | ok | ✗ |
| placed/required | 0/12 | 0/12 | 12/12 | ✗ |
| sparrow_converged | false | false | true | ✗ |
| collision pairs init→final | 66→28 | 66→10 | →0 | ✗ |
| raw loss init→final | 1320→560 | 1320→200 | →0 | ✗ |
| cde_engine_builds | 7650 | **4246 (−45%)** | ≤1530 (−80%) | ✗ |
| cache pair hits/misses | — | 20043/6253 (76%) | active | ✓ |
| runtime | ~25 s | **~9.7 s** | no timeout | ✓ |
| bbox_fallback / lbf_fallback | 0 / 0 | 0 / 0 | 0 / 0 | ✓ |
| backend_used | cde_adapter | cde_adapter | cde | ✓ |

Production `sparrow_cde` outcome accounting (`bench --quick`): ok=3, partial=0,
unsupported=1, timeout=0, error=0; converged 3/4 (tiny, two_rect, boundary
converge; medium does not). See
`codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_measurements.md`.

## 5) Gate status vs run.md §9

| gate | status |
|---|---|
| medium status ok / placed=required / converged | ✗ NOT_CONVERGED_REVISE |
| bbox_fallback_queries == 0 | ✓ |
| lbf_fallback_used == 0 | ✓ |
| backend_used == cde_adapter | ✓ |
| no timeout | ✓ (~9.7 s) |
| engine builds −80% vs 7650 | ✗ (−45%) |
| cache hit/miss/invalidation metrics present | ✓ |
| incremental collision graph metrics present | ✗ (graph still O(n²) snapshot) |
| production route uses sparrow_cde | ✗ (selectable + quarantined; default not flipped) |
| failures keep diagnostics | ✓ |
| cargo tests pass | ✓ (428 lib) |
| smoke passes (hard gates) | ✓ (33) |
| quick bench JSON+MD with denominator accounting | ✓ |

## 6) Remaining cutover work (precise blockers)
1. **Single-engine-multi-hazard existence query** — one `CDEngine` per candidate
   (all fixed items as `Hole` hazards + sheet `Exterior`), queried once via
   `collect_poly_collisions`, replacing N pairwise builds. The ≥80% lever. Needs a
   CDE-specific batched path through `eval_with_severity_backend` (today backend-
   agnostic `&dyn CollisionBackend`) + per-hazard touching post-policy.
2. **Probe-cost reduction** via the same single-engine path (`run_pair_probe`/
   `run_boundary_probe`).
3. **Incremental collision graph** (replace O(n²) `CollisionGraphSnapshot::from_tracker`).
4. **Multi-target Sparrow pass** (Algorithm 5/10).
5. **Fixed-sheet exploration/compression** (Algorithm 12/13 analogue).
6. **Production default routing** — dedicated run-config switch to `sparrow_cde`
   (serde-default flip breaks legacy/API contract tests).

## 7) Tests / commands
* `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **428 passed, 0 failed**
  (includes `optimizer::sparrow`, `optimizer::cde_session`,
  `optimizer::collision_severity`, `optimizer::search_position`,
  `optimizer::separator`, `adapter`). New: `cde_q23r1_cache_hit_avoids_second_engine_build`,
  `cde_q23r1_cache_key_includes_geometry_not_just_id`, `cde_q23r1_reset_clears_cache`.
* `python3 scripts/smoke_sgh_q23r1_production_sparrow_cutover.py` → **33 hard-gate checks pass**;
  `MEDIUM_CDE_STATUS: NOT_CONVERGED_REVISE` (honest).
* `python3 scripts/bench_sgh_q23r1_production_sparrow_cutover.py --quick` → measurements written.

## 8) Files
**New:** reference delta, impl doc, this report, measurements (`.json`/`.md`),
`.verify.log`, `scripts/smoke_sgh_q23r1_*`, `scripts/bench_sgh_q23r1_*`.
**Modified:** `cde_adapter.rs`, `cde_observability.rs`, `collision_backend.rs`,
`io.rs`, `adapter.rs`.

## 9) Honest limitations
Medium/large CDE not converged; engine reduction 45% (gate 80%); production
default not flipped; incremental graph / multi-target / exploration-compression
not implemented. All documented as concrete blockers (§6), not hidden.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T17:46:38+02:00 → 2026-05-30T17:49:26+02:00 (168s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.verify.log`
- git: `main@0c48699`
- módosított fájlok (git status): 18

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     |  26 ++-
 rust/vrs_solver/src/io.rs                          |  15 ++
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 234 +++++++++++++++++++++
 rust/vrs_solver/src/optimizer/cde_observability.rs |  43 +++-
 rust/vrs_solver/src/optimizer/collision_backend.rs |  42 +---
 5 files changed, 318 insertions(+), 42 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/cde_observability.rs
 M rust/vrs_solver/src/optimizer/collision_backend.rs
?? README_SGH_Q23R1_PRODUCTION_SPARROW_CUTOVER_IMPLEMENTATION_PACKAGE.md
?? canvases/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
?? codex/codex_checklist/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q23r1_production_sparrow_cutover_implementation.yaml
?? codex/prompts/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation/
?? codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
?? codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.verify.log
?? codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_measurements.json
?? codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_measurements.md
?? docs/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
?? docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md
?? scripts/bench_sgh_q23r1_production_sparrow_cutover.py
?? scripts/smoke_sgh_q23r1_production_sparrow_cutover.py
```

<!-- AUTO_VERIFY_END -->
