# Codex checklist - dxf_prefilter_e4_t6_accepted_files_to_parts_flow

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] A `GET /projects/{project_id}/files` route optional `include_part_creation_projection` query flaggel bővült
- [x] A files list projection megkülönbözteti az `accepted_ready`, `accepted_geometry_import_pending` és `not_eligible_*` állapotokat
- [x] A projection a meglévő geometry truth-ra épít (`geometry_revisions` + `geometry_derivatives`) új endpoint nélkül
- [x] A projection minimalisan jelzi az existing part truth-ot (`existing_part_definition_id`, `existing_part_revision_id`, `existing_part_code`)
- [x] Frontend type boundary bővült (`ProjectFileLatestPartCreationProjection`, `ProjectPartCreateRequest/Response`)
- [x] Frontend API helper elkészült a meglévő `POST /projects/{project_id}/parts` route-hoz (`createProjectPart`)
- [x] A `DxfIntakePage` külön `Accepted files -> parts` blokkot kapott
- [x] A code/name draft page-local state maradt (`partCreationDraftByFileId`), nincs új persisted draft domain
- [x] Create-part csak accepted+ready fájlra aktív; pending/rejected/review-required állapotokhoz explicit UX jelzés van
- [x] Create-part után egyértelmű refresh/result state fut (`loadData()` + státusz üzenet)
- [x] T4 diagnostics drawer regresszió nélkül megmaradt
- [x] T5 conditional review modal regresszió nélkül megmaradt
- [x] Elkészült task-specifikus smoke (`scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`)
- [x] `python3 -m py_compile api/routes/files.py scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py` OK
- [x] `python3 scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py` OK
- [x] `npm --prefix frontend run build` OK
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md` PASS
