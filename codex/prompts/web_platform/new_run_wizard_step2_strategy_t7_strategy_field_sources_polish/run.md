# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T7 Field Sources Polish

TASK_SLUG: new_run_wizard_step2_strategy_t7_strategy_field_sources_polish

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish/fill_canvas_new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.yaml`
- `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/lib/types.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts`
- `api/routes/runs.py`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, mezőt vagy enumot. A `strategy_field_sources` mező már létezik a backend viewer-data response-ban, a frontend típusban és a mock API-ban; ezt kell UI-szinten megjeleníteni.
- Ez T7 polish/observability task. Nem DB migration, nem backend resolver, nem worker backend resolution, nem New Run Wizard Step2 redesign.
- A meglévő T5 és T6 Run Detail / full-chain E2E viselkedést nem ronthatod el.
- A field-source renderelés legyen determinisztikus: kulcs szerint rendezett field/source párok.
- Null, undefined vagy üres `strategy_field_sources` nem okozhat runtime hibát.
- A reportban PASS csak ténylegesen lefutott gate esetén szerepelhet. Környezeti blocker esetén BLOCKED/FAIL legyen pontos okkal.
- Titok, token, lokális env érték nem kerülhet repo-ba.

## Implementációs cél

A T6 zárás után a strategy audit lánc működik, de a Run Detail audit kártya még nem mutatja meg, hogy az egyes strategy mezők melyik precedence forrásból jöttek. A backend és a frontend type/mocking contract már tartalmazza a `strategy_field_sources` mezőt, ezért most csak UI polish + regressziós védelem kell.

Ebben a taskban ezt kell elkészíteni:

1. Run Detail `Strategy and engine audit` kártya bővítése `Strategy field sources` breakdown-nal.
2. T7 Playwright spec pozitív és fallback esettel.
3. T7 offline source-level smoke.
4. T6 rollout doc frissítése, hogy a field-source UI már ne maradjon known limitation.
5. Checklist + report + verify.

## Részletes követelmények

### 1. RunDetailPage UI

Módosítsd:

`frontend/src/pages/RunDetailPage.tsx`

Kötelező:

- a `Strategy and engine audit` kártya továbbra is megjelenik;
- új látható címke: `Strategy field sources`;
- ha `viewerData.strategy_field_sources` tartalmaz kulcsokat, a párok jelenjenek meg determinisztikusan;
- legalább ilyen szövegek E2E-vel assertálhatók legyenek: `quality_profile`, `run_config`, `engine_backend_hint`, `request`, `nesting_engine_runtime_policy`, `global_default`;
- üres/null értéknél stabil fallback legyen, például `No field source evidence`;
- a meglévő `Not available yet` viewer-data fallback és engine_meta artifact evidence maradjon.

### 2. T7 E2E

Hozd létre:

`frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts`

Legyen benne két teszt:

1. field-source breakdown renderelése mock viewer-data alapján;
2. fallback renderelése null/üres `strategy_field_sources` mellett.

A spec a meglévő `installMockApi` helperrel dolgozzon, valódi API/DB/worker nélkül.

### 3. T7 smoke

Hozd létre:

`scripts/smoke_new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.py`

Source-szintű ellenőrzésekkel validálja a T7 contractot. Hiba esetén exit code != 0.

### 4. Rollout doc

Frissítsd:

`docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`

A `strategy_field_sources` UI-hiány ne maradjon known limitation. Dokumentáld, hogy a Run Detail audit kártya már mutatja a field-source breakdown-t.

### 5. Report és verify

Hozd létre/frissítsd:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.verify.log`

## Tesztparancsok

Minimum:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.py
```

Ha a frontend dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts
```

Végül kötelező:

```bash
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md
```

## Zárási elvárás

A végén a reportban legyen egyértelmű:

- T7 UI field-source breakdown elkészült;
- null/üres fallback működik;
- T7 E2E PASS vagy pontos blocker;
- T7 smoke PASS;
- rollout doc frissült;
- nincs gyökérszintű duplikált T7 canvas/yaml;
- verify PASS vagy pontosan dokumentált blocker.
