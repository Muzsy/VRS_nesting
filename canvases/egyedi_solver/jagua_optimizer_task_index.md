# Jagua optimizer — task index

## Source of truth

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `canvases/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t00_task_scaffold_and_master_runner.yaml`

## Strategic decision

- `jagua-rs` szerepe: collision/geometriai backend.
- Saját optimizer réteg épül rá fixed-sheet és multi-sheet célra.
- Fázisolt megvalósítás: rectangular -> irregular/remnant -> cavity-prepack.
- Minden fázisban kötelező exact final validation és reprodukálható benchmark.
- A Sparrow nem kész solver-coreként kerül átvételre, hanem szelektív algoritmikus mintaforrásként.

## Global invariants

- `REAL_CODE_ONLY`: csak valós repo-elemekre támaszkodhatunk.
- `NO_SILENT_GEOMETRY_LOSS`: nem veszhet el contour/hole/identity/quantity/transzform.
- `EXACT_VALIDATION_REQUIRED`: invalid layout nem lehet sikeres.
- `CHECKLIST_REQUIRED`: report és checklist evidence nélkül nincs PASS.
- Determinizmus: seed + input -> reprodukálható eredmény.
- Time budget: explicit limit és stop policy minden hosszú kereséshez.
- Feature gating: új jagua útvonal nem törheti a régi backendeket.

## Real repo anchors

Ellenőrzött anchorok (`FOUND`):

- `rust/vrs_solver/Cargo.toml`
- `rust/vrs_solver/src/main.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/cavity_prepack.py`
- `worker/cavity_validation.py`
- `scripts/validate_nesting_solution.py`
- `scripts/validate_sparrow_io.py`
- `scripts/run_sparrow_smoketest.sh`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_engine/cavity_prepack_contract_v2.md`
- `docs/solver_io_contract.md`

## Baseline preflight

- Kötelező tooling: `python3`, `cargo`, repo rootban futó `./scripts/verify.sh`.
- Kötelező szabályfájlok: `AGENTS.md`, `docs/codex/*`, `docs/qa/testing_guidelines.md`.
- Kötelező anchor ellenőrzés: solver/runtime/cavity/validator pathok létezése.
- Ha preflight FAIL: `BLOCKED` státusz és explicit hibapont.

## Task list

| Task | Slug | Phase | Cél | Függőség | Expected canvas | Expected goal YAML | Expected runner | Expected checklist | Expected report | Acceptance gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JG-00 | `jagua_optimizer_t00_task_scaffold_and_master_runner` | 0 / scaffold | Task index + master runner scaffold | — | `canvases/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t00_task_scaffold_and_master_runner.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md` | `codex/reports/egyedi_solver/jagua_optimizer_t00_task_scaffold_and_master_runner.md` | JG-00..JG-27 index + dependency graph + phase gate + self-contained master runner |
| JG-01 | `jagua_optimizer_t01_repo_and_source_audit` | 0 / audit | Repo + jagua + Sparrow audit | JG-00 | `canvases/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t01_repo_and_source_audit.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md` | `codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md` | Anchor/képesség/kockázat audit táblázat kész |
| JG-02 | `jagua_optimizer_t02_solver_module_scaffold` | 0 / architecture | `vrs_solver` moduláris scaffold viselkedésváltozás nélkül | JG-01 | `canvases/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t02_solver_module_scaffold.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md` | `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md` | Build + smoke regressziómentes |
| JG-03 | `jagua_optimizer_t03_outer_only_contract_and_hole_gate` | 1 / rectangular preflight | Outer-only contract + hole gate | JG-02 | `canvases/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t03_outer_only_contract_and_hole_gate.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md` | `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md` | Hole-os input explicit unsupported/error |
| JG-04 | `jagua_optimizer_t04_jagua_adapter_contract_poc` | 1 / backend adapter | jagua adapter contract PoC | JG-02, JG-03 | `canvases/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t04_jagua_adapter_contract_poc.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` | `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` | Adapter valid/invalid smoke + model izoláció |
| JG-05 | `jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures` | 1 / rectangular sheets | Rectangular sheet provider + fixturek | JG-03, JG-04 | `canvases/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md` | `codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md` | Multi-sheet fixture + validator PASS |
| JG-06 | `jagua_optimizer_t06_item_geometry_store_and_rotation_cache` | 1 / item model | Item geometry store + rotation cache | JG-05 | `canvases/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t06_item_geometry_store_and_rotation_cache.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md` | `codex/reports/egyedi_solver/jagua_optimizer_t06_item_geometry_store_and_rotation_cache.md` | Stabil instance + rotation ordering |
| JG-07 | `jagua_optimizer_t07_layout_state_and_candidate_model` | 1 / optimizer core | Layout state + candidate model | JG-06 | `canvases/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t07_layout_state_and_candidate_model.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` | `codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` | State tesztek és v1 contract kompatibilis |
| JG-08 | `jagua_optimizer_t08_initial_construction_placer_v1` | 1 / initial placement | Initial construction placer | JG-07, JG-04 | `canvases/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t08_initial_construction_placer_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md` | Valid elhelyezés, invalid sosem sikeres |
| JG-09 | `jagua_optimizer_t09_exact_validation_bridge_and_metrics` | 1 / validation | Exact validator bridge + metrikák | JG-08 | `canvases/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t09_exact_validation_bridge_and_metrics.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md` | `codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md` | PASS/FAIL korrekt + runtime/placement metrikák |
| JG-10 | `jagua_optimizer_t10_repair_search_loop_v1` | 1 / repair search | Repair search loop | JG-09 | `canvases/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t10_repair_search_loop_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md` | Javítás valid lesz, time-limit + determinizmus |
| JG-11 | `jagua_optimizer_t11_score_model_v1` | 1 / objective | Score model v1 | JG-10 | `canvases/egyedi_solver/jagua_optimizer_t11_score_model_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t11_score_model_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t11_score_model_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md` | Score breakdown auditálható |
| JG-12 | `jagua_optimizer_t12_multi_sheet_manager_v1` | 1 / multi-sheet | Multi-sheet manager | JG-11 | `canvases/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t12_multi_sheet_manager_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` | `sheet_count_used` pontos és determinisztikus |
| JG-13 | `jagua_optimizer_t13_sheet_elimination_v1` | 1 / sheet count reduction | Sheet elimination | JG-12 | `canvases/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t13_sheet_elimination_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md` | Elimináció rollback-biztos |
| JG-14 | `jagua_optimizer_t14_phase1_benchmark_matrix` | 1 / benchmark gate | Phase1 benchmark matrix | JG-13 | `canvases/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t14_phase1_benchmark_matrix.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` | `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` | Minden elfogadott layout validator PASS |
| JG-15 | `jagua_optimizer_t15_irregular_sheet_capability_spike` | 2 / irregular spike | Irregular capability spike | JG-14 | `canvases/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t15_irregular_sheet_capability_spike.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` | `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` | PASS/NO-GO döntési report |
| JG-16 | `jagua_optimizer_t16_irregular_sheet_provider_and_margin` | 2 / irregular provider | Irregular provider + margin policy | JG-15 | `canvases/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t16_irregular_sheet_provider_and_margin.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` | `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` | Irregular input valid, rectangular regresszió nincs |
| JG-17 | `jagua_optimizer_t17_irregular_boundary_validation` | 2 / boundary validation | Irregular boundary validation | JG-16 | `canvases/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t17_irregular_boundary_validation.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md` | `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md` | Kilógás FAIL, belül PASS |
| JG-18 | `jagua_optimizer_t18_irregular_candidate_generation` | 2 / irregular search | Irregular candidate generation | JG-17 | `canvases/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t18_irregular_candidate_generation.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md` | `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md` | Candidate/rejection report + determinizmus |
| JG-19 | `jagua_optimizer_t19_remnant_score_model_v1` | 2 / remnant scoring | Remnant score model | JG-18 | `canvases/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t19_remnant_score_model_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md` | Sheet-cost és utilization breakdown |
| JG-20 | `jagua_optimizer_t20_phase2_irregular_benchmark_matrix` | 2 / benchmark gate | Phase2 irregular benchmark | JG-19 | `canvases/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t20_phase2_irregular_benchmark_matrix.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` | `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` | Irregular benchmark valid + no rectangular regresszió |
| JG-21 | `jagua_optimizer_t21_cavity_prepack_integration_audit` | 3 / cavity audit | Cavity integration audit | JG-20 | `canvases/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t21_cavity_prepack_integration_audit.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md` | `codex/reports/egyedi_solver/jagua_optimizer_t21_cavity_prepack_integration_audit.md` | Bridge pontok és hiányok auditálva |
| JG-22 | `jagua_optimizer_t22_cavity_extraction_and_usability_filter` | 3 / cavity model | Cavity extraction/filter | JG-21 | `canvases/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t22_cavity_extraction_and_usability_filter.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md` | `codex/reports/egyedi_solver/jagua_optimizer_t22_cavity_extraction_and_usability_filter.md` | Hole metadata megmarad + usability reasons |
| JG-23 | `jagua_optimizer_t23_single_child_cavity_prepack_v1` | 3 / cavity prepack v1 | Single-child cavity prepack | JG-22, JG-14 | `canvases/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t23_single_child_cavity_prepack_v1.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md` | `codex/reports/egyedi_solver/jagua_optimizer_t23_single_child_cavity_prepack_v1.md` | Child lokálisan valid + macro metadata |
| JG-24 | `jagua_optimizer_t24_macro_part_expansion_and_final_validation` | 3 / expansion | Macro expansion + exact final validation | JG-23 | `canvases/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t24_macro_part_expansion_and_final_validation.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md` | `codex/reports/egyedi_solver/jagua_optimizer_t24_macro_part_expansion_and_final_validation.md` | Minden instance pontosan egyszer + validator PASS |
| JG-25 | `jagua_optimizer_t25_cavity_prepack_main_solver_bridge` | 3 / solver bridge | Cavity bridge a main solverbe | JG-24, JG-20 | `canvases/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t25_cavity_prepack_main_solver_bridge.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md` | `codex/reports/egyedi_solver/jagua_optimizer_t25_cavity_prepack_main_solver_bridge.md` | Rectangular+cavity E2E PASS, geometry loss nincs |
| JG-26 | `jagua_optimizer_t26_quality_profiles_and_backend_selection` | 4 / integration | Backend/profile capability wiring | JG-14 vagy JG-20; cavity flags csak JG-25 után | `canvases/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t26_quality_profiles_and_backend_selection.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md` | `codex/reports/egyedi_solver/jagua_optimizer_t26_quality_profiles_and_backend_selection.md` | Capability flags és backward compatibility |
| JG-27 | `jagua_optimizer_t27_final_benchmark_and_release_closure` | 5 / release gate | Final benchmark és release döntés | JG-26; Phase 3 csak JG-25 után | `canvases/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md` | `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t27_final_benchmark_and_release_closure.yaml` | `codex/prompts/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure/run.md` | `codex/codex_checklist/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md` | `codex/reports/egyedi_solver/jagua_optimizer_t27_final_benchmark_and_release_closure.md` | Continue/revise/stop döntés validációs bizonyítékokkal |

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

## Execution order

- Kötelező sorrend: a `Dependency graph` topologikus rendje.
- Javasolt lineáris főút: `JG-00 -> JG-01 -> ... -> JG-27`.
- Párhuzamosítás csak a `Parallelization notes` szerint.

## Critical path

Rectangular:

```text
JG-00 -> JG-01 -> JG-02 -> JG-03 -> JG-04 -> JG-05 -> JG-06 -> JG-07 -> JG-08 -> JG-09 -> JG-10 -> JG-11 -> JG-12 -> JG-13 -> JG-14
```

Irregular/remnant:

```text
JG-14 -> JG-15 -> JG-16 -> JG-17 -> JG-18 -> JG-19 -> JG-20
```

Cavity:

```text
JG-20 -> JG-21 -> JG-22 -> JG-23 -> JG-24 -> JG-25
```

Release:

```text
JG-25 -> JG-26 -> JG-27
```

## Phase gates

- Gate 0 (Scaffold + audit): JG-00 és JG-01 kész, showstopper nélkül.
- Gate 1 (Rectangular viability): JG-14 valid benchmark, exact validator PASS, hole input explicit unsupported.
- Gate 2 (Irregular viability): JG-20 valid benchmark, nincs rectangular regresszió.
- Gate 3 (Cavity viability): JG-25 E2E cavity bridge valid, geometry loss nélkül.
- Gate 4 (Release): JG-27 döntési report és benchmark matrix kész.

## Parallelization notes

- JG-15..JG-20 közben JG-21 audit párhuzamosítható.
- JG-22+ implementáció csak Gate 2 után indulhat.
- JG-26 profile integráció csak JG-14 vagy JG-20 után, cavity flags csak JG-25 után.

## First package batch

1. `jagua_optimizer_t00_task_scaffold_and_master_runner`
2. `jagua_optimizer_t01_repo_and_source_audit`
3. `jagua_optimizer_t02_solver_module_scaffold`
4. `jagua_optimizer_t03_outer_only_contract_and_hole_gate`
5. `jagua_optimizer_t04_jagua_adapter_contract_poc`

## Stop conditions

- Kötelező repo anchor hiányzik.
- `jagua-rs` API nem illeszthető a tervezett adapterhez.
- Scope-on túli fájlmódosítás kellene.
- Phase 1/2 hole input csak silent droppal lenne kezelhető.
- Exact validator invalid layoutot jelez.
- Repo gate nem futtatható és az ok nem dokumentálható.
- A task diff túl nagy biztonságos review-hoz.

## Rollback rules

1. Minden rollback taskonként, az adott YAML `outputs` fájljaira korlátozva történik.
2. Scope-on kívüli production módosítás esetén azonnali rollback szükséges.
3. Benchmark/profil váltás rollbackje feature-flag biztonságos alapállapotra történjen.
4. Verify FAIL esetén `PASS` státusz nem adható.

## Reporting rules

1. Report formátum: `docs/codex/report_standard.md`.
2. Kötelező verify parancs: `./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md`.
3. Minden DoD ponthoz evidence és parancslog hivatkozás kell.
4. AUTO_VERIFY blokk kézi szerkesztése tilos.

## REQUIRES_DECISION

- Eltérés rögzítve: a régebbi `jagua_rs_sajat_optimizer_fejlesztesi_terv.md` még JG-00 audit fókuszt említ, míg a `jagua_optimizer_canvas_yaml_runner_task_bontas.md` + `jagua_optimizer_task_progress_checklist.md` + `jagua_optimizer_master_plan.md` alapján a hivatalos JG-00 scope scaffold/master-runner.
- A jelen index a hivatalos task-bontásos forrásokat tekinti elsődlegesnek.
