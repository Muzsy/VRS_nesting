PASS

## 1) Meta
- Task slug: `dxf_prefilter_e2_t1_preflight_inspect_engine_v1`
- Kapcsolodo canvas: `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.yaml`
- Futas datuma: `2026-04-19`
- Branch / commit: (verify.sh tolti ki)
- Fokusz terulet: `Backend (inspect-only)`

## 2) Scope

### 2.1 Cel
- Minimal, public importer-inspect helper kinyitasa `vrs_nesting/dxf/importer.py` alatt (nincs uj parser).
- Normalized entity inventory bovitese a preflight T1-hez szukseges raw signalokkal (`layer`, `type`, `closed`, `color_index`, `linetype_name`).
- Kulon backend inspect service (`api/services/dxf_preflight_inspect.py`), amely nyers inspect result objektumot ad vissza kulon inventory + diagnostics reteggel.
- Task-specifikus unit teszt + smoke a determinisztikus backend-fuggetlen bizonyitasra.

### 2.2 Nem-cel (explicit)
- Role resolver / canonical `CUT_OUTER`/`CUT_INNER`/`MARKING` role assignment (E2-T2 marad).
- Gap repair / deduplikacio javitas / auto-fix (E2-T3/T4 marad).
- Normalized DXF writer (E2-T5 marad).
- Acceptance gate, DB persistence, API route, geometry import pipeline bekotes vagy frontend UI (E2-T6 / E3 marad).

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok
- Backend importer (raw inspect surface):
  - `vrs_nesting/dxf/importer.py`
- Backend inspect service:
  - `api/services/dxf_preflight_inspect.py`
- Tesztek / smoke:
  - `tests/test_dxf_preflight_inspect.py`
  - `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- Codex artefaktok:
  - `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
  - `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.yaml`
  - `codex/prompts/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1/run.md`
  - `codex/codex_checklist/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
  - `codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`

### 3.2 Miert valtoztak?
- Az importer minimal public inspect-felulettel egeszul ki (`normalize_source_entities`, `probe_layer_rings`), hogy a preflight inspect ne uj parhuzamos parserre, hanem a meglevo truth-lancra epuljon.
- Az inspect service kulon reteg; role assignment / repair / acceptance nelkul adja a nyers megfigyelest.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md` (a futas utan AUTO_VERIFY_START/END blokk tartalmazza a PASS/FAIL eredmenyet)

### 4.2 Opcionais, feladatfuggo parancsok
- `python3 -m py_compile vrs_nesting/dxf/importer.py api/services/dxf_preflight_inspect.py tests/test_dxf_preflight_inspect.py scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `python3 -m pytest -q tests/test_dxf_preflight_inspect.py`
- `python3 scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes; a verify.sh futtatja a teljes repo gate-et (pytest + mypy + Sparrow + DXF smoke suite + validator).

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Van minimal, public importer-felulet a raw inspect celra; nem uj parser logika keszult. | PASS | `vrs_nesting/dxf/importer.py:914`; `vrs_nesting/dxf/importer.py:944` | Az uj `normalize_source_entities` es `probe_layer_rings` public helperek a letezo `_normalize_entities` / `_collect_layer_rings` belso logikara epulnek, nem uj parser. | `tests/test_dxf_preflight_inspect.py:250`; `tests/test_dxf_preflight_inspect.py:274` |
| A normalized entity inventory hordozza a preflight T1-hez szukseges `layer/type/closed/color_index/linetype_name` raw signalokat. | PASS | `vrs_nesting/dxf/importer.py:143`; `vrs_nesting/dxf/importer.py:159`; `vrs_nesting/dxf/importer.py:176`; `vrs_nesting/dxf/importer.py:211`; `vrs_nesting/dxf/importer.py:290` | A JSON fixture parser es az ezdxf backend is beteszi a `color_index` / `linetype_name` raw signalokat; hiany eseten determinisztikusan `None` marad. | `tests/test_dxf_preflight_inspect.py:35`; `tests/test_dxf_preflight_inspect.py:250` |
| Letrejott kulon backend inspect service (`api/services/dxf_preflight_inspect.py`). | PASS | `api/services/dxf_preflight_inspect.py:48`; `api/services/dxf_preflight_inspect.py:78` | Az uj `DxfPreflightInspectError` + `inspect_dxf_source` belepesi pont kizarolag a public importer inspect helperre ul. | `tests/test_dxf_preflight_inspect.py:35`; `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py:1` |
| A service inspect result objektumot ad vissza, kulon inventory es diagnostics reteggel. | PASS | `api/services/dxf_preflight_inspect.py:118`; `api/services/dxf_preflight_inspect.py:137`; `api/services/dxf_preflight_inspect.py:159`; `api/services/dxf_preflight_inspect.py:197`; `api/services/dxf_preflight_inspect.py:205`; `api/services/dxf_preflight_inspect.py:341` | A `inspect_dxf_source` `entity_inventory` / `layer_inventory` / `color_inventory` / `linetype_inventory` / `diagnostics` retegeket kulon kulcsokon adja vissza. | `tests/test_dxf_preflight_inspect.py:35` |
| A service javitas nelkul tud konturjelolteket, open-path jelolteket, duplicate contour jelolteket es outer-like/inner-like jelolteket listazni. | PASS | `api/services/dxf_preflight_inspect.py:218`; `api/services/dxf_preflight_inspect.py:238`; `api/services/dxf_preflight_inspect.py:250`; `api/services/dxf_preflight_inspect.py:277` | `_build_contour_candidates` / `_build_open_path_candidates` / `_build_duplicate_contour_candidates` / `_build_topology_candidates` csak jelolteket listaz; nincs geometria-modositas vagy role-assignment. | `tests/test_dxf_preflight_inspect.py:92`; `tests/test_dxf_preflight_inspect.py:128`; `tests/test_dxf_preflight_inspect.py:157` |
| A task nem nyitotta meg a route/persistence/UI scope-ot. | PASS | `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.yaml:9`; `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py:59` | A YAML outputs listaja nem tartalmaz `api/routes/*`, `api/services/dxf_geometry_import.py`, DB migration vagy frontend fajlt; a smoke explicit `FORBIDDEN_KEYS` blokkja tiltja az acceptance / role / repair kulcsokat. | `./scripts/verify.sh --report ...` |
| A mai `import_part_raw()` acceptance viselkedese nem romlott. | PASS | `tests/test_dxf_importer_json_fixture.py:1`; `tests/test_dxf_importer_error_handling.py:1`; `scripts/smoke_dxf_import_convention.py:1`; `tests/test_dxf_preflight_inspect.py:299` | A meglevo importer unit + smoke tesztek tovabbra is zoldek; uj regression-guard teszt is igazolja, hogy `DXF_OPEN_OUTER_PATH` stabil marad. | `./scripts/verify.sh --report ...` |
| Keszult task-specifikus unit teszt es smoke script. | PASS | `tests/test_dxf_preflight_inspect.py:35`; `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py:1` | Deterministic JSON fixture alapu pytest csomag (10 teszt) + task-specifikus smoke script. | `python3 -m pytest -q tests/test_dxf_preflight_inspect.py`; `python3 scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py` |
| A checklist es report evidence-alapon frissult. | PASS | `codex/codex_checklist/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md:1`; `codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md:1` | Checklist pontjai evidence-alapon kipipalhatoak; a report DoD->Evidence matrixa konkret fajl+sor hivatkozasokat ad. | self-review |
| `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md` PASS. | PASS | lasd a file alan AUTO_VERIFY blokkot (eredmeny: PASS, check.sh exit: 0) | A repo gate wrapperrel fut, az eredmenyt az automatikus AUTO_VERIFY blokk rogziti. | `./scripts/verify.sh --report ...` |

## 6) Kulon kiemelesek (run.md kovetelmenyek)
- _Importer helper felulet_: a task csak `normalize_source_entities` es `probe_layer_rings` public helpereket vezeti be a meglevo `_normalize_entities` / `_collect_layer_rings` korul.
- _`import_part_raw()` kompatibilitas_: a belso parser logika nem valtozott, csak a normalized entity dict kapott optional `color_index` / `linetype_name` mezoket, amelyeket a letezo codelancok nem olvasnak.
- _Raw signalok_: `layer`, `type`, `closed`, `color_index` (int | None), `linetype_name` (str | None), plusz point_count / bbox szintu strukturalis adat.
- _Deterministic bizonyitekok_: JSON fixture alapu pytest + smoke script (nincs `ezdxf` fuggoseg a T1 evidence-hez).
- _T2..T6 scope-ban marad_: T2 role resolver, T3 gap repair, T4 duplicate dedupe, T5 normalized DXF writer, T6 acceptance gate + geometry import / route / UI bekotes.

## 7) Advisory notes
- A `color_index` raw ACI tartomanyt tukroz; kesobb az E2-T2 role resolver hozza ossze a canonical role-policyval (pl. BYLAYER / red / green semantika). V1-ben tudatosan nem ertelmezzuk.
- A duplicate contour jelolt koordinata-alapu fingerprintre epul; az orientacio-invariancia es a cyclic-shift normalizalas a T4 dedupe feladat resze lesz.
- Az outer-like/inner-like jelzes jelen T1-ben bbox-alapu topology proxy; a T2 role resolver polygon containment alapon finomithatja, ez mostani scope-bol tudatosan kimarad.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-19T21:42:52+02:00 → 2026-04-19T21:45:46+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.verify.log`
- git: `main@ebeca05`
- módosított fájlok (git status): 118

**git diff --stat**

```text
 .claude/settings.json                              |   6 +-
 scripts/bench_nesting_engine_f2_3_large_fixture.py |   0
 scripts/canonicalize_json.py                       |   0
 scripts/check.sh                                   |   0
 scripts/ensure_sparrow.sh                          |   0
 scripts/export_openapi_schema.py                   |   0
 scripts/export_real_dxf_nfp_pairs.py               |   0
 scripts/fuzz_nfp_regressions.py                    |   0
 scripts/gen_h3_quality_benchmark_fixtures.py       |   0
 scripts/gen_nesting_engine_large_fixture.py        |   0
 .../gen_nesting_engine_real_dxf_quality_fixture.py |   0
 scripts/run_h3_quality_benchmark.py                |   0
 scripts/run_real_dxf_sparrow_pipeline.py           |   0
 scripts/run_sparrow_smoketest.sh                   |   0
 scripts/run_trial_run_tool.py                      |   0
 scripts/run_web_platform.sh                        |   0
 scripts/smoke_docs_commands.py                     |   0
 scripts/smoke_dxf_import_convention.py             |   0
 .../smoke_export_original_geometry_block_insert.py |   0
 scripts/smoke_export_run_dir_out.py                |   0
 scripts/smoke_geometry_pipeline.py                 |   0
 ...pload_endpoint_service_h0_schema_realignment.py |   0
 ...smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py |   0
 scripts/smoke_h1_e2_t1_dxf_parser_integracio.py    |   0
 scripts/smoke_h1_e2_t2_geometry_normalizer.py      |   0
 .../smoke_h1_e2_t3_validation_report_generator.py  |   0
 ..._t4_geometry_derivative_generator_h1_minimum.py |   0
 ...ion_service_es_derivative_binding_h1_minimum.py |   0
 ...e_h1_e3_t2_sheet_creation_service_h1_minimum.py |   0
 ...t3_project_requirement_management_h1_minimum.py |   0
 ...t4_project_sheet_input_management_h1_minimum.py |   0
 ...oke_h1_e4_t1_run_snapshot_builder_h1_minimum.py |   0
 ...e_h1_e4_t2_run_create_api_service_h1_minimum.py |   0
 ...ke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py |   0
 ...5_t1_engine_adapter_input_mapping_h1_minimum.py |   0
 ..._h1_e5_t2_solver_process_futtatas_h1_minimum.py |   0
 .../smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py |   0
 .../smoke_h1_e6_t1_result_normalizer_h1_minimum.py |   0
 ...moke_h1_e6_t2_sheet_svg_generator_h1_minimum.py |   0
 ...eet_dxf_export_artifact_generator_h1_minimum.py |   0
 scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py |   0
 scripts/smoke_h1_e7_t2_h1_audit_es_hibajavitas.py  |   0
 scripts/smoke_h1_real_artifact_chain_closure.py    |   0
 scripts/smoke_h1_real_infra_closure.py             |   0
 .../smoke_h1_real_solver_artifact_chain_closure.py |   0
 ...oke_h2_e1_t2_project_manufacturing_selection.py |   0
 ...anufacturing_canonical_derivative_generation.py |   0
 ...moke_h2_e2_t2_contour_classification_service.py |   0
 scripts/smoke_h2_e3_t1_cut_rule_set_model.py       |   0
 scripts/smoke_h2_e3_t2_cut_contour_rules_model.py  |   0
 scripts/smoke_h2_e3_t3_rule_matching_logic.py      |   0
 ...moke_h2_e4_t1_snapshot_manufacturing_bovites.py |   0
 .../smoke_h2_e4_t2_manufacturing_plan_builder.py   |   0
 ...ke_h2_e4_t3_manufacturing_metrics_calculator.py |   0
 .../smoke_h2_e5_t1_manufacturing_preview_svg.py    |   0
 ...tprocessor_profile_version_domain_aktivalasa.py |   0
 scripts/smoke_h2_e5_t3_machine_neutral_exporter.py |   0
 ...smoke_h2_e5_t4_elso_machine_specific_adapter.py |   0
 ...5_masodik_machine_specific_adapter_qtplasmac.py |   0
 ...moke_h2_e6_t1_end_to_end_manufacturing_pilot.py |   0
 scripts/smoke_h2_e6_t2_h2_audit_es_hibajavitas.py  |   0
 ...smoke_h3_e1_t1_run_strategy_profile_modellek.py |   0
 scripts/smoke_h3_e1_t2_scoring_profile_modellek.py |   0
 .../smoke_h3_e1_t3_project_level_selectionok.py    |   0
 scripts/smoke_h3_e2_t1_run_batch_modell.py         |   0
 scripts/smoke_h3_e2_t2_batch_run_orchestrator.py   |   0
 scripts/smoke_h3_e3_t1_run_evaluation_engine.py    |   0
 scripts/smoke_h3_e3_t2_ranking_engine.py           |   0
 ...moke_h3_e3_t3_best_by_objective_lekerdezesek.py |   0
 ...y_t1_engine_observability_and_artifact_truth.py |   0
 ...2_benchmark_pack_and_quality_summary_harness.py |   0
 ...ity_t3_snapshot_to_nesting_engine_v2_adapter.py |   0
 ...quality_t4_worker_dual_engine_runtime_bridge.py |   0
 ...5_viewer_data_v2_truth_and_artifact_evidence.py |   0
 ...6_local_tool_backend_selector_and_ab_compare.py |   0
 ..._quality_profiles_and_run_config_integration.py |   0
 ...tic_compaction_postpass_and_profile_evidence.py |   0
 ...quality_t9_quality_lane_audit_es_hibajavitas.py |   0
 scripts/smoke_multisheet_wrapper_edge_cases.py     |   0
 scripts/smoke_nesting_engine_determinism.sh        |   0
 ...moke_nesting_engine_float_policy_determinism.sh |   0
 scripts/smoke_nesting_engine_sa_cli.py             |   0
 scripts/smoke_nfp_placer_stats_and_perf_gate.py    |   0
 scripts/smoke_part_in_part_pipeline.py             |   0
 ...ke_phase1_api_auth_projects_files_validation.py |   0
 scripts/smoke_phase1_storage_bucket_policies.py    |   0
 scripts/smoke_phase1_supabase_schema_state.py      |   0
 scripts/smoke_phase2_dod_acceptance.py             |   0
 scripts/smoke_phase4_auth_security_config.py       |   0
 scripts/smoke_phase4_cleanup_lifecycle.py          |   0
 scripts/smoke_phase4_load_profile.py               |   0
 scripts/smoke_placement_export_bbox_origin_fix.py  |   0
 scripts/smoke_platform_determinism_rotation.sh     |   0
 scripts/smoke_real_dxf_fixtures.py                 |   0
 scripts/smoke_real_dxf_nfp_pairs.py                |   0
 scripts/smoke_real_dxf_sparrow_pipeline.py         |   0
 scripts/smoke_sparrow_determinism.py               |   0
 scripts/smoke_stock_fixture_size_contract.py       |   0
 scripts/smoke_svg_export.py                        |   0
 scripts/smoke_time_budget_guard.py                 |   0
 scripts/smoke_trial_run_tool_cli_core.py           |   0
 scripts/smoke_trial_run_tool_tkinter_gui.py        |   0
 scripts/trial_run_tool_core.py                     |   0
 scripts/trial_run_tool_gui.py                      |   0
 scripts/uptime_health_ping.py                      |   0
 scripts/validate_nesting_solution.py               |   0
 scripts/validate_sparrow_io.py                     |   0
 scripts/verify.sh                                  |   0
 vrs_nesting/dxf/importer.py                        | 157 ++++++++++++++++++++-
 109 files changed, 161 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .claude/settings.json
 M scripts/bench_nesting_engine_f2_3_large_fixture.py
 M scripts/canonicalize_json.py
 M scripts/check.sh
 M scripts/ensure_sparrow.sh
 M scripts/export_openapi_schema.py
 M scripts/export_real_dxf_nfp_pairs.py
 M scripts/fuzz_nfp_regressions.py
 M scripts/gen_h3_quality_benchmark_fixtures.py
 M scripts/gen_nesting_engine_large_fixture.py
 M scripts/gen_nesting_engine_real_dxf_quality_fixture.py
 M scripts/run_h3_quality_benchmark.py
 M scripts/run_real_dxf_sparrow_pipeline.py
 M scripts/run_sparrow_smoketest.sh
 M scripts/run_trial_run_tool.py
 M scripts/run_web_platform.sh
 M scripts/smoke_docs_commands.py
 M scripts/smoke_dxf_import_convention.py
 M scripts/smoke_export_original_geometry_block_insert.py
 M scripts/smoke_export_run_dir_out.py
 M scripts/smoke_geometry_pipeline.py
 M scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py
 M scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py
 M scripts/smoke_h1_e2_t1_dxf_parser_integracio.py
 M scripts/smoke_h1_e2_t2_geometry_normalizer.py
 M scripts/smoke_h1_e2_t3_validation_report_generator.py
 M scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py
 M scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py
 M scripts/smoke_h1_e3_t2_sheet_creation_service_h1_minimum.py
 M scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py
 M scripts/smoke_h1_e3_t4_project_sheet_input_management_h1_minimum.py
 M scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py
 M scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py
 M scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py
 M scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py
 M scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py
 M scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py
 M scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py
 M scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py
 M scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py
 M scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py
 M scripts/smoke_h1_e7_t2_h1_audit_es_hibajavitas.py
 M scripts/smoke_h1_real_artifact_chain_closure.py
 M scripts/smoke_h1_real_infra_closure.py
 M scripts/smoke_h1_real_solver_artifact_chain_closure.py
 M scripts/smoke_h2_e1_t2_project_manufacturing_selection.py
 M scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py
 M scripts/smoke_h2_e2_t2_contour_classification_service.py
 M scripts/smoke_h2_e3_t1_cut_rule_set_model.py
 M scripts/smoke_h2_e3_t2_cut_contour_rules_model.py
 M scripts/smoke_h2_e3_t3_rule_matching_logic.py
 M scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py
 M scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py
 M scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py
 M scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py
 M scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py
 M scripts/smoke_h2_e5_t3_machine_neutral_exporter.py
 M scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py
 M scripts/smoke_h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.py
 M scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py
```

<!-- AUTO_VERIFY_END -->
