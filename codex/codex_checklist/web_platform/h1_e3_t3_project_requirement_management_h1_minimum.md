# Codex checklist - h1_e3_t3_project_requirement_management_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `api/services/project_part_requirements.py` service
- [x] Keszult minimalis `api/routes/project_part_requirements.py` endpointkeszlet es be van kotve az `api/main.py`-ba
- [x] A service a meglévo `app.projects` + `app.part_definitions` + `app.part_revisions` + `app.project_part_requirements` tablakra epul
- [x] Uj `(project_id, part_revision_id)` parra uj `project_part_requirement` rekord jon letre
- [x] Meglevo `(project_id, part_revision_id)` par eseten update tortenik, nincs duplikalas
- [x] A service kezeli a `required_qty`, `placement_priority`, `placement_policy`, `is_active`, `notes` mezoket
- [x] A service ellenorzi a projekt-owner es part-owner scope-ot
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py`
- [x] `python3 -m py_compile api/services/project_part_requirements.py api/routes/project_part_requirements.py api/main.py scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e3_t3_project_requirement_management_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
