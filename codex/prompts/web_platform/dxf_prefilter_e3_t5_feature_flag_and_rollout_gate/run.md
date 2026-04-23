# DXF Prefilter E3-T5 Feature flag es rollout gate
TASK_SLUG: dxf_prefilter_e3_t5_feature_flag_and_rollout_gate

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `api/config.py`
- `api/routes/files.py`
- `api/services/dxf_preflight_runtime.py`
- `api/services/dxf_geometry_import.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/DxfIntakePage.tsx`
- `canvases/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.md`
- `canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `canvases/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md`
- `canvases/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **feature flag + rollout gate** task. Ne nyiss project-settings domaint, migrationt vagy runtime config API-t.
- A canonical backend gate env-level legyen.
- Flag OFF eseten a source DXF finalize legacy direct geometry import fallbackra alljon vissza a mar meglevo helperen keresztul.
- A replacement route feature OFF eseten legyen gate-elve.
- A frontend current-code V1 megoldasa build-time mirror flag; ne talalj ki uj backend config endpointot a UI-nak.
- Ne nyiss review/download/artifact/UI redesign vagy E4-T5/T6/T7 scope-ot.

Modellezesi elvek:
- A backend canonical flag a Settings retegben jelenjen meg.
- A jelenlegi `complete_upload` source DXF branch kapcsoljon a ket letezo ut kozt:
  1. validate + `run_preflight_for_upload(...)`
  2. validate + `import_source_dxf_geometry_revision_async(...)`
- Ne duplikald a geometry import logikat a route-ban.
- A `replace_file` route maradhat ugyanott, de feature OFF eseten ne legyen hasznalhato.
- A frontend oldalon minimalis visibility gate eleg:
  - DXF Intake route csak akkor legyen bent, ha a mirror flag aktiv;
  - ProjectDetailPage CTA csak akkor latszodjon, ha a mirror flag aktiv.
- A `DxfIntakePage` belso fallback UX-et most ne ird ujra.

Kulon figyelj:
- az E3-T5-ben ne csuszz at project-level rollout domainbe;
- ne csuszz at runtime frontend config endpoint scope-ba;
- ne csuszz at migration vagy adatmodell modositasba;
- ne csuszz at E4-T5/T6/T7 mutating UI flow-kba;
- a reportban nevezd meg, hogy a frontend gate csak build-time mirror truth, mert nincs runtime config endpoint.

A reportban kulon nevezd meg:
- miert env-level canonical gate a helyes current-code V1 irany;
- hogyan ter vissza a rendszer legacy direct geometry import utra;
- miert gate-elt replacement flow a helyes rollout semantics;
- miert build-time mirror flag a frontend visibility gate;
- mit bizonyitanak a unit tesztek es a smoke-ok;
- mi marad kesobbi project-level rollout / config endpoint scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
