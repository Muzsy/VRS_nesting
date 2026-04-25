# Codex checklist - dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Elkeszult a soft-archive migration (`supabase/migrations/20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql`)
- [x] `api/routes/files.py` list endpoint kezeli a `deleted_at` mezot es `include_deleted` queryt
- [x] `DELETE /projects/{project_id}/files/{file_id}` soft archive (`update_rows`) es nem hard delete
- [x] Frontend API/types kezeli a `deleted_at` mezot es `include_deleted` opciot
- [x] Project Detail intake-aware statusz / next-step megjelenitesre valtott
- [x] Rejected/review/pending source upload kulon intake attention nezetben van
- [x] Action copy hard delete helyett `Hide upload` / `Archive upload` / `Manage in DXF Intake`
- [x] Mock API soft archive jellegu DELETE route tamogatast kapott
- [x] Elkeszult a task-specifikus E2E (`frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts`)
- [x] Elkeszult az offline smoke (`scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py`)
- [x] `python3 scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py` lefutott
- [x] `npm --prefix frontend run build` lefutott
- [x] Celozott Playwright futas lefutott
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md` lefuttatva
