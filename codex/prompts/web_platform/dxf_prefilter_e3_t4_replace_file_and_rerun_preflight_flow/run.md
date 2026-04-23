# DXF Prefilter E3-T4 Replace file es re-run preflight flow
TASK_SLUG: dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `api/routes/files.py`
- `api/request_models.py`
- `api/services/dxf_preflight_runtime.py`
- `api/services/dxf_preflight_persistence.py`
- `canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `canvases/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **backend replace-file + implicit rerun** task. Ne nyiss UI scope-ot, ne modositsd a DxfIntakePage-et.
- Ne vezess be kulon manualis rerun endpointot.
- A replace flow a meglevo signed-upload + complete_upload ketlepeses mintara epuljon.
- A regi file objectet ne ird felul in-place uj tartalommal.
- A regi file objecthez tartozo preflight runok auditkent maradjanak meg.
- A replacement lineage-hez minimalis persisted truth kell; ne maradjon pusztan response-level informacio.
- Ne nyiss review workflow, artifact download, feature flag vagy rollout scope-ot.

Modellezesi elvek:
- A replace action route a `POST /projects/{project_id}/files/{file_id}/replace` legyen.
- A route validalja, hogy a target file letezik, a projekthez tartozik es `source_dxf` jellegu.
- A route uj replacement file_id-t generaljon es signed upload URL-t adjon vissza a jelenlegi upload-url mintahoz igazodva.
- A `complete_upload` kapjon optional replacement bridge mezot.
- A `file_objects` domainben jelenjen meg minimalis persisted replacement lineage truth (self-FK irany a helyes current-code V1 megoldas).
- Replacement finalize utan a meglevo source DXF branch ugyanugy inditsa el:
  1. `validate_dxf_file_async(...)`
  2. `run_preflight_for_upload(...)`
- Ez a rerun current-code truth szerint eleg; ne talalj ki kulon `rerun` endpointot.
- Ne torold automatikusan a regi storage objectet es ne implementalj superseded-file hiding/grouping UX-et.

Kulon figyelj:
- az E3-T4-ben ne csuszz at E3-T5 feature flag/rollout scope-ba;
- ne csuszz at UI button vagy lineage table UX scope-ba;
- ne csuszz at artifact download/detail API scope-ba;
- ne hozz letre kulon replacement domaint, ha a minimalis self-FK eleg;
- a regi filehoz tartozo audit truth maradjon erintetlen;
- a replacement finalize viselkedese maradjon kompatibilis a jelenlegi route response modellel, ahol lehet.

A reportban kulon nevezd meg:
- miert replace action route a helyes current-code irany;
- miert implicit a rerun es miert nincs kulon rerun endpoint;
- hogyan maradnak meg auditkent a korabbi preflight runok;
- miert kell minimalis persisted lineage truth;
- mit bizonyitanak a unit tesztek es a smoke-ok;
- mi marad kifejezetten E3-T5 / kesobbi UI scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
