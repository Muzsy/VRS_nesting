# Codex checklist - h1_e2_t3_validation_report_generator

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit geometry validation report service a normalized geometry truth folott
- [x] A validation a meglévo `app.geometry_validation_reports` tablat hasznalja
- [x] A report strukturalt `summary_jsonb` es `report_jsonb` payloadot ir issue-listaval es severity osszesitessel
- [x] A `validation_seq` es `validator_version` korrekten toltodik
- [x] A `geometry_revisions.status` a validation verdicthez igazodik (`validated` / `rejected`)
- [x] A geometry import lanc sikeres futas utan automatikusan letrehozza a validation reportot
- [x] Valid geometry eseten query-zheto `validated` report jon letre
- [x] Hibas canonical geometry eseten query-zheto `rejected` report jon letre
- [x] Parse/import failure eseten tovabbra sem jon letre hamis parsed geometry revision
- [x] Letrejott a task-specifikus smoke script: `scripts/smoke_h1_e2_t3_validation_report_generator.py`
- [x] `python3 -m py_compile api/services/geometry_validation_report.py api/services/dxf_geometry_import.py api/routes/files.py scripts/smoke_h1_e2_t3_validation_report_generator.py` PASS
- [x] `python3 scripts/smoke_h1_e2_t3_validation_report_generator.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t3_validation_report_generator.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
