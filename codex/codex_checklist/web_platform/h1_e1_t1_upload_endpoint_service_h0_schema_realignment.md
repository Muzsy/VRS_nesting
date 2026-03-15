# Codex checklist - h1_e1_t1_upload_endpoint_service_h0_schema_realignment

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] `api/routes/projects.py` H0 `app.projects` (`owner_user_id`, `lifecycle`) modellre allitva
- [x] `api/routes/files.py` H0 `app.file_objects` modellre allitva
- [x] Source upload path policy: `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}`
- [x] Upload flow nem hasznal `project_files` tablat
- [x] Upload flow nem hasznal `owner_id` vagy `archived_at` mezologikat
- [x] DXF validacios helper nem ir legacy `validation_status`/`validation_error` oszlopokba
- [x] Letrejott a task-specifikus smoke script: `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py`
- [x] Smoke script futtatva: `python3 scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
