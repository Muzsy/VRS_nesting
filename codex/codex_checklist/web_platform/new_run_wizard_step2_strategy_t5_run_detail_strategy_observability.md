# Checklist: New Run Wizard Step2 Strategy T5 — Run Detail Strategy Observability

## DoD Checklist

- [x] **#1** Backend `viewer-data` response kiteszi a T3 engine_meta audit mezőket (8 új optional mező)
- [x] **#2** Régi runoknál / hiányzó engine_meta nincs 500-as hiba — minden mező optional, fallbackkel
- [x] **#3** Frontend `ViewerDataResponse` típus szinkronban a backend válasszal (14 mező)
- [x] **#4** `RunDetailPage` non-fatal módon lekéri a viewer-data-t (try/catch, nem írja felül a főhibát)
- [x] **#5** `RunDetailPage` megjeleníti a "Strategy and engine audit" kártyát 8 mezővel
- [x] **#6** Fallback szöveg hiányzó viewer-data esetén ("Not available yet")
- [x] **#7** Mock API `ViewerData` interface tartalmazza az új optional observability mezőket
- [x] **#8** Playwright E2E 2/2 PASS (fő teszt + regressziós teszt)
- [x] **#9** Dedikált T5 smoke PASS — 60/60 check
- [x] **#10** `npm --prefix frontend run build` PASS (TypeScript + Vite, 0 hiba)
- [x] **#11** `phase4.stable.spec.ts` regresszió nem tört el (2/2 PASS)
- [x] **#12** `verify.sh` report frissítve, AUTO_VERIFY blokk PASS

## Érintett fájlok

| Fájl | Változás |
|------|----------|
| `api/routes/runs.py` | `ViewerDataResponse` 8 új optional mező; `get_viewer_data()` return bővítés |
| `frontend/src/lib/types.ts` | `ViewerDataResponse` interface: 14 optional mező (6 régi + 8 új) |
| `frontend/src/pages/RunDetailPage.tsx` | `ViewerDataResponse` import, viewer-data state + non-fatal fetch, audit kártya |
| `frontend/e2e/support/mockApi.ts` | `ViewerData` interface 8 új optional audit mezővel |
| `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts` | Új Playwright spec (2 teszt) |
| `scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py` | Új offline smoke (60 check) |
| `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md` | Ez a fájl |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md` | Report |
| `codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.verify.log` | Verify log |
