# Codex checklist - dxf_prefilter_e4_t1_dxf_intake_project_preparation_page

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Minimal backend file-list preflight summary projection elkészült (`api/routes/files.py`)
- [x] Frontend API/types boundary bővítve (`frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`)
- [x] Új DXF Intake oldal + route elkészült (`frontend/src/pages/DxfIntakePage.tsx`, `frontend/src/App.tsx`)
- [x] ProjectDetail explicit intake CTA elkészült (`frontend/src/pages/ProjectDetailPage.tsx`)
- [x] Készült deterministic backend unit teszt (`tests/test_project_files_preflight_summary.py`)
- [x] Készült deterministic smoke (`scripts/smoke_dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.py`)
- [x] Célzott ellenőrzések lefutottak (`py_compile`, `pytest`, smoke, `npm --prefix frontend run build`)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t1_dxf_intake_project_preparation_page.md` lefutott, report AUTO_VERIFY blokkal frissítve (a gate FAIL oka pre-existing nesting-engine canonical JSON determinism mismatch)
