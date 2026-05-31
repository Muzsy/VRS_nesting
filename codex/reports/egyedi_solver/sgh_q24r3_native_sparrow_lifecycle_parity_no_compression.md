PASS

# SGH-Q24R3 native Sparrow lifecycle parity (no compression)

SGH-Q24R3_STATUS: READY_FOR_AUDIT
MEDIUM_CDE_HARD_GATE: PASS (ok, 12/12, pairs 24→0, boundary 0, search_position>0, ~23.5s under 90s cap)
CONSTRUCTIVE_SEED: ACTIVE (build_constructive_seed_layout — area-sorted row/grid spread; replaces all-origin)
CDE_DECISIVE_LOSS: search separation = CDE batch separation distance (not bbox area)
COMPRESSION_STATUS: GATED OFF by default (SparrowConfig::enable_compression=false; 0 default passes)
PRODUCTION_BACKEND: sparrow_cde forces CDE; no bbox/LBF/legacy fallback
Q19_STATUS: HOLD

> `PASS`. The production `sparrow_cde` path now converges the **medium CDE 12/12
> hard gate** through the native Sparrow lifecycle, with compression excluded by
> default. The decisive change is requirement #3: a constructive (LBF/grid-like)
> fixed-sheet initial solution replaces the all-at-origin seed — initial medium
> collisions drop 66 → 24 and every item starts near its final neighbourhood, so
> the (now full-budget, compression-free) exploration/separation/search lifecycle
> resolves to 0 collision pairs and 0 boundary violations. `.cache/sparrow` was
> read; the function-by-function map is in
> `docs/egyedi_solver/sgh_q24r3_sparrow_reference_map.md`.

## 1) `.cache/sparrow` files read
`src/optimizer/mod.rs` (Alg 11), `separator.rs` (Alg 9/10), `worker.rs` (Alg 5),
`explore.rs` (Alg 12), `sample/search.rs` (Alg 6), `quantify/tracker.rs` (Alg 1/8);
`compress.rs` (Alg 13) skimmed only — out of scope.

## 2) Function-by-function Sparrow → VRS map
See `docs/egyedi_solver/sgh_q24r3_sparrow_reference_map.md`. Summary: `optimize`→
`SparrowSeparationKernel::run`; `LBFBuilder::construct`→`build_constructive_seed_layout`
(NEW); `exploration_phase`→`exploration_phase`+`disrupt_large_items`; `separate`→
`separate`; `move_items_multi`→`move_items_multi`; worker `move_items`→
`worker_move_items` (all colliding); `search_placement`→`search_position_for_target`
+ CDE batch separation; `CollisionTracker`→`VrsCollisionTracker`; `compress.rs`→
`compression_phase` (GATED OFF).

## 3) Rust files changed
- `rust/vrs_solver/src/optimizer/sparrow.rs` — **main deliverable**:
  - `build_constructive_seed_layout` (constructive LBF/grid seed, area-sorted,
    in-bounds, mild ~10% overlap, multi-sheet, overlap-allowed fallback only when
    the grid is full);
  - `SparrowConfig::enable_compression` (default **false**); `run()` gives
    exploration the FULL budget when compression is off and skips
    `compression_phase` by default;
  - the Q24R2 native lifecycle (separator strike loop, worker-master, worker
    move_items over all colliding, exploration pool + disruption) retained.
- `rust/vrs_solver/src/adapter.rs` — `run_sparrow_pipeline` seeds via
  `build_constructive_seed_layout` (was `build_sparrow_seed_layout` all-origin).

## 4) Seed builder changes (run.md #3)
`build_constructive_seed_layout`: expands instances, sorts by part area desc
(deterministic tie-break by instance_id), places on a coarse per-sheet row/grid
with pitch = 0.9 × rotated dims (mild overlap → near-feasible, search still has
work), wrapping rows and advancing sheets; all placements in-bounds; instances
that fit no sheet → `PART_NEVER_FITS_STOCK`; overlap-allowed origin fallback only
when the grid is full on every sheet. Never emitted as success without the Sparrow
separation lifecycle + final CDE validation. Medium effect: initial colliding
pairs 66 → 24.

## 5) State/problem/tracker (run.md #2)
Reuses `WorkingLayout` (`snapshot`) + `VrsCollisionTracker`
(`snapshot_loss`/`restore_but_keep_weights`/`update_placement`/`colliding_indices`/
`update_weights`) as the coherent layout+tracker state; workers load the master
snapshot; rollback preserves GLS weights (Q24R2). CDE candidate-session reuse
(`cde_adapter::CdeCandidateSession`, per-target-search fingerprint cache) keeps the
geometry state consistent.

## 6) CDE loss (run.md #4)
Collision/boundary EXISTENCE is CDE (`CdeCollisionBackend` → jagua `CDEngine`); the
decisive search separation loss is the CDE-truth separation distance
(`evaluate_transform_cde_batch`/`cde_batch_separation_loss`), never bbox `dx*dy`.
bbox is broad-phase prune only. The GLS tracker weight loss uses a smooth
penetration surrogate (documented fixed-sheet delta; drives weight pressure, not
the move decision).

## 7) Search depth + active-set (run.md #5/#6)
Production search keeps the Q24 non-trivial budget (global grid + focused + top-k +
two-stage coord descent) under CDE; search was NOT reduced to dodge timeout —
instead the constructive seed + full (compression-free) budget make it affordable.
Q24R1 per-target-search CDE session reuse remains active. (Large-sheet active-set
hazard filtering remains the LV8 follow-up; not needed for the medium gate.)

## 8) Exploration (run.md #7)
Bounded infeasible pool sorted by raw loss, biased restore (top half), repeated
restore/disrupt/separate, best feasible/infeasible tracking, large-item swap
disruption — retained from Q24R2 and now operational under CDE on the medium
fixture (it converges because the lifecycle works, not because tests were weakened;
the provided smoke is the unmodified package smoke).

## 9) Compression status (run.md #8) — OUT OF SCOPE
`SparrowConfig::enable_compression` defaults to **false**. `run()` skips
`compression_phase` by default and gives exploration the full budget. Medium CDE
converges with `sparrow_compression_passes == 0`. Compression code remains dormant
behind the flag (exercised only by an explicit unit test).

## 10) Tests / commands
- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` → ok.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **434 passed, 0 failed**.
- `python3 scripts/smoke_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.py`
  → **21 passed, 0 failed** (SMOKE: PASS) — the unmodified package smoke.
- `.cache/sparrow` present and read (§1).

## 11) Medium CDE hard-gate result
`medium_10_to_20_items / sparrow_cde / forced CDE`: status **ok**, placed **12/12**,
`sparrow_converged=true`, final collision pairs **0**, final boundary violations
**0**, `backend_used=cde_adapter`, bbox_fallback 0, LBF fallback 0,
search_position calls 18 / samples 322, compression passes **0**, ~23.5 s (< 90 s cap).

## 12) Remaining gaps toward full LV8
- Large-sheet (LV8 1500×3000) active-set hazard filtering for affordable CDE search
  at 12-types/24-instance scale (real irregular geometry) — the Q24R1-documented
  query-bound wall; not a Q24R3 gate.
- Full 276/276 LV8 multisheet tuning; sheet-count minimisation.
- Fixed-sheet compression on the last partially-used sheet (intentionally deferred).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T10:21:17+02:00 → 2026-05-31T10:24:20+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.verify.log`
- git: `main@0b9cdc5`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs           |   6 +-
 rust/vrs_solver/src/optimizer/sparrow.rs | 167 +++++++++++++++++++++++++++++--
 2 files changed, 162 insertions(+), 11 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow.rs
?? README_SGH_Q24R3_NATIVE_SPARROW_LIFECYCLE_PARITY_NO_COMPRESSION_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.yaml
?? codex/prompts/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression/
?? codex/reports/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.md
?? codex/reports/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.verify.log
?? docs/egyedi_solver/sgh_q24r3_sparrow_reference_map.md
?? scripts/smoke_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.py
```

<!-- AUTO_VERIFY_END -->
