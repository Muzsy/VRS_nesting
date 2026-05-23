PASS

# Report — JG-11 `jagua_optimizer_t11_score_model_v1`

## Dependency evidence

- `codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md` exists, first line `PASS`, contains `JG-11_STATUS: READY`.
- `rust/vrs_solver/src/optimizer/repair.rs` exists (JG-10 artifact).
- `rust/vrs_solver/src/optimizer/stopping.rs` exists (JG-10 artifact).
- `scripts/smoke_jagua_repair_search_v1.py` exists (JG-10 smoke artifact).

## Real code audit

| File | Finding |
|---|---|
| `optimizer/score.rs` | Skeleton had `ObjectiveBreakdown` with only counts + `penalty_placeholder`. Fully replaced with ScoreModel V1 implementation in JG-11. `pub mod score;` already in `mod.rs`. |
| `optimizer/state.rs` | `LayoutState`, `PlacedItem`, `UnplacedItem`, `PlacementTransform` present and serializable. JG-11 does not use LayoutState as primary scoring input (see design decision). |
| `optimizer/repair.rs` | `find_violations()` and `ViolationType` (pub) available; reused for overlap/boundary detection in score. |
| `optimizer/initializer.rs` | `bbox_from_placement()` available for bbox recovery from `io::Placement`. |
| `optimizer/candidates.rs` | `PlacedBbox::overlaps()` available; used internally by `find_violations()`. |
| `item.rs` | `Part`, `dims_for_rotation()`, `ItemGeometryStore`, `area` field. `dims_for_rotation` used for placed area calculation. |
| `sheet.rs` | `SheetShape`, `rect_inside_sheet_shape()` available for boundary checks via `find_violations()`. |
| `io.rs` | `SolverOutput` v1 contract: `contract_version`, `status`, `unsupported_reason`, `placements`, `unplaced`, `metrics`. Score model is internal only — does not touch this contract. |

## Score API design decision

**Operating on `Vec<Placement>` / `Vec<Unplaced>` directly, not LayoutState.**

Rationale: consistent with JG-10 RepairEngine decision. Phase 1 rectangular items carry all needed geometry in `io::Placement` + `Part` dimensions. `bbox_from_placement()` recovers the bbox. LayoutState integration is deferred to JG-12+ when cross-sheet tracking becomes needed.

**Score direction: lower `total_cost` is better (minimization).**

`ScoreModel::is_better(a, b)` returns `true` iff `a.total_cost < b.total_cost`.

## Default weight profile

| Component | Field | Default weight | Rationale |
|---|---|---|---|
| Placed area reward | `placed_area_reward` | 1.0 | Reward per unit² placed (negative contribution) |
| Unplaced penalty | `unplaced_penalty_per_item` | 1,000,000.0 | Strong incentive to place all items |
| Sheet count penalty | `sheet_count_penalty_per_sheet` | 10,000.0 | Prefer fewer sheets |
| Overlap penalty | `overlap_penalty_per_pair` | 1,000,000,000.0 | Validity guard — dominates all |
| Boundary penalty | `boundary_penalty_per_item` | 1,000,000,000.0 | Validity guard — dominates all |
| Compactness weight | `compactness_weight` | 0.001 | Tie-breaker only — never overrides above |

**Penalty hierarchy:**
```
overlap/boundary (1e9) >> unplaced (1e6) >> sheet_count (1e4) >> placed_area (1.0) >> compactness (0.001)
```

This hierarchy guarantees: no quality improvement (placed area, compactness) can make an invalid layout score better than a valid one.

## Implemented files

| File | Status |
|---|---|
| `rust/vrs_solver/src/optimizer/score.rs` | REPLACED — full ScoreModel V1 with ScoreWeights, ScoreModel, ObjectiveBreakdown, ScoreResult, score_layout(), 8 unit tests |
| `docs/egyedi_solver/jagua_optimizer_score_model_v1.md` | NEW — score documentation |
| `scripts/smoke_jagua_score_model_v1.py` | NEW — 16-check smoke script |

`optimizer/mod.rs` unchanged — `pub mod score;` was already present.
`adapter.rs` unchanged — ScoreModel is internal, not wired into Phase 1 adapter yet (deferred to JG-12).
`io.rs` unchanged — v1 contract not touched.

## ObjectiveBreakdown example (from smoke run)

Fixture: 3x A(50×50) + 2x B(80×30, rot 0/90) on sheet 300×200.
All 5 placed, 0 unplaced, 1 sheet used, `validation_status=pass`, `utilization=0.205`.

Computed breakdown (approximate, weights default):
```
placed_area = 3*(50*50) + 2*(30*80) = 7500 + 4800 = 12300 units²
sheet_count_used = 1
overlap_violations = 0
boundary_violations = 0
placed_area_contribution ≈ -12300.0
unplaced_contribution = 0.0
sheet_count_contribution = 10000.0
overlap_contribution = 0.0
boundary_contribution = 0.0
compactness_contribution = small
total_cost ≈ -2300 + small compactness
```

## Invalid vs valid score evidence (from unit tests)

| Scenario | overlap_violations | total_cost relationship |
|---|---|---|
| Two adjacent valid items (no overlap) | 0 | baseline |
| Two overlapping items (overlap 40×40) | 1 | +1,000,000,000.0 — dominates |
| Item placed at (200,200) on 100×100 sheet | 1 boundary | +1,000,000,000.0 — dominates |
| 1 item unplaced vs all placed | 0 | +1,000,000 penalty for unplaced |
| 2 sheets vs 1 sheet (same placed area) | 0 | +10,000 extra for second sheet |
| Compact vs spread (same items, same sheet) | 0 | diff < 1,000 (compactness only) |

All 8 unit tests PASS, covering these scenarios deterministically.

## Cargo build and test results

```
cargo build --manifest-path rust/vrs_solver/Cargo.toml
→ PASS (exit 0)

cargo test --manifest-path rust/vrs_solver/Cargo.toml
→ 54 passed; 0 failed; 0 ignored
  (JG-11 adds 8 new score tests; total was 49 in JG-10)

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
→ 8 passed; 0 failed
```

## Smoke results: smoke_jagua_score_model_v1.py

```
=== JG-11 ScoreModel V1 Smoke ===
Check 1: Rust score unit tests PASS (8/8)               PASS
Check 2: All 8 expected score test names present        PASS (8/8)
Check 3: Integration valid fixture → validation=pass    PASS
Check 4: metrics fields present (5 fields)              PASS
Check 5: JG-10 regression (smoke_jagua_repair_search)  PASS

=== RESULTS: 16 PASS, 0 FAIL ===
OVERALL: PASS
```

## Exact validation policy

The ScoreModel V1 is an optimizer-internal component only. The exact validation bridge (`validate_multi_sheet_output`) remains the definitive final gate. ScoreModel does not replace or weaken it. Invalid layout scoring (via `find_violations`) is used only to guide internal optimization — the final output is still validated by the Python bridge before `validation_status=pass` is written.

## Globális progress checklist

`canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-11 szakasza: `[x] Kész`.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T01:03:55+02:00 → 2026-05-24T01:06:54+02:00 (179s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.verify.log`
- git: `main@79f3363`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     |  32 +-
 rust/vrs_solver/src/optimizer/score.rs             | 518 ++++++++++++++++++---
 2 files changed, 480 insertions(+), 70 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M rust/vrs_solver/src/optimizer/score.rs
?? canvases/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t11_score_model_v1.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t11_score_model_v1/
?? codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
?? codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.verify.log
?? docs/egyedi_solver/jagua_optimizer_score_model_v1.md
?? scripts/smoke_jagua_score_model_v1.py
```

<!-- AUTO_VERIFY_END -->

JG-12_STATUS: READY
