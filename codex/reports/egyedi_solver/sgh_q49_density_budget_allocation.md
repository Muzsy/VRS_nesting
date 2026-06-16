# SGH-Q49 — Budget allocation for the density compaction pass

## 1. Executive summary

SGH-Q49 fixes the SGH-Q48 budget-starvation finding. The interlock-aware density compaction was
gated to the time left *after* the BPP sheet-reduction, which consumed the whole budget on full276,
so the pass only reached a few parts (Q48 full276: **20** interlock generated / **2** accepted).
Q49 (a) **reserves** a fraction of the budget for the density pass and (b) makes its per-part search
**efficient** (incremental tracker + multi-sweep + spacing-correct candidate) so a full sweep over
all 276 parts fits.

**Result (full276, 300 s): the density pass now acts on all 276 parts** — 18 sweeps, 1656 parts
processed, **497 density moves accepted (480 interlock)**, 109 991 interlock candidates generated —
a **240× jump in accepted interlock moves vs Q48 (2 → 480)**, with **no regression** (valid, 3
sheets). **Verdict: PASS.**

**Honest finding (the next lever is now cleanly isolated).** Despite 497 accepted moves, the layout
stays at **3 sheets / 54.415 % utilization (bit-identical to density-off)** — because utilization =
placed-part-area ÷ (used-sheet-count × sheet-area), which is invariant to *within-sheet* tightening;
only a **sheet-count drop** moves it. So single-part greedy density compaction, even running at full
scale, tightens within sheets but does not achieve the deep coordinated **3-curved-parts-per-sheet**
interlock the reference reaches. That is **coordinated multi-part LNS (SGH-Q50)** — Q49 is the
proven substrate that makes the density pass fast and budget-fed enough for it.

## 2. Implemented files

| File | Change |
| --- | --- |
| `optimizer/sparrow/bpp_reduction.rs` | T1 `density_budget_frac` + `reduction_deadline` cap (reduction loop stops at `total_budget·(1−frac)−guard`); T2 `density_samples`, spacing-correct candidate (`spacing_collision_base_shape`), incremental tracker in `density_compact_sheet`; T3 multi-sweep until convergence/deadline + final safety net; reduction/density time-split |
| `optimizer/sparrow/quantify/tracker.rs` | `prepare_item` made `pub(crate)` for the incremental per-move shape update |
| `io.rs` | `bpp_reduction_time_ms`, `bpp_density_time_ms`, `bpp_density_sweeps`, `bpp_density_parts_processed` |
| `tests/sparrow_density_compaction.rs` | + `density_multi_sweep_processes_all_parts` (parts_processed ≥ placed, ≥1 sweep, time-split populated) |
| `scripts/bench_sgh_q49_density_budget.py` (new) | A/B full276 harness capturing the Q49 diagnostics |

## 3. How it works

- **Budget reservation (T1).** `VRS_BPP_DENSITY_BUDGET_FRAC` (default 0.35, active only when density
  is on; off ⇒ 0.0 ⇒ reduction deadline unchanged). The reduction loop is capped at
  `total_budget·(1−frac) − guard`; `density_deadline = total_budget − guard` ⇒ the pass gets the
  reserved ≈ frac. Safe trade: on full276 the reduction reaches 3 sheets fast then wastes time on
  failed 2-sheet attempts, so capping it at 65 % still reaches 3 sheets.
- **Per-part efficiency (T2).** The Q48 per-part full `SparrowCollisionTracker::build` (O(N²)/sheet)
  is replaced by an **incremental** update: the tracker is built once; after each accepted move only
  `tracker.shapes[li]` is refreshed (all `build_sheet_session` reads). The candidate now uses the
  **spacing-collision** base shape (matching the obstacles + upstream LBF), so the clear-check is
  spacing-correct — fewer propose-then-revert moves. Sample budget is tunable
  (`VRS_BPP_DENSITY_SAMPLES`).
- **Multi-sweep (T3).** Sweeps repeat per sheet until convergence (no accepted move) or the
  deadline. A single final full-feasibility check reverts the whole pass if anything broke (instead
  of the Q48 per-move O(N) check).

## 4. Guardrails honoured

- CDE is the collision truth; continuous stays continuous; no NFP / bbox shortcut / clustering /
  per-sheet prediction; cavity in prepack.
- **Default OFF** — `VRS_BPP_DENSITY_COMPACT=0` ⇒ `frac=0` ⇒ pre-Q49 reduction deadlines, no density
  pass; additive IO; deterministic.

## 5. A/B benchmark (full276 LV8, 300 s/side)

`artifacts/benchmarks/sgh_q49/q49_summary.json`. margin 5 / spacing 8 / continuous, 6×1500×3000.

| metric | A — density ON (Q49) | B — density OFF | Q48 (starved) |
| --- | ---: | ---: | ---: |
| status / placed | ok / **276/276** | ok / 276/276 | ok / 276/276 |
| used sheets | **3** | 3 | 3 |
| utilization | 54.415 % | 54.415 % | 54.415 % |
| density sweeps | **18** | 0 | ~1 |
| parts processed | **1656** | 0 | few |
| **interlock accepted** | **480** | 0 | **2** |
| moves accepted | 497 | 0 | 2 |
| interlock generated | 109 991 | 0 | 20 |
| reduction / density time | 181 s / **78 s** | 276 s / 0 | starved |
| wall time | 272.8 s | 291.6 s | — |

Acceptance: `valid_a` ✓, `valid_b` ✓, `no_sheet_count_regression` ✓, `density_pass_ran` ✓,
`density_processed_all_276` ✓ (1656 ≥ 276) ⇒ **PASS**.

The 6×`Lv8_11612` fixture (density on) corroborates: 9 sweeps, 847 interlock generated, **7 accepted**
(Q48: 4) — the multi-sweep + spacing-correct candidate strengthen the pass everywhere.

## 6. Tests

- `tests/sparrow_density_compaction.rs` (3): pass runs + feasibility preserved; interlock candidates
  generated; **multi-sweep processes ≥ all parts + time-split populated**.
- Existing suites green: lib, `sparrow_finite_stock_multisheet` (16), `sparrow_shape_profile` (3),
  density (3). Default-off ⇒ no behaviour change.

## 7. Verdict & next lever

**PASS.** The density pass is no longer budget-starved: on full276 it processes all 276 parts and
accepts 480 interlock moves (240× Q48), with no regression. This **isolates the remaining gap
precisely**: single-part greedy density compaction, even at full scale, tightens within sheets but
does not drop a sheet — the reference's 3-curved-parts-per-sheet interlock needs **coordinated
multi-part motion (SGH-Q50: a multi-part LNS / swap-and-repair on the density objective)**. Q49 is
the fast, budget-fed substrate that makes that next step viable. No 2-sheet promise; the mechanism
and its budget are now proven.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-16T22:52:51+02:00 → 2026-06-16T22:55:16+02:00 (145s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q49_density_budget_allocation.verify.log`
- git: `sgh-q49-density-budget-allocation@edb6ae6`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |   9 ++
 .../src/optimizer/sparrow/bpp_reduction.rs         | 120 ++++++++++++++++-----
 .../src/optimizer/sparrow/quantify/tracker.rs      |   2 +-
 .../vrs_solver/tests/sparrow_density_compaction.rs |  22 ++++
 4 files changed, 124 insertions(+), 29 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/tests/sparrow_density_compaction.rs
?? artifacts/benchmarks/sgh_q49/
?? canvases/egyedi_solver/sgh_q49_density_budget_allocation.md
?? codex/codex_checklist/egyedi_solver/sgh_q49_density_budget_allocation.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q49_density_budget_allocation.yaml
?? codex/reports/egyedi_solver/sgh_q49_density_budget_allocation.md
?? codex/reports/egyedi_solver/sgh_q49_density_budget_allocation.verify.log
?? scripts/bench_sgh_q49_density_budget.py
```

<!-- AUTO_VERIFY_END -->
