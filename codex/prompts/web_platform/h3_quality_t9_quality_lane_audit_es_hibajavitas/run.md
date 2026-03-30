# DXF Nesting Platform Codex Task - H3-Quality-T9 quality lane audit es hibajavitas
TASK_SLUG: h3_quality_t9_quality_lane_audit_es_hibajavitas

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t9_quality_lane_audit_es_hibajavitas.yaml`
- `canvases/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`
- `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
- `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `canvases/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `canvases/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `worker/main.py`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `scripts/check.sh`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task **nem** uj quality feature, nem migration, nem API schema es nem
  benchmark-refaktor. Kizarolag a bizonyitott closure-fix hibak javitasara szolgal.
- A `--compaction` fix a Python runner parser / arg-build retegben maradjon;
  ne bontsd meg a T7/T8 worker/profile truthot, ha erre nincs kozvetlen ok.
- A T1 smoke ne legyen sem stale literal, sem tul laza placeholder. Valodi,
  strukturalt evidence-t ellenorizzen.
- A T1/T6 historical artefaktoknal truth-preserving, minimalis korrekciot csinalj.
  Ne szelesits historical YAML outputs listat vakon, es ne vagd ki a report allitast
  sem vakon. Elobb nezd meg, melyik irany all osszhangban a repo jelenlegi evidenciaval.
- Ha a historical drift rendezesehez eleg a report pontositasa, ne irj at tobbet.
  Ha a YAML minimalis bovitese a helyesebb, akkor csak a szukseges fajlt add hozza.
- Az uj closure-fix smoke legyen olcso, pure-Python es determinisztikus. Ne igenyeljen
  Rust buildet, valodi Solvert, Supabase-t vagy worker processzt.

Implementacios elvarasok:
- A `vrs_nesting.runner.nesting_engine_runner` parser kapjon `--compaction off|slide`
  argumentumot `choices` validacioval.
- A `main()` epitse be ezt a flaget a `nesting_engine_cli_args` listaba, ugyanabban a
  mintaban, mint a `--placer`, `--search`, `--part-in-part` es SA flag-eket.
- A `run_nesting_engine()` ne kapjon kulon compaction special-case-et; a mar meglevo
  `extra_cli_args` uton menjen at a flag.
- A T1 smoke ellenorizze a valodi `engine_meta` truthot es a canonical artifact evidence-t.
- Az uj T9 smoke legalabb ezt bizonyitsa:
  - parser accepts `--compaction slide`;
  - a tovabbitott CLI args kozott tenyleg megjelenik a flag;
  - a T1 smoke jelen allapotban zold;
  - a T1/T6 historical taskoknal nincs outputs/report drift.
- A `scripts/check.sh` fusson az uj smoke-kal is.

A reportban kulon nevezd meg:
- pontosan miert torott a T7/T8 quality lane a Python runner parseren;
- hogyan bizonyitja az uj smoke, hogy a `--compaction` fix tenylegesen mukodik;
- miert volt stale a T1 smoke eredeti assertje;
- hogyan lett rendezve a T1/T6 outputs drift;
- hogy a task szandekosan closure-fix stabilizacio, nem uj feature.

Feladat-specifikus minimum bizonyitas:
- `python3 -m py_compile vrs_nesting/runner/nesting_engine_runner.py scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`
- `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `python3 scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`
- `python3 -m vrs_nesting.runner.nesting_engine_runner --input /tmp/missing.json --seed 1 --time-limit 1 --compaction slide`
  - itt az egyetlen elfogadhato hiba a parser utan mar input/binary runtime jellegu hiba;
    `unrecognized arguments: --compaction slide` nem maradhat.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`

Ez frissitse:
- `codex/reports/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`
- `codex/reports/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.verify.log`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
