# Checklist: New Run Wizard Step2 Strategy T4 — Frontend Step2 API Submit Flow

## DoD Checklist

- [x] **#1** Step2-ben van strategy UI blokk (strategy source radio + advanced overrides)
- [x] **#2** Project default hiánya (404) nem töri el a wizardot — `getProjectRunStrategySelection` null-t ad vissza
- [x] **#3** Profile/version listázás működik API kliensből (`listRunStrategyProfiles`, `listRunStrategyProfileVersions`)
- [x] **#4** `createRunConfig(...)` képes strategy mezőket küldeni (`run_strategy_profile_version_id`, `solver_config_overrides_jsonb`)
- [x] **#5** `createRun(...)` ténylegesen küldi a `run_config_id`-t (regressziós hiba javítva)
- [x] **#6** `createRun(...)` strategy request mezőket is küld (`run_strategy_profile_version_id`, `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy`, `sa_eval_budget_sec`)
- [x] **#7** Step3 summary mutatja a strategy döntést
- [x] **#8** E2E mock rögzíti a `run-configs` és `runs` POST bodykat (`runConfigBodies`, `runCreateBodies`)
- [x] **#9** E2E assert bizonyítja a `run_config_id` + strategy payload átadását (2 Playwright teszt, 2/2 PASS)
- [x] **#10** `npm --prefix frontend run build` PASS (TypeScript + Vite build clean)
- [x] **#11** Dedikált Playwright spec PASS (`new_run_wizard_step2_strategy_t4.spec.ts` — 2/2)
- [x] **#12** Phase 4 stable spec regresszió nem tört el (`phase4.stable.spec.ts` — 2/2 PASS)
- [x] **#13** `verify.sh` report frissítve

## Érintett fájlok

| Fájl | Változás |
|------|----------|
| `frontend/src/lib/types.ts` | Strategy típusok hozzáadva |
| `frontend/src/lib/api.ts` | `requestOrNull`, 4 új strategy metódus, `createRunConfig`/`createRun` payload bővítés + bug fix |
| `frontend/src/pages/NewRunPage.tsx` | Step2 strategy UI, payload builderek, submit-flow javítás, Step3 summary |
| `frontend/e2e/support/mockApi.ts` | Strategy mock state + route handlerek + capture arrays |
| `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts` | Új Playwright spec (2 teszt) |
| `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md` | Ez a fájl |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md` | Report |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.verify.log` | Verify log |
