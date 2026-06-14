# SGH-Q46 — Density gap diagnostic: VRS vs. nestandcut reference (full276 LV8)

**Diagnostic only.** No solver change. Goal: measure exactly where VRS loses packing density
versus a professional reference nesting of the *same* 276 parts, and produce a costed plan.

## 1. Reference (ground truth)

`samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf` + the two nested DXFs
(`2447207_SHEET_001/002_QTY_1.dxf`). Same 12 part types / 276 instances, same 3000×1500 sheet,
"all rotations allowed", 60 s optimisation. Engine: nestandcut.com (mature irregular nester).

| metric | reference | VRS BPP (Q45, 1200 s) |
| --- | ---: | ---: |
| sheets used | **2** (2nd partial → 365×1500 offcut) | 3 (full) |
| material used | 5.624 m × 1.5 = **8.44 m²** | 3 × 4.5 = **13.50 m²** |
| nesting efficiency | **73.1 %** (sheet1 76.1 %, sheet2 69.8 %) | **45.8 %** |
| big part `Lv8_11612_6db` per sheet | **3 + 3** | 2 + 2 + 2 |
| material vs reference | 1.0× | **1.60× (5.1 m² wasted)** |

The reference reaches the **area lower bound (2 sheets)**. Our earlier claim that "3 sheets is
geometrically optimal / 2 is impossible" (Q45 report §15) is **wrong** and is corrected here.

## 2. Smoking gun: interlocking of thin curved parts

`Lv8_11612_6db` has bounding box 2522×733 mm but a true surface of only **0.586 m² (≈32 % of its
bbox)** — it is a long, thin, **curved** part. The reference fits **3 per sheet** by interleaving
the curves so their bounding boxes overlap while the polygons stay collision-free:

```
Reference sheet 1, three big parts (bbox 2528×733 each), measured from the DXF:
  A∩B  bbox y-overlap = 178 mm   (x-overlap 2479 mm)
  A∩C  bbox y-overlap = 531 mm   (x-overlap 2066 mm)
  → bounding boxes OVERLAP, polygons are collision-free  ⇒  INTERLOCKING
```

Our BPP places the two big parts on a sheet ~2500 mm apart (bbox-separated: sheet 0 anchors
y=260 and y=2755) → only 2 fit. **6 big parts ÷ 2/sheet = 3 sheets minimum** in our layout, vs
**6 ÷ 3/sheet = 2 sheets** for the reference. This single effect explains the extra sheet.

## 3. Root causes (where density is lost)

1. **No interlocking search (primary).** The CDE collision backend is polygon-exact and *would*
   accept bbox-overlapping/clear placements, but the VRS Sparrow **search never explores them**:
   the LBF builder uses a **bbox-fit gate** and the separation search samples/rewards low-overlap
   feasible positions, not tightly-interleaved ones. Concave/thin parts are effectively treated
   as their bounding boxes ⇒ they cannot nest into each other's concavities.
2. **Feasibility, not density.** The separator (`separate`/`exploration_phase`) minimises overlap
   to reach a *collision-free* state and then stops; on fixed sheets there is no strip-shrink
   "compression" driving density, and there is **no real compaction/gravity** pass. Result: loose
   layouts with gaps everywhere (~46 % even though all parts are placed).
3. **Q45 reduction loosens further.** The reduction redistributes a sheet's items "wherever they
   fit" via the same loose search, and `compact_sheet` is too weak (uses the separation search,
   not a true bottom-left re-pack), so density drops from the old subset manager's ~54 % to ~46 %.

## 4. Fairness caveat

Reference uses **part gap 5 mm**; our run used **spacing 8 mm** (+ margin 5). The 3 mm tighter
gap helps the reference marginally, but cannot explain a 46→73 % gap. A spacing-5 control run is
part of M1 to isolate the algorithmic gap.

## 5. Costed development plan (with targets)

| milestone | work | expected outcome |
| --- | --- | --- |
| **M1 — Reference parity harness + density instrumentation** (small) | Load each reference DXF as a VRS layout (map polygons → part ids), run it through our **CDE final-validation tracker**; add per-sheet true-efficiency + per-part bbox-overlap metrics; re-run our solver at spacing 5 for a fair control. | **Proves the gap is in SEARCH, not collision** (expectation: our CDE accepts the interlocked reference layout as collision-free). Pins the problem precisely and gives a measurement baseline. |
| **M2 — Compaction / gravity post-pass** (medium) | True translational bottom-left compaction: per sheet, repeatedly slide each part toward a corner along collision-free directions (real LBF re-pack, not the separation search); fill low sheets first. | Lifts efficiency ~46 % → **~55–60 %**, edge-aligns big parts, tightens small-part clusters. Does **not** by itself reach 2 sheets (interlocking still missing). |
| **M3 — Interlocking-aware placement** (large, the hard part) | NFP-style (no-fit-polygon) placement or a density-rewarding search that samples bbox-overlapping, polygon-clear positions for concave parts; drive the big curved parts to 3/sheet. | Targets the **2-sheet / ~70 %** regime; this is where the real R&D is. |
| **M4 — Re-benchmark + reference comparison** | Full276 at spacing 5 and 8, part-position-level diff vs the reference DXF. | Quantified closure of the gap. |

**Recommended next step: M1** — it is cheap, and it definitively localises the failure (search vs
collision) before any solver investment. I do **not** promise quickly matching 73 % / 2 sheets;
M2 is a realistic near-term win, M3 is the substantial effort.

## 6. M1 results — search vs. collision (executed)

### M1.a Reference interlocking is real and collision-free (shapely on the DXF)
Per reference sheet, the 3 big parts (`Lv8_11612_6db`) are pairwise **collision-free**
(overlap area 0) at a measured min clearance of **4.2 mm (sheet 1) / 6.5 mm (sheet 2)**, while
their bounding boxes overlap by 178–531 mm. Interlocking confirmed numerically.

### M1.b Our solver, 6 big parts only, at the reference's 5 mm gap → still 2/sheet
Isolation experiment (`/tmp/q46_6big.json`: 6× `Lv8_11612_6db`, 3000-class sheet, **spacing 5**,
continuous rotation, our production BPP path):

```text
status ok, placed 6/6, used_sheets = 3, per-sheet big count = {0:2, 1:2, 2:2}
```

→ At the **same 5 mm spacing** as the reference, our solver fits only **2 big parts/sheet (3
sheets)**, where the geometry and the reference achieve **3/sheet (2 sheets)**. The 520-vertex
curved part is handled correctly by our CDE (valid `ok` output). **The failure is the search**,
not the collision engine and not the spacing.

### M1.c Why the collision engine is not the blocker
Our CDE broad-phase only prunes **AABB-separated** pairs (provably non-colliding); any
**AABB-overlapping** pair is sent to the exact polygon CDE. So bbox-overlapping/polygon-clear
(interlocked) placements are **accepted by construction** — the engine would validate the
reference arrangement; the search simply never proposes such placements.

### M1.d Spacing nuance
The reference's tightest big-part clearance (4.2 mm) is **below our 8 mm production spacing**, so
at spacing 8 we cannot even represent that interlocking. But M1.b shows that **even at spacing 5**
the search caps at 2/sheet — so spacing is a secondary factor; the dominant gap is the search.

### M1.e Spacing-5 full276 control — spacing contributes 0 % of the gap
Full276 at spacing 5 vs the Q45 run at spacing 8:

| run | sheets | big part/sheet | efficiency |
| --- | ---: | ---: | ---: |
| Q45 full276, spacing 8 | 3 | 2 | 45.8 % |
| control full276, spacing 5 | 3 | 2 | **45.8 %** |
| reference, spacing 5 | **2** | **3** | **73.1 %** |

Tightening the gap from 8 mm to 5 mm produced an **identical** layout (same 3 sheets, same 2
big/sheet, same 45.8 %). So spacing accounts for **0 %** of the 45.8→73.1 % gap — the entire
shortfall is the placement search.

### M1 conclusion
**The density gap is in the placement SEARCH, not in the collision engine or the spacing.** Our
CDE can represent and validate interlocked layouts; our search never discovers them. This pins the
investment for M2/M3 squarely on the placement/search layer.

## M2 — gravity / bottom-left compaction (implemented)

`gravity_compact_layout` in `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`: a
translational density post-pass run after the reduction loop. Per sheet, every part is slid
toward the bottom-left corner along collision-free directions (monotone descent + binary
contact refinement), iterating in sweeps until convergence. It reuses the existing CDE
candidate-session primitive (`build_sheet_session` + `LBFEvaluator::score_lbf_candidate`), so it
respects the exact same collision/spacing model as the solver. Pure translation (no rotation
change), **feasibility-preserving by construction** (a part only ever moves to a clear spot).
Toggle with `VRS_BPP_GRAVITY=0`. New diagnostics: `bpp_gravity_compaction_applied`,
`bpp_gravity_compaction_sweeps`, `bpp_gravity_moved_total_mm`.

### A/B evidence (gravity OFF vs ON)
- **24× 200×200 on one sheet:** placed-parts vertical extent **2684 → 2036 mm (−24 %)**, x-extent
  1275 → 1116 mm; 3 sweeps, 11.87 m total movement; still `ok`, 24/24.
- **6 big parts:** bottom rect-min pulled to the sheet edge — `y` per part **65/209/65/84/346 →
  5/21/5/5/61 mm** (i.e. onto the 5 mm margin line), directly fixing the "big parts float
  mid-sheet" complaint.
- All 15 multisheet tests pass with gravity on (feasibility preserved); new test
  `bpp_gravity_compaction_runs_and_preserves_feasibility`.

### Full276 effect — honest result
gravity-on vs the Q45 baseline (1200 s, same input), renders in
`artifacts/benchmarks/sgh_q46/renders/{baseline,m2gravity}_sheet*.png`:

| metric | baseline (no gravity) | M2 (gravity) |
| --- | ---: | ---: |
| sheets / status | 3 / ok | 3 / ok |
| per-sheet utilization | 50.2 / 50.1 / 47.9 % | **50.2 / 50.1 / 47.9 %** (unchanged) |
| sheet-2 used length (max anchor-y) | 2909 mm | **2692 mm** (~217 mm offcut freed) |
| big parts pulled to edge (rect-min y) | 19–41 mm | **1–5 mm** |
| gravity sweeps / movement | – | 4 / 60.3 m |

**The efficiency metric does NOT move (still 45.8 %), and the sheet count stays 3** — because
gravity is within-sheet and all parts remain on 3 sheets; utilization on a counted sheet is fixed
by sheet count, not packing tightness. **My earlier "~55–60 %" estimate for M2 was wrong.**

What M2 *does* deliver, visible in the renders: big parts edge-aligned (onto the 5 mm margin line),
parts pulled cornerward, and ~200 mm of clean recoverable offcut freed at the top of the
least-full sheet. But the dominant waste — the snaking empty channel between the two
**un-interlocked** big parts — is untouched, because eliminating it requires nesting the big parts
together (**M3 / interlocking**), which gravity cannot do.

**Conclusion:** M2 is a real but modest layout-quality + offcut-recovery improvement (and useful
infrastructure for M3), **not** an efficiency or sheet-count mover. The headline win remains M3.

**Scope note:** gravity is within-sheet only; it does not move parts across sheets (no sheet-count
reduction, no small-part rebalancing onto lower sheets).

## 7. Files referenced

- `samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf`
- `samples/real_work_dxf/0014-01H/lv8jav/Nested/2447207_2026_05_11.zip` → `*_SHEET_001/002_QTY_1.dxf`
- `artifacts/benchmarks/sgh_q45/outputs/q45_full276_bpp_6x1500x3000_margin5_spacing8_continuous_1200_output.json`
