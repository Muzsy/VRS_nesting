# SGH-Q34 Report

## Scope

SGH-Q34 makes the `TechnologyClearancePolicy` sheet margin (Q33) *actually constrain*
the solver. The `margin_mm` / `effective_sheet_margin_mm()` value now shrinks the usable
sheet boundary in the `sparrow_cde_multisheet` pipeline — **rectangular stocks only**.

If `margin_mm = 10.0`, the solver may not place any part closer than 10 mm to the outer
edge of the sheet. Placement output coordinates remain in original sheet coordinates.

This task is intentionally narrow:
- only sheet boundary margin;
- only rectangular stock;
- only `sparrow_cde_multisheet`;
- no part-part spacing, no kerf-expanded geometry, no polygon offset, no cavity prepack.

## Existing code audit

Q33 left the policy diagnostic-only:
- `SolverInput` had `margin_mm`, `spacing_mm`, `kerf_mm`.
- `TechnologyClearancePolicy::effective_sheet_margin_mm()` existed.
- `sparrow_cde_multisheet` diagnostics emitted `technology_margin_mm`, `technology_effective_sheet_margin_mm`, etc.
- But the solver still used the *original* sheet contour — margin did not change geometry.

The finite-stock manager (`run_finite_stock_multisheet`) internally expanded stocks via
`expand_sheets(stocks)` and ran the Sparrow core on those sheets directly.

## Why Q34 only applies sheet margin

`margin_mm` is the only one of the three technology fields with a well-defined,
geometry-free meaning at sheet level: an inset of the placement region. Part-part spacing
and kerf require polygon offsetting / inter-part distance enforcement, which is out of scope
here and reserved for later tasks. Q34 therefore keeps `spacing_mm` and `kerf_mm`
diagnostic-only and applies only the sheet boundary inset.

## Files changed

| File | Change |
|---|---|
| `rust/vrs_solver/src/sheet.rs` | Added `apply_rectangular_sheet_margin` and `count_sheet_margin_violations` |
| `rust/vrs_solver/src/io.rs` | 5 new `technology_margin_*` / `technology_sheet_margin_applied` diagnostics fields |
| `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs` | `FiniteStockRunConfig.solver_sheets_override`; core attempt uses shrunk sheets when set |
| `rust/vrs_solver/src/adapter.rs` | Build margin-shrunk solver sheets; run final validator; populate new diagnostics |
| `rust/vrs_solver/tests/technology_sheet_margin.rs` | 10 new tests |
| `scripts/smoke_sgh_q34_sheet_margin_enforcement.py` | 31-check smoke |
| `artifacts/benchmarks/sgh_q34/` | synthetic inputs + outputs |

## Sheet margin implementation

`apply_rectangular_sheet_margin(sheets, margin_mm) -> Result<Vec<SheetShape>, String>`:

- `margin_mm == 0.0` → clone of input (no-op).
- `margin_mm < 0.0` → `Err`.
- `has_irregular_outer == true` && `margin_mm > 0.0` → `Err(UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34)`.
- `2 * margin_mm >= width` or `>= height` (i.e. usable w/h ≤ 0) → `Err(MARGIN_EXCEEDS_SHEET_DIMENSIONS)`.

**Chosen unusable-sheet policy:** *error* if any sheet becomes unusable from the margin
(per the task's recommended simplicity). Per-sheet skip is left for a later refinement.

The shrunk sheet:
```
min_x += m;  min_y += m;  max_x -= m;  max_y -= m
width  = max_x - min_x;   height = max_y - min_y;   area = width * height
has_irregular_outer = false;  outer_vertices = Vec::new()
cost_per_use = original.cost_per_use
_outer_poly  = rebuilt SPolygon of the inset rectangle
```

## Multisheet integration

`FiniteStockRunConfig` gained `solver_sheets_override: Option<Vec<SheetShape>>`. When set,
`run_finite_stock_multisheet` builds each subset's sheets from the override (shrunk) while
`compute_utilization` still reports areas from the original physical sheets.

In `adapter.rs::run_sparrow_finite_stock_multisheet_pipeline`:
1. `margin_mm = technology_policy.effective_sheet_margin_mm()`.
2. If `margin_mm > 0`: `apply_rectangular_sheet_margin(original_sheets, margin_mm)` → `solver_sheets_override`.
   On error, the run returns immediately with all instances unplaced carrying the error reason.
3. The manager runs the Sparrow core on the shrunk sheets; placement `sheet_index` stays the
   original expanded index, and coordinates stay in original sheet space (the shrunk sheet shares
   the same coordinate origin, only its bounds are inset).
4. Physical `used_sheet_area` is unchanged (original sheets); the new usable-area diagnostic
   reports the shrunk area.

## Final margin validator

`count_sheet_margin_violations(placements, parts, original_sheets, margin_mm) -> usize`
re-checks every placement's *rotated bounding box* (rotation-aware, not anchor-only) against
the margin-inset rectangle of the original sheet. Works for rectangle parts and
`outer_points` rect parts; rotation is applied via `rotated_bbox_min_offset_f64` /
`dims_for_rotation_f64`.

If `margin_violation_count > 0` and the run reported `ok`, the adapter downgrades the status
to `partial` and clears `best_full_solution_found` (safety net — the solver runs on the shrunk
sheet so this should not trigger in practice). A valid `ok` output always has
`technology_margin_violation_count == 0`.

## Diagnostics fields

Added to `OptimizerDiagnosticsOutput` (all optional, skip-if-none):

- `technology_sheet_margin_applied` — true when `effective_sheet_margin_mm() > 0`.
- `technology_margin_applied_sheet_count` — number of expanded sheets shrunk.
- `technology_margin_usable_sheet_area` — Σ shrunk usable area of used sheets.
- `technology_margin_physical_used_sheet_area` — Σ original physical area of used sheets.
- `technology_margin_violation_count` — final-validator violations (0 for valid output).

## Synthetic tests

`rust/vrs_solver/tests/technology_sheet_margin.rs` — 10 tests:

| Test | Asserts |
|---|---|
| `rect_sheet_shrink_100x100_margin_10` | inset 10..90, 80×80, area 6400 |
| `margin_zero_is_noop_clone` | margin 0 = unchanged clone |
| `negative_margin_errors` | negative margin → Err |
| `margin_too_large_errors` | margin 50 / 100×100 → MARGIN_EXCEEDS_SHEET_DIMENSIONS |
| `irregular_stock_with_margin_errors` | irregular + margin → UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34 |
| `irregular_stock_with_zero_margin_ok` | irregular + margin 0 → no-op clone |
| `solver_placement_respects_margin` | full run: ok, pairs=0, all placements inside [10,90] |
| `part_too_big_with_margin_not_ok` | 95×95 + margin 10 → not ok, 0 placed, 1 unplaced |
| `no_margin_backwards_compatible` | no margin → ok, `technology_sheet_margin_applied == false` |
| `explicit_zero_margin_backwards_compatible` | margin 0 → applied == false |

All 10 PASS.

## Smoke results

`scripts/smoke_sgh_q34_sheet_margin_enforcement.py` — 31/31 PASS.

- `sheet_margin_ok.json`: status=ok, placed=2, unplaced=0, violation_count=0, usable=6400,
  physical=10000, all placements within [10,90].
- `sheet_margin_too_large.json`: status=partial, placed=0, unplaced=1, explicit reason
  (`PART_NEVER_FITS_STOCK` — the 95×95 part does not fit the 80×80 inset sheet).

## Q32 regression check

`python3 scripts/smoke_sgh_q32_finite_stock_multisheet.py` → **PASS=89 FAIL=0**.

Confirms the Q32 pipeline, artifacts, Q31 base-shape cache fields, score/utilization, and the
no-compression / no-legacy guards are intact.

## Non-goals

- No part-part spacing enforcement.
- No kerf-expanded geometry.
- No polygon offset.
- No cavity prepack.
- No lead-in/out handling.

`spacing_mm` and `kerf_mm` remain diagnostic-only. In Q34 `margin_mm` is **only** a sheet
boundary margin — it does not imply part-part spacing, kerf compensation, part polygon offset,
or reserved lead-in area.

## Final verdict

**PASS.** All acceptance criteria met:

- `margin_mm` shrinks the solver sheet boundary in `sparrow_cde_multisheet`.
- Every margin synthetic placement's full rotated bbox lies inside the margin-inset sheet.
- `technology_margin_violation_count` diagnostic exists and is 0 for valid output.
- Too-large margin / too-large part does not yield a false `ok`.
- `spacing_mm` and `kerf_mm` remain diagnostic-only; no spacing/kerf offset introduced.
- Q33 policy, Q32 multisheet smoke, and Q31 base-shape cache unaffected.
- No compression / legacy regression.
- build / lib (455) / Q33 (9) / Q34 (10) / smoke (Q34 31, Q33 43, Q32 89) / check.sh / verify.sh all PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-11T11:33:58+02:00 → 2026-06-11T11:36:20+02:00 (142s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q34_sheet_margin_enforcement.verify.log`
- git: `main@02b1654`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 .claude/settings.local.json                        |   8 +-
 .../outputs/technology_policy_smoke_output.json    |  25 +++--
 rust/vrs_solver/src/adapter.rs                     |  94 +++++++++++++++-
 rust/vrs_solver/src/io.rs                          |  17 +++
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |  14 ++-
 rust/vrs_solver/src/sheet.rs                       | 123 +++++++++++++++++++++
 6 files changed, 267 insertions(+), 14 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .claude/settings.local.json
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/sheet.rs
?? artifacts/benchmarks/sgh_q34/
?? codex/reports/egyedi_solver/sgh_q34_sheet_margin_enforcement.md
?? codex/reports/egyedi_solver/sgh_q34_sheet_margin_enforcement.verify.log
?? rust/vrs_solver/tests/technology_sheet_margin.rs
?? scripts/smoke_sgh_q34_sheet_margin_enforcement.py
```

<!-- AUTO_VERIFY_END -->
