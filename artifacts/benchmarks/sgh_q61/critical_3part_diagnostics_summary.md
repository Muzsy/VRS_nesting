# SGH-Q61 — focused 3-critical diagnostics summary

REAL solver path (`vrs_solver::adapter::solve`), 3 × Lv8_11612_6db, 1500×3000, continuous rotation.

## Scenario A — spacing = 0
- Builder path (VRS_SHEET_BUILDER): placed 3, max/sheet **3**, sheets 1 → 3-on-one-sheet = **true** (FEASIBLE).
- Skeleton + all Q56–Q60 modules: placed 3, max/sheet 3.

## Scenario B — real spacing = 8 (margin 5)
- Skeleton + all modules: placed 3, max/sheet **2**, best valid partial = 2.

## Module consumption (skeleton + all gates, spacing 0)
| module | consumed | candidates generated | accepted |
| --- | --- | --- | --- |
| Q56C anchor catalog | true | 48 | 0 |
| Q57B pair/interlock | true | 32 | 1 |
| Q59 band slot-edge | true | 24 | 0 |
| Q60 simultaneous (parts moved) | true | attempts=2 | moved=true |
| Q58B best-partial tracker | true | max_critical=2 | downgrades_rejected=1 |

pair_rejection_summary (sp0): (none)

## Honest conclusion
3 large LV8 parts ARE geometrically feasible on one sheet (builder path places 3/3 at spacing 0).
The skeleton + Q56–Q60 module path consumes the modules but currently reaches 2 critical/sheet
at real spacing → **PARTIAL_FAIL_ALGORITHMIC_GAP** (best valid partial = 2; no infeasibility claim).
The gap is the co-movable / SA separation not converging to the tight 3-way interlock from the
module-generated seeds at real spacing — an implementation gap, not geometry.
