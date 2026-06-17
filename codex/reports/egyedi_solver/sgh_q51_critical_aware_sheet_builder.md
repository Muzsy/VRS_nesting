# SGH-Q51 — Critical-aware constructive sheet builder (anchor-first admission)

## 1. Executive summary

SGH-Q51 changes the **construction** itself: instead of the flat largest-first LBF seed, the
builder fills each sheet **anchor-first** with **admission control** — when a sheet is opened it
repeatedly admits the next *critical* (large / concave / slender) part with the already-admitted
critical parts kept **co-movable** (so several big parts re-arrange together into a deep interlock);
fillers come only after the critical capacity is tested; the sheet count **emerges**. Gated
(`VRS_SHEET_BUILDER=1`), default off.

**BREAKTHROUGH — the first 2-sheet result in the programme.** On the 6×`Lv8_11612` fixture at
spacing 0, the builder produces **3 big curved parts per sheet, 2 sheets, valid (6/6)** — the
reference's structure, reached end-to-end for the first time. The co-movable admission (seed the
candidate overlapping the admitted set, then separate the whole sheet so all big parts move
together) finds the 3-way interlock that every Q47–Q50 approach missed.

**Honest finding — the 3-way curved interlock is spacing-dependent.** At spacing 5 (the reference's
gap) and 8 (current production) the admission only reaches **2 big/sheet** — the tighter interlock
*exists* (the reference fits 3 at gap 5) but our overlap-minimising separation does not yet find it.
The genuine next R&D is a **density-biased separation** that resolves overlap *toward* interlock
while keeping the gap — **SGH-Q52**.

**Stabilised — no regression.** The builder seed is used **only when it is complete and fully
feasible**; otherwise the RNG is restored and it **falls back to the LBF seed**, with the builder's
wall time capped to a **budget fraction** (≈ 12 %, clamped [4 s, 20 s]) so the fallback leaves the
BPP reduction enough time at any budget. Result: spacing 0 → the 2-sheet win; spacing 5/8 →
identical to builder-off (valid, 3 sheets, no partial), verified clean even at a tight 60 s budget.
Default off ⇒ production unaffected.

## 2. Implemented files

| File | Change |
| --- | --- |
| `optimizer/sparrow/shape_profile.rs` | T1 `CriticalityTier` + `is_critical` / `criticality_tier` (project-general; LV8: the 2 big parts ⇒ Critical) |
| `optimizer/sparrow/fixed_sheet.rs` | T1 `build_criticality_queues` (critical / structural / filler, priority-sorted) |
| `optimizer/sparrow/bpp_reduction.rs` | T2 `try_admit_critical` (direct density insert + co-movable separation) + `density_insert_part` reuse; T3 `build_critical_aware_seed` (phased: admission → structural → filler), `direct_insert_on_sheet`, `sheet_builder_enabled`; feasibility-gated + RNG-restored + time-capped fallback wiring |
| `io.rs` | T5 `bpp_sheet_builder_applied` / `critical_admitted` / `critical_deferred` / `sheets_opened` / `max_critical_per_sheet` |
| `tests/sparrow_sheet_builder.rs` (new) | builder ON valid + no-regression |
| `scripts/bench_sgh_q51_sheet_builder.py` (new) | proof (6-big spacing 0) + full276 no-regression |

## 3. How it works

- **Criticality tiers (T1):** from the Q47 `PartShapeProfile` — `Critical` (large_anchor /
  high_interlock / slender / high priority, never tiny), `Filler` (tiny), `Structural` (the rest).
- **Admission (T2):** `try_admit_critical` — (1) **direct** density insertion with the admitted set
  fixed; (2) on failure, **co-movable** — seed the candidate overlapping the admitted set, then
  `separate_sheet_local` over the whole sheet (admitted + candidate move together, continuous
  rotation), accept only a CDE-feasible on-sheet result. The mid-build feasibility check is "placed
  parts collision-free", not "all instances placed".
- **Builder (T3):** per sheet, a critical admission phase precedes structural + filler insertion; a
  new sheet opens when the critical frontier is exhausted. Fallback: used only if the whole seed is
  feasible, else LBF (RNG restored, builder time-capped) ⇒ never worse than builder-off.

## 4. Guardrails honoured

- CDE is the collision truth; continuous stays continuous; **no NFP**; no bbox shortcut; **no
  prediction** (admission, never "N must fit"); no clustering; cavity in prepack.
- **Default OFF**; feasibility-gated + RNG-restored + time-capped fallback ⇒ no regression at any
  spacing. Deterministic; additive IO.

## 5. Measure-gate (mechanism proof) — POSITIVE

A unit test (`measure_gate_admit_third_big_part_on_one_sheet`) loads the real `Lv8_11612` geometry
(520 vertices), seeds **2** big parts side by side on a 1500×3000 sheet, and calls
`try_admit_critical` for the **3rd**: it is admitted, **3 big parts on one sheet, CDE-feasible**.
The co-movable admission finds the interlock on real geometry (spacing 0).

## 6. Benchmark

`artifacts/benchmarks/sgh_q51/q51_summary.json`.

| run | status | sheets | big/sheet | util | builder |
| --- | --- | ---: | --- | ---: | --- |
| **6×Lv8_11612, spacing 0, builder ON** | **ok** | **2** | **3 + 3** | 39.8 % | win |
| 6×Lv8_11612, spacing 8, builder ON | ok | 3 | 2 + 2 + 2 | 27.9 % | fallback |
| full276, builder ON (spacing 8) | ok | 3 | 2 + 2 + 2 | 54.4 % | fallback |
| full276, builder OFF (spacing 8) | ok | 3 | 2 + 2 + 2 | 54.4 % | — |

Acceptance: `PROOF_2sheets_3big_per_sheet_at_spacing0` ✓, `no_full276_regression_vs_off` ✓ ⇒
**PASS**. The builder's wall time is capped to a **budget fraction** (≈ 12 %, clamped [4 s, 20 s]),
so the feasibility-gated + RNG-restored fallback leaves the BPP reduction enough time at **any**
budget — verified clean at a tight 60 s budget too (spacing 0 → 2 sheets; spacing 8 → 3 sheets, ==
builder-off).

## 7. Tests

- `shape_profile.rs` / `fixed_sheet.rs::q51_tests`: tier classification (anchor / structural /
  filler), tiny-never-critical, queue split + sort, determinism.
- `bpp_reduction.rs::q51_measure_gate`: 3rd big part admitted on one sheet (real geometry).
- `tests/sparrow_sheet_builder.rs`: builder ON valid + no regression.
- Existing suites green (multisheet 16, density 4, shape_profile, …); default-off unchanged.

## 8. Verdict & next lever

**PASS** — the critical-aware constructive builder reaches **2 sheets / 3 big curved parts per
sheet at spacing 0**, the first such result in the programme, with **no regression** at production
spacing (feasibility-gated fallback). The architecture (anchor-first admission with **co-movable**
anchors) is the right one: deep interlock comes from re-arranging several big parts *together*
during construction, not from sequential placement or post-hoc repair.

The remaining gap is precise and singular: **the 3-way curved interlock at the production/reference
spacing (5–8)**. It exists (the reference fits 3 at gap 5) but our overlap-minimising separation
does not yet find it; **SGH-Q52** = a **density-biased admission separation** (resolve overlap
toward interlock, gap-preserving). The Q51 builder is the proven substrate it plugs into. No
2-sheet promise at production spacing yet — but for the first time it is a tuning/search problem on
a working architecture, not a missing capability.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-17T13:08:02+02:00 → 2026-06-17T13:10:26+02:00 (144s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q51_critical_aware_sheet_builder.verify.log`
- git: `sgh-q51-critical-aware-sheet-builder@cad82af`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |  10 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 432 ++++++++++++++++++++-
 .../src/optimizer/sparrow/fixed_sheet.rs           | 115 ++++++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   2 +-
 .../src/optimizer/sparrow/shape_profile.rs         |  65 ++++
 5 files changed, 622 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
?? artifacts/benchmarks/sgh_q51/
?? canvases/egyedi_solver/sgh_q51_critical_aware_sheet_builder.md
?? codex/codex_checklist/egyedi_solver/sgh_q51_critical_aware_sheet_builder.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q51_critical_aware_sheet_builder.yaml
?? codex/reports/egyedi_solver/sgh_q51_critical_aware_sheet_builder.md
?? codex/reports/egyedi_solver/sgh_q51_critical_aware_sheet_builder.verify.log
?? rust/vrs_solver/tests/sparrow_sheet_builder.rs
?? scripts/bench_sgh_q51_sheet_builder.py
```

<!-- AUTO_VERIFY_END -->
