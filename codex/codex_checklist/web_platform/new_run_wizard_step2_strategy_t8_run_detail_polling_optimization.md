# Checklist: New Run Wizard Step2 Strategy T8 — Run Detail Polling Optimization

## DoD Checklist

- [x] **#1** `viewerDataAttemptedRef` guard prevents viewer-data fetch from repeating after the first terminal-state call
- [x] **#2** `isTerminalRef` prevents timer callback from issuing further API refreshes once terminal state is confirmed — stale `run` closure bug resolved
- [x] **#3** viewer-data error remains non-fatal: 404 / network error does not set global error banner
- [x] **#4** `viewerDataAttemptedRef` and `isTerminalRef` reset on `projectId`/`runId` change
- [x] **#5** T5/T6/T7 audit UI texts preserved: `Strategy and engine audit`, `Not available yet`, `Strategy field sources`, `No field source evidence`
- [x] **#6** T8 Playwright spec: done-once case (viewer-data ≤ 1 call, not repeated after 4.5 s) — PASS
- [x] **#7** T8 Playwright spec: running-no-viewer-data case (viewer-data count = 0 after 4.5 s) — PASS
- [x] **#8** T8 offline smoke PASS — 38/38 checks
- [x] **#9** Rollout doc frissült: Run Detail polling known limitation lezárva ("Covered in T8")
- [x] **#10** Nincs gyökérszintű duplikált T8 canvas/yaml artefakt
- [x] **#11** `npm --prefix frontend run build` PASS (TypeScript + Vite, 84 modul, 0 hiba)
- [x] **#12** T5 + T6 + T7 + T8 Playwright specek PASS (7/7)
- [x] **#13** `verify.sh` PASS — AUTO_VERIFY blokk a reportban

## Érintett fájlok

| Fájl | Változás |
|------|----------|
| `frontend/src/pages/RunDetailPage.tsx` | `viewerDataAttemptedRef` + `isTerminalRef` hozzáadva; viewer-data fetch terminális + once-only feltételhez kötve; timer terminális állapotnál leáll |
| `frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts` | Új Playwright spec (2 teszt: done-once, running-no-viewer-data) |
| `scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py` | Új offline smoke (38 check) |
| `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` | Run Detail polling known limitation lezárva (T8) |
| `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md` | Ez a fájl |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md` | Report |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.verify.log` | Verify log |
