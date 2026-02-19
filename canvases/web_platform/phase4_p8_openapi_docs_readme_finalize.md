# canvases/web_platform/phase4_p8_openapi_docs_readme_finalize.md

# Phase 4 P8 OpenAPI + docs finalize

## Funkcio
A P4.8 celja az API dokumentacio es uzemeltetesi dokumentumok lezárása:
OpenAPI export, `/docs` ellenorzes, README quick-start + Phase 4 operational decisions frissites.

## Scope
- Benne van:
  - OpenAPI export script + statikus schema artifact;
  - `/docs` es `/openapi.json` elerhetoseg ellenorzes;
  - root `README.md` quick-start frissites;
  - `api/README.md` Phase 4 allapothoz igazitasa.
- Nincs benne:
  - kulso wiki/konfluens dokumentacio.

## Erintett fajlok
- `canvases/web_platform/phase4_p8_openapi_docs_readme_finalize.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p8_openapi_docs_readme_finalize.yaml`
- `codex/codex_checklist/web_platform/phase4_p8_openapi_docs_readme_finalize.md`
- `codex/reports/web_platform/phase4_p8_openapi_docs_readme_finalize.md`
- `codex/reports/web_platform/phase4_p8_openapi_docs_readme_finalize.verify.log`
- `scripts/export_openapi_schema.py`
- `docs/api_openapi_schema.json`
- `README.md`
- `api/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] OpenAPI schema export automatizalva.
- [ ] Swagger UI `/docs` endpoint ellenorzottan elerheto.
- [ ] README quick-start + Phase 4 operational decisions frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p8_openapi_docs_readme_finalize.md` PASS.
