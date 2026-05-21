# Jagua Optimizer Master Runner

## Cél

Ez a dokumentum a JG-00..JG-27 fejlesztési lánc végrehajtási kerete. A master runner nem implementálja a taskokat, hanem rögzíti az olvasási sorrendet, a preflightot, a gate-eket és a reportolási szabályokat.

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`

## Kötelező olvasnivaló

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `canvases/egyedi_solver/jagua_optimizer_task_index.md`
7. Az aktuálisan futtatott task package:
   - `canvases/egyedi_solver/<TASK_SLUG>.md`
   - `codex/goals/canvases/egyedi_solver/fill_canvas_<TASK_SLUG>.yaml`
   - `codex/prompts/egyedi_solver/<TASK_SLUG>/run.md`

## Baseline preflight

Minden tényleges task indítása előtt:

```bash
python3 --version
cargo --version
python3 -m pip show pytest >/dev/null || echo "WARN: pytest not installed"
python3 -m pip show mypy >/dev/null || echo "WARN: mypy not installed"
python3 -m pip show ezdxf >/dev/null || echo "WARN: ezdxf not installed"

ls AGENTS.md
ls docs/codex/overview.md
ls docs/codex/yaml_schema.md
ls docs/codex/report_standard.md
ls docs/qa/testing_guidelines.md

ls rust/vrs_solver/Cargo.toml
ls rust/vrs_solver/src/main.rs
ls rust/nesting_engine/src/placement/nfp_placer.rs
ls rust/nesting_engine/src/multi_bin/greedy.rs
ls rust/nesting_engine/src/search/sa.rs
ls vrs_nesting/config/nesting_quality_profiles.py
ls worker/cavity_prepack.py
ls worker/cavity_validation.py
ls scripts/validate_nesting_solution.py
ls scripts/validate_sparrow_io.py
ls scripts/run_sparrow_smoketest.sh
ls docs/nesting_engine/cavity_prepack_contract_v1.md
ls docs/nesting_engine/cavity_prepack_contract_v2.md
ls docs/solver_io_contract.md
```

Ha bármelyik kötelező anchor hiányzik: STOP és report `BLOCKED/FAIL`.

## Global hard rules

1. Csak valós repo fájlokra és parancsokra támaszkodhatsz.
2. Csak olyan fájl módosítható, ami az adott YAML step `outputs` listájában szerepel.
3. Tilos silent geometry loss (hole/contour/instance/quantity/transform).
4. Invalid layout nem lehet PASS.
5. Minden task végén kötelező a `verify.sh` wrapper futtatás.
6. Feature-gate nélkül tilos régi backend útvonalat megtörni.
7. Determinizmus és time-limit policy kötelező.

## Global invariants

- `REAL_CODE_ONLY`
- `NO_SILENT_GEOMETRY_LOSS`
- `EXACT_VALIDATION_REQUIRED`
- `CHECKLIST_REQUIRED`

## Files and anchors to verify before start

- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `rust/vrs_solver/Cargo.toml`
- `rust/vrs_solver/src/main.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `worker/cavity_prepack.py`
- `worker/cavity_validation.py`
- `scripts/validate_nesting_solution.py`

## Execution order

```text
JG-00 -> JG-01 -> JG-02
JG-02 -> JG-03
JG-03 + JG-02 -> JG-04
JG-03 + JG-04 -> JG-05
JG-05 -> JG-06 -> JG-07
JG-07 + JG-04 -> JG-08
JG-08 -> JG-09 -> JG-10 -> JG-11 -> JG-12 -> JG-13 -> JG-14
JG-14 -> JG-15 -> JG-16 -> JG-17 -> JG-18 -> JG-19 -> JG-20
JG-20 -> JG-21 -> JG-22
JG-22 + JG-14 -> JG-23 -> JG-24
JG-24 + JG-20 -> JG-25
JG-14 vagy JG-20 -> JG-26
JG-26 -> JG-27
```

## Dependency graph

```text
JG-00 -> JG-01 -> JG-02
JG-02 -> JG-03
JG-03 + JG-02 -> JG-04
JG-03 + JG-04 -> JG-05
JG-05 -> JG-06 -> JG-07
JG-07 + JG-04 -> JG-08
JG-08 -> JG-09 -> JG-10 -> JG-11 -> JG-12 -> JG-13 -> JG-14
JG-14 -> JG-15 -> JG-16 -> JG-17 -> JG-18 -> JG-19 -> JG-20
JG-20 -> JG-21 -> JG-22
JG-22 + JG-14 -> JG-23 -> JG-24
JG-24 + JG-20 -> JG-25
JG-14 vagy JG-20 -> JG-26
JG-26 -> JG-27
```

## Critical path

- Rectangular: `JG-00 -> ... -> JG-14`
- Irregular/remnant: `JG-14 -> ... -> JG-20`
- Cavity: `JG-20 -> ... -> JG-25`
- Release: `JG-25 -> JG-26 -> JG-27`

## Checkpoints

- CHECKPOINT-0: Gate 0 (JG-00 + JG-01) zöld.
- CHECKPOINT-1: Gate 1 (JG-14 benchmark) zöld.
- CHECKPOINT-2: Gate 2 (JG-20 benchmark) zöld.
- CHECKPOINT-3: Gate 3 (JG-25 cavity bridge) zöld.
- CHECKPOINT-FINAL: Gate 4 (JG-27 release matrix) zöld.

Minden checkpointnál kötelező:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md
```

## Per-task runner references

- JG-00 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner/run.md`
  Status: present.
- JG-01 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit/run.md`
  Status: to be created by its own package task.
- JG-02 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold/run.md`
  Status: to be created by its own package task.
- JG-03 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate/run.md`
  Status: to be created by its own package task.
- JG-04 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc/run.md`
  Status: to be created by its own package task.
- JG-05 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures/run.md`
  Status: to be created by its own package task.
- JG-06 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache/run.md`
  Status: to be created by its own package task.
- JG-07 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model/run.md`
  Status: to be created by its own package task.
- JG-08 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1/run.md`
  Status: to be created by its own package task.
- JG-09 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics/run.md`
  Status: to be created by its own package task.
- JG-10 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1/run.md`
  Status: to be created by its own package task.
- JG-11 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t11_score_model_v1/run.md`
  Status: to be created by its own package task.
- JG-12 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1/run.md`
  Status: to be created by its own package task.
- JG-13 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1/run.md`
  Status: to be created by its own package task.
- JG-14 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix/run.md`
  Status: to be created by its own package task.
- JG-15 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike/run.md`
  Status: to be created by its own package task.
- JG-16 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin/run.md`
  Status: to be created by its own package task.
- JG-17 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation/run.md`
  Status: to be created by its own package task.
- JG-18 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation/run.md`
  Status: to be created by its own package task.
- JG-19 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1/run.md`
  Status: to be created by its own package task.
- JG-20 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/run.md`
  Status: to be created by its own package task.
- JG-21 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit/run.md`
  Status: to be created by its own package task.
- JG-22 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter/run.md`
  Status: to be created by its own package task.
- JG-23 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1/run.md`
  Status: to be created by its own package task.
- JG-24 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation/run.md`
  Status: to be created by its own package task.
- JG-25 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge/run.md`
  Status: to be created by its own package task.
- JG-26 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection/run.md`
  Status: to be created by its own package task.
- JG-27 expected runner path: `codex/prompts/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure/run.md`
  Status: to be created by its own package task.

## Phase gates

- Gate 0: JG-00 scaffold + JG-01 audit kész, showstopper nélkül.
- Gate 1: JG-14 rectangular benchmark validációval PASS.
- Gate 2: JG-20 irregular/remnant benchmark validációval PASS.
- Gate 3: JG-25 cavity bridge E2E PASS.
- Gate 4: JG-27 release decision matrix kész.

## Benchmark and validation policy

- Minden elfogadott layouthoz exact validator PASS kötelező.
- Invalid layoutot reportban explicit FAIL-ként kell jelölni.
- Benchmark report minimum metrikák: runtime, placed, unplaced, used_sheets, utilization.
- Determinizmus ellenőrzése fix seeddel kötelező.

## Rollback rules

1. Csak az adott task YAML `outputs` fájljaira rollbackelj.
2. Ha production diff guard sérül (`rust/**`, `worker/**`, `api/**`, `vrs_nesting/config/nesting_quality_profiles.py` nem megengedett taskban), azonnali rollback.
3. Feature-flagelt lépések rollbackje default safe módra állítással történjen.
4. Ha verify FAIL és blocker, státusz `REVISE` vagy `BLOCKED`, nem `PASS`.

## Reporting rules

1. Minden task report `docs/codex/report_standard.md` szerint készüljön.
2. A report végén kötelező status mező: `PASS`, `FAIL` vagy `PASS_WITH_NOTES`.
3. `AUTO_VERIFY` blokkot csak `./scripts/verify.sh` írhatja.
4. Checklist evidence nélkül nincs PASS.
5. Task szintű végső összegzés tartalmazza: status, changed files, verify parancs + log.

## Stop conditions

- Kötelező anchor hiányzik.
- A task csak scope-on kívüli fájlmódosítással teljesíthető.
- Exact validator invalid layoutot jelez.
- Repo gate nem futtatható dokumentálható ok nélkül.
