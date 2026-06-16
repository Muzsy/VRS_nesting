# SGH-Q48 — Interlocking-aware density compaction

## 1. Executive summary

SGH-Q48 builds the density lever that SGH-Q47 proved is missing (Q47 A==B: ordering+budget are
outcome-neutral; the gap is in the placement *search*). It adds an **interlock-aware density
compaction** pass that re-places parts to the densest **collision-free** position — tucking parts
into concavities / interlocking — steered by a new **density objective** and **contour-aware
sampling**, with the CDE remaining the sole collision truth. Opt-in (`VRS_BPP_DENSITY_COMPACT=1`),
default off.

**This is the first mechanism in the programme that actually generates and keeps interlocked
(bbox-overlapping, polygon-clear) placements** — unlike Q47's outcome-neutral ordering/budget.
On the focused 6×`Lv8_11612` fixture it generates **189** interlock candidates and accepts **4**
interlock moves; on full276 (budget-starved, see §6) it still generates **20** / accepts **2**.

**Honest framing (unchanged from the plan).** Reaching 2 sheets is a stretch goal, not a promise.
Q48 delivers a *working, proven* interlock mechanism + decision-diagnostics with **no regression**;
the clear next lever is **budget allocation** (let the pass run at scale — §6, §8).

**Verdict: PASS** — valid, regression-free, the pass runs, and interlock generation is proven.

## 2. Implemented files

| File | Change |
| --- | --- |
| `optimizer/sparrow/density.rs` (new) | `density_candidate_score` (added-extent + attraction; lower = denser), `DensityWeights`, `DensityEvaluator`, `is_interlock_candidate`/`bbox_overlaps`, `contour_near_rect_mins` (T3 NFP-free contour sampling); 4 unit tests |
| `optimizer/sparrow/mod.rs` | `pub mod density;` |
| `optimizer/sparrow/bpp_reduction.rs` | `density_place_part` (per-part density search over uniform + contour candidates × rotation set, CDE-clear-checked, interlock-counted), `density_compact_sheet`, `density_compact_layout` (gated, wired before gravity) |
| `io.rs` | `bpp_density_compaction_applied`, `bpp_density_moves_accepted`, `bpp_interlock_candidates_generated/accepted` |
| `optimizer/sparrow/fixed_sheet.rs` | T5: `fitting_rotation` gives continuous parts a **continuous** min-width seed (fine scan, no discrete snapping) |
| `tests/sparrow_density_compaction.rs` (new) | 2 integration tests (pass runs + feasibility preserved; interlock candidates generated) |
| `scripts/bench_sgh_q48_density_compaction.py` (new) | A/B (`VRS_BPP_DENSITY_COMPACT=0|1`) full276 regression harness |

## 3. How it works

- **Density objective** (`density.rs`): `w_extent · added_used_extent − w_contact · proximity`,
  minimised. A part placed into a concavity grows the sheet's used bounding extent ~0 and sits
  close to its neighbour ⇒ low score. Smooth ⇒ coord-descent-able; collision decided by the CDE.
- **Contour-aware sampling** (T3): besides uniform random samples, candidates are drawn abutting
  each placed neighbour's vertices — the interlock positions a uniform sampler misses. **NFP-free**
  (sampling *near* a contour ≠ computing a no-fit polygon).
- **Compaction pass** (T4): per sheet, in Q47-priority order, lift each part and re-place it at the
  lowest-density clear position (translation + the part's rotation set; continuous parts keep
  continuous rotation). Accept only if collision-free **and** density improves; full-feasibility
  safety net reverts any bad move. Replaces the y-only `compact_sheet` gravity gate as the density
  driver.

## 4. Guardrails honoured

- **CDE is the collision truth** — the density score only ranks already-clear candidates.
- **Continuous stays continuous** — the rotation set is the instance's resolved continuous samples;
  the T5 seed is a continuous min-width scan; no discrete-grid snapping.
- **No NFP, no bbox shortcut, no clustering, no per-sheet prediction; cavity stays in prepack.**
- **No compression dependence** — the M3 `compress_layout`/`strip_compress_fit` stay deprecated.
- **Default OFF** — `VRS_BPP_DENSITY_COMPACT=0` reproduces pre-Q48 behaviour; additive IO field.

## 5. Measure gate (mechanism proof) — PASS

Focused fixture `/tmp/q48_6big.json` = 6×`Lv8_11612` (the real long thin curved part, surface
≈ 0.597 m²), 1500×3000 stock, margin 5 / spacing 8 / continuous, density ON:

```text
status ok, placed 6/6, used_sheets 3
density_applied true, moves_accepted 4
interlock_candidates generated 189, accepted 4
```

The contour-sampling + density-score **generate 189 interlock candidates and accept 4 interlock
moves** on the actual curved parts. The mechanism demonstrably proposes and keeps bbox-overlapping /
polygon-clear placements — the capability Q46 M1 / Q47 showed was missing.

## 6. A/B regression benchmark (full276 LV8, 300 s/side)

`artifacts/benchmarks/sgh_q48/q48_summary.json`. margin 5 / spacing 8 / continuous, 6×1500×3000.

| metric | A — density ON | B — density OFF |
| --- | ---: | ---: |
| status / placed | ok / **276/276** | ok / **276/276** |
| collisions / boundary | 0 / 0 | 0 / 0 |
| used sheets | **3** | **3** |
| utilization | 54.415 % | 54.415 % |
| density pass applied | **true** | false |
| density moves accepted | 2 | 0 |
| interlock generated / accepted | **20 / 2** | 0 / 0 |
| wall time | 293.6 s | 292.4 s |

Acceptance: `valid_a` ✓, `valid_b` ✓, `no_sheet_count_regression` ✓, `density_pass_ran` ✓ ⇒ **PASS**.

**Honest finding (budget starvation at scale).** On full276 the density pass runs *after* the BPP
sheet-reduction, which consumes most of the 300 s; the pass is deadline-bounded by the remaining
budget, so it only reaches a few parts (20 interlock generated / 2 accepted) and the layout is
unchanged (3 sheets, same utilization). The mechanism is **not** outcome-neutral by design (it does
accept interlock moves), it is **budget-starved** at scale — the §5 fixture proves the capability
when budget is available. The clear next lever is **budget allocation**: reserve a density-pass
budget or interleave density with the reduction (SGH-Q49), so the pass can act on all 276 parts.

## 7. Tests

- `density.rs` unit (4): interlocked placement scores better than separated; deterministic;
  density-neutral with no neighbours; evaluator matches the free function.
- `tests/sparrow_density_compaction.rs` (2): pass runs + feasibility preserved; interlock
  candidates generated on concave parts.
- Existing suites green: lib (478), `sparrow_finite_stock_multisheet` (16),
  `sparrow_shape_profile` (3). Default-off ⇒ no behaviour change.

## 8. Verdict & next lever

**PASS.** A working, deterministic, reversible interlock-aware density mechanism — the first to
demonstrably generate and keep interlocked placements (189/4 on the fixture; 20/2 on budget-starved
full276), with no regression. It pins the next density work on **budget allocation for the density
pass (SGH-Q49)** — and, if single-part greedy compaction proves insufficient at scale, coordinated
multi-part LNS thereafter. No 2-sheet promise; this is the proven substrate it builds on.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-16T02:23:35+02:00 → 2026-06-16T02:25:58+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q48_interlocking_density_compaction.verify.log`
- git: `sgh-q48-interlocking-density-compaction@d36d95b`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |   7 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 203 +++++++++++++++++++++
 .../src/optimizer/sparrow/fixed_sheet.rs           |  27 ++-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   1 +
 4 files changed, 235 insertions(+), 3 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? artifacts/benchmarks/sgh_q48/
?? canvases/egyedi_solver/sgh_q48_interlocking_density_compaction.md
?? codex/codex_checklist/egyedi_solver/sgh_q48_interlocking_density_compaction.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q48_interlocking_density_compaction.yaml
?? codex/reports/egyedi_solver/sgh_q48_interlocking_density_compaction.md
?? codex/reports/egyedi_solver/sgh_q48_interlocking_density_compaction.verify.log
?? rust/vrs_solver/src/optimizer/sparrow/density.rs
?? rust/vrs_solver/tests/sparrow_density_compaction.rs
?? scripts/bench_sgh_q48_density_compaction.py
```

<!-- AUTO_VERIFY_END -->
