REVISE

# SGH-Q24R1 native Sparrow parity lifecycle + LV8 gate completion

SGH-Q24R1_STATUS: REVISE
CDE_SESSION_REUSE_STATUS: ACTIVE (medium reuse_ratio≈0.90, builds 152→29, pairwise_fallback=0)
ACTIVE_SET_STATUS: NOT_DONE_REVISE
WORKER_MOVE_ITEMS_PARITY_STATUS: PARTIAL (Q23R3 multi-target; full move_items parity not done)
SEARCH_PLACEMENT_PARITY_STATUS: PARTIAL (Q24 focused+container+2-stage CD budgets; BestSamples partial)
TRACKER_LOSS_STATUS: PARTIAL (CdeSeparation identity; tracker still smooth-surrogate, not CDE-shape)
EXPLORATION_POOL_STATUS: NOT_DONE_REVISE
COMPRESSION_REWRITE_STATUS: NOT_DONE_REVISE
MEDIUM_GATE_STATUS: PASS (ok 12/12, pairs 66→0)
LV8_12TYPES_GATE_STATUS: NOT_MET_TIMEOUT
LV8_24_GATE_STATUS: NOT_MET_TIMEOUT
Q19_STATUS: HOLD

> `REVISE`, not report-only. Q24R1 implemented the documented linchpin (#2) — a
> **per-target-search CDE session reuse** cache — which cut medium CDE session
> builds ~152→29 with a measured reuse ratio ≈0.90 (≥0.80 gate, on medium) and
> `cde_pairwise_fallback_queries=0`, with no regression (433 lib tests, medium
> still `ok 12/12`). But the LV8 12-types/24 hard gates **still time out**: the
> cost is now **query-bound** (`collect_poly_collisions` over large real polygons
> × separation-probe volume), which session *build* reuse does not remove. Full
> parity (active-set query reduction #3, worker move_items #4, CDE-shape tracker
> loss #6, exploration pool #7, compression #8) is not done. PASS forbidden.

## 1) Sparrow reference map (run.md #1)

| Sparrow (.cache/sparrow) | VRS file | status |
|---|---|---|
| Alg 11 optimize (`optimizer/mod.rs`) | `optimizer/sparrow.rs` run loop | FIXED_SHEET_ADAPTATION |
| Alg 9 separate (`optimizer/separator.rs`) | `optimizer/sparrow.rs` separation/strike loop (Q23R3) | FIXED_SHEET_ADAPTATION |
| Alg 10 move_items_multi | `optimizer/sparrow.rs` multi-target worker pass (Q23R3) | PARTIAL (top-K, not full move_items) |
| Alg 5 worker move_items (`optimizer/worker.rs`) | `optimizer/sparrow.rs` per-target moves | REVISE (not every colliding item per worker pass) |
| Alg 6 search_placement (`sample/search.rs`) | `optimizer/search_position.rs` | PARTIAL (focused+container+2-stage CD; BestSamples retention partial) |
| Alg 8 tracker/update_weights (`quantify/tracker.rs`) | `optimizer/separator.rs` VrsCollisionTracker | PARITY (GLS weights) / REVISE (loss still smooth-surrogate, not CDE-shape) |
| Alg 12 exploration (`optimizer/explore.rs`) | `optimizer/sparrow.rs` restart/disruption (Q23R3 minimal) | REVISE (no real pool/biased restore) |
| Alg 13 compression (`optimizer/compress.rs`) | `optimizer/sparrow.rs` compaction (Q23R3 minimal) | REVISE (no restore→pressure→separate→accept) |
| live `CDEngine` (`Layout::cde()`) | `optimizer/cde_adapter.rs` `CdeCandidateSession` + Q24R1 per-target-search reuse | FIXED_SHEET_ADAPTATION (per-call build, now session-reused per target search) |

## 2) Implemented this run — #2 CDE target-search session reuse (DONE)
`rust/vrs_solver/src/optimizer/cde_adapter.rs`: `build_candidate_session` now caches
the `CdeCandidateSession` in a thread-local keyed by a **fixed-hazard fingerprint**
(target_idx + sheet + every other same-sheet placement's geometry+transform). During
one target's search the others are fixed → the fingerprint is stable → all candidate
evaluations (global grid, focused, both coord-descent stages, separation probes)
reuse one `CDEngine` instead of rebuilding it. Reset per solve.

Diagnostics surfaced: `cde_candidate_session_builds`, `cde_candidate_session_reuses`
(→ reuse ratio), alongside Q23R2's `cde_batch_*` and `cde_pairwise_fallback_queries`.

Measured (medium, sparrow_cde + CDE): `session_builds=29`, `session_reuses=267`,
**reuse_ratio≈0.902**, `cde_batch_engine_builds` 152→29, `pairwise_fallback=0`.
Hard gates `cde_pairwise_fallback_queries==0` ✓ and `reuse_ratio>=0.80` ✓ **on
medium**. (The gate also requires ≥0.80 on LV8 rows, which time out → unmeasured.)

## 3) Why LV8 hard gates still fail — precise blocker
Session **build** reuse removes `CDEngine::new` cost, but each `session.query`
(`collect_poly_collisions`) still iterates the candidate's edges against all
registered hazards, and the separation probe issues ~O(8×14) queries per candidate
× many candidates × 12 targets × passes. Over LV8's large many-vertex real polygons
this `query` cost dominates → >60 s timeout. The remaining fix is **active-set
hazard reduction (#3)** — register only hazards near the target's reachable region
so each query is cheap — combined with bounded probe/search volume. Active-set,
however, trades off against whole-sheet session reuse (the global grid spans the
sheet), so it requires per-region sessions or a spatial-grid query, i.e. the larger
lifecycle rewrite (#3–#8). That is the next-run scope.

## 4) Hard-gate status (run.md)

| gate | status |
|---|---|
| #2 cde_pairwise_fallback_queries == 0 | PASS (medium) |
| #2 cde_session_reuse_ratio ≥ 0.80 | PASS on medium; LV8 unmeasured (timeout) |
| #3 active-set | NOT DONE |
| #4 worker move_items parity (nonincrease==0, items_seen>passes) | PARTIAL (Q23R3 multi-target) |
| #5 search parity (container/focused/pre+final refine > 0) | PARTIAL (Q24 budgets) |
| #6 tracker CDE-shape loss (bbox_proxy_queries==0, cde_shape_queries>0) | NOT DONE (smooth surrogate) |
| #7 exploration pool inserts/restores/disruption | NOT DONE |
| #8 compression separation lifecycle | NOT DONE |
| #9 medium ok 12/12 | PASS |
| #9 lv8_12types_x1 ok 12/12 | **FAIL (timeout)** |
| #9 lv8_24_instances ok 24/24 | **FAIL (timeout)** |
| #10 no fallback (bbox/lbf/pairwise) | PASS (medium: all 0) |

## 5) Tests / commands
* `cargo build --release` → ok.
* `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **433 passed, 0 failed** (no regression).
* `python3 scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py` → medium + session-reuse gates pass; LV8 12-types/24 hard gates fail (timeout). Smoke exits non-zero.
* `python3 scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py --quick` → measurements written; LV8 ladder measured honestly (timeouts counted).
* `.cache/sparrow` present and used as the reference (§1).

## 6) Files
**New:** `scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py`,
`scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py`, this report,
measurements (`.json`/`.md`), `.verify.log`.
**Modified:** `rust/vrs_solver/src/optimizer/cde_adapter.rs` (session-reuse
fingerprint cache + `build_candidate_session` → `Rc` + reset), `cde_observability.rs`
(`candidate_session_builds`/`reuses`), `io.rs` (session reuse diag fields),
`adapter.rs` (surface session counters in 3 diag constructors).

## 7) Explicit REVISE reason
Per run.md, PASS is forbidden unless every hard gate passes. The LV8 12-types/24
convergence gates time out (query-bound), and #3 active-set, #4 full worker
move_items, #6 CDE-shape tracker loss, #7 exploration pool, #8 compression are not
implemented. Delivered and measured: #2 per-target-search session reuse
(reuse_ratio≈0.90 on medium, builds 152→29, pairwise_fallback=0), with no medium
regression. The precise remaining blocker (active-set query reduction) is in §3.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T22:08:44+02:00 → 2026-05-30T22:11:30+02:00 (166s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.verify.log`
- git: `main@4c23840`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     |  6 +++
 rust/vrs_solver/src/io.rs                          |  5 +++
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 52 +++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/cde_observability.rs | 14 ++++++
 4 files changed, 75 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/cde_observability.rs
?? README_SGH_Q24R1_NATIVE_SPARROW_PARITY_LIFECYCLE_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r1_native_sparrow_parity_lifecycle.yaml
?? codex/prompts/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle/
?? codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
?? codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.verify.log
?? codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.json
?? codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.md
?? scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py
?? scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py
```

<!-- AUTO_VERIFY_END -->
