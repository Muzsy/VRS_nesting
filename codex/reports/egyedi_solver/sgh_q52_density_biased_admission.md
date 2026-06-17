# SGH-Q52 — Density-biased admission separation

## 1. Executive summary

SGH-Q52 replaces the **overlap-minimising** co-movable admission step in the Q51 builder
(`separate_sheet_local`) with a **density-biased** separation: when a critical part is seeded
overlapping the already-admitted parts on a sheet, a focused coordinate descent moves each part to
the candidate that is **CDE-clear and most interlocked** (lowest added extent / highest contact on
the **spacing-collision** gap-preserving shape) rather than the one that merely spreads parts apart.
Gated by `VRS_ADMISSION_DENSITY_BIAS` (default `0.0` = off), only active inside the gated
`VRS_SHEET_BUILDER` admission.

**Honest verdict — NEGATIVE on the stretch goal, retained as a building block.** At the production /
reference spacing (5 and 8) the density-biased admission reaches the **same 2 big curved parts per
sheet** as Q51's overlap-minimising separation — **it does not unlock the 3-way curved interlock**.
The measure-gate and a `w_density` sweep (0.5 / 2 / 6 / 15, up to 300 samples) confirmed this is
**not an objective-tuning problem**: the bottleneck is the **search structure**. The density-biased
separator is a *sequential, single-part* coordinate descent — it cannot discover the **simultaneous
multi-part repositioning** the tight 3-way interlock needs (the reference fits 3 at gap 5). The
correct objective is now in place and tested; the lever moves to **SGH-Q53 = a simultaneous
multi-part admission search**.

**What it nonetheless buys (why we keep it).** (1) The density objective + spacing-collision
gap-preserving candidate machinery is exactly what Q53's simultaneous search will reuse. (2) With
bias on, the co-movable admission *succeeds more often* — `critical_admitted` rises from 2 to 6 on
the 6-big fixture (it admits all big parts as co-movable) — it just can't pack them 3-to-a-sheet.
(3) It is **feasibility-gated and falls back exactly like Q51**, so it is a safe, tested, default-off
substrate.

**No regression.** Default off ⇒ production byte-identical to Q51. With bias on: the separator only
replaces the co-movable step, is CDE-validated, and the Q51 builder fallback (RNG-restored,
time-capped) still guards the whole seed ⇒ never worse than builder-off at any spacing.

## 2. Implemented files

| File | Change |
| --- | --- |
| `optimizer/sparrow/bpp_reduction.rs` | T1 `density_biased_separate` (lexicographic clear-first/interlock-ranked coordinate descent, spacing-collision gap-preserving shape, continuous rotation, budgeted) + `sheet_local_feasible` + `admission_density_bias`; T2/T3 wired into `try_admit_critical`'s co-movable step behind `VRS_ADMISSION_DENSITY_BIAS`; T1 unit test `density_biased_separate_resolves_overlap_into_interlock` |
| `tests/sparrow_density_admission.rs` (new) | T4 integration: builder+bias valid + no-regression vs builder-only, default-off baseline |
| `scripts/bench_sgh_q52_density_biased_admission.py` (new) | T5 A/B: tight spacing 5/8 (bias vs builder-only), spacing-0 proof, full276 no-regression |

## 3. How it works

- **`density_biased_separate` (T1):** over the parts on one sheet, `SWEEPS=12` coordinate-descent
  passes; per part it builds a `SparrowCollisionTracker` + `build_sheet_session` + `LBFEvaluator`,
  samples candidates (current pose + uniform + `contour_near_rect_mins`, continuous rotation) on the
  **spacing-collision base shape** (gap-preserving), and chooses **lexicographically**:
  - prefer a **CDE-clear** candidate (`ev.score_lbf_candidate(...).is_some()`), ranked by
    `density_candidate_score · w_density` (lower = more interlocked);
  - only if **no** candidate is clear, take the lowest `quantify_collision_poly_poly_value` sum
    (progress toward feasible).
  Stops when the sheet is CDE-feasible or the budget expires.
- **Deviation from the canvas (honest note).** The canvas specified a *combined* objective
  `collision_proxy + w·density_proxy`. T1 first implemented that and the unit test failed: a
  low-collision-but-not-clear position won and the result was infeasible. The fix was the
  **lexicographic** form above (clear-first, density only among clear candidates) — it preserves
  feasibility while still biasing toward interlock. The combined form is not retained.
- **Wiring (T2/T3):** in `try_admit_critical`'s co-movable restart loop, when
  `admission_density_bias() > 0.0` the density-biased separator runs instead of
  `separate_sheet_local`; the result is `final_validation_tracker`-checked before acceptance.

## 4. Guardrails honoured

- CDE is the collision truth; continuous stays continuous; **no NFP**; no bbox shortcut; **no
  prediction**; no clustering; cavity in prepack.
- **Default OFF** (`VRS_ADMISSION_DENSITY_BIAS=0.0`); only active under `VRS_SHEET_BUILDER`; Q51's
  feasibility-gated + RNG-restored + time-capped fallback intact ⇒ no regression. Deterministic;
  additive IO.

## 5. Measure-gate (the Q52 decision point) — NEGATIVE, as expected

6×`Lv8_11612` at **spacing 5**, builder + density-bias:

| w_density | samples | used sheets | big/sheet | max |
| ---: | ---: | ---: | --- | ---: |
| 0.5 | 300 | 3 | 2 / 2 / 2 | 2 |
| 2.0 | 300 | 3 | 2 / 2 / 2 | 2 |
| 6.0 | 300 | 3 | 2 / 2 / 2 | 2 |
| 15.0 | 300 | 3 | 2 / 2 / 2 | 2 |

Uniformly **2 big/sheet** across the weight sweep ⇒ the objective weighting is **not** the lever.
The sequential single-part coordinate descent resolves the seeded overlap to a feasible-but-loose
2-part config and cannot relocate the trio **simultaneously** into the tight 3-way interlock. The
topology is findable (Q51 proved 3/sheet at spacing 0); finding it at gap 5 requires simultaneous
multi-part repositioning → SGH-Q53.

## 6. Benchmark — `artifacts/benchmarks/sgh_q52/q52_summary.json`

| run | bias | status | sheets | big/sheet | util |
| --- | --- | --- | ---: | --- | ---: |
| 6×Lv8_11612, spacing 5 | builder-only | ok | 3 | 2 / 2 / 2 | — |
| 6×Lv8_11612, spacing 5 | **+bias w=2** | ok | 3 | 2 / 2 / 2 | — |
| 6×Lv8_11612, spacing 8 | builder-only | ok | 3 | 2 / 2 / 2 | 27.9 % |
| 6×Lv8_11612, spacing 8 | **+bias w=2** | ok | 3 | 2 / 2 / 2 | 27.9 % |
| 6×Lv8_11612, spacing 0 (proof) | builder | **ok** | **2** | **3 + 3** | 39.8 % |
| full276, spacing 8 | builder-only / +bias / off | ok | 3 | 2 / 2 / 2 | 54.4 % |

Acceptance: `PROOF_2sheets_3big_at_spacing0` ✓, `tight_spacing_no_regression_vs_builder_only` ✓,
`full276_no_regression` ✓, `tight_spacing_improved_big_per_sheet` **✗ (the honest negative
finding)** ⇒ benchmark **PASS** (the gate is no-regression + proof holds, not improvement). With
bias on, `critical_admitted` on the 6-big fixture rises 2 → 6: the separator admits all big parts
co-movably, yet still packs them 2/sheet — pinpointing search structure, not admission count.

## 7. Tests

- `bpp_reduction.rs::q50_tests::density_biased_separate_resolves_overlap_into_interlock`: a U-shape +
  square seeded overlapping resolves into the U's mouth (CDE-feasible + bbox-overlapping = nested),
  not apart.
- `tests/sparrow_density_admission.rs`: builder+bias produces valid, fully-placed output with
  `used_sheets ≤ builder-only`; default-off baseline valid (env phases run sequentially in one test
  to avoid intra-binary races).
- Full suite green: 486 unit + all integration (multisheet 16, density compaction 4, sheet builder
  2, shape profile 3, …); default-off unchanged.

## 8. Verdict & next lever

**PASS as a building block; NEGATIVE on the stretch.** Density-biased separation does **not** reach
3 big curved parts per sheet at production spacing (5–8) — it matches Q51's 2/sheet — and a weight
sweep proves the objective is not the bottleneck. The finding is **definitive and useful**: the
limitation is the **sequential single-part coordinate-descent search**, which cannot perform the
**simultaneous multi-part repositioning** the tight 3-way interlock requires. The density objective
and gap-preserving candidate machinery are now implemented, tested, and gated — the substrate Q53
plugs into.

**SGH-Q53 = simultaneous multi-part admission search:** a joint move over the critical set
(annealing / GLS that repositions several big parts *together* under the CDE, reusing Q52's density
objective and spacing-collision shapes), targeting the tight-spacing 3-way interlock that sequential
descent cannot find. The architecture (Q51 anchor-first admission) and the objective (Q52
density-biased, gap-preserving) are in place; Q53 changes the **search move** from single-part to
joint.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-17T18:10:09+02:00 → 2026-06-17T18:12:33+02:00 (144s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q52_density_biased_admission.verify.log`
- git: `sgh-q52-density-biased-admission@eebb9a0`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         | 266 ++++++++++++++++++++-
 1 file changed, 263 insertions(+), 3 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
?? artifacts/benchmarks/sgh_q52/
?? canvases/egyedi_solver/sgh_q52_density_biased_admission.md
?? codex/codex_checklist/egyedi_solver/sgh_q52_density_biased_admission.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q52_density_biased_admission.yaml
?? codex/reports/egyedi_solver/sgh_q52_density_biased_admission.md
?? codex/reports/egyedi_solver/sgh_q52_density_biased_admission.verify.log
?? rust/vrs_solver/tests/sparrow_density_admission.rs
?? scripts/bench_sgh_q52_density_biased_admission.py
```

<!-- AUTO_VERIFY_END -->
