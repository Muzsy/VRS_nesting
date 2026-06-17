# SGH-Q52 — Density-biased admission separation

## Goal

Close the precise gap SGH-Q51 isolated: the critical-aware builder reaches **2 sheets / 3 big curved
parts per sheet at spacing 0**, but only **2 big/sheet at spacing 5–8** (production / reference gap),
because the co-movable admission separation (`separate_sheet_local` → `exploration_phase`) resolves
overlap by **spreading** parts apart, not by **tucking them into interlock**. The 3-way interlock
*exists* at gap 5 (the reference fits 3) — our search does not find it. Q52 replaces the admission
separation with a **density-biased** one that resolves overlap **toward interlock, gap-preserving**.

**Honest framing.** Q51 proved the topology is findable (spacing 0 → 2 sheets). Q52 tries to make
the search find it at production spacing — a hard combinatorial config. **No 2-sheet promise.** A
measure-gate after T2 (6×`Lv8_11612` at spacing 5: 3 big/sheet?) decides before the full integration.

## Why the current separator misses it

`exploration_phase` minimises the overlap proxy ⇒ a feasible-but-loose state (parts pushed apart).
At spacing 0 many feasible configs exist, so 3 fit. At spacing 5/8 the gap constraint makes the
spreading separator push the 3rd part off the sheet instead of nesting it into the concavity.

## Mechanism (NFP-free, on existing primitives)

A focused **density-biased separation** over the critical set: iteratively, for each overlapping
part, sample candidates (uniform + contour-near, Q48) at continuous rotations and score each by a
**combined** objective —

```
score = collision_proxy(cand, neighbours)  +  w_density · density_proxy(cand, neighbours)
```

- `collision_proxy` = pole-based `quantify_collision_poly_poly` (drives overlap → 0),
- `density_proxy` = Q48 `density_candidate_score` on the **spacing-collision** shape (low added
  extent + high contact ⇒ pulls toward interlock, and is **gap-preserving** because the shape is
  spacing-expanded).

Move each part to the best combined position; iterate until collision-free (CDE-valid) or budget.
This resolves overlap **into concavities** rather than spreading.

## Non-goals (hard constraints)

- Continuous stays continuous; CDE is the collision truth; **no NFP**; no bbox shortcut; no
  prediction; no clustering; cavity in prepack.
- **Default OFF** (the density-bias applies only inside the gated `VRS_SHEET_BUILDER` admission, via
  `VRS_ADMISSION_DENSITY_BIAS`); Q51's feasibility-gated fallback stays ⇒ no regression.
- Deterministic; additive IO.

## Task breakdown

- **T1** `density_biased_separate(layout, sheet, set, w_density, …)` — focused iterative separator
  with the combined objective (pole-collision + density), continuous rotation, CDE-valid, budgeted.
  Unit test: a synthetic overlapping concave pair resolves **into interlock**, not apart.
- **T2** Wire into `try_admit_critical`'s co-movable step (replace/augment `separate_sheet_local`).
  **Measure-gate:** 6×`Lv8_11612` at **spacing 5** — can the admission place 3 big parts/sheet? If
  not, rethink the weighting/sampling before T3.
- **T3** Weight + budget tuning (`w_density`, sweeps, per-part budget); `VRS_ADMISSION_DENSITY_BIAS`.
- **T4** Tests (separator yields interlock; builder+bias valid; default-off unchanged).
- **T5** A/B benchmark (6-big spacing 5/8 + full276): builder+bias ON vs Q51-builder-only vs OFF —
  big/sheet, used_sheets, validity.
- **T6** verify + report + checklist.

## Acceptance criteria

- Default off reproduces Q51/pre-Q52 behaviour; CDE/rotation/NFP guardrails held; deterministic.
- The density-biased separator resolves a synthetic overlapping concave pair into interlock (unit).
- No regression vs Q51 (feasibility-gated fallback intact).
- Stretch (not promised): 3 big/sheet at spacing 5 ⇒ a path to production 2 sheets.

## Risks

- The density-bias may still not find the 3-way interlock at spacing 5/8 (hard config) — measured at
  the gate; **no 2-sheet promise**.
- Objective weighting is sensitive (too much density ⇒ overlap not resolved; too little ⇒ spreads).
  `w_density` is tuned.
- All gated + Q51 fallback ⇒ no production regression.

## Status

Planned. T1 in progress. Stacked on `sgh-q51-...` / main (Q47–Q51 merged through Q50; Q51 on branch).
