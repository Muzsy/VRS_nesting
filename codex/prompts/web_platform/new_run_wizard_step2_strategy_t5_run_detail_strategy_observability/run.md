# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T5 Run Detail Strategy Observability

TASK_SLUG: new_run_wizard_step2_strategy_t5_run_detail_strategy_observability

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/fill_canvas_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.yaml`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `api/routes/runs.py`
- `worker/main.py`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/ViewerPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/e2e/support/mockApi.ts`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, mezőt vagy enumot. Minden contractot a valós backend route-okból és a T1–T4 reportokból vezess le.
- Ez T5 observability/integration task. Nem DB migration, nem worker backend resolution task, nem strategy resolver precedence task, nem New Run Wizard Step2 redesign.
- A `RunDetailPage` meglévő run/artifact/log/cancel/rerun működését nem törheted el.
- A `viewer-data` lekérés hibája nem lehet fatal a Run Detail oldal számára. Régi runok és hiányzó `engine_meta.json` esetén fallback UI kell.
- A T3 `engine_meta.json` mezőneveit őrizd meg; ne nevezz át meglévő truth mezőket.
- Titok, token, lokális env érték nem kerülhet repo-ba.

## Implementációs cél

A T1–T4 után a strategy választás már bekerül a run indítási láncba, de a Run Detail oldalon még nem látszik, hogy végül milyen strategy/backend truth futott. Ebben a taskban ezt kell bekötni:

1. `engine_meta.json` T3 auditmezők kitétele a `viewer-data` response-ba.
2. Frontend típusok szinkronizálása.
3. `RunDetailPage` strategy/engine audit kártya.
4. Mock API + Playwright E2E.
5. Offline-barát dedikált smoke.
6. Report + verify.

## Részletes követelmények

### 1. Backend viewer-data contract

`api/routes/runs.py`:

Bővítsd a `ViewerDataResponse` modellt optional mezőkkel:

```python
requested_engine_backend: str | None = None
effective_engine_backend: str | None = None
backend_resolution_source: str | None = None
snapshot_engine_backend_hint: str | None = None
strategy_profile_version_id: str | None = None
strategy_resolution_source: str | None = None
strategy_field_sources: dict[str, Any] | None = None
strategy_overrides_applied: list[str] | None = None
```

A `get_viewer_data(...)` returnban ezeket az `engine_meta_payload` alapján add vissza.

Elvárások:

- Hiányzó/hibás engine_meta nem fatal.
- Dict/list mezőket típusellenőrzéssel normalizálj.
- `effective_engine_backend` fallbackelhet `engine_backend` értékre, ha az új mező hiányzik.
- A már meglévő viewer-data response mezők ne változzanak visszafelé inkompatibilis módon.

### 2. Frontend types

`frontend/src/lib/types.ts`:

A `ViewerDataResponse` interface kapja meg a backend régi és új optional evidence mezőit:

- `engine_backend`
- `engine_contract_version`
- `engine_profile`
- `input_artifact_source`
- `output_artifact_filename`
- `output_artifact_kind`
- `requested_engine_backend`
- `effective_engine_backend`
- `backend_resolution_source`
- `snapshot_engine_backend_hint`
- `strategy_profile_version_id`
- `strategy_resolution_source`
- `strategy_field_sources`
- `strategy_overrides_applied`

### 3. RunDetailPage

`frontend/src/pages/RunDetailPage.tsx`:

- Adj `ViewerDataResponse | null` state-et.
- A refresh során próbáld lekérni az `api.getViewerData(...)` endpointot.
- A viewer-data hiba ne írja felül a fő run betöltési hibát.
- Adj `Strategy and engine audit` kártyát.
- Mutasd legalább:
  - requested backend,
  - effective backend,
  - backend resolution source,
  - snapshot backend hint,
  - strategy profile version id,
  - strategy resolution source,
  - strategy overrides applied,
  - engine_meta artifact evidence present/missing.
- Használj stabil fallbacket: `-`, `Not available yet`, vagy hasonló.

### 4. Mock API + Playwright

`frontend/e2e/support/mockApi.ts`:

- Bővítsd a mock `ViewerData` interface-t az optional audit mezőkkel.
- A viewer-data route maradjon kompatibilis.

Új spec:

`frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`

Kötelező fő teszt:

- mock project + done run;
- engine_meta artifact;
- viewer-data audit mezők;
- Run Detail oldal betöltése;
- assert UI: `Strategy and engine audit`, `nesting_engine_v2`, `snapshot_solver_config`, `version-t5-1`, `run_config`, `quality_profile`, `engine_meta.json` vagy engine meta evidence.

Kötelező regressziós teszt:

- nincs viewer-data payload;
- Run Detail oldal továbbra is betölt;
- fallback audit szöveg látszik;
- nincs globális fatal error.

### 5. Smoke

`scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py`:

Offline source-level smoke. Ne igényeljen DB-t, Supabase-t vagy node_modules-t.

Minimum checkek:

- backend model mezők;
- backend return mezők;
- frontend type mezők;
- RunDetail `api.getViewerData` használat;
- RunDetail audit kártya szöveg;
- mock API viewer-data mezők;
- T5 spec kötelező assertion szövegek.

## Tesztparancsok

Futtasd:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py
```

Ha a frontend dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.config.ts frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts
```

Végül kötelező:

```bash
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md
```

## Zárási elvárás

A végén frissítsd:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.verify.log`

A reportban legyen DoD → Evidence matrix konkrét fájlútvonalakkal és lehetőség szerint sorsávokkal. Környezeti blocker esetén a státusz legyen őszinte: PASS csak ténylegesen lefutott gate esetén.
