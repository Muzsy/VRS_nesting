# Codex checklist - dxf_prefilter_e4_t4_diagnostics_drawer_modal

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Backend `latest_preflight_diagnostics` optional projection elkészült a meglévő file-list route-on
- [x] `include_preflight_diagnostics=false` esetben a T3 viselkedés változatlan
- [x] Frontend `ProjectFileLatestPreflightDiagnostics` típusok bekerültek
- [x] Frontend API normalizer optional-safe diagnostics mappinggel bővült
- [x] `DxfIntakePage` row-level non-mutating `View diagnostics` trigger elkészült
- [x] `DxfIntakePage` page-local diagnostics drawer/modal a kötelező szekciókkal elkészült
- [x] Nem nyílt új historical/detail endpoint és nem került mutating review/replace/rerun/accepted->parts UI
- [x] Elkészült deterministic route-level teszt (`tests/test_project_files_preflight_diagnostics.py`)
- [x] Elkészült deterministic smoke (`scripts/smoke_dxf_prefilter_e4_t4_diagnostics_drawer_modal.py`)
- [x] Kötelező futtatások lefutottak (`py_compile`, `pytest`, smoke, `npm --prefix frontend run build`)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t4_diagnostics_drawer_modal.md` lefutott és report AUTO_VERIFY frissült
