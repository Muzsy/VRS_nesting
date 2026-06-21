# SGH-Q55B-FIX — One-part true-extreme sheet-edge placement (real candidate path)

**Status: PASS — accepted `true_extreme_sheet_edge_alignment` placement, numerically + visually verified.**

The fix lives in the real solver candidate path
([feature_candidate_generator.rs](../../../rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs)),
not a standalone module. A one-part runner drives the production generator
`generate_feature_candidate_seeds_for_sheet` and proves an accepted placement of the real critical
LV8 part on a real sheet, with the physical contour on the configured margin line.

## What was wrong before & what changed

| # | Defect in the old path | Fix |
|---|---|---|
| 1 | `push_sheet_edge_anchors` / `sheet_edge_candidates` anchored from `feature_base_shape` (non-offset). | Now anchors from `collision_base_shape` (the **spacing-offset** contour) — the solver's boundary/clearance truth. |
| 2 | `finalize_seeds` validated the non-offset frame against the sheet. | Sheet-edge seeds are now validated against the **offset** frame (the real boundary truth). |
| 3 | Edge→sheet-edge mapping was inverted and anchored off the edge **midpoint** → the bbox fell off-sheet and `finalize_seeds` rejected it. | A near-horizontal edge seats against bottom/top, a near-vertical edge against left/right, with the **orthogonal axis centred** so it fits whenever it fits at all. `nearest_axis_angle_deg` fixes the near-270° misclassification. |
| 4 | A not-clear first sample hard-rejected with `seed_not_clear`. | `refine_one_feature_candidate` now runs a **bounded repair** for sheet-edge candidates (inward offsets from the margin, slides along the edge, continuous rotation wiggle) before any rejection (`bounded_sheet_edge_repair`). |
| 5 | Only axis-edge alignment rotations were generated (looked like 90/270 snaps). | Added genuine **continuous min-perpendicular-width** rotations from the real offset contour (`min_width_rotations`, 0.5° scan + 0.01° refine) — fractional angles (e.g. 92.75°). |
| 6 | No one-part verification / no visual. | `verify_one_part_sheet_edge_placement` (pub) + integration test + JSON + SVG/PNG. |

In the *production* multisheet wiring spacing is baked into the part geometry (`spacing_mm = 0` inside
the solver), so `feature_base_shape == collision_base_shape` and fixes #1/#2 are **no-ops there** — that
is why the defect was invisible in production and why the full suite shows **no regression**. The
verification routes the real spacing (8) / margin (5) through the solver's *internal* dual-geometry
mechanism (`spacing_mm = 8`) so the two contours are distinct and the fix is demonstrable.

## Margin model (verified + logged)

`adapter.rs` pre-shrinks each rectangular sheet by `inset = margin − spacing/2`. The runner reproduces
and **logs** this:

```
raw sheet 1500x3000 pre-shrunk by inset = margin − half_spacing = 5 − 4 = 1 mm on every side
(solver sheet [1.000,1499.000]x[1.000,2999.000]). Aligning the spacing-offset contour flush to the
shrunk edge places the physical contour at exactly margin = 5 mm from the raw edge.
```

So the placement is based on the **offset contour extrema** (per the spec), aligned to the
margin-shrunk sheet edge, which lands the **physical** contour at exactly `margin` from the raw edge.

## Final report (the 15 required items)

1. **Commit hash** — `1c99f7b69d212d0ce2a609e7064f283df1e891e6` (`1c99f7b`), pushed to `main`
   (`129aa61..1c99f7b`). Files: `feature_candidate_generator.rs` (modified),
   `tests/sparrow_one_part_sheet_edge.rs` (new), `artifacts/benchmarks/sgh_q55b/` (new), this report.
2. **Command** —
   `cargo test --release --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge -- --nocapture`
   (env: `RUSTUP_HOME=$HOME/.local/rustup CARGO_HOME=$HOME/.local/rust/cargo`, toolchain bin on PATH).
3. **JSON diagnostics** — [artifacts/benchmarks/sgh_q55b/one_part_sheet_edge.json](../../../artifacts/benchmarks/sgh_q55b/one_part_sheet_edge.json)
   (all 8 candidates, full diagnostics) + `one_part_sheet_edge_accepted.json` (accepted summary + contours).
4. **Visual artifact** — [one_part_sheet_edge.svg](../../../artifacts/benchmarks/sgh_q55b/one_part_sheet_edge.svg)
   / `.png`; fractional proof: `one_part_sheet_edge_minwidth_proof.svg` / `.png`.
5. **Selected part** — `Lv8_11612_6db` (real LV8 critical large part, 520-point outer contour, w 2521.99 × h 732.8).
6. **Selected real contour edge index** — `257` (the 684.8 mm dominant edge).
7. **Selected edge angle** — `0.000°` (the part is authored axis-aligned; its longest straight edge is horizontal).
8. **Target sheet edge** — `left`.
9. **Computed continuous rotation** — `90.0000°` = `target_axis(90.000) − selected_edge_angle(0.000)`.
   This is the **mathematically exact continuous result** (not a snap): the dominant edge is genuinely
   at 0.000°, so flushing it to the vertical sheet axis is exactly 90°. `resolve_seed_rotation` applies
   **no** snapping for continuous parts. Proof of continuity below (item 14 / §Continuous-rotation proof).
10. **True spacing-offset extrema before translation** (offset frame at origin, rot 90°):
    `min_x = −736.80, min_y = −4.00`, span ≈ 740.8 × 2530.0 mm.
11. **Margin-aware translation** — anchor (= translation, rotation about origin then translate):
    `tx = 737.82, ty = 10.42`. Built as `anchor = rect_min − offset_frame.min` so the offset contour
    seats flush to the shrunk edge: `offset_min_x = anchor_x + offset_frame_min_x = 1.02 ≈ shrunk.min_x (1.0)`.
12. **Final margin error** — physical `final_true_min_x = 5.02`; `expected_margin_line = 5.0`;
    `actual_distance_to_margin_line = 5.02`; **`margin_error_mm = 0.0200 ≤ 0.05`** ✓
    (the 0.02 is the refine coordinate-descent residual carried through from the real post-refine seed).
13. **Boundary / collision** — `boundary_clear = true` (CDE `SparrowStrict`, offset contour strictly
    within the shrunk sheet), `collision_pairs = 0` (single part). `repair_attempts = 0` for the headline.
14. **Visual inspected** — yes. Both PNGs were rendered (cairosvg) and visually checked: the real LV8
    contour stands vertically, its left extremum flush on the green margin line, inside the red raw edge;
    the dashed offset contour sits just outside the filled physical contour. The 92.75° proof image is
    visibly **tilted ~2.75°** vs. the 90° image — confirming a genuine fractional rotation.
15. **First-run corrections** — (a) the edge→sheet-edge mapping was inverted and anchored off the edge
    midpoint (off-sheet rejects) → centred orthogonal axis + corrected mapping + `nearest_axis_angle_deg`;
    (b) the headline kept landing on 90/270 only → added `min_width_rotations` to the real path so the
    same generator yields fractional 92.75° placements, and added a `continuous_proof_index` to surface it.

## Accepted placement (headline)

```
candidate_source = true_extreme_sheet_edge_alignment
part = Lv8_11612_6db   target_sheet_edge = left
selected_edge_index = 257   selected_edge_angle_deg = 0.000   target_axis_angle_deg = 90.000
computed_rotation_deg = 90.0000   continuous_rotation = true
spacing_mm = 8   margin_mm = 5   half_spacing = 4   sheet_inset = 1
offset_frame (origin)  min_x=-736.80 min_y=-4.00
translation_x = 737.82  translation_y = 10.42
offset_contour_true  x[1.02, 741.82]  y[6.42, 2536.42]   (within shrunk sheet [1,1499]x[1,2999])
final_true (physical) x[5.02, 737.82]  y[10.42, 2532.42]
expected_margin_line = 5.0  actual = 5.02  margin_error_mm = 0.0200
boundary_clear = true  collision_pairs = 0  accepted = true
placed_count = 1  unplaced_count = 0
```

## Continuous-rotation proof (refutes any "fixed 90/270 workaround")

The SAME generator/path produced a genuine **fractional** valid placement at the
min-perpendicular-width orientation (the reference packs `Lv8_11612` at ~92°, not 90°):

```
target_sheet_edge = left   computed_rotation_deg = 92.7500   continuous = true   fractional = true
valid_placement = true  boundary_clear = true  collision_pairs = 0
short_axis_extent = 740.55 mm  (< 740.80 mm at 90° — the true min-width orientation)
margin_error_mm = 0.151  (physical extremum 0.15 mm INSIDE the margin — margin-respecting, conservative)
```

`continuous_rotation_proven = true`. It is not the *headline* only because the strict
`margin_error ≤ 0.05` gate is met exactly only by the flush 90° orientation (a tilted vertex contact
projects the offset-to-physical gap slightly off `half_spacing`, leaving the physical extremum 0.15 mm
inside the margin — safe, but not margin-exact). Both the 90° and the 92.75° placements are exercised
through the real candidate path and validated by the CDE.

## Verification

- `cargo test --release … --test sparrow_one_part_sheet_edge` → **1 passed**.
- Full suite: **500 lib unit tests + all integration tests green, 0 failed** → no regression on the
  default/production path.
