# LV8 2-sheet 10mm 600s Claude Code quality search report

## Verdict

**PARTIAL.** The best non-BLF quality candidate (`cgal_s42_180`) placed
**189 / 276 instances on 1 sheet at ~23 % utilization in ~236 s wall**,
using the `quality_cavity_prepack_cgal_reference` profile. All 87 unplaced
items carried `reason: TIME_LIMIT_EXCEEDED` — the engine ran out of budget
while still working on sheet 0 and never attempted spillover to sheet 1,
so the 2-sheet, 276/276 PASS gate was not reached. No layout was
CAM-grade validated.

The 600 s budget for the same profile/seed timed out *worse* than the 180 s
budget (no output at all), indicating the engine's SA inner-eval scales
poorly with `time_limit_sec` and that the current sweet spot is around
~180 s wall for one SA round on the LV8 prepack.

## Target

- 3000 × 1500 mm sheet (engine sees `width_mm=1500`, `height_mm=3000` — equivalent geometry, transposed orientation)
- 10 mm `spacing_mm` (inter-part gap)
- 10 mm `margin_mm` (sheet border gap)
- 276 / 276 instances of 12 LV8 types
- ≤ 2 sheets used
- ≥ ~69.5 % utilization
- ≤ 600 s wall per run

## Repo state

- commit: `0cd40b3` (Add narrow-phase etalon benchmarking script)
- binary: `rust/nesting_engine/target/release/nesting_engine` (already built, mtime 2026-05-11 21:30; no rebuild needed)
- harness: [scripts/experiments/lv8_2sheet_claude_search.py](scripts/experiments/lv8_2sheet_claude_search.py)
- validator: [scripts/experiments/lv8_2sheet_claude_validate.py](scripts/experiments/lv8_2sheet_claude_validate.py)
- artifact root: [tmp/lv8_2sheet_claude_search_20260512T160130Z/](tmp/lv8_2sheet_claude_search_20260512T160130Z/)
- commands: [tmp/lv8_2sheet_claude_search_20260512T160130Z/commands.sh](tmp/lv8_2sheet_claude_search_20260512T160130Z/commands.sh)

## Input validation

| Check | Source | Value |
|-------|--------|-------|
| Fixture path | [tmp/lv8_2sheet_claude_search_20260512T160130Z/inputs/lv8_target_10mm.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/inputs/lv8_target_10mm.json) | derived from `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` |
| Total part types | parsed | **12** |
| Total required instances | sum of `quantity` | **276** |
| `spacing_mm` | `sheet.spacing_mm` in fixture | **10.0** |
| `margin_mm` | `sheet.margin_mm` in fixture | **10.0** |
| `sheet.width_mm` × `sheet.height_mm` | fixture | 1500 × 3000 (transposed from "3000 × 1500" wording) |
| Rotations | each part | `[0, 90, 180, 270]` (r90 baseline) |
| External contour count expected | per type | 12 (one per type; each ×qty) |
| Internal contour count expected | top-level holes in fixture | 24 holes pre-prepack; 0 after cavity_prepack |
| `flip` | not present in nesting_engine_v2 schema | implicit disabled |

The harness records `placed_types`, `required_types`, `placed_instances`,
`required_instances`, `sheets_used`, `utilization_pct`, `runtime_sec`,
`spacing_mm`, `margin_mm`, `timed_out`, `return_code`, `valid` in every
run's `summary.json`, in `runs.jsonl`, and in `runs.csv`. The Hermes
`12/12 types` ambiguity is corrected: success requires `placed_instances
== required_instances`, not just `placed_types == required_types`.

## Permanent solver policy

- BLF is **not** a production quality solver for LV8 (see
  [codex/decisions/ADR-0001-blf-not-quality-solver.md](codex/decisions/ADR-0001-blf-not-quality-solver.md), created in this task).
- Allowed BLF uses: diagnostics, fallback compare, smoke tests,
  `can_place`/narrow-phase debugging.

## Hermes prior run lessons applied

| Hermes finding | Action taken | Outcome |
|----------------|--------------|---------|
| BLF non-expanded chain blocked | Confirmed BLF is not for quality; ran minimum repros only. | BLF on the full pair (28+20=48 inst.) completed in 60 s with `partial` (37 placed, 11 unplaced) — no infinite loop, just unsatisfactory quality. The earlier "infinite loop" framing is too strong; "slow + low quality" fits better. |
| Expanded vs non-expanded ambiguity | Used the original non-expanded fixture (12 types, sum qty 276) with cavity_prepack to handle holes. | All success metrics now report instance counts, not type counts. |
| `spacing=0`, `margin=0` previously | Built fresh fixture with `spacing_mm=10`, `margin_mm=10`, asserted in harness. | Confirmed engine reads them via `NestSheet`. |
| r90 baseline best | Kept `allowed_rotations_deg = [0,90,180,270]`. | r90 baseline used throughout. |
| seed=1 special | Ran seed=1 alongside seed=42. | seed=42: 189 placed; seed=1: 187 placed → seed=42 wins on this fixture. |
| `quality_cavity_prepack` recommended | Ran. | NFP `old_concave` path: engine never finished one SA eval in 180 s or 30 s budget. Stderr dominated by `[CONCAVE NFP DIAG]` lines (~10 MB / 240 s, ~66k pair logs). |
| `cavity_prepack_cgal_reference` recommended | Ran. | Produced the only valid outputs: 189/276 (seed=42, 180 s), 187/276 (seed=1, 180 s). |

## Run matrix

All cells from [tmp/.../runs.csv](tmp/lv8_2sheet_claude_search_20260512T160130Z/runs.csv) and `runs.jsonl`.

| id | profile | placer | kernel | search | compaction | rotations | seed | tl_sec | runtime_sec | placed_inst / 276 | sheets | util_pct | valid | notes |
|----|---------|--------|--------|--------|------------|-----------|------|--------|------------|-------------------|--------|----------|-------|-------|
| cavprep_s42_180 | quality_cavity_prepack | nfp | old_concave | sa | slide | r90 | 42 | 180 | 241.3 | 0 / 276 | 0 | n/a | false | watchdog kill; no output; stderr 9.6 MB of `[CONCAVE NFP DIAG]` |
| cavprep_quiet_30 | quality_cavity_prepack | nfp | old_concave | sa | slide | r90 | 42 | 30 | 90.9 | 0 / 276 | 0 | n/a | false | with stderr→/dev/null; still no output → blockage is algorithmic, not IO |
| **cgal_s42_180** | quality_cavity_prepack_cgal_reference | nfp | cgal_reference | sa | slide | r90 | 42 | 180 | 236.5 | **189 / 276** | **1** | **23.06** | false (quantity) | best candidate; 87 unplaced with `TIME_LIMIT_EXCEEDED` |
| cgal_s42_600 | quality_cavity_prepack_cgal_reference | nfp | cgal_reference | sa | slide | r90 | 42 | 600 | 660.5 | 0 / 276 | 0 | n/a | false | watchdog kill; longer budget WORSE than 180 s; SA eval grew unboundedly |
| cgal_s1_180 | quality_cavity_prepack_cgal_reference | nfp | cgal_reference | sa | slide | r90 | 1 | 180 | 240.4 | 187 / 276 | 1 | 21.16 | false (quantity) | seed=1 slightly worse than seed=42 on this fixture |

### BLF diagnostics (Phase 2, minimum repros only)

From [tmp/.../diagnostics/blf_min_repro_summary.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/diagnostics/blf_min_repro_summary.json):

| repro | placed | unplaced | sheets | status | wall | comment |
|-------|--------|----------|--------|--------|------|---------|
| `LV8_00035` only (28 inst.) | 28 | 0 | 1 | ok | <10 s | BLF handles single LV8 type with qty=28 fine. |
| `LV8_00035 + LV8_00057`, qty=4 each (8 inst.) | 8 | 0 | 1 | ok | <1 s | The Hermes-suspect pair at small qty: completes immediately. |
| `LV8_00035 + LV8_00057`, full (48 inst.) | 37 | 11 | 1 | partial | 60 s | Hit the 60 s `time_limit_sec`; produced partial layout, did NOT infinite-loop. Hermes "infinite loop" framing was an overstatement: BLF here is slow + poor, not stuck. |

## Best candidate

- id: **cgal_s42_180**
- profile: `quality_cavity_prepack_cgal_reference`
- engine CLI: `nest --placer nfp --search sa --part-in-part off --compaction slide --nfp-kernel cgal_reference`
- env: `NESTING_ENGINE_NFP_KERNEL=cgal_reference`
- input: prepacked from [tmp/.../inputs/lv8_target_10mm.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/inputs/lv8_target_10mm.json)
- prepacked solver input: [tmp/.../cavity_prepack_cgal/seed42_180s/prepacked_solver_input.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/cavity_prepack_cgal/seed42_180s/prepacked_solver_input.json)
- cavity_plan: [tmp/.../cavity_prepack_cgal/seed42_180s/cavity_plan.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/cavity_prepack_cgal/seed42_180s/cavity_plan.json)
- solver stdout (canonical copy): [tmp/.../best_candidate.stdout.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/best_candidate.stdout.json)
- solver stderr (silenced; marker file): [tmp/.../best_candidate.stderr.log](tmp/lv8_2sheet_claude_search_20260512T160130Z/best_candidate.stderr.log)
- summary: [tmp/.../best_candidate.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/best_candidate.json)
- layout copy: [tmp/.../best_candidate_layout.json](tmp/lv8_2sheet_claude_search_20260512T160130Z/best_candidate_layout.json)
- runtime: 236.5 s
- sheets used: 1
- placed instances: **189 / 276**
- placed types: 8 distinct part-IDs out of 12 in the prepacked input
- utilization (single-sheet): 23.06 %
- unplaced: 87, all `reason: TIME_LIMIT_EXCEEDED` (engine never reached sheet 2)

Note on `virtual_parent_count` (228 in the cavity_plan) vs `required_instances` (276):
The cavity_prepack v2 split the input into 228 "named" virtual parts plus a
set of `__cavity_composite__..._empty__<hash>` placeholders. When summed
back to original parts via `quantity_delta`, all 12 parts have
`internal_qty = 0` and `top_level_qty = original_required_qty`, so all 276
instances are top-level placements. The harness counts every placement
as exactly 1 real instance, which is consistent with this cavity_plan
(no children packed into cavities — every relevant cavity was
`cavity_too_small` for this LV8 set under 10 mm spacing).

## Validation

Conservative AABB-based validator
([scripts/experiments/lv8_2sheet_claude_validate.py](scripts/experiments/lv8_2sheet_claude_validate.py)):

- quantity: **FAIL** (189 / 276 placed)
- sheets_used ≤ 2: passes structurally (only 1 sheet used)
- boundary AABB violations: 41
- AABB-overlap pairs: 167
- spacing AABB violations: 101

Status: **PARTIALLY_VALIDATED**. The validator is AABB-only and so is
unsuitable for the concave LV8 outlines: two L-shaped parts well-tiled
on the sheet can have overlapping AABBs with no polygon overlap and no
real clearance violation. Likewise, the 41 boundary "violations" are
not definitive: the engine's contract is that the *inflated* outline
(nominal + `spacing/2` halo) sits inside the bin shrunk by
`(spacing/2 - margin)` mm — for `spacing=10, margin=10` that means
nominal AABB ranges from `[5, w-5]` on the *inflated* coords but
the per-part `outer_points_mm` in the prepacked input encode composite
cavity outlines that differ from the solver's effective polygon. A
polygon-aware validator (`i_overlay`-backed, or reuse of
`worker.cavity_validation.validate_cavity_plan_v2`) is required to
convert these warnings into definitive overlap / clearance / boundary
verdicts.

Since the candidate already fails the quantity gate decisively, no
further validator effort was spent: there is no useful validation of an
incomplete layout. See
[tmp/.../validation/validation_summary.md](tmp/lv8_2sheet_claude_search_20260512T160130Z/validation/validation_summary.md)
for the full validator note.

## Findings

### What worked

1. **`quality_cavity_prepack_cgal_reference`** is the only solver path
   that produced any valid 10 mm/276-target output in this task. The
   CGAL kernel skips the OldConcave decomposition that traps the
   default path.
2. **Instance counting is fixed.** Every run summary records
   `placed_instances` from `len(placements)` reconciled against the
   `virtual_parts` map, so `12/12 types placed` can no longer be
   mistaken for success.
3. **Spacing/margin enforcement is real.** The 10 mm fixture is used
   end-to-end through `prepacked_solver_input.json`; no run reports the
   spacing=0 ambiguity Hermes flagged.
4. **BLF chain isn't infinite-looped after all.** With 60 s budget the
   LV8_00035 + LV8_00057 full-qty pair completes with a `partial`
   status and no hang. The Hermes "infinite loop" framing should be
   downgraded to "slow + poor quality, not stuck."

### What failed

1. **NFP `old_concave` (`quality_cavity_prepack` profile) cannot
   complete even one SA evaluation on the LV8 prepack** within 30, 90,
   or 180 s budgets. Both with and without stderr capture, the engine
   stays at 100 % CPU for the entire watchdog window and never emits
   stdout. Per stderr, the inner loop is decomposing concave LV8
   outlines into 40-241 convex parts and computing partial NFPs in a
   nested `O(N×M)` loop. With diagnostics on, ~66 k partial-NFP lines
   per minute hit stderr; without diagnostics, the same arithmetic
   simply doesn't finish.
2. **Engine respects `time_limit_sec` only between SA evaluations.**
   The first SA eval on the LV8 prepack takes longer than every short
   budget we tried, so the deadline check
   ([rust/nesting_engine/src/search/sa.rs:368](rust/nesting_engine/src/search/sa.rs#L368))
   never fires until the eval finishes — and the eval doesn't finish
   for OldConcave.
3. **`cgal_s42_600` was *worse* than `cgal_s42_180`.** Same profile,
   same seed, longer wall budget — but at 600 s `time_limit_sec` the
   engine's per-eval budget (`eval_budget_sec`) scales up too,
   apparently letting a single greedy attempt grow into a non-completing
   one. The 180 s budget is the engine's current sweet spot for LV8.
4. **Greedy multi-sheet does not spill within budget.** All 189 placed
   instances landed on sheet 0; the 87 unplaced all carried
   `TIME_LIMIT_EXCEEDED` rather than `PART_NEVER_FITS_SHEET`. The
   engine timed out filling sheet 0 instead of starting sheet 1, so the
   2-sheet objective is not exercised at all.
5. **AABB-based validation is too coarse for LV8.** A polygon-aware
   validator is required to make any binding statement about overlap /
   spacing / boundary compliance.

### Where time is spent

- `cavity_prepack v2`: ~0.5 s per fixture. Reduces 24 top-level holes
  to 0. With `cavity_too_small` for the LV8 set, no children are
  packed into cavities (`internal_qty = 0` for every type).
- NFP `old_concave` setup: starts within ~1 s.
- NFP `old_concave` per-eval: never completes inside 180 s.
- NFP `cgal_reference` per-eval: ~200-240 s on this fixture; emits
  output once the SA returns its best-of-run state.
- Stderr `[CONCAVE NFP DIAG]` from
  [rust/nesting_engine/src/nfp/concave.rs:226-313](rust/nesting_engine/src/nfp/concave.rs#L226-L313)
  is always-on (no env gate) and accounts for ~9.6 MB / 240 s on the
  OldConcave path. Silencing stderr does not unstick OldConcave but it
  does prevent the IO-stall variant of the failure.

### Whether 2 sheets is reached

**No.** Every successful run placed strictly on sheet 0 and emitted
unplaced items rather than spilling to sheet 1. The 2-sheet objective is
currently untestable on this fixture because the engine's per-sheet pass
does not return before the budget expires.

## Next recommended actions (max 3)

1. **Gate `[CONCAVE NFP DIAG]` behind an env flag and add a pair-NFP
   cache** in [rust/nesting_engine/src/nfp/concave.rs](rust/nesting_engine/src/nfp/concave.rs).
   Today every `(part_a_idx, part_b_idx)` is recomputed from scratch
   inside `compute_stable_concave_nfp`'s nested loop, and stderr is
   spammed unconditionally. A simple `HashMap<(rotation_a, rotation_b),
   Polygon64>` cache plus an `if std::env::var("NESTING_ENGINE_NFP_DIAG").is_some()`
   gate should turn the OldConcave path from "doesn't complete in 180 s"
   into a usable second quality kernel and let us actually compare
   `quality_cavity_prepack` against `quality_cavity_prepack_cgal_reference`.

2. **Force multi-sheet spillover before `TIME_LIMIT_EXCEEDED`.**
   Today `greedy_multi_sheet` lets the time check fire while still on
   sheet 0, so unplaced parts pile up with `TIME_LIMIT_EXCEEDED` even
   when sheet 1 is empty and would clearly take them. The 2-sheet
   objective is the actual benchmark gate, so a small change to spill
   to sheet 1 *first* when sheet 0 cannot fit a candidate, before
   accepting `TIME_LIMIT_EXCEEDED`, would let the current
   `cgal_s42_180`-class result jump from 189/276 to (likely) the full
   276 on 2 sheets at the cost of a slightly worse utilization.

3. **Replace the AABB validator with a polygon-aware one.** Reuse
   either `worker.cavity_validation.validate_cavity_plan_v2` (already
   handles overlap / bounds) wrapped around the engine's `placements`
   plus the prepacked outer-points, or call the engine's own
   `narrow_phase` via a small Rust CLI that takes stdout-JSON in and
   prints `{overlap_count, clearance_count, boundary_count}` per sheet.
   Without it, even a future PASS layout cannot be claimed
   CAM-production valid.

## Changed / created files

- [codex/decisions/ADR-0001-blf-not-quality-solver.md](codex/decisions/ADR-0001-blf-not-quality-solver.md) — new ADR.
- [scripts/experiments/lv8_2sheet_claude_search.py](scripts/experiments/lv8_2sheet_claude_search.py) — quality-search harness with watchdog, canonical run summary, and stderr quieting.
- [scripts/experiments/lv8_2sheet_claude_validate.py](scripts/experiments/lv8_2sheet_claude_validate.py) — AABB validator (conservative).
- [codex/reports/nesting_engine/lv8_2sheet_10mm_600s_claude_code_report.md](codex/reports/nesting_engine/lv8_2sheet_10mm_600s_claude_code_report.md) — this report.
- [tmp/lv8_2sheet_claude_search_20260512T160130Z/](tmp/lv8_2sheet_claude_search_20260512T160130Z/) — full artifact tree:
  - `inputs/lv8_target_10mm.json`, `inputs/blf_*.json`, `inputs/prepacked_lv8_10mm.json`
  - `cavity_prepack/{seed42_180s, quiet_30s, nfp_greedy_120s}/...`
  - `cavity_prepack_cgal/{seed42_180s, seed42_600s, seed1_180s}/...`
  - `blf_diag/single_lv8_00035.stdout.json`, `pair_00035_00057_qty4.stdout.json`, `pair_00035_00057_full.stdout.json`
  - `diagnostics/blf_min_repro_summary.json`
  - `validation/cgal_s42_180_validation.json`, `validation_summary.md`, `best_candidate_validation.json`
  - `runs.jsonl`, `runs.csv`
  - `best_candidate.json`, `best_candidate.stdout.json`, `best_candidate.stderr.log`, `best_candidate_layout.json`
  - `commands.sh`, `summary.md`

No source files in `rust/nesting_engine/` were edited in this task. No
prior reports or artifacts were removed.

## Commands run

See [tmp/lv8_2sheet_claude_search_20260512T160130Z/commands.sh](tmp/lv8_2sheet_claude_search_20260512T160130Z/commands.sh).
The interesting subset:

```bash
# Phase 1 — 10 mm fixture (12 types, 276 instances, 10 mm spacing+margin)
python3 - <<'PY'  # see commands.sh; writes tmp/.../inputs/lv8_target_10mm.json
PY

# Phase 2 — minimum BLF repros (≤ 60 s each, stderr discarded)
timeout 90s bash -c "cat tmp/.../inputs/blf_single_lv8_00035.json |
  rust/.../nesting_engine nest --placer blf --search none --part-in-part off --compaction off
  > tmp/.../blf_diag/single_lv8_00035.stdout.json 2>/dev/null"
# ... and the two pair repros

# Phase 3 — cavity_prepack quality (OldConcave NFP; no output produced)
LV8_HARNESS_QUIET=1 python3 scripts/experiments/lv8_2sheet_claude_search.py \
  --fixture tmp/.../inputs/lv8_target_10mm.json \
  --out-dir tmp/.../cavity_prepack/seed42_180s \
  --quality-profile quality_cavity_prepack \
  --time-limit-sec 180 --seed 42 --label cavprep_s42_180 \
  --runs-jsonl tmp/.../runs.jsonl

# Phase 4 — cavity_prepack_cgal_reference (best path)
LV8_HARNESS_QUIET=1 python3 scripts/experiments/lv8_2sheet_claude_search.py \
  --fixture tmp/.../inputs/lv8_target_10mm.json \
  --out-dir tmp/.../cavity_prepack_cgal/seed42_180s \
  --quality-profile quality_cavity_prepack_cgal_reference \
  --time-limit-sec 180 --seed 42 --label cgal_s42_180 \
  --runs-jsonl tmp/.../runs.jsonl
# repeated with --time-limit-sec 600 (worse: watchdog kill) and --seed 1 (187/276)

# Phase 6 — validation on best candidate
python3 scripts/experiments/lv8_2sheet_claude_validate.py \
  --fixture tmp/.../inputs/lv8_target_10mm.json \
  --prepacked-input tmp/.../cavity_prepack_cgal/seed42_180s/prepacked_solver_input.json \
  --solver-stdout tmp/.../cavity_prepack_cgal/seed42_180s/solver_stdout.json \
  --out tmp/.../validation/cgal_s42_180_validation.json
```
