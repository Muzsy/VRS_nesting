REVISE

# SGH-Q24 Sparrow parity quality hardening

SGH-Q24_STATUS: REVISE
PRODUCTION_LOSS_STATUS: CDE_SEPARATION_ACTIVE (loss_model_used=CdeSeparationLoss, bbox_primary=false)
PRODUCTION_SEARCH_STATUS: NON_TRIVIAL_ACTIVE (grid=2, focused=2, coord_descent=3, top_k=2; medium ~316 search samples)
MEDIUM_GATE_STATUS: PASS (ok, 12/12, pairs 66→0, raw 1320→0, no fallback)
LV8_12TYPES_GATE_STATUS: NOT_MET_TIMEOUT
LV8_24_GATE_STATUS: NOT_MET_TIMEOUT
EXPLORATION_POOL_STATUS: NOT_REWRITTEN (Q23R3 minimal restart/disruption retained)
COMPRESSION_REWRITE_STATUS: NOT_REWRITTEN (Q23R3 minimal compaction retained)
Q19_STATUS: HOLD

> `REVISE`, not report-only. Q24 implemented the production **loss-model identity
> (D)** and **search-strength uplift (A)** on top of the Q23R3 baseline, with no
> regression (433 lib tests pass; medium stays `ok 12/12`, `66→0`). But the Q24
> hard LV8 gates (`lv8_12types_x1` 12/12, `lv8_24_instances` 24/24) **do not
> converge — they time out** on real irregular LV8 geometry. The smoke fails those
> gates honestly; per run.md that is REVISE. The exploration-pool (B) and
> compression (C) rewrites are not done. Precise blocker + measurements below.

## 1) Meta
* **Task slug:** `sgh_q24_sparrow_parity_quality_hardening`
* **Run date:** 2026-05-30
* **Baseline:** Q23R3 (PASS milestone — multi-target pass, incremental graph,
  minimal exploration/compression, medium 12/12, `sparrow_cde` Phase1 default).
* `.cache/sparrow` present and used as reference.

## 2) Implemented this run

### D — shape-aware / CDE-aware production loss (DONE)
- New `LossModelKind::CdeSeparation` (`rust/vrs_solver/src/optimizer/loss_model.rs`):
  the authoritative search loss for production `sparrow_cde` is the CDE-truth
  batch **separation distance** (`evaluate_transform_cde_batch`, Q23R2), never
  `dx*dy` bbox area. The tracker/secondary `pair_loss`/`compute_boundary_loss`
  methods use the smooth penetration surrogate (not bbox-area).
- `run_sparrow_pipeline` sets `loss_model = CdeSeparation` for the CDE path
  (bbox-area only on non-CDE debug runs).
- Diagnostics `loss_model_used`, `loss_bbox_proxy_used_as_primary` surfaced to
  output. Medium: `loss_model_used = CdeSeparationLoss`, `bbox_primary = false`.
  Hard requirement `loss_model_used != bbox_area` ✓.

### A — production search-strength uplift (DONE)
- Production `SearchPositionConfig` was effectively disabled in Q23R3
  (`global_grid_n=1, focused=0, coord_descent=0, top_k=1`). Q24 sets a
  deterministic, non-trivial budget: `global_grid_n=2, focused_sample_count=2,
  coord_descent_max_steps=3, coord_descent_top_k=2`.
- Medium now shows real search activity: `sparrow_search_position_calls=24`,
  `sparrow_search_position_samples≈316` (was effectively 0). Hard requirement
  "non-trivial search activity, all-zero not PASS" ✓ for medium.

### Not done (B, C)
- B (exploration pool/disruption rewrite) and C (compression restore→compact→
  separate→accept lifecycle) retain the Q23R3 minimal versions. Their diagnostics
  are present (exploration/compression fields exist), but they are not the full
  pool/lifecycle the run.md demands.

## 3) Measured (production `sparrow_cde` + CDE)

`bench --quick` (sheet 1500×3000 LV8 fixture for LV8 rows; seed 11; orthogonal):

| row | hard | status | placed/req | converged | runtime | loss_model | search_samples |
|---|---|---|---|---|---:|---|---:|
| medium_10_to_20_items | Y | **ok** | 12/12 | true | ~24 s | CdeSeparationLoss | 316 |
| lv8_12types_x1 | Y | **timeout** | -/12 | - | 35 s cap | — | — |
| lv8_24_instances | Y | **timeout** | -/24 | - | 35 s cap | — | — |
| lv8_50_instances | n | timeout | -/50 | - | 45 s cap | — | — |

Outcome accounting: ok=1, timeout=3, total=4; hard gates passed **1/3** (medium only).
Measurements: `codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.{json,md}`.

## 4) Why LV8 hard gates fail — precise blocker
The LV8 subsets are real irregular polygons on a 1500×3000 sheet. With the uplifted
search (A), each move evaluates several candidates, and **each candidate builds its
own CDE session** (`CdeCandidateSession`, Q23R2 — built per candidate, not per
search). Over 12+ large many-vertex polygons the per-candidate `collect_poly_collisions`
+ separation probe cost explodes → wall-cap timeout (>35 s) with no convergence.
The fix (next run) is to **build the multi-hazard session once per target search
and reuse it across candidates/probe steps** (threading the session through
`search_position` → `evaluate_transform_cde_batch`), plus active-set hazard
filtering for large layouts. Until then LV8 12-type/24 cannot meet the hard gate.

## 5) DoD evidence matrix

| DoD row | status | evidence |
|---|---|---|
| production search budget uplift | PASS | `adapter.rs` SearchPositionConfig grid=2/focused=2/cd=3/top_k=2 |
| search diagnostics | PASS | medium `search_position_calls=24`, `samples≈316` |
| exploration pool/disruption | PARTIAL/REVISE | Q23R3 minimal restart/disruption only (B not rewritten) |
| compression lifecycle | PARTIAL/REVISE | Q23R3 minimal compaction only (C not rewritten) |
| production loss model | PASS | `loss_model_used=CdeSeparationLoss`, `bbox_primary=false` |
| medium 12/12 | PASS | ok, 12/12, pairs 66→0, raw 1320→0 |
| LV8 12-types-x1 | **FAIL (timeout)** | bench/smoke: timeout 35 s, not 12/12 |
| LV8 24-instance | **FAIL (timeout)** | bench/smoke: timeout 35 s, not 24/24 |
| larger LV8 denominator | PASS (measured) | lv8_50 measured (timeout), counted in denominator |
| no fallback | PASS | medium `bbox_fallback=0`, `lbf_fallback=0` |
| CDE backend | PASS | medium `backend_used=cde_adapter` |
| smoke/bench/check commands | PASS (executed) | see §6 |

## 6) Tests / commands
* `cargo build --release` → ok.
* `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` → **433 passed, 0 failed** (no regression).
* `python3 scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py` → **13 pass, 2 fail**
  (the 2 failures are the LV8 12-types/24 hard convergence gates; medium + all production
  quality gates pass). Smoke exits non-zero — LV8 convergence is a hard gate.
* `python3 scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py --quick` → measurements written; hard 1/3.
* `./scripts/check.sh` → run via verify.sh (below).

## 7) Files
**New:** `scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py`,
`scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py`, this report,
measurements (`.json`/`.md`), `.verify.log`.
**Modified:** `rust/vrs_solver/src/optimizer/loss_model.rs` (CdeSeparation variant +
`is_bbox_area_primary`), `rust/vrs_solver/src/adapter.rs` (production loss + search
budget + `loss_model_used` diagnostics), `rust/vrs_solver/src/io.rs` (loss diag fields).

## 8) Explicit REVISE reason
Per run.md: LV8 12-types-x1 and LV8 24-instance hard gates fail (timeout). B
(exploration pool) and C (compression) are not the full rewrites. These are the
remaining cutover items; D (production loss) and A (search uplift) are delivered
and verified with no medium regression. The LV8 timeout root cause and fix
(per-search session reuse) are documented in §4.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T21:34:05+02:00 → 2026-05-30T21:36:56+02:00 (171s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.verify.log`
- git: `main@dea176c`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs              | 29 ++++++++++++++++++++++++-----
 rust/vrs_solver/src/io.rs                   | 10 ++++++++++
 rust/vrs_solver/src/optimizer/loss_model.rs | 24 ++++++++++++++++++++++--
 3 files changed, 56 insertions(+), 7 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/loss_model.rs
?? README_SGH_Q24_SPARROW_PARITY_QUALITY_HARDENING_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.md
?? codex/codex_checklist/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24_sparrow_parity_quality_hardening.yaml
?? codex/prompts/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening/
?? codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.md
?? codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.verify.log
?? codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.json
?? codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.md
?? scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py
?? scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py
```

<!-- AUTO_VERIFY_END -->
