# Codex checklist - h1_e3_t4_project_sheet_input_management_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `api/services/project_sheet_inputs.py` service
- [x] Keszult minimalis `api/routes/project_sheet_inputs.py` endpointkeszlet es be van kotve az `api/main.py`-ba
- [x] A service a meglévo `app.projects` + `app.sheet_definitions` + `app.sheet_revisions` + `app.project_sheet_inputs` tablakra epul
- [x] Uj `(project_id, sheet_revision_id)` parra uj `project_sheet_input` rekord jon letre
- [x] Meglevo `(project_id, sheet_revision_id)` par eseten update tortenik, nincs duplikalas
- [x] A service kezeli a `required_qty`, `is_active`, `is_default`, `placement_priority`, `notes` mezoket
- [x] `is_default=true` eseten projekt-szinten lekapcsolodnak a tobbi default rekordok
- [x] A service ellenorzi a projekt-owner es sheet-owner scope-ot
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e3_t4_project_sheet_input_management_h1_minimum.py`
- [x] `python3 -m py_compile api/services/project_sheet_inputs.py api/routes/project_sheet_inputs.py api/main.py scripts/smoke_h1_e3_t4_project_sheet_input_management_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e3_t4_project_sheet_input_management_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t4_project_sheet_input_management_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
