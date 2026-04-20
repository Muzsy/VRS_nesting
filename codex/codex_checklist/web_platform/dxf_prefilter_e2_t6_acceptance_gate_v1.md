# Codex checklist - dxf_prefilter_e2_t6_acceptance_gate_v1

- [x] Canvas + goal YAML + run prompt + checklist + report artefaktok elerhetoek
- [x] Letrejott kulon backend acceptance gate service: `api/services/dxf_preflight_acceptance_gate.py`
- [x] A gate a T5 normalized DXF artifactot a tenyleges `import_part_raw(...)` utvonalon teszteli vissza
- [x] A canonical geometry/bbox/hash eloallitas minimal public helper boundaryval tortenik (`api/services/dxf_geometry_import.py`)
- [x] A validator probe ugyanarra a validator logikara epul public helperen keresztul, DB insert nelkul (`api/services/geometry_validation_report.py`)
- [x] A service explicit precedence szerint ad `accepted_for_import` / `preflight_rejected` / `preflight_review_required` verdictet
- [x] A service strukturalt `blocking_reasons` es `review_required_reasons` outputot ad
- [x] A task nem nyitotta meg a persistence / route / upload trigger / UI scope-ot
- [x] Keszult task-specifikus unit teszt csomag (`tests/test_dxf_preflight_acceptance_gate.py`)
- [x] Keszult task-specifikus smoke script (`scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`)
- [x] Checklist es report evidence alapon frissitve
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md` PASS
