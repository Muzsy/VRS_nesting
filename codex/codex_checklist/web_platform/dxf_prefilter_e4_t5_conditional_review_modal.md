# Codex checklist - dxf_prefilter_e4_t5_conditional_review_modal

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Frontend típusbővítés elkészült a replacement upload response-hoz (`ProjectFileReplaceUploadResponse`)
- [x] Frontend API helper elkészült a meglévő replacement route-hoz (`replaceProjectFile`)
- [x] `completeUpload` payload optional `replaces_file_object_id` bridge mezővel bővült
- [x] A `DxfIntakePage` táblában a review trigger feltételesen jelenik meg (`preflight_review_required` + diagnostics payload)
- [x] Külön page-local conditional review modal készült (nem a diagnostics drawer átnevezése)
- [x] A modal megjeleníti a review-required issue szeletet és a remaining review-required signals listát
- [x] A modal explicit current-code disclaimer-t tartalmaz: nincs persisted review decision save
- [x] A modal replacement upload entrypointot ad a meglévő `POST /projects/{project_id}/files/{file_id}/replace` route-ra
- [x] A replacement finalize a meglévő `complete_upload` útvonalon megy, `replaces_file_object_id` bridge-dzsel
- [x] A page aktuális settings draftja replacement finalize-kor is `rules_profile_snapshot_jsonb`-ként átmegy
- [x] Az E4-T4 diagnostics drawer regresszió nélkül megmaradt (`View diagnostics` + drawer blokkok)
- [x] Elkészült a task-specifikus smoke (`scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py`)
- [x] `python3 -m py_compile scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py` OK
- [x] `python3 scripts/smoke_dxf_prefilter_e4_t5_conditional_review_modal.py` OK
- [x] `npm --prefix frontend run build` OK
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md` PASS
