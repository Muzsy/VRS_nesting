PASS

# Report — JG-20 `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`

## Meta

- **Task slug:** `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`
- **Task id:** JG-20
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t20_phase2_irregular_benchmark_matrix.yaml`
- **Runner:** `codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/run.md`
- **Fókusz terület:** Phase 2 irregular/remnant benchmark gate

---

## Dependency evidence

- `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md` első sora: `PASS`
- JG-19 report tartalmazza: `JG-20_STATUS: READY`
- `scripts/smoke_jagua_remnant_score_model_v1.py` létezik és JG-19 szerint PASS
- `rust/vrs_solver/src/optimizer/score.rs` tartalmaz sheet-cost / usable_area_utilization útvonalat
- Nincs JG-19 által jelölt STOP, NO-GO vagy unresolved blocker

---

## Code audit summary

| Fájl | Találat |
|---|---|
| `bench_jagua_optimizer_phase1_rectangular.py` | `run_solver_in_dir` pattern, JSON+MD summary — mintaként auditálva |
| `smoke_jagua_irregular_sheet_provider.py` | JG-16 regressziós smoke — 12/12 PASS |
| `smoke_jagua_irregular_boundary_validation.py` | JG-17 boundary validation — 11/11 PASS |
| `smoke_jagua_irregular_candidate_generation.py` | JG-18 candidate generation — 10/10 PASS |
| `smoke_jagua_remnant_score_model_v1.py` | JG-19 remnant score — 12/12 PASS |
| `vrs_solver_runner.py` | `run_solver_in_dir` → meta: `placements_count`, `unplaced_count`, `sheet_count_used`, `utilization`, `validation_status`, `duration_sec`, `solver_bin` |
| `sheet.rs` | `Stock.outer_points`, `SheetShape.has_irregular_outer`, `SheetShape.area`, `cost_per_use` — elérhető |
| `boundary.rs` | `rect_within_boundary` facade — canonical boundary policy |
| `candidates.rs` | `generate_candidates_with_sheets` + `CandidateGenerationStats` — elérhető |
| `score.rs` | `score_breakdown` in output, `usable_area_utilization`, `sheet_cost_total` — elérhető |

**Boundary rejects:** Nem standard `solver_output.json` v1 mező. Proxy: `score_breakdown.boundary_contribution = 0.0` minden valid placement esetén.

---

## Benchmark matrix

`scripts/bench_jagua_optimizer_phase2_irregular.py` létrehozva és futtatva.

### Case definíciók

| case_id | leírás | stock típus | cost_per_use |
|---------|--------|-------------|-------------|
| `l_shape` | L-alakú 150×150 bbox (75×75 notch), 4 × 25×20 part | irregular | 1.0 |
| `concave_remnant` | L-alakú remnant, 4 × 25×20 part | irregular | 0.2 |
| `mixed_rectangular_remnant` | 1 rectangular (200×200) + 1 L-shape remnant (200×200 bbox), 3 × 50×50 | mixed | 1.0 / 0.2 |
| `rectangular_phase1_regression` | JG-14 'small' rectangular (200×150), 3 part type, 0/90 rot | rectangular | 1.0 |

Minden fixture: **hole-free, outer-only**.

---

## Benchmark eredmények

| case_id | status | placed | unplaced | sheets | utilization | dur_s | validation | stock_type |
|---------|--------|--------|----------|--------|-------------|-------|------------|------------|
| l_shape | pass | 4 | 0 | 1 | 0.1185 | 0.002 | pass | irregular |
| concave_remnant | pass | 4 | 0 | 1 | 0.1185 | 0.002 | pass | irregular |
| mixed_rectangular_remnant | pass | 3 | 0 | 1 | 0.1875 | 0.002 | pass | mixed |
| rectangular_phase1_regression | pass | 9 | 0 | 1 | 0.3733 | 0.004 | pass | rectangular |

---

## Score breakdown

| case_id | total_cost | placed_area | sheet_cost_contrib | sheet_cost_total | usable_area_util | boundary |
|---------|-----------|-------------|-------------------|-----------------|-----------------|---------|
| l_shape | 8000.00 | -2000.00 | 10000.00 | 1.0 | 0.1185 | 0.0 |
| concave_remnant | 0.00 | -2000.00 | 2000.00 | 0.2 | 0.1185 | 0.0 |
| mixed_rectangular_remnant | 2500.00 | -7500.00 | 10000.00 | 1.0 | 0.1875 | 0.0 |
| rectangular_phase1_regression | -1191.20 | -11200.00 | 10000.00 | 1.0 | 0.3733 | 0.0 |

**Boundary contribution = 0.0** minden esetben — nincs boundary violation a solver outputban.

**JG-19 score evidence:** `concave_remnant` (`sheet_cost_total=0.2`) kedvezőbb `total_cost` értéket ér el mint `l_shape` (`sheet_cost_total=1.0`), azonos placed count mellett.

---

## Exact validation evidence

Minden elfogadott layout `validation_status=pass` az exact Python validation bridge-től (`vrs_nesting/nesting/instances.py validate_multi_sheet_output()`).

`validation_status=fail` eset automatikusan `status=fail` — nem sikeres benchmark result.

---

## Invalid boundary fail evidence

`python3 scripts/smoke_jagua_irregular_boundary_validation.py` → **11/11 PASS**

- Check 5: Notch placement negatív kontroll — exact validator elutasítja a notch-ba elhelyezett itemet.
- Check 7: Invalid boundary layout nem lehet successful.
- Check 8: `margin_mm > 0` Phase1 → `UNSUPPORTED_MARGIN_MM_RUNTIME`.

**Bizonyított:** invalid boundary layout nem kaphat successful benchmark státuszt.

---

## Phase 1 rectangular regression

`python3 scripts/bench_jagua_optimizer_phase1_rectangular.py` → **PHASE1_GATE_DECISION: PASS**

- smoke: pass (placed=2, validation=pass)
- small: pass (placed=9, validation=pass)
- medium: pass (placed=6, validation=pass)
- realistic_no_hole: pass (placed=26, validation=pass)

**Nincs rectangular regresszió.**

---

## JG-16/JG-17/JG-18/JG-19 regression evidence

| Script | Eredmény |
|--------|----------|
| `smoke_jagua_irregular_sheet_provider.py` | **12/12 PASS** |
| `smoke_jagua_irregular_boundary_validation.py` | **11/11 PASS** |
| `smoke_jagua_irregular_candidate_generation.py` | **10/10 PASS** |
| `smoke_jagua_remnant_score_model_v1.py` | **12/12 PASS** |
| `cargo test --manifest-path rust/vrs_solver/Cargo.toml` | **97/97 PASS** |

---

## Summary outputs

- `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json`
- `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md`

---

## Checklist update evidence

- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` — minden item [x]
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-20 Kész + Gate 2 frissítve

---

## Risks/blockers

Nincs blokkoló. `boundary_rejects` nem standard solver_output.json v1 mező — proxy evidence `boundary_contribution=0.0` elegendő.

---

## Deviations from plan

Nincs érdemi eltérés. A benchmark script a `run_solver_in_dir` runner boundary-t használja, nem saját process duplikációt.

---

PHASE2_GATE_DECISION: PASS

JG-21_STATUS: READY

```text
JG-20 — `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`
```

## Created files

- `canvases/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t20_phase2_irregular_benchmark_matrix.yaml`
- `codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/run.md`
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.verify.log`

## Read / used project documents

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`

## Task definition extracted

From `jagua_optimizer_canvas_yaml_runner_task_bontas.md` and the checklist:

- **Task id:** JG-20
- **Slug:** `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`
- **Phase:** Phase 2 / benchmark gate
- **Dependency:** JG-19
- **Primary implementation output:** `scripts/bench_jagua_optimizer_phase2_irregular.py`
- **Benchmark outputs:**
  - `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json`
  - `codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md`
- **Gate:** `PHASE2_GATE_DECISION: PASS | REVISE | STOP`

## Dependency snapshot evidence

The current snapshot contains:

- `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- first line: `PASS`
- marker: `JG-20_STATUS: READY`
- `scripts/smoke_jagua_remnant_score_model_v1.py`
- `rust/vrs_solver/src/optimizer/score.rs`

Therefore the generated JG-20 runner treats the implementation task as startable, while still enforcing a preflight gate in the actual agent run.

## Real code observations used in this package

- `scripts/bench_jagua_optimizer_phase1_rectangular.py` exists and is the benchmark-script pattern to reuse.
- `vrs_nesting/runner/vrs_solver_runner.py` exists and should remain the runner/exact validation boundary.
- `scripts/smoke_jagua_irregular_sheet_provider.py`, `scripts/smoke_jagua_irregular_boundary_validation.py`, `scripts/smoke_jagua_irregular_candidate_generation.py`, and `scripts/smoke_jagua_remnant_score_model_v1.py` exist and are the relevant Phase 2 regressions.
- `rust/vrs_solver/src/sheet.rs` contains `has_irregular_outer`, `outer_vertices`, `area`, and `cost_per_use` data relevant to irregular/remnant benchmark metadata.
- `rust/vrs_solver/src/optimizer/boundary.rs` is the boundary policy façade.
- `rust/vrs_solver/src/optimizer/candidates.rs` contains irregular-aware candidate generation.
- `rust/vrs_solver/src/optimizer/score.rs` contains JG-19 score/remnant breakdown path.

## Validations performed during package generation

- YAML parse sanity: `YAML_OK steps: 8`.
- Sandbox path sanity: package text must not contain machine-specific absolute paths.
- Repo verify attempted via:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
```

## Checklist status

A task-specific checklist file was created, but items are intentionally unchecked because this package generation is not the JG-20 implementation. The implementation agent must check items only with concrete benchmark evidence.

## Next step

Copy/import this package into the local repo, then run:

```text
codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/run.md
```

with the normal local task runner / Codex CLI / Claude Code / Hermes workflow.

## Final status

```text
STATUS: REVISE
REASON: Package generated, but full repo verify cannot be marked PASS in this sandbox until the environment gate succeeds. This is the runnable JG-20 task package, not the JG-20 implementation.
```

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T19:37:43+02:00 → 2026-05-24T19:40:37+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.verify.log`
- git: `main@9af5895`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     | 44 +++++++++++-----------
 ...gua_optimizer_phase1_rectangular_benchmark.json |  4 +-
 2 files changed, 24 insertions(+), 24 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json
?? canvases/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t20_phase2_irregular_benchmark_matrix.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/
?? codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json
?? codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md
?? codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md
?? codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.verify.log
?? scripts/bench_jagua_optimizer_phase2_irregular.py
```

<!-- AUTO_VERIFY_END -->
