# DXF Prefilter E3-T2 Upload utani preflight trigger bekotes
TASK_SLUG: dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `api/routes/files.py`
- `api/services/file_ingest_metadata.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `api/services/dxf_preflight_acceptance_gate.py`
- `api/services/dxf_preflight_diagnostics_renderer.py`
- `api/services/dxf_preflight_persistence.py`
- `canvases/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- `canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **upload utani preflight trigger integration task**. Ne vezess be explicit preflight-start API route-ot,
  geometry import gate-et, feature flaget, UI-t vagy rules-profile domaint.
- A `complete_upload` route response shape-ja maradjon valtozatlan.
- A meglevo geometry import es legacy readability background task maradjon bent; a task csak preflight triggert kot be mellejuk.
- A runtime service a meglevo E2/T7 + E3-T1 service-eket hivja; ne duplikalj inspect/repair/writer/gate/render/persist logikat.
- Current-code truth szerint nincs implementalt rules-profile domain es nincs project-level active dxf-rules selection.
  A runtime V1 bridge-kent `rules_profile=None` / ures snapshot vilagban fusson.
- A `run_seq` ne kliens inputbol jojjon; service-side, az `app.preflight_runs` truth-bol legyen szamolva.
- A trigger FastAPI `BackgroundTasks`-ra uljon; ne vezess be worker queue-t, outboxot vagy polling workflow-t.
- A minimalis failure handling logger-alapu legyen; ahol lehet, persisted `preflight_failed` truth legyen, de ne nyiss teljes lifecycle/polling scope-ot.

Modellezesi elvek:
- Az uj runtime/orchestration service letolti a source DXF-et storage-bol temp path-ra, majd sorrendben hivja:
  1. `inspect_dxf_source(...)`
  2. `resolve_dxf_roles(...)`
  3. `repair_dxf_gaps(...)`
  4. `dedupe_dxf_duplicate_contours(...)`
  5. `write_normalized_dxf(...)`
  6. `evaluate_dxf_prefilter_acceptance_gate(...)`
  7. `render_dxf_preflight_diagnostics_summary(...)`
  8. `persist_preflight_run(...)`
- A normalized writer output path tempdiren belul legyen; ne talalj ki globalis artifact cache-t.
- A trigger jelenleg nem gate: a geometry import task marad, es a preflight task mellette fut.
- A preflight runtime csak `source_dxf` + `.dxf` finalize eseten triggerelodjon.
- A route integration legyen minimalis-invaziv: a route tovabbra is ugyanazt a `ProjectFileResponse`-t adja vissza.

Kulon figyelj:
- az E3-T2-ben ne csuszz at E3-T3 geometry import gate scope-ba;
- az E3-T2-ben ne csuszz at E3-T4 replace/rerun flow scope-ba;
- az E3-T2-ben ne csuszz at E3-T5 feature flag/rollout scope-ba;
- ha a runtime-nak helper kell a persistence service-ben, csak minimalis, current-scope kompatibilis bovitest vegezz;
- a smoke legyen deterministic, monkeypatch/fake gateway alapon; ne tegyel kotelezove valodi Supabase-hozzaferest vagy valodi DXF fixture futast csak a trigger miatt.

A reportban kulon nevezd meg:
- hogyan lett a preflight runtime/orchestration boundary kialakitva;
- miert marad bent a geometry import trigger is ebben a taskban;
- hogyan szamolodik a `run_seq` a mar letezo `preflight_runs` truth-bol;
- hogyan kezeli a task a rules-profile domain jelenlegi hianyat;
- hogyan nez ki a minimalis failure handling;
- hogyan bizonyitja a tesztcsomag a runtime lancot es a route-trigger integraciot;
- mi marad kifejezetten E3-T3 / E3-T4 / E3-T5 / kesobbi explicit preflight API es UI scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
