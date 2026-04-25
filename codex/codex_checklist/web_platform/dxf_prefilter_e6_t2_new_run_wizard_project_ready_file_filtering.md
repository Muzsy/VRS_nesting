# Codex checklist - dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] `frontend/src/pages/NewRunPage.tsx` intake-aware file list betoltesre valtott (`include_preflight_summary` + `include_part_creation_projection`)
- [x] Bevezetesre kerult project-ready helper logika (`hasLinkedPartRevision`, `isProjectReadyPartFile`, `isRunUsableStockFile`)
- [x] Step 1 stock dropdown csak eligible source listabol renderel
- [x] Step 1 part lista csak project-ready linked part file-okat mutat
- [x] `selectedParts` es `wizardRevisionIds` sync project-ready file korre szukult
- [x] Blocked/empty UX copy + DXF Intake CTA megjelenik, ha nincs project-ready part
- [x] Elkeszult az E6-T2 Playwright regresszio spec (`frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts`)
- [x] E6-T2 regresszio explicit lefedi a `rejected + existing_part_revision_id` (stale linkage) esetet (`Kor_D120-BodyPad.dxf`)
- [x] Elkeszult az offline smoke (`scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py`)
- [x] `python3 scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py` lefutott
- [x] `npm --prefix frontend run build` lefutott
- [x] Celozott Playwright futas lefutott (`dxf_prefilter_e6_t1` + `dxf_prefilter_e6_t2`)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md` lefuttatva
