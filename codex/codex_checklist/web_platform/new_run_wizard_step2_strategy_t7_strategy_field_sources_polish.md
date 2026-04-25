# Checklist: New Run Wizard Step2 Strategy T7 — Strategy Field Sources Polish

## DoD Checklist

- [x] **#1** Run Detail `Strategy and engine audit` kártya megjeleníti a `Strategy field sources` breakdown-t (kulcs szerint rendezve)
- [x] **#2** Üres/null `strategy_field_sources` esetén stabil `No field source evidence` fallback jelenik meg, runtime hiba nélkül
- [x] **#3** T7 Playwright spec lefedi a pozitív esetet (key/source párok) és a fallback esetet (null field sources) — 2/2 PASS
- [x] **#4** T7 offline smoke PASS — 30/30 check
- [x] **#5** T6 rollout doc frissült: `strategy_field_sources` UI known limitation lezárva ("Covered in T7")
- [x] **#6** Nincs gyökérszintű duplikált T7 canvas/yaml artefakt
- [x] **#7** `npm --prefix frontend run build` PASS (TypeScript + Vite, 84 modul, 0 hiba)
- [x] **#8** T5 + T6 + T7 Playwright specek PASS (5/5)
- [x] **#9** `verify.sh` PASS — AUTO_VERIFY blokk a reportban

## Érintett fájlok

| Fájl | Változás |
|------|----------|
| `frontend/src/pages/RunDetailPage.tsx` | `Strategy field sources` szekció hozzáadva: rendezett key/source lista, `No field source evidence` fallback |
| `frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts` | Új Playwright spec (2 teszt) |
| `scripts/smoke_new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.py` | Új offline smoke (30 check) |
| `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` | `strategy_field_sources` known limitation lezárva |
| `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md` | Ez a fájl |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md` | Report |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.verify.log` | Verify log |
