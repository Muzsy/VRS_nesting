# Codex checklist - dxf_prefilter_e5_t3_ui_smoke_and_integration_tests

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Elkészült az új, dedikált Playwright spec (`frontend/e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`)
- [x] A meglévő mock API harness bővült: `MockFile.latest_preflight_summary`, `MockFile.latest_preflight_diagnostics`, `MockState.finalizedBodies`
- [x] POST `/projects/{id}/files` handler capture-olja a finalize body-t `state.finalizedBodies`-ba
- [x] Browserből bizonyított a settings -> upload finalize bridge (`rules_profile_snapshot_jsonb` payload assertion)
- [x] Browserből bizonyított az accepted latest run táblázat (`accepted` badge + `Ready for next step` advisory)
- [x] Browserből bizonyított a diagnostics drawer 6 fő blokkja: Source inventory, Role mapping, Issues, Repairs, Acceptance, Artifacts
- [x] Browserből bizonyított legalább egy non-accepted (`review_required`) latest run vizuális állapota
- [x] `Ready for next step` advisory nem jelenik meg non-accepted fájlnál (`not.toBeVisible` guard)
- [x] Diagnostics drawer non-accepted file esetén is megnyitható (ha van `latest_preflight_diagnostics`)
- [x] Nem nyílt új backend endpoint, új tesztframework vagy accepted->parts scope
- [x] Elkészült a task-specifikus structural smoke (`scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`)
- [x] `python3 -m py_compile scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py` OK
- [x] `npm --prefix frontend run build` OK
- [x] `cd frontend && npx playwright test e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts` 3 passed
- [x] `python3 scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py` OK
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md` lefuttatva
