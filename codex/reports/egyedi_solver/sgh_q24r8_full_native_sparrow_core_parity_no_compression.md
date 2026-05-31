# SGH-Q24R8 Full native Sparrow core parity, compression excluded

**Status:** PASS_WITH_NOTES
**SGH-Q24R8_STATUS:** PASS

## 1) Meta

- **Task slug:** `sgh_q24r8_full_native_sparrow_core_parity_no_compression`
- **Canvas:** `canvases/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r8_full_native_sparrow_core_parity_no_compression.yaml`
- **Run date:** 2026-05-31
- **Branch / commit:** `main` / `e3e40b8`
- **Focus area:** Solver / Native Sparrow / QA

## 2) Scope

### 2.1 Goal

- Replace the Q24R7-R1 dense proof shortcuts with a fuller native Sparrow-style core path.
- Keep the production `sparrow_cde` adapter boundary on `SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution`.
- Add native LBF/search/evaluator/worker/separator/exploration equivalents adapted to fixed sheets.
- Keep compression disabled and unused.
- Prove dense LV8 191 is a real full-validation partial run that improves loss and pair count over the seed.

### 2.2 Non-goals

- No strip-width compression or Sparrow compression phase port in this task.
- No legacy VRS `WorkingLayout` / `VrsCollisionTracker` reintroduction inside production Sparrow.
- No claim that the LV8 191 first-sheet case is fully feasible; it remains explicit `partial`.

## 3) Change Summary

### 3.1 Affected Files

- **Solver core:**
  - `rust/vrs_solver/src/optimizer/sparrow/mod.rs`
- **QA smoke:**
  - `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py`
- **Task artifacts:**
  - `README_SGH_Q24R8_FULL_NATIVE_SPARROW_CORE_PARITY_PACKAGE.md`
  - `canvases/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`
  - `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r8_full_native_sparrow_core_parity_no_compression.yaml`
  - `codex/codex_checklist/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`
  - `codex/prompts/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression/run.md`
  - `codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`

### 3.2 Why They Changed

- `sparrow/mod.rs` now owns the fuller native Sparrow-like LBF/search/tracker/separator/exploration flow and removes the dense bounded shortcuts.
- The Q24R8 smoke now has static architecture checks plus medium, LV8 x1, and dense LV8 191 runtime progress gates.
- Task artifacts were copied from `tmp/task` and this report records the execution evidence.

## 4) Verification

### 4.1 Mandatory Command

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md` -> PASS.

### 4.2 Task Commands Run Before Verify

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` -> PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> PASS, 432 passed
- `python3 scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py` -> PASS_WITH_DENSE_FIT_PARTIAL

### 4.3 AUTO_VERIFY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T21:22:31+02:00 → 2026-05-31T21:25:32+02:00 (181s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.verify.log`
- git: `main@e3e40b8`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/sparrow/mod.rs | 1121 ++++++++++++++++----------
 1 file changed, 713 insertions(+), 408 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
?? README_SGH_Q24R8_FULL_NATIVE_SPARROW_CORE_PARITY_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r8_full_native_sparrow_core_parity_no_compression.yaml
?? codex/prompts/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression/
?? codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md
?? codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.verify.log
?? scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD point | Status | Evidence | Explanation | Check |
| --- | --- | --- | --- | --- |
| Q24R7-R1 report read and dense weakness understood | PASS | `codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md`; `codex/prompts/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression/run.md` | Baseline dense weak metrics were used as the comparison target for the new smoke. | Q24R8 smoke dense progress gate |
| Upstream Sparrow core modules read from `.cache/sparrow` | PASS | `.cache/sparrow/src/optimizer/lbf.rs`, `.cache/sparrow/src/optimizer/separator.rs`, `.cache/sparrow/src/sample/search.rs`, `.cache/sparrow/src/quantify/tracker.rs` | Local implementation maps the upstream LBF/search/separator/tracker concepts into fixed-sheet VRS constraints. | Static architecture gate |
| Production `sparrow_cde` uses native problem/optimizer/solution | PASS | `rust/vrs_solver/src/adapter.rs:477`, `rust/vrs_solver/src/adapter.rs:518`, `rust/vrs_solver/src/adapter.rs:537`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1953` | Adapter constructs `SparrowProblem`, calls `SparrowOptimizer::solve`, and projects only at output boundary. | Smoke static architecture gate |
| Old VRS core not used inside production Sparrow | PASS | `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:103` | Static gate rejects `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, and `MultiSheetManager`. | Q24R8 smoke |
| Native LBF builder equivalent implemented | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1008`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1119` | `LBFBuilder` orders instances and uses evaluator-backed candidates, with deterministic overlap-minimizing fallback after budget expiry. | Unit tests + smoke |
| Native collision tracker uses CDE-confirmed quantification | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:875`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1573` | Tracker uses full final validation and CDE-confirmed pair/container collisions before quantified native loss assignment. | Unit tests + smoke |
| Sample eval/best samples/uniform sampler/coord descent/search implemented | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1186`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1217`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1251`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1302` | Search uses `SampleEval`, `SampleEvaluator`, `BestSamples`, `UniformBBoxSampler`, and refinement. | Q24R8 smoke static/runtime |
| Separation evaluator implemented | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1350` | `SeparationEvaluator` scores candidates against CDE session results and tracker-weighted collisions. | Q24R8 smoke |
| Separator worker Alg 5 semantics implemented | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1809` | `SeparatorWorker` clones state, processes colliding targets until budget expiry, and returns candidate state/statistics. | `native_optimizer_worker_competition_is_active` |
| Separator Alg 9 and `move_items_multi` Alg 10 semantics implemented | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:1993`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:2053` | Multi-worker candidates are compared/loaded back; separator loops with rollback and GLS updates. | Unit tests + smoke |
| Exploration pool/restore/disruption Alg 12 adapted without compression | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:2120`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:2244` | Solve loop pools infeasible states, restores, disrupts, and retries. Strip shrink/compression is omitted. | Unit tests + smoke |
| Dense shortcuts and bounded validation removed | PASS | `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:130`, `rust/vrs_solver/src/optimizer/sparrow/mod.rs:2331` | Static gate rejects Q24R7-R1 shortcut symbols and final validation uses full tracker. | Q24R8 smoke |
| Full final CDE validation runs for dense probe | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:2331` | Final layout is validated through `SparrowCollisionTracker::final_validation_tracker`. | Q24R8 smoke dense gate |
| Medium CDE and LV8 12 types x1 pass | PASS | `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:242`, `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:262` | Smoke validates 12/12 medium and 12/12 LV8 x1 with zero final pairs/boundary violations. | Q24R8 smoke |
| LV8 reference sheet1 191 improves loss and pairs | PASS | `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:280`, `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:315` | Last smoke: raw loss 381928.401 -> 216263.248, pairs 202 -> 152, validated 39. | Q24R8 smoke |
| Compression disabled and unused | PASS | `rust/vrs_solver/src/optimizer/sparrow/mod.rs:125`, `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py:237` | Config disables compression and smoke asserts zero compression passes. | Q24R8 smoke |

## 6) IO Contract / Samples

- No Sparrow IO contract fields or POC sample schemas were changed.
- Output boundary remains `SparrowSolution::to_solver_projection` into `crate::io::Placement`.

## 7) Documentation Sync

- Q24R8 canvas, YAML, checklist, prompt, and this report were added under existing `egyedi_solver` task artifact paths.

## 8) Advisory Notes

- Dense LV8 191 remains explicit `partial`: status `partial`, reason `time_budget_exhausted`, unresolved IDs reported.
- The implementation is a fixed-sheet adaptation of Sparrow core concepts; strip shrink/compression remains intentionally excluded.
- Existing repo warnings remain in unrelated modules and do not fail the required gates.

## 9) Follow-ups

- Improve dense convergence beyond partial by replacing the bbox-overlap LBF budget fallback with a faster exact CDE-backed candidate cache.
- Remove remaining dead probe helpers in `sparrow/mod.rs` once no tests or diagnostics depend on them.
