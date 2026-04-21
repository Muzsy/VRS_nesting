# DXF Prefilter E3-T3 Geometry import gate bekotes
TASK_SLUG: dxf_prefilter_e3_t3_geometry_import_gate_integration

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `api/routes/files.py`
- `api/services/dxf_preflight_runtime.py`
- `api/services/dxf_preflight_persistence.py`
- `api/services/dxf_preflight_acceptance_gate.py`
- `api/services/dxf_geometry_import.py`
- `api/services/dxf_validation.py`
- `canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t3_geometry_import_gate_integration.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **geometry import gate integration task**. Ne vezess be explicit preflight route-ot,
  review workflow-t, replace/rerun flow-t, feature flaget, UI-t vagy rules-profile domaint.
- A `complete_upload` response shape maradjon valtozatlan.
- A geometry import tobbe ne a route-bol induljon kozvetlenul source DXF finalize utan.
- A legacy `validate_dxf_file_async(...)` secondary signal maradjon bent a route-ban.
- A gate-et a meglevo E3-T2 runtime-hoz kossd, ne talalj ki kulon worker queue-t vagy polling workflow-t.
- A geometry import inputja a persisted `normalized_dxf` artifact storage truth legyen, ne a nyers source DXF.
- A meglevo geometry import pipeline-t ne duplikald; csak minimalis helper/generic storage-import boundary nyithato.
- Ne vezess be uj migrationt vagy kulon DB lifecycle-mezot csak az `imported` bridge miatt.
- Geometry import helper hiba eseten logger warning + swallowed failure eleg V1-ben; ne torje el a `complete_upload` HTTP valaszt.

Modellezesi elvek:
- A route source DXF finalize utan mar csak ket hattertaskot regisztraljon:
  1. `validate_dxf_file_async(...)`
  2. `run_preflight_for_upload(...)`
- A preflight runtime persistence utan ellenorizze a persisted acceptance outcome-ot.
- Ha `accepted_for_import`, akkor keresse ki a persisted `artifact_refs` kozul a `normalized_dxf` ref-et,
  es csak erre inditsa el a geometry importot.
- Ha `preflight_rejected` vagy `preflight_review_required`, akkor explicit skip/log legyen.
- Ha accepted, de nincs `normalized_dxf` artifact ref, akkor is skip/log legyen; tilos nyers source fallbacket bevezetni.
- Ha kell, a `api/services/dxf_geometry_import.py` oldalon nyiss minimalis generic helper-boundaryt,
  hogy a meglevo import pipeline storage-backed normalized artifact ref-rol is meghivhato legyen.
- A geometry import tovabbra is ugyanazt a canonical geometry + validator + derivative lancot hasznalja.

Kulon figyelj:
- az E3-T3-ban ne csuszz at E3-T4 replace/rerun scope-ba;
- az E3-T3-ban ne csuszz at E3-T5 feature flag/rollout scope-ba;
- az E3-T3-ban ne csuszz at explicit preflight API/artifact download scope-ba;
- ne talalj ki uj `imported` DB allapotot migration nelkul;
- az eredeti `source_file_object_id` linkage maradjon meg a geometry importnal is;
- a `source_hash_sha256` current-code truth-ja maradjon az eredeti feltoltott source file hash, ne talalj ki uj hash-szemantikat.

A reportban kulon nevezd meg:
- miert kellett a geometry importot kivenni a route-bol;
- hogyan kapcsolodik a gate a persisted acceptance outcome-hoz;
- miert a `normalized_dxf` artifact a geometry import input;
- hogyan marad bent a legacy validation secondary signalkent;
- hogyan kezeli a task az import-failure minimalis logger boundaryt;
- mit bizonyitanak a unit tesztek es a smoke-ok;
- mi marad kifejezetten E3-T4 / E3-T5 / kesobbi explicit preflight API es UI scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
