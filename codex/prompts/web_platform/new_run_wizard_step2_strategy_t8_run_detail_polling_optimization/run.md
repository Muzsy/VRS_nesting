# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T8 Run Detail Polling Optimization

TASK_SLUG: new_run_wizard_step2_strategy_t8_run_detail_polling_optimization

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/fill_canvas_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.yaml`
- `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, mezőt vagy enumot.
- Ez T8 frontend polling/stabilizációs task. Nem DB migration, nem backend resolver, nem worker backend resolution, nem New Run Wizard redesign.
- A meglévő T5/T6/T7 Run Detail audit UI viselkedést nem ronthatod el.
- `viewer-data` hiba továbbra is non-fatal maradjon; ne jelenjen meg globális fatal error banner csak azért, mert viewer-data hiányzik.
- A timer/polling logika ne stale `run` closure-re támaszkodjon.
- A reportban PASS csak ténylegesen lefutott gate esetén szerepelhet. Környezeti blocker esetén BLOCKED/FAIL legyen pontos okkal.
- Titok, token, lokális env érték nem kerülhet repo-ba.

## Implementációs cél

A T7 után a Run Detail audit kártya teljesebb, de a T6/T7 rollout doc még nyitva hagyta a Run Detail polling optimalizációt. A jelenlegi `RunDetailPage.tsx` 3 másodperces ciklusban frissít, és a `viewer-data` hívás nincs egyszeri terminális fetchként védve.

Ebben a taskban ezt kell elkészíteni:

1. Run Detail polling javítása terminális állapotnál.
2. `viewer-data` fetch egyszeri, terminális, non-fatal guarddal.
3. T8 Playwright spec done-once és running-no-viewer-data esettel.
4. T8 offline source-level smoke.
5. Rollout doc frissítése, hogy a polling limitation covered státuszba kerüljön.
6. Checklist + report + verify.

## Részletes követelmények

### 1. RunDetailPage polling

Módosítsd:

`frontend/src/pages/RunDetailPage.tsx`

Kötelező:

- kezdeti betöltéskor továbbra is lekéri a run állapotot és artifactokat;
- queued/running státuszban továbbra is lehet pollolni;
- done/failed/cancelled státusz után ne legyen további felesleges periodikus API-refresh;
- `api.getViewerData(...)` ne fusson minden refreshben feltétel nélkül;
- `viewer-data` csak terminális státusznál legyen megpróbálva;
- adott `projectId/runId` párosra a terminális viewer-data fetch egyszer történjen meg;
- viewer-data 404/hiba non-fatal maradjon;
- `projectId` vagy `runId` váltáskor a guardok resetelődjenek;
- meglévő audit UI szövegek maradjanak: `Strategy and engine audit`, `Strategy field sources`, `No field source evidence`, `Not available yet`.

### 2. T8 E2E

Hozd létre:

`frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts`

Legyen benne legalább két teszt:

1. done run esetén a `/viewer-data` GET pontosan egyszer vagy legfeljebb egyszer fut, és 3+ másodperc után sem ismétlődik;
2. running run esetén 3+ másodperc alatt nem történik `/viewer-data` GET, miközben a Run Detail oldal betölt és a `RUNNING` státusz látszik.

A request countot `page.on("request", ...)` vagy ezzel egyenértékű Playwright módszerrel mérd. A spec ne igényeljen valódi backend/Supabase/worker/solver környezetet.

### 3. T8 smoke

Hozd létre:

`scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py`

Source-szintű ellenőrzésekkel validálja a T8 contractot. Hiba esetén exit code != 0.

### 4. Rollout doc

Frissítsd:

`docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`

A Run Detail polling optimalizáció ne maradjon nyitott known limitation. Dokumentáld, hogy T8 után terminális státuszban egyszeri, non-fatal viewer-data audit fetch működik.

### 5. Report és verify

Hozd létre/frissítsd:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.verify.log`

## Tesztparancsok

Minimum:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py
```

Ha a frontend dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts
```

Végül kötelező:

```bash
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md
```

## Zárási elvárás

A végén a reportban legyen egyértelmű:

- T8 polling guard elkészült;
- viewer-data csak terminális állapotban, egyszeri non-fatal fetchként fut;
- running run nem kér viewer-data-t;
- T5/T6/T7 audit UI nem tört el;
- T8 E2E PASS vagy pontos blocker;
- T8 smoke PASS;
- rollout doc frissült;
- nincs gyökérszintű duplikált T8 canvas/yaml;
- verify PASS vagy pontosan dokumentált blocker.
