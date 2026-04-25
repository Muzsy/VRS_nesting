# Checklist: New Run Wizard Step2 Strategy T6 — Rollout Closure + Full-chain Regression

## DoD Checklist

- [x] **#1** T6 full-chain E2E PASS — Step2 custom strategy → run-config body → run create body → Run Detail audit kártya (1/1 Playwright)
- [x] **#2** T6 offline closure smoke PASS — 86/86 check (T1–T6 contractok, artefaktok, duplikátum-tiltás, T1–T5 reportok)
- [x] **#3** Rollout/compatibility dokumentum elkészült (deploy sorrend, compatibility matrix, rollback, known limitations)
- [x] **#4** T1–T5 reportok mind léteznek és PASS státuszt tartalmaznak
- [x] **#5** T1–T6 task artefaktok (canvas, goal yaml, runner) saját slug-alkönyvtárban vannak
- [x] **#6** Nincs `new_run_wizard_step2_strategy_t*` gyökérszintű duplikált canvas/yaml
- [x] **#7** `npm --prefix frontend run build` PASS (TypeScript + Vite, 84 modul, 0 hiba)
- [x] **#8** T4 + T5 + T6 Playwright specek PASS (5/5)
- [x] **#9** `verify.sh` PASS — AUTO_VERIFY blokk a reportban

## Érintett fájlok

| Fájl | Változás |
|------|----------|
| `frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts` | Új Playwright spec — full-chain closure teszt |
| `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` | Új rollout/compatibility dokumentum |
| `scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py` | Új offline closure smoke (86 check) |
| `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md` | Ez a fájl |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md` | Záró report |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log` | Verify log |
