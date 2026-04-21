# Codex checklist - dxf_prefilter_e3_t3_geometry_import_gate_integration

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] `api/routes/files.py` source DXF ágon már nem regisztrál közvetlen geometry import background taskot
- [x] A route-ban bent marad a két task: `validate_dxf_file_async(...)` és `run_preflight_for_upload(...)`
- [x] A preflight runtime persistence után gate-elt import trigger logika készült
- [x] A runtime csak `accepted_for_import` esetén próbál geometry importot indítani
- [x] A runtime a persisted `artifact_refs` listából a `normalized_dxf` storage ref-et használja
- [x] Rejected/review outcome esetén explicit skip logika van
- [x] Accepted + missing/invalid normalized artifact esetén warning + skip van, source fallback nélkül
- [x] Geometry import helper hiba esetén warning + swallowed failure működik
- [x] A geometry import pipeline nem duplikálódott; generic storage-backed helper készült és a source wrapper erre delegál
- [x] Készült deterministic unit teszt: `tests/test_dxf_preflight_geometry_import_gate.py`
- [x] Készült deterministic smoke: `scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py`
- [x] Célzott tesztfuttatás zöld: `python3 -m pytest -q tests/test_dxf_preflight_runtime.py tests/test_dxf_preflight_geometry_import_gate.py` (17 passed)
- [x] Smoke futás zöld: `python3 scripts/smoke_dxf_prefilter_e3_t3_geometry_import_gate_integration.py`
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md` lefutott, report AUTO_VERIFY blokkal frissítve (a gate FAIL oka pre-existing nesting-engine canonical JSON determinism mismatch)
