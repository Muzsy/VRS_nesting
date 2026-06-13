# SGH-Q40 Report — Unified single-geometry margin/spacing model

## Scope

Refactor technology clearance (sheet **margin** + part **spacing**) out of the solver's inner
logic into two geometry transforms applied *around* a plain nester:

- **spacing** → offset every part contour OUTWARD by `spacing/2` (one geometry; the solver
  treats the offset shapes as the parts and allows them to touch);
- **margin** → offset every solver sheet by the SIGNED inset `margin − spacing/2`
  (positive shrinks inward, negative grows outward).

The inner Sparrow/CDE core then runs with spacing disabled (`spacing_mm = 0`) and on the
offset sheets — no per-iteration spacing computation. Output placements record anchor +
rotation only, so swapping the offset parts back to the original parts is exact (the offset
preserves the local origin). No cavity prepack, kerf geometry, compression, legacy fallback,
or UI/API changes.

## Why: the dual-geometry mechanism was the packing culprit

Q36–Q39 used a *dual-geometry* spacing mechanism: the solver carried BOTH the original
contour (boundary) and a half-spacing-expanded contour (part-part collision) per instance and
quantified pairs on the expanded geometry inside the search loop. The Q39 full-LV8 benchmark
showed an unexplained spacing loss (e.g. full276 2-sheet `S2` placed 237/276 at `spacing = 2`).

A 3-way control isolated the cause: nesting the **already-offset shapes directly** packed
**257**, while the **dual-geometry mechanism** packed only **146** on the same instance — i.e.
the loss came from the *mechanism*, not from the 2 mm of geometry. The user's hypothesis ("2 mm
spacing cannot justify the dropped parts") was correct. The unified model replaces the
mechanism with the direct-offset approach.

## Corrected sheet-offset formula

The user's first formulation inset the sheet by `margin − spacing`; the geometrically correct
inset is **`margin − spacing/2`**. A part offset outward by `spacing/2` whose outer edge sits on
a sheet inset by `margin − spacing/2` places the ORIGINAL contour exactly `margin` from the
physical edge:

```
original_edge = inset_edge + spacing/2 = (margin − spacing/2) + spacing/2 = margin   ✓
```

When `spacing/2 > margin` the inset is negative and the solver sheet GROWS outward
(symmetrically, preserving the coordinate origin), so a single part may legitimately sit past
the solver-sheet edge while its original contour still respects the (smaller) margin.

## Implementation

- `rust/vrs_solver/src/sheet.rs` — `apply_rectangular_sheet_offset(sheets, inset_mm)`: signed
  rectangular offset. `inset == 0` → byte-identical clone; irregular outer + non-zero →
  `UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34`; collapsing shrink → `SHEET_OFFSET_COLLAPSES_SHEET_Q40`;
  non-finite → error. The Q34 `apply_rectangular_sheet_margin` is retained but no longer wired
  into the pipeline.
- `rust/vrs_solver/src/adapter.rs`
  - `build_offset_parts(parts, part_offset)`: offsets each part template's outer contour
    outward by `spacing/2` via the Q38 straight-skeleton offset (`build_spacing_expanded_outer_polygon`),
    preserving the local origin and updating `outer_points`/`prepared_outer_points`/`width`/`height`.
    Parts whose offset cannot be built are excluded; their instances become
    `UNSUPPORTED_SPACING_OFFSET_Q36` unplaced. Returns an `OffsetBuildMetrics` inventory
    (build ms, part count, vertex totals, area ratios) for the Q37 diagnostics.
  - Pipeline rewiring: compute `part_offset = spacing/2`, `sheet_inset = margin − part_offset`;
    nest `offset_parts` on `apply_rectangular_sheet_offset(sheets, sheet_inset)` with the inner
    config's `spacing_mm = 0`. Diagnostics (`technology_spacing_offset_*`) are now sourced from
    the adapter-level preprocessing instead of the (now-inactive) inner core.
  - **Q35 validator disabled by default.** The O(n²) part-spacing re-validation (37–70 s on
    full LV8) is redundant — the offset geometry guarantees spacing — and is gated behind
    `SGH_Q35_SPACING_VALIDATOR=1` for audit only. The Q34 margin validator
    (`find_sheet_margin_violations`) still runs on the PHYSICAL sheet with the full margin as a
    safety net that demotes any violating placement out of `ok`.
  - `technology_margin_usable_sheet_area` now reports the TRUE `margin`-shrunk area (independent
    of the spacing-adjusted solver sheet); equal to the prior value when `spacing = 0`.

## Determinism

`spacing = 0 && margin = 0` is a structural no-op: `part_offset = 0` makes `build_offset_parts`
clone the parts; `sheet_inset = 0` makes `apply_rectangular_sheet_offset` a clone and leaves
`solver_sheets_override = None`; the inner config already received `spacing_mm = 0` in the
baseline. The solver therefore sees identical parts/sheets/seed and produces identical
placements. Unit-covered by `sheet_offset_zero_is_noop_clone`.

## Verification

Short 3-way re-run on full276 2-sheet at a 90 s cap (mid-search snapshots; not the production
time limit), seed 42:

| run | margin | spacing | placed | offset_mm | offset_parts | offset_fail | final_pairs | boundary | margin_viol | spacing_validator_ms |
|-----|-------:|--------:|-------:|----------:|-------------:|------------:|------------:|---------:|------------:|---------------------:|
| baseline          | 0 | 0 | 167 | 0.0 | 0  | 0 | 0 | 0 | 0 | ~0 |
| spacing2          | 0 | 2 | 169 | 1.0 | 12 | 0 | 0 | 0 | 0 | ~0.002 |
| margin5_spacing2  | 5 | 2 | 174 | 1.0 | 12 | 0 | 0 | 0 | 0 | ~0.001 |

- Spacing now **tracks the baseline** (169 vs 167) instead of collapsing to 146 — the
  dual-geometry packing loss is eliminated.
- `offset_mm = spacing/2 = 1.0`; kerf is never folded in. `area_ratio_avg ≈ 1.058`
  (offset parts ~5.8 % larger), `offset_build_ms ≈ 235` (one-time preprocessing).
- The Q35 validator overhead is **gone** (`spacing_final_validator_ms ≈ 0`). The Q34 margin
  validator still runs when `margin > 0` (`margin_final_validator_ms ≈ 264` on the margin run).

## Tests & smokes

- `cargo test --release` (vrs_solver): **541 passed, 0 failed**. Added 6 `apply_rectangular_sheet_offset`
  unit tests (shrink / grow+origin / zero-clone / collapse / irregular / non-finite). Fixed a
  pre-existing non-compiling test (`sparrow_single_sheet_validation.rs` predated the Q33
  `spacing_mm`/`kerf_mm` fields) so the full suite compiles again.
- Smokes: **Q33 43/0, Q34 42/0, Q35 33/0, Q36 50/0** all PASS. Q34 smoke updated to assert the
  unified-model sheet transform (`apply_rectangular_sheet_offset` + retained
  `find_sheet_margin_violations`) instead of the old standalone margin shrink.

## Interpretation

Both technology constraints are now pure geometry transforms around an unmodified nester. This
(a) removes the dual-geometry packing penalty, (b) removes the dominant added wall-time (the
O(n²) validator), and (c) keeps margin/spacing/kerf independent with an exact original-geometry
swap-back. The inner solver's legacy dual-geometry spacing code remains in the source but is
inactive (`spacing_mm = 0`); it costs no runtime and is left for a separate cleanup task to
avoid regression risk in this change.

## Recommended next task

Re-run the full LV8 production benchmark (Q39 matrix) under the unified model to refresh the
now-obsolete spacing-loss numbers (S0–S5) and renders, then schedule removal of the dead
inner-solver dual-geometry spacing path (tracker/search/lbf `spacing_collision_base_shape`).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-13T15:21:28+02:00 → 2026-06-13T15:25:07+02:00 (219s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q40_unified_margin_spacing_model.verify.log`
- git: `main@cec9d07`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 .../outputs/technology_policy_smoke_output.json    |  32 +--
 .../sgh_q34/outputs/sheet_margin_ok_output.json    |   8 +-
 .../outputs/sheet_margin_too_large_output.json     |   8 +-
 .../sgh_q35/outputs/part_spacing_ok_output.json    |  28 +--
 .../outputs/part_spacing_violation_output.json     |  38 ++--
 .../outputs/spacing_geometry_touch_ok_output.json  |  38 ++--
 .../outputs/spacing_not_sheet_margin_output.json   |  28 +--
 .../outputs/spacing_violation_safety_output.json   | 104 ++++-----
 rust/vrs_solver/src/adapter.rs                     | 246 ++++++++++++++++-----
 rust/vrs_solver/src/sheet.rs                       |  62 ++++++
 .../tests/sparrow_single_sheet_validation.rs       |   2 +
 rust/vrs_solver/tests/technology_sheet_margin.rs   |  75 ++++++-
 scripts/smoke_sgh_q34_sheet_margin_enforcement.py  |  10 +-
 13 files changed, 477 insertions(+), 202 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_ok_output.json
 M artifacts/benchmarks/sgh_q34/outputs/sheet_margin_too_large_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_ok_output.json
 M artifacts/benchmarks/sgh_q35/outputs/part_spacing_violation_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_geometry_touch_ok_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_not_sheet_margin_output.json
 M artifacts/benchmarks/sgh_q36/outputs/spacing_violation_safety_output.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/sheet.rs
 M rust/vrs_solver/tests/sparrow_single_sheet_validation.rs
 M rust/vrs_solver/tests/technology_sheet_margin.rs
 M scripts/smoke_sgh_q34_sheet_margin_enforcement.py
?? codex/reports/egyedi_solver/sgh_q40_unified_margin_spacing_model.md
?? codex/reports/egyedi_solver/sgh_q40_unified_margin_spacing_model.verify.log
```

<!-- AUTO_VERIFY_END -->
