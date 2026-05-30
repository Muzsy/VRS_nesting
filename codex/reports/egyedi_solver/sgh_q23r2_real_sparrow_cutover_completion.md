REVISE

# Report — SGH-Q23R2 Real Sparrow cutover completion

SGH-Q23R2_STATUS: REVISE
SPARROW_PRODUCTION_STATUS: PARTIAL_WITH_EXPLICIT_BLOCKERS
CDE_BATCH_CANDIDATE_STATUS: ACTIVE  (single-engine multi-hazard, 97% engine-build reduction)
CDE_ENGINE_BUILD_REDUCTION_GATE: MET  (7650 → 198 total builds, ≥80% target)
PROBE_BATCH_STATUS: ACTIVE  (separation probe reuses the session; pairwise_fallback = 0)
INCREMENTAL_GRAPH_STATUS: NOT_DONE_REVISE
MULTI_TARGET_PASS_STATUS: NOT_DONE_REVISE
EXPLORATION_COMPRESSION_STATUS: NOT_DONE_REVISE
PRODUCTION_DEFAULT_STATUS: LEGACY_STILL_DEFAULT_REVISE  (unsafe to flip while medium unsupported)
MEDIUM_CDE_STATUS: NOT_CONVERGED_REVISE
Q19_STATUS: HOLD

> `REVISE`, not report-only. Q23R2 implemented requirement **A** in full — the
> single-engine multi-hazard CDE candidate session — the #1 documented lever.
> Result: per-solve CDE engine builds on the medium fixture dropped **7650 → 198
> total** (72 legacy + 126 batch) = **97.4% reduction**, exceeding the ≥80% gate,
> with `cde_pairwise_fallback_queries = 0` and the separation probe running
> entirely through the reused session (requirement B). The medium fixture still
> does **not** converge (66→15, `unsupported`): convergence needs the multi-target
> pass (D), incremental graph (C) and fixed-sheet exploration/compression (E),
> which are not implemented. Per run.md §G the medium gate is hard, so the smoke
> fails it honestly and the top line is REVISE.

## 1) Meta
* **Task slug:** `sgh_q23r2_real_sparrow_cutover_completion`
* **Run date:** 2026-05-30
* **Branch:** main (uncommitted, on top of `a3b5a5a`)
* **Prior:** Q23 (broad-phase + `sparrow_cde` pipeline), Q23R1 (solve-scoped cache).
* `.cache/sparrow` present; jagua-rs 0.6.4 `collect_poly_collisions` +
  `BasicHazardCollector` + `HazardEntity::{Hole,Exterior}` confirmed and used.

## 2) Implemented this run

### A — single-engine multi-hazard candidate session (DONE)
`rust/vrs_solver/src/optimizer/cde_adapter.rs`: `CdeCandidateSession` builds ONE
`CDEngine` with the sheet as `Exterior` hazard + every same-sheet fixed item as a
`Hole { idx }` hazard. `query(candidate)` calls `collect_poly_collisions` once and
returns `{boundary_collision, colliding_layout_idxs}` with the VRS touching
post-policy applied per collided hazard (`polygons_collide` /
`polygon_within_sheet_pts`). `build_candidate_session` uses the Q23R1 prepared-
shape cache for every fixed item. Unit tests:
`cde_q23r2_batch_session_one_build_many_queries` (one build, many queries, correct
attribution), `cde_q23r2_batch_session_detects_boundary_violation`.

### B — batch probe (DONE)
`rust/vrs_solver/src/optimizer/collision_severity.rs::evaluate_transform_cde_batch`
routes the CDE production search path through the session: one boundary+pair
existence query, then a CDE-truth **separation-distance** loss
(`cde_batch_separation_loss`) — 8-direction bracket+binary probe whose every step
is a `session.query` (no engine build, no bbox-as-loss). `pairwise_fallback`
counted (0 on all fixtures). Diagnostics added: `cde_batch_candidate_queries`,
`cde_batch_engine_builds`, `cde_batch_hazards_registered`,
`cde_batch_collisions_returned`, `cde_pairwise_fallback_queries`.

## 3) Measured — medium_10_to_20_items / sparrow_cde / CDE

| metric | Q23 | Q23R1 | Q23R2 | gate |
|---|---:|---:|---:|---|
| total CDE engine builds | 7650 | 4246 | **198** (72 legacy + 126 batch) | ≤1530 ✓ |
| reduction vs Q23 | — | 45% | **97.4%** | ≥80% ✓ |
| pairwise fallback | — | — | **0** | 0 ✓ |
| collision pairs init→final | 66→28 | 66→10 | 66→15 | →0 ✗ |
| raw loss init→final | 1320→560 | 1320→200 | 1320→300 | →0 ✗ |
| status / placed | unsup 0/12 | unsup 0/12 | **unsup 0/12** | ok 12/12 ✗ |
| converged | false | false | **false** | true ✗ |
| bbox/lbf fallback | 0/0 | 0/0 | 0/0 | 0/0 ✓ |

The engine-build gate is decisively met (97%). Convergence is not: the single-
target greedy kernel + separation-distance loss plateaus, and only 7 iterations
fit the 8 s budget because the separation probe issues ~8k `session.query` calls
(cheap individually, but no multi-target progress per iteration).

## 4) run.md gate status

| # | requirement | status |
|---|---|---|
| A | single-engine multi-hazard candidate eval | ✓ DONE (97% engine reduction) |
| B | probe cost via batch session | ✓ DONE (separation probe on session; fallback 0) |
| C | incremental collision graph (vs O(n²)) | ✗ NOT DONE |
| D | multi-target / move_items_multi pass | ✗ NOT DONE |
| E | fixed-sheet exploration/compression | ✗ NOT DONE |
| F | flip production default to sparrow_cde | ✗ NOT DONE (unsafe while medium unsupported; would break production for medium-scale inputs + legacy contract tests) |
| G | medium converges 12/12 (hard) | ✗ NOT MET |
| H | LV8 readiness subset smoke | ✗ NOT DONE (fixture present; deferred) |

## 5) Why not PASS — precise remaining blockers
Convergence (G) is gated on the search escaping local minima, which needs:
1. **D — multi-target pass**: move all top-K colliding items per iteration across
   deterministic workers, select best by weighted loss (the kernel still moves one
   worst item/iteration → plateaus at 66→15).
2. **C — incremental collision graph**: maintain per-move edge updates instead of
   the O(n²) `CollisionGraphSnapshot::from_tracker` rebuild, so more iterations fit.
3. **E — exploration/compression**: restarts + disruption on stagnation to leave
   local minima, then compaction.
Only after G converges is **F** (default flip) safe; flipping now would route
medium-scale production inputs to an `unsupported` path. These are the next-run
scope; A+B (the CDE throughput lever) are done and measured here.

## 6) Tests / commands
* `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **430 passed, 0 failed**
  (incl. 2 new session tests; collision_severity / cde_adapter / search_position / adapter green).
* `python3 scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py` → **35 pass, 5 fail**
  (the 5 failures are exactly the medium hard convergence checks; engine-build gate passes).
  Smoke exits non-zero — medium convergence is a hard gate per run.md §G.
* `python3 scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py --quick` → measurements written
  (`sgh_q23r2_real_sparrow_cutover_measurements.{json,md}`); production converged 3/4.

## 7) Files
**New:** `scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py`,
`scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py`, this report,
measurements (`.json`/`.md`), `.verify.log`.
**Modified:** `rust/vrs_solver/src/optimizer/cde_adapter.rs` (CdeCandidateSession +
2 tests), `collision_severity.rs` (batch evaluator + separation loss),
`cde_observability.rs` (batch counters), `io.rs` + `adapter.rs` (batch diagnostics).

## 8) Honest limitations
Medium does not converge; C/D/E/F/H not implemented; production default unchanged.
All surfaced as concrete blockers (§5), nothing hidden; every production run counts
in the bench denominator.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T18:21:49+02:00 → 2026-05-30T18:24:49+02:00 (180s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.verify.log`
- git: `main@39d80d4`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     |  15 ++
 rust/vrs_solver/src/io.rs                          |  11 ++
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 210 +++++++++++++++++++++
 rust/vrs_solver/src/optimizer/cde_observability.rs |  32 ++++
 .../vrs_solver/src/optimizer/collision_severity.rs | 190 ++++++++++++++++++-
 5 files changed, 453 insertions(+), 5 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/cde_observability.rs
 M rust/vrs_solver/src/optimizer/collision_severity.rs
?? README_SGH_Q23R2_REAL_SPARROW_CUTOVER_COMPLETION_PACKAGE.md
?? canvases/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.md
?? codex/codex_checklist/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q23r2_real_sparrow_cutover_completion.yaml
?? codex/prompts/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion/
?? codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.md
?? codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.verify.log
?? codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.json
?? codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.md
?? scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py
?? scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py
```

<!-- AUTO_VERIFY_END -->
