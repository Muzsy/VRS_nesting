# Codex checklist - dxf_prefilter_e5_t2_end_to_end_api_tests

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Elkészült az új, dedikált API-level E2E pack (`tests/test_dxf_preflight_api_end_to_end.py`)
- [x] A pack route-level láncot használ: `complete_upload` -> `BackgroundTasks` -> `run_preflight_for_upload` -> `list_project_files`
- [x] A core T1->T7 runtime pipeline valósan fut; csak I/O seam patch történik (`load_file_ingest_metadata`, `download_storage_object_blob`, geometry import recorder)
- [x] A fake Supabase world lefedi: `app.projects`, `app.file_objects`, `app.preflight_runs`, `app.preflight_diagnostics`, `app.preflight_artifacts`
- [x] Signed upload URL + artifact payload capture bizonyíték benne van a tesztben
- [x] `pytest.importorskip("ezdxf")` explicit guard szerepel
- [x] Lefedett minimum scenario-k: accepted, lenient review_required, strict rejected
- [x] Geometry import gate különbség explicit: accepted esetben fut, non-accepted esetben nem fut
- [x] Rules profile snapshot bridge bizonyított: `complete_upload` -> runtime kwargs -> persisted `rules_profile_snapshot_jsonb`
- [x] Elkészült a task-specifikus structural smoke (`scripts/smoke_dxf_prefilter_e5_t2_end_to_end_api_tests.py`)
- [x] Kötelező futtatások: `py_compile` OK, célzott `pytest` 3 passed, smoke OK
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md` lefuttatva
