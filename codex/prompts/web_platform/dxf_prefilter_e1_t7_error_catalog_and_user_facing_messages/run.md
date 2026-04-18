Olvasd el az `AGENTS.md`-t, majd a kovetkezoket:
- `canvases/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.yaml`
- `docs/error_code_catalog.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`

Ezutan hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kulon kotelezo felderites:
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/dxf_validation.py`
- `api/services/geometry_validation_report.py`
- `docs/error_code_catalog.md`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/ViewerPage.tsx`

Feladatcel:
- keszits docs-only error catalog es user-facing message freeze dokumentumot a DXF prefilter V1-hez;
- kulonitsd el a current-code error truthot es a future canonical DXF prefilter error catalogot;
- a future catalog a meglevo kodokra es jelenlegi hibaforrasokra uljon ra, ne kitalalt UX rendszer legyen.

Kotelezo tartalmi kovetelmenyek:
1. A dokumentum kulon fejezetben mutassa be a current-code error truthot:
   - importer `DXF_*` structured codes,
   - geometry validation issue-kodok + severity,
   - global runtime error code formatum,
   - jelenlegi frontend nyers hibamegjelenitesi pontok.
2. A dokumentum rogzitse a future canonical error-catalog kategoriakat:
   - file ingest / upload boundary,
   - DXF parse/readability/unsupported input,
   - contour/topology/layer contract,
   - repair-policy,
   - acceptance-gate,
   - geometry validation,
   - review-required,
   - replace/rerun informacios allapotok.
3. A dokumentum rogzitse a minimum catalog-item mezoket:
   - `code`, `severity`, `title`, `user_message`, `suggested_action`, `debug_evidence_source`, opcionisan `support_notes`.
4. A dokumentum kulon mondja ki, hogy a user-facing uzenet nem azonos a nyers technical exceptionnel,
   es hogy a debug/path/details evidence kulon diagnostics/support feluletre valo.
5. A dokumentum adjon grounded mapping peldakat valos kodokkal, minimum:
   - `DXF_NO_OUTER_LAYER`
   - `DXF_OPEN_OUTER_PATH`
   - `DXF_OPEN_INNER_PATH`
   - `DXF_MULTIPLE_OUTERS`
   - `DXF_UNSUPPORTED_ENTITY_TYPE`
   - `DXF_UNSUPPORTED_UNITS`
   - legalabb nehany `GEO_*` validator issue-kod.
6. A dokumentum mondja ki, hogy:
   - T4 lifecycle miatt kulon kell kezelnunk az `error` es `review_required` allapotokat;
   - T5 miatt kell structured code/severity/message contract a persistencehez;
   - T6 miatt a catalog majd future preflight read/diagnostics surface-ben jelenik meg,
     de ennek HTTP response modellje nem T7 scope.
7. A dokumentum explicit anti-scope blokkban tiltsa:
   - backend translator/service implementaciot,
   - frontend page/component modositasat,
   - API response/OpenAPI schema reszletes definiciojat,
   - i18n/localization rendszer tervezeset implementacios reszletesseggel.

Fontos anti-scope:
- Ne hozz letre vagy modosits `api/routes/*.py`, `api/services/*.py` vagy `frontend/src/*` fajlt.
- Ne modosits OpenAPI exportot.
- Ne irj translation registryt vagy UI komponenst.
- Ne tervezz support tooling implementaciot.

Kotelezo outputok:
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.verify.log`

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`

A reportban DoD -> Evidence formatumban hivatkozz a konkret kodforrasokra es frontend page-ekre.
