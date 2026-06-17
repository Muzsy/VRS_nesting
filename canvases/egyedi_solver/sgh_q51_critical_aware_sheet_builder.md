# SGH-Q51 — Critical-aware constructive sheet builder (anchor-first admission)

## Goal

Attack the **root cause** the Q47–Q50 arc isolated (and the render confirmed): the macro layout never
changes because the solver **closes a sheet too early and too flatly** — it scatters the big parts
2-per-sheet, then the post-passes only shuffle parts *within* a sheet. Verified on full276: density
ON vs OFF is **bit-identical** (per-sheet 112/105/59, big `Lv8_11612` 2/2/2 on both).

Q51 changes the **construction** itself: build each sheet **anchor-first** with **admission
control** — when a sheet is opened, repeatedly try to admit the next *critical* (large / concave /
slender / low-fill) part with the already-admitted critical parts kept **co-movable** (so multiple
big parts can re-arrange together into a deep interlock); fillers come only after the critical
capacity is genuinely tested; a sheet is sealed only when its phases are actually exhausted. The
number of sheets **emerges** from construction — it is **not** pre-decided and there is **no**
"3 must fit" prediction.

**Honest framing (the architecture is the gain; the search is the risk).** This is the right
structural fix — it removes the filler-blocking obstacle that the renders show. But getting **3 thin
curved parts onto one sheet** still requires the **co-movable admission search** (transient overlap
→ density/interlock-guided separation of the critical set, continuous rotation) to actually *find*
the interlock. The existing separator minimises overlap by **spreading** parts; a density-biased
separation that resolves overlap by **tucking into concavities** is the genuine R&D. **No 2-sheet
promise.** A measure-gate after T2 decides whether the full builder (T3+) is worth building.

## Why the post-pass approach was wrong (user's correction)

Post-hoc "first-sheet repack" is wasteful and over-fits a single case. The question is **not**
"given a 3-sheet layout, how to cram the 3rd sheet's big part into sheet 1?" but **"while building
sheet 1, when do we keep trying to admit a hard part vs declare the sheet closeable?"** Build it
right the first time; the BPP reduction becomes a secondary repair line, not the primary path.

## Non-goals (hard constraints)

- Continuous stays continuous; CDE is the collision truth; **no NFP**; no bbox shortcut; **no
  prediction** (admission process, never "N must fit"); no clustering; cavity stays in prepack.
- **Default OFF** (`VRS_SHEET_BUILDER=1` to enable); off ⇒ the current `build_native_constructive_seed`
  (LBF) path, pre-Q51 behaviour exactly. Deterministic; additive IO; no production regression.
- **Critical anchors are soft-movable, not frozen** — they may move during later phases if the sheet
  score improves, with an inertia penalty so fillers do not drag them.

## Approach (verified hooks)

| hook | file | role |
| --- | --- | --- |
| `build_native_constructive_seed` | `fixed_sheet.rs:65` | replaced (when enabled) by `build_critical_aware_seed` |
| `PartShapeProfile` (Q47) | `shape_profile.rs` | static criticality tiers (critical / structural / filler) |
| `separate_sheet_local` / `exploration_phase` | `bpp_reduction.rs:760` / `explore.rs:14` | co-movable separation of the critical set in admission |
| `density_insert_part` / density objective (Q48–Q50) | `bpp_reduction.rs` / `density.rs` | direct interlock insertion + density-biased separation |

## Task breakdown

- **T1** Criticality tiers + queues (critical / structural / filler) from `PartShapeProfile`
  (deterministic) + unit tests.
- **T2** `try_admit_critical(sheet, admitted_set, candidate)` — (1) direct density insertion with the
  admitted set fixed; (2) on failure, **co-movable**: seed the candidate overlapping the set,
  density-biased separation over `{admitted ∪ candidate}` (continuous rotation, CDE-valid, budgeted).
  The gating R&D core. Unit test on a constructed concave-pair fixture.
- **Measure-gate** — on the 6×`Lv8_11612` fixture, can the admission place **3** big parts on one
  sheet (mechanism level)? If not, stop and reconsider the density-biased separation **before T3**.
- **T3** `build_critical_aware_seed` — per sheet: critical admission phase (T2) → structural phase →
  filler phase → seal → next sheet; sheet count emerges. Gated `VRS_SHEET_BUILDER`.
- **T4** Soft-movable anchors in structural/filler (inertia penalty) — reuse the density compaction
  with a movement penalty so fillers don't unseat good anchor configs.
- **T5** Decision diagnostics: `critical_admitted`/`deferred` per sheet, admission attempts/failures,
  phase-close reasons, sheets opened.
- **T6** Tests (builder on/off; deterministic; existing suites green).
- **T7** A/B benchmark full276 (builder on/off): used_sheets, critical-per-sheet, validity.
- **T8** verify + report + checklist.

## Acceptance criteria

- `VRS_SHEET_BUILDER=0` reproduces pre-Q51 behaviour; CDE/rotation/NFP guardrails held.
- Builder produces valid layouts (276/276, no collisions) and does **not** regress sheet-count vs off.
- Diagnostics prove anchor-first admission ran (critical parts admitted before fillers; sheets not
  closed until the critical frontier is exhausted). Deterministic.
- Stretch (not promised): more critical parts per sheet / fewer sheets on full276.

## Risks

- **Primary:** the co-movable admission search may not find the 3-thin-curved-part interlock (the
  existing separator spreads, not tucks). Measured at the gate after T2; if it can't, the
  density-biased separation needs more R&D before the full builder. **No 2-sheet promise.**
- Major architectural change (constructive seed) ⇒ gated + A/B; greedy per-sheet ⇒ local-optimum
  risk (scoring must weigh sheet quality, not just critical count).
- BPP reduction demoted to a secondary repair line.

## Status

Planned. Stacked on `sgh-q50-...` / main (Q47–Q50 merged).
