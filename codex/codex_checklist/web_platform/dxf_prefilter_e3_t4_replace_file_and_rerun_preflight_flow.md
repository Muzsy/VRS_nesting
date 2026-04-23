# Codex checklist - dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow

- [x] Canvas + goal YAML + run prompt artefaktok elérhetők
- [x] Migration létrejött: `replaces_file_object_id` nullable self-FK az `app.file_objects` táblában
- [x] `POST /projects/{project_id}/files/{file_id}/replace` route létrejött
- [x] A replace route csak létező, projekthez tartozó `source_dxf` targetra működik
- [x] A replace route új `file_id`-t és signed upload URL-t ad vissza a meglévő upload-url mintához igazodva
- [x] `FileCompleteRequest` kap optional `replaces_file_object_id` mezőt
- [x] `complete_upload` replacement finalize esetén persisted lineage truth-tal hozza létre az új file_objects sort
- [x] Replacement finalize után a meglévő `validate_dxf_file_async` + `run_preflight_for_upload` background taskok regisztrálódnak az új file-ra
- [x] Nem jön létre külön manuális rerun endpoint
- [x] Nem történik régi file in-place felülírása
- [x] Elkészült a task-specifikus unit teszt (`tests/test_dxf_preflight_replace_flow.py`)
- [x] Elkészült a task-specifikus smoke (`scripts/smoke_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.py`)
- [x] `python3 -m pytest tests/test_dxf_preflight_replace_flow.py -v` OK — 7 passed
- [x] `python3 scripts/smoke_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.py` OK — ALL SCENARIOS PASSED
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md` PASS
