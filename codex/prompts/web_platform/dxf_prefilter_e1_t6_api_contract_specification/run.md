Olvasd el az `AGENTS.md`-t, majd a kovetkezoket:
- `canvases/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t6_api_contract_specification.yaml`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`

Ezutan hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kulon kotelezo felderites:
- `api/routes/files.py`
- `api/routes/run_strategy_profiles.py`
- `api/routes/scoring_profiles.py`
- `api/routes/postprocessor_profiles.py`
- `api/routes/project_strategy_scoring_selection.py`
- `api/routes/project_manufacturing_selection.py`
- `api/routes/runs.py`
- `api/request_models.py`
- ha szukseges: `docs/api_openapi_schema.json`

Feladatcel:
- keszits docs-only API contract freeze dokumentumot a DXF prefilter V1-hez;
- kulonitsd el a current-code route truthot es a future canonical DXF prefilter API contractot;
- a future contract a meglevo route mintakhoz igazodjon, ne onkenyes uj stilust talaljon ki.

Kotelezo tartalmi kovetelmenyek:
1. A dokumentum kulon fejezetben mutassa be a current-code API truthot:
   - project files ingest
   - owner-scoped profile/version route mintak
   - project-level selection route mintak
   - runs artifact list/url/download mintak.
2. A dokumentum rogzitse a future canonical route-csaladokat:
   - `dxf-rules-profiles` + `versions`
   - `projects/{project_id}/dxf-rules-selection`
   - `projects/{project_id}/files/{file_id}/preflight-runs`
   - `projects/{project_id}/preflight-runs/{preflight_run_id}`
   - `.../artifacts`, `.../artifacts/{artifact_id}/url`, `.../download`
   - review / replace / opcionális rerun action endpointok.
3. A dokumentum rogzitse a minimalis request/response/status-code elveket,
   de csak docs-szinten. Ne irj FastAPI modelleket.
4. A dokumentum expliciten mondja ki, hogy:
   - auth/RLS nem T6 scope;
   - OpenAPI export nem T6 scope;
   - frontend hook/service contract nem T6 scope;
   - route/request model implementacio nem T6 scope.
5. A dokumentum mondja ki, hogy a T4 lifecycle es a T5 data-model mar korabban
   lefagyasztott szerzodes, es a T6 csak a HTTP API surface-et rogzit.

Fontos anti-scope:
- Ne hozz letre vagy modosits `api/routes/*.py` fajlt.
- Ne modositd az `api/request_models.py`-t.
- Ne exportalj OpenAPI schema-t.
- Ne tervezz reszletes frontend UI flow-t.
- Ne irj SQL migrationt vagy RLS policyt.

Kotelezo outputok:
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.verify.log`

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t6_api_contract_specification.md`

A reportban DoD -> Evidence formatumban hivatkozz a konkret route mintakra es dokumentumokra.
