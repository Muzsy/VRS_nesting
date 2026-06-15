# SGH-Q47 — Shape Profile Priority Layer for the VRS Sparrow/BPP solver

## 1. Executive summary

SGH-Q47 introduces a cheap, deterministic **per-part-type shape-profile metadata layer**
([rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs](../../../rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs))
that informs the existing jagua-rs / Sparrow / CDE + BPP solver's **decisions** — *ordering*,
*BPP redistribution/compaction order*, *placement budget*, and *decision-diagnostics* — without
touching the collision engine, rotation handling, NFP, clustering, or any predicted per-sheet
part count. It is the **prioritisation half** of the agreed two-part goal (the *interlocking-search*
half — a real density-compact pass — is deferred to SGH-Q48).

The layer is **gated** by `VRS_SHAPE_PROFILE` (default on); `VRS_SHAPE_PROFILE=0` reproduces the
exact pre-Q47 behaviour (every priority is `0.0`, so the ordering keys collapse to the legacy
`convex_hull_area × diameter` + `instance_id`).

**Verdict: PASS** as a correct, safe, regression-free prioritisation + diagnostics increment.
The benchmark also produced the **honest, expected** finding that ordering+budget alone do **not**
move the full276 packing outcome (see §5) — confirming the M1 localisation that the density lever
is the placement *search*, not the item *priority*.

## 2. Implemented files

| File | Change |
| --- | --- |
| `optimizer/sparrow/shape_profile.rs` (new) | `PartShapeProfile` struct + `compute()` (true/bbox/hull area, fill/convexity/aspect/slenderness, classes, `priority_score`, `search_budget_multiplier`); `class_labels()`; `profile_sheet_scale()`; `build_shape_profile_diagnostics()`; `shape_profile_enabled()`; 7 unit tests |
| `optimizer/sparrow/mod.rs` | `pub mod shape_profile;` + `pub(crate) use shape_profile::PartShapeProfile;` |
| `optimizer/sparrow/model.rs` | per-unique-part profile cache in `from_solver_input` (computed once per `part_id`, like the base-shape cache) + `SPInstance.shape_profile: Rc<PartShapeProfile>` |
| `optimizer/sparrow/lbf.rs` | `order()` primary key = `priority_score`, tie-break legacy `convex_hull_area × diameter`, then `instance_id` |
| `optimizer/sparrow/bpp_reduction.rs` | `profile_order_key` used by the displaced-redistribution, `compact_bin`, and `pick_large` sorts (T3); per-placement micro-budget scaled by `search_budget_multiplier` in `search_placement_on_sheet` (T4) |
| `optimizer/sparrow/multisheet.rs` | `FiniteStockRunResult.shape_profile_diagnostics` field |
| `io.rs` | `ShapeProfileDiagnostics` struct + `OptimizerDiagnosticsOutput.shape_profiles` |
| `adapter.rs` | `shape_profiles` surfaced from the BPP result |
| `tests/sparrow_shape_profile.rs` (new) | 3 end-to-end tests (emitted diagnostics, anchor outranks filler, collision feasibility preserved) |
| `scripts/bench_sgh_q47_shape_profile_full276.py` (new) | A/B (`VRS_SHAPE_PROFILE=0|1`) full276 regression harness |

## 3. Guardrails honoured

- **No collision change** — the profile is metadata; the CDE remains the sole collision truth.
- **Continuous stays continuous** — no rotation/sampler code touched; angle-sensitive metrics
  (`min_dim`, `slenderness`) are one-time descriptors and never reach placement rotation.
- **No bbox shortcut, no NFP, no clustering, no per-sheet count prediction, no `part_id` rules.**
- **Reversible** — `VRS_SHAPE_PROFILE=0` restores pre-Q47 ordering/budget; no IO-contract change
  (the new diagnostics field is additive, `skip_serializing_if Option::is_none`).

## 4. Profile correctly identifies the critical part

The full276 LV8 `shape_profiles` diagnostics (Run A, profile on) rank the layout-determining part
first and the easily-placed fillers last — exactly the de-flattening the task targeted:

| rank | part | classes | priority_score | budget× |
| ---: | --- | --- | ---: | ---: |
| 0 | `Lv8_11612_6db` | concave_like, **large_anchor**, repeated_family, **high_interlock_potential** | 0.614 | 2.25 |
| 1 | `Lv8_15348_6db_GRAVIR` | concave_like, medium_structural | 0.188 | 1.00 |
| 2 | `Lv8_07921_50db` | rectangle_like, concave_like, medium_structural | 0.128 | 1.00 |
| 3–11 | the 9 small types | **tiny_filler** (+ convex/rectangle) | −0.13 … −0.25 | 0.50 |

`Lv8_11612_6db` — the long, thin, curved part that determines the sheet count — is now the #1
anchor with a 2.25× search budget; the tiny tabs are deferred with a 0.5× budget.

## 5. A/B regression benchmark (full276 LV8, 300 s/side)

`artifacts/benchmarks/sgh_q47/q47_summary.json`. margin 5 / spacing 8 / continuous, 6×1500×3000.

| metric | A — `VRS_SHAPE_PROFILE=1` | B — `VRS_SHAPE_PROFILE=0` |
| --- | ---: | ---: |
| status / placed | ok / **276/276** | ok / **276/276** |
| collisions / boundary | 0 / 0 | 0 / 0 |
| used sheets | **3** | **3** |
| utilization | **54.415 %** | **54.415 %** |
| wall time | 315.8 s | 290.1 s |

Acceptance: `valid_a` ✓, `valid_b` ✓, `no_sheet_count_regression` ✓, `priority_change_visible` ✓
⇒ **PASS**.

**Honest finding (ordering + budget are outcome-neutral on full276).** Runs A and B are
**bit-identical** in used-sheet count and utilization, both before (T3 only) and after the T4
budget multiplier was added. Reordering *who* is placed first, and giving the hard anchors up to
4.5 s of placement search, did **not** change the packing result (still 3 sheets / 54.4 %). This
matches the SGH-Q46 M1 evidence (even 6 big parts alone, at full sample budget, stay 2/sheet): the
density gap lives in the placement **search** (discovering bbox-overlapping / polygon-clear
interlocked positions), not in item **priority** or per-placement time. The prioritisation layer
is *necessary substrate + measurement*, but the density breakthrough is **SGH-Q48** (an
interlocking-aware density-compact pass replacing the y-only `compact_sheet`).

## 6. Tests

- `shape_profile.rs` unit tests (7): deterministic compute; rectangle / slender / tiny-filler /
  large-concave-low-fill classification; anchor outranks tiny in priority; gate default.
- `tests/sparrow_shape_profile.rs` (3): `shape_profiles` emitted per type with contiguous ranks;
  anchor outranks tiny end-to-end with `large_anchor`/`tiny_filler` classes; profile layer keeps
  the layout collision-free / fully placed (no-collision-semantics-change).
- Existing `tests/sparrow_finite_stock_multisheet.rs` (16) still green.

## 7. T4 decision record

T4 (budget multiplier) was plan-gated on "diagnostics show ordering helps". T6 showed ordering is
outcome-neutral (A==B), so T4 was implemented as the agreed **cheap measured experiment** and
re-measured: still A==B. T4 is **kept** (clean, gated, harmless) because it is the correct
mechanism for when the Q48 search can actually exploit the extra anchor budget; it is documented
here as currently outcome-neutral on full276.

## 8. Verdict

**PASS.** A correct, deterministic, reversible prioritisation + decision-diagnostics layer that
(a) proves the solver now ranks the critical curved anchor first and the fillers last, and
(b) measures honestly that this does not yet move full276 (3 sheets) — pinning the next density
investment squarely on **SGH-Q48 (interlocking-aware density-compact search)**.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-16T01:34:31+02:00 → 2026-06-16T01:36:56+02:00 (145s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q47_shape_profile_priority_layer.verify.log`
- git: `sgh-q47-shape-profile-priority-layer@7135f00`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     |  4 ++
 rust/vrs_solver/src/io.rs                          | 27 +++++++++++++
 .../src/optimizer/sparrow/bpp_reduction.rs         | 44 +++++++++++++++++-----
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       | 33 ++++++++++++----
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  2 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     | 22 +++++++++++
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |  5 +++
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     | 14 +++++++
 8 files changed, 134 insertions(+), 17 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? artifacts/benchmarks/sgh_q47/
?? canvases/egyedi_solver/sgh_q47_shape_profile_priority_layer.md
?? codex/codex_checklist/egyedi_solver/sgh_q47_shape_profile_priority_layer.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q47_shape_profile_priority_layer.yaml
?? codex/reports/egyedi_solver/sgh_q47_shape_profile_priority_layer.md
?? codex/reports/egyedi_solver/sgh_q47_shape_profile_priority_layer.verify.log
?? rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
?? rust/vrs_solver/tests/sparrow_shape_profile.rs
?? scripts/bench_sgh_q47_shape_profile_full276.py
```

<!-- AUTO_VERIFY_END -->
