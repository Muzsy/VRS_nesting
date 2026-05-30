REVISE

# Report — SGH-Q23 Full Sparrow parity cutover (fixed-sheet)

SGH-Q23_STATUS: REVISE
SPARROW_PRODUCTION_STATUS: CDE_FIRST_PARTIAL_PRODUCTION_PATH_ESTABLISHED_MEDIUM_CDE_CONVERGENCE_BLOCKED
LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED_FOR_CDE_SCALE (solve-scoped decision caches + dirty invalidation + incremental graph)

> First line is `REVISE` per the Q23 contract: the full cutover cannot be
> completed in one run. The production `sparrow_cde` path is established and is
> genuinely CDE-first + legacy-quarantined, AABB broad-phase query reduction is
> implemented and measurable, and 3/4 production fixtures converge — but the
> **medium CDE convergence acceptance gate is not met**. Precise remaining work
> and measurements are below. This is deliberately not a weak PASS.

---

## 1) Meta

* **Task slug:** `sgh_q23_full_sparrow_parity_cutover`
* **Canvas:** `canvases/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md`
* **Prompt:** `codex/prompts/egyedi_solver/sgh_q23_full_sparrow_parity_cutover/run.md`
* **Run date:** 2026-05-30
* **Branch / commit:** main (uncommitted changes on top of `a3b5a5a`)
* **Reference map:** `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`
* **Design doc:** `docs/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md`

## 2) Step 0 — Sparrow reference audit (done)

`.cache/sparrow` is present locally. The full port map (real source paths/types
→ VRS equivalents, plus intentional deviations) is in
`docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`. Key finding for this task:
Sparrow's throughput depends on a **live, incrementally-updated `CDEngine`**
(`Layout::cde()`), upper-bounded early-terminating evaluation
(`eval/sep_evaluator.rs` Algorithm 7), and an incremental per-item collision
tracker (`quantify/tracker.rs`). VRS integrates jagua-rs 0.6.4 as **per-call**
`CDEngine::new` (`cde_session.rs` = `PerCallOnly`) — the structural reason medium
CDE fixtures do not scale.

## 3) Step 1 — pre-implementation blocker summary

| # | Blocker (pre-Q23) | Location |
|---|---|---|
| A | No CDE-first **production** pipeline; `sparrow_experimental` lets the caller pick bbox, which can act as collision truth | `io.rs`, `adapter.rs` |
| B | Every CDE pair/boundary query rebuilds a `CDEngine` → medium CDE timeout (Q22R1 `REQUIRED_FOR_CDE_SCALE`) | `cde_adapter.rs`, `cde_session.rs` |
| C | No AABB broad-phase; even provably-separated pairs pay a full engine build | `cde_adapter.rs` |
| D | Sparrow kernel moves one worst-weighted target/iteration, not Algorithm 5/10 all-colliding-items/pass | `optimizer/sparrow.rs` |
| E | Collision graph rebuilt O(n²) each refresh; no incremental update / active-set filtering | `optimizer/sparrow.rs::CollisionGraphSnapshot` |
| F | No fixed-sheet strip-shrink analogue of exploration/compression (Algorithm 12/13) in Sparrow mode | — |

## 4) What Q23 delivers (this run)

1. **Production pipeline `optimizer_pipeline = "sparrow_cde"`**
   (`OptimizerPipelineKind::SparrowCde`). CDE-first by contract: forces the CDE
   backend (ignores a bbox request), forbids LBF/finite-candidate fallback
   (`allow_lbf_fallback=false`), never falls back to a legacy solver, labels
   `pipeline_used="sparrow_cde"`, and preserves full optimizer + backend
   diagnostics on any failure. Shared driver `run_sparrow_pipeline` unifies the
   experimental and production paths (blocker A).
2. **AABB broad-phase query reduction** in `CdeAdapter::query_pair`: AABB-separated
   pairs resolve as `NoCollision` without a `CDEngine` build; counted as
   `broadphase_pruned` and surfaced as `cde_broadphase_pruned`. Broad-phase never
   asserts positive collision truth (blocker C). Measured prune rate 26–45%.
3. **Diagnostics:** `cde_broadphase_pruned` added to
   `CollisionBackendDiagnosticsOutput`; query/engine/prune metrics visible in
   smoke + bench.
4. **Smoke + bench** with full outcome accounting (ok/partial/unsupported/
   timeout/error), CDE-first, no skip-on-failure.

Blockers B, D, E, F remain — see §7.

## 5) Sparrow parity contract — honest status

| Contract item | Status |
|---|---|
| 1. Explicit SparrowState lifecycle (infeasible states, best feas/infeas incumbents, GLS-preserving rollback) | **DONE** (Q22, reused) |
| 2. Backend-confirmed collision graph + weighted target selection | **DONE** but full O(n²) rebuild (no incremental/active-set) |
| 3. `search_position` primary relocation (global+focused sampling, top-k, coord descent, rotation policy, backend oracle, deterministic seed) | **DONE** (Q20R/Q22) |
| 4. Move accept/reject/rollback, GLS on stagnation, no legacy fallback | **DONE** |
| 5. Exploration/compression strip-shrink (Alg 12/13) fixed-sheet analogue | **NOT DONE** (single separation loop only) |
| 6. CDE/Jagua geometry truth (existence, boundary, commit, diagnostics on failure, metrics) | **DONE** (forced CDE) |
| 7. Fixed-sheet adaptation (inside sheet, no collision, place all required; multi-sheet HOLD) | **DONE** single-sheet; multi-sheet HOLD |
| CDE scaling (session/cache, prepared/pair/boundary caches, dirty invalidation, active-set, incremental graph, broadphase, query budget) | **PARTIAL** — only AABB broad-phase + query-budget diagnostics done |

## 6) Acceptance result (honest)

Production `sparrow_cde` + CDE (`bench --quick`, seed 1):

| fixture | status | converged | runtime | pairs i→f | raw loss i→f | engine builds | broadphase pruned |
|---|---|---|---:|---|---|---:|---:|
| tiny | ok | true | 0.23 s | 1→0 | 20.0→0.0 | 71 | 25 |
| two_rect_overlap | ok | true | 0.80 s | 1→0 | 30.0→0.0 | 255 | 209 |
| boundary_recovery | ok | true | 0.004 s | 0→0 | 0→0 | 2 | 0 |
| medium_10_to_20_items | **unsupported** | **false** | **25.0 s** | 66→28 | 1320→560 | 7650 | 3586 |

Production outcome accounting: **ok=3, partial=0, unsupported=1, timeout=0,
error=0; converged 3/4.**

The Q23 PASS gate requires `medium_10_to_20_items + sparrow_cde + cde` to not
timeout under the quick cap AND be `ok` or a well-defined partial with
`sparrow_converged` true for full-convergence fixtures. Medium does **not**
converge (58% loss reduction, 66→28 pairs, but not feasible) and runs ~25 s. →
**REVISE**.

## 7) Precise remaining cutover work (the REVISE blocker list)

Throughput-critical (without these medium CDE cannot meet the gate):

1. **Solve-scoped CDE decision caches** keyed by stable transform signatures:
   prepared-geometry cache (per part+rotation `SPolygon`), pair decision cache,
   boundary decision cache, with **dirty invalidation** on item move. Requires a
   stateful CDE backend (interior mutability or a `&mut` cache threaded through
   `collision_severity.rs` / `search_position.rs` / `separator.rs`), since the
   `CollisionBackend` trait is `&self`. This eliminates most of the 7650 per-call
   `CDEngine::new` builds.
2. **Incremental collision-graph update** (mirror Sparrow
   `CollisionTracker::register_item_move`) instead of the O(n²) sweep in
   `CollisionGraphSnapshot::from_tracker`.
3. **Active-set pair filtering** (only re-query AABB-near pairs).

Parity-completeness (separate, non-throughput):

4. **Algorithm 5/10 parity**: move every colliding item per pass across parallel
   workers; current kernel moves one worst-weighted target per iteration.
5. **Exploration/compression** fixed-sheet analogue of Algorithm 12/13.
6. **Multi-sheet** minimisation (Q19 HOLD).

## 8) Tests

* `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **425 passed, 0 failed** (216s).
  Includes the run.md targets `optimizer::sparrow`, `optimizer::cde_session`,
  `optimizer::collision_severity`, `optimizer::search_position`, `adapter`.
* New Rust tests:
  * `cde_adapter::cde_q23_broadphase_prunes_separated_rects_without_engine_build`
  * `cde_adapter::cde_q23_broadphase_does_not_prune_overlapping_rects`
  * `adapter::sparrow_cde_pipeline_deserializes_from_snake_case`
  * `adapter::sparrow_cde_tiny_converges_and_labels_pipeline_sparrow_cde`
  * `adapter::sparrow_cde_forces_cde_backend_even_when_bbox_requested`
  * `adapter::sparrow_cde_failure_preserves_full_diagnostics`
  * Updated `collision_backend::cde_observability_engine_builds_counted_for_pair_query`
    to an overlapping pair (broad-phase aware).
* `python3 scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py` → **40 passed, 0 failed** (SMOKE: PASS).
* `python3 scripts/bench_sgh_q23_full_sparrow_parity_cutover.py --quick` → measurements written.

## 9) Files

**New:**
* `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`
* `docs/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md`
* `scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py`
* `scripts/bench_sgh_q23_full_sparrow_parity_cutover.py`
* this report + measurements (`.json`, `.md`) + `.verify.log`

**Modified:**
* `rust/vrs_solver/src/io.rs` — `SparrowCde` variant, `cde_broadphase_pruned` field
* `rust/vrs_solver/src/adapter.rs` — `run_sparrow_pipeline` driver, `SparrowCde` routing, label param, broadphase in 3 diag ctors, 4 tests
* `rust/vrs_solver/src/optimizer/cde_adapter.rs` — AABB broad-phase prune + 2 tests
* `rust/vrs_solver/src/optimizer/cde_observability.rs` — `broadphase_pruned` counter
* `rust/vrs_solver/src/optimizer/collision_backend.rs` — broad-phase-aware engine-build test

## 10) Known limitations (allowed under REVISE)

* Medium/large CDE does not converge under the quick cap (blocker §7.1–3).
* No Algorithm 5/10 multi-item/multi-worker parity (§7.4).
* No fixed-sheet exploration/compression (§7.5).
* Multi-sheet minimisation HOLD (Q19).
* Broad-phase pruning is pair-only; boundary queries are not pruned (conservative
  for irregular sheets).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T16:38:36+02:00 → 2026-05-30T16:41:42+02:00 (186s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.verify.log`
- git: `main@a3b5a5a`
- módosított fájlok (git status): 19

**git diff --stat**

```text
 .codegraphcontext/db/falkordb.settings             |   2 +-
 rust/vrs_solver/src/adapter.rs                     | 343 +++++++++++++++------
 rust/vrs_solver/src/io.rs                          |   9 +
 rust/vrs_solver/src/optimizer/cde_adapter.rs       |  57 ++++
 rust/vrs_solver/src/optimizer/cde_observability.rs |  16 +
 rust/vrs_solver/src/optimizer/collision_backend.rs |   8 +-
 6 files changed, 345 insertions(+), 90 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .codegraphcontext/db/falkordb.settings
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/cde_observability.rs
 M rust/vrs_solver/src/optimizer/collision_backend.rs
?? README_SGH_Q23_FULL_SPARROW_PARITY_CUTOVER_PACKAGE.md
?? canvases/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
?? codex/codex_checklist/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q23_full_sparrow_parity_cutover.yaml
?? codex/prompts/egyedi_solver/sgh_q23_full_sparrow_parity_cutover/
?? codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
?? codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.verify.log
?? codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.json
?? codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.md
?? docs/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
?? docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
?? scripts/bench_sgh_q23_full_sparrow_parity_cutover.py
?? scripts/smoke_sgh_q23_full_sparrow_parity_cutover.py
```

<!-- AUTO_VERIFY_END -->
