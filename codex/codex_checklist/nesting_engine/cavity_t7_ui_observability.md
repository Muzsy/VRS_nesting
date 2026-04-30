# Codex checklist - cavity_t7_ui_observability

- [x] AGENTS.md + Codex szabalyok + T7 canvas/YAML/prompt atnezve
- [x] Additiv backend cavity observability mezok bevezetve `api/routes/files.py` preflight summary/diagnostics payloadba
- [x] Additiv run viewer cavity prepack summary mező bevezetve `api/routes/runs.py` `viewer-data` valaszba
- [x] Frontend TS tipusok es normalizalas bovitve (`frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`)
- [x] DXF Intake diagnostics drawer cavity blokk implementalva (`frontend/src/pages/DxfIntakePage.tsx`)
- [x] Copy source-of-truth frissitve (`frontend/src/lib/dxfIntakePresentation.ts`)
- [x] Run Detail audit kartya cavity prepack summary blokk implementalva (`frontend/src/pages/RunDetailPage.tsx`)
- [x] Cavity UI adat nelkul nem jelenik meg Run Detail oldalon
- [x] New Run Wizard filtering logika nem lett modositva (nincs wizard file diff)
- [x] Playwright spec keszult: `frontend/e2e/cavity_prepack_observability.spec.ts`
- [x] Smoke script keszult: `scripts/smoke_cavity_t7_ui_observability.py`
- [x] `cd frontend && npm run build` PASS
- [x] `python3 scripts/smoke_cavity_t7_ui_observability.py` PASS
- [x] `cd frontend && npx playwright test e2e/cavity_prepack_observability.spec.ts` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t7_ui_observability.md` PASS
