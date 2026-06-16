# SGH-Q50 — Density-guided LNS "sheet-drop" pass

## 1. Executive summary

SGH-Q50 adds a **density-guided Large Neighborhood Search (LNS) sheet-drop pass** — the coordinated
multi-part move the programme isolated as the last lever (Q49: single-part density compaction
tightens within a sheet but cannot drop one). After the density compaction, the LNS **ruins** the
least-utilized used sheet and tries to **re-home its parts onto the others** via density-guided
interlock insertion, with perturbed restarts; it accepts only when a sheet is actually emptied and
the layout stays feasible, otherwise it reverts. Opt-in (`VRS_BPP_LNS=1`), default off.

**The mechanism is correct and proven:** the unit test shows the LNS **drops a droppable sheet**
(re-homes a part onto another sheet and empties the source). On full276 the pass **runs and attempts
elimination** (1 attempt, 3 perturbed restarts), preserves feasibility, and shows **no regression**.

**Honest finding (the final gap, precisely isolated).** On full276 the LNS **cannot drop the 3rd
sheet** (0 parts re-homed): the least-full sheet's binding part is a big curved `Lv8_11612`, and each
receiving sheet already holds 2 of them — a 3rd has no clear single-insertion spot. Re-homing the
big curved parts **one at a time**, even inside ruin-recreate, cannot create the **simultaneous
3-way interlock** the reference achieves. The remaining gap therefore needs **simultaneous
multi-part placement** (place 2–3 big parts together in an interlocked configuration, or
overlap-and-separate on insertion) — a genuinely harder, NFP-class step. **Verdict: PASS**
(acceptance met: valid, no regression, LNS runs + attempts); the **2-sheet stretch is not reached.**

## 2. Implemented files

| File | Change |
| --- | --- |
| `optimizer/sparrow/bpp_reduction.rs` | T1 `density_insert_part` (density-guided insertion onto a chosen sheet); T2 `try_drop_sheet` (ruin-recreate one sheet) + `lns_sheet_drop` (least-full-first, perturbed restarts, full revert) + `lns_enabled`/`lns_restarts`/`sheet_free_area`; wired after density compaction with a reserved budget half; + 2 unit tests (q50_tests) |
| `io.rs` | T3 `bpp_lns_applied` / `bpp_lns_attempts` / `bpp_lns_sheets_dropped` / `bpp_lns_parts_reinserted` / `bpp_lns_restarts` |
| `tests/sparrow_density_compaction.rs` | + `lns_sheet_drop_runs_and_preserves_feasibility` |
| `scripts/bench_sgh_q50_lns_sheet_drop.py` (new) | A/B (density+LNS vs density-only) full276 harness |

## 3. How it works

- **`density_insert_part`** (T1): density-guided insertion of a not-yet-placed part onto a chosen
  target sheet — session over the target sheet's parts, uniform + contour-near candidates, CDE
  clear-check, ranked by the density score (prefers interlock). Continuous rotation preserved.
- **`try_drop_sheet`** (T2): ruin a sheet (its parts' tracker shapes → `None`), re-insert each
  (hardest first; order rotated per restart) into the receiving sheets (most-free-area first) via
  `density_insert_part`; succeed only if **all** re-home feasibly ⇒ the sheet is empty.
- **`lns_sheet_drop`** (T2): repeatedly drop the least-utilized used sheet with perturbed restarts;
  accept on success (sheet emptied + feasible), else revert. Runs in the reserved budget's second
  half (the density compaction gets the first half).

## 4. Guardrails honoured

- CDE is the collision truth; continuous stays continuous; no NFP / bbox shortcut / clustering /
  per-sheet prediction; cavity in prepack.
- **Default OFF** (`VRS_BPP_LNS=0` ⇒ pre-Q50 behaviour; the density budget split only applies when
  LNS is on). **Feasibility-preserving** (full revert on any failure). Deterministic (fixed seed +
  deterministic restart order). Additive IO.

## 5. Measure (mechanism proof)

- **Unit (`try_drop_sheet_rehomes_a_droppable_sheet`):** a 2-sheet layout whose sheet-1 part fits on
  sheet 0 ⇒ the LNS re-homes it and empties sheet 1 (feasible). The mechanism drops a sheet when it
  is possible.
- **6×`Lv8_11612` fixture (density + LNS on):** ok, 6/6, 3 sheets; `lns_attempts 1`,
  `lns_restarts 3`, `lns_parts_reinserted 0`, `sheets_dropped 0` — the LNS attempts but the big
  curved parts cannot be re-homed (each receiving sheet already holds 2); reverts safely.

## 6. A/B benchmark (full276 LV8, 300 s/side)

`artifacts/benchmarks/sgh_q50/q50_summary.json`. margin 5 / spacing 8 / continuous, 6×1500×3000.

| metric | A — density + LNS | B — density only |
| --- | ---: | ---: |
| status / placed | ok / **276/276** | ok / 276/276 |
| used sheets | **3** | 3 |
| utilization | 54.415 % | 54.415 % |
| lns applied / attempts | true / **1** | false / 0 |
| lns restarts | 3 | 0 |
| **lns parts re-homed** | **0** | 0 |
| **lns sheets dropped** | **0** | 0 |
| wall time | 243.0 s | 273.1 s |

Acceptance: `valid_a` ✓, `valid_b` ✓, `no_sheet_count_regression` ✓, `lns_pass_ran` ✓,
`lns_attempted_elimination` ✓ ⇒ **PASS**. `STRETCH_lns_dropped_a_sheet` = **false**.

## 7. Tests

- `bpp_reduction.rs::q50_tests` (2): `density_insert_part` finds an interlock insertion;
  `try_drop_sheet` re-homes a droppable sheet.
- `tests/sparrow_density_compaction.rs`: + `lns_sheet_drop_runs_and_preserves_feasibility`.
- Existing suites green; default-off ⇒ no behaviour change.

## 8. Verdict & where the programme stands

**PASS** as a correct, deterministic, reversible LNS sheet-drop mechanism that drops a sheet when it
is possible and attempts it on full276 with no regression. **It does not reach 2 sheets on full276**:
the 3-curved-parts-per-sheet interlock cannot be produced by **sequential** ruin-recreate insertion.

This precisely closes the "make density work" arc (Q47 priority → Q48 interlock mechanism → Q49
budget → Q50 coordinated ruin-recreate) and isolates the genuine final blocker: **simultaneous
multi-part interlock placement** of the big curved parts. The candidate next levers, all NFP-free:
(a) **pair/triple insertion** — search a relative interlock configuration for 2–3 big parts and
place them together; (b) **overlap-and-separate insertion** — insert with transient overlap and
density-separate the receiving sheet (the coroush "pressure" idea on insertion). Both are
substantial; neither is promised to reach 2 sheets. Honest status: with the current constraints the
solver's proven floor on full276 is **3 sheets**; the reference's 2 sheets require simultaneous
multi-part interlock, the hardest remaining step.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-16T23:40:56+02:00 → 2026-06-16T23:43:21+02:00 (145s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q50_density_lns_sheet_drop.verify.log`
- git: `sgh-q50-density-lns-sheet-drop@1a24566`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |  10 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 456 ++++++++++++++++++++-
 .../vrs_solver/tests/sparrow_density_compaction.rs |  20 +
 3 files changed, 485 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/tests/sparrow_density_compaction.rs
?? artifacts/benchmarks/sgh_q50/
?? canvases/egyedi_solver/sgh_q50_density_lns_sheet_drop.md
?? codex/codex_checklist/egyedi_solver/sgh_q50_density_lns_sheet_drop.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q50_density_lns_sheet_drop.yaml
?? codex/reports/egyedi_solver/sgh_q50_density_lns_sheet_drop.md
?? codex/reports/egyedi_solver/sgh_q50_density_lns_sheet_drop.verify.log
?? scripts/bench_sgh_q50_lns_sheet_drop.py
```

<!-- AUTO_VERIFY_END -->
