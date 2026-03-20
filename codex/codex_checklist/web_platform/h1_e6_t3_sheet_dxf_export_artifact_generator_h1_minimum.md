# Codex checklist - h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit worker-oldali sheet DXF generator boundary: `worker/sheet_dxf_artifacts.py`
- [x] A generator projection truth + snapshot + `nesting_canonical` derivative adatokbol exportal
- [x] Per hasznalt sheet legalabb egy deterministic DXF dokumentum generalodik
- [x] A geometriak placement transzformacioval a `nesting_canonical` polygonokbol rajzolodnak
- [x] Az artifactok `sheet_dxf` kinddal a canonical `run-artifacts` bucketbe kerulnek
- [x] A regisztracio route-kompatibilis `filename` + `sheet_index` metadata truth-ot ad
- [x] Az upload/regisztracio retry-biztos deterministic kimenetet ad azonos bemenetre
- [x] A worker success path a sheet DXF generator utan zar `done` allapotba
- [x] A task scope nem nyit bundle/manufacturing/frontend-redesign iranyba
- [x] Letrejott task-specifikus smoke: `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`
- [x] `python3 -m py_compile worker/main.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py worker/result_normalizer.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
