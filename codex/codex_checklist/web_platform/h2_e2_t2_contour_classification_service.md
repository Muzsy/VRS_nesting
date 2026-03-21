# Codex checklist - h2_e2_t2_contour_classification_service

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a minimalis migration: `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- [x] Letrejott a classification service: `api/services/geometry_contour_classification.py`
- [x] `dxf_geometry_import.py` pipeline bovitve a contour classification hivatassal
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e2_t2_contour_classification_service.py`
- [x] `python3 -m py_compile api/services/geometry_contour_classification.py api/services/dxf_geometry_import.py scripts/smoke_h2_e2_t2_contour_classification_service.py` PASS
- [x] `python3 scripts/smoke_h2_e2_t2_contour_classification_service.py` PASS (6/6 test)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t2_contour_classification_service.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
