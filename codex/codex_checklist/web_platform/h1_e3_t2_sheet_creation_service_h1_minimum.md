# Codex checklist - h1_e3_t2_sheet_creation_service_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `api/services/sheet_creation.py` service
- [x] Keszult minimalis `api/routes/sheets.py` endpoint es be van kotve az `api/main.py`-ba
- [x] A service a meglévo `app.sheet_definitions` + `app.sheet_revisions` tablakra epul
- [x] Uj `code` eseten uj definition + `revision_no = 1` jon letre
- [x] Meglevo `code` eseten kovetkezo revision jon letre, es frissul a `current_revision_id`
- [x] H1 minimum teglalap model (`width_mm`, `height_mm`, opcionális `grain_direction`) ervenyesul
- [x] A task nem hoz letre `project_sheet_inputs` rekordot, es nem ker `project_id`-t
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e3_t2_sheet_creation_service_h1_minimum.py`
- [x] `python3 -m py_compile api/services/sheet_creation.py api/routes/sheets.py api/main.py scripts/smoke_h1_e3_t2_sheet_creation_service_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e3_t2_sheet_creation_service_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
