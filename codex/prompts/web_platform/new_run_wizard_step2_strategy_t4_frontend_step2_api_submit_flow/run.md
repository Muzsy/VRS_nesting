# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T4 frontend Step2 API submit flow

TASK_SLUG: new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/fill_canvas_new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.yaml`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/phase4.stable.spec.ts`
- `api/routes/run_configs.py`
- `api/routes/runs.py`
- `api/routes/run_strategy_profiles.py`
- `api/routes/project_strategy_scoring_selection.py`
- `vrs_nesting/config/nesting_quality_profiles.py`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, mezőt vagy enumot. Minden contractot a valós backend route-okból vezess le.
- Ez T4 frontend task. Nem backend route/service task, nem DB migration, nem worker task, nem solver task.
- A meglévő New Run Wizard file/part selection és part requirement sync működését ne törjük el.
- A jelenlegi submit-flow hibát explicit javítani kell: a `createRunConfig(...)` válaszában kapott `id` menjen tovább `createRun(...)` payloadba `run_config_id` néven.
- `engine_backend_hint: "auto"` tilos backend felé. Az `auto` csak frontend UI mód, amely beküldéskor mezőkihagyást jelent.
- Project default strategy selection hiánya nem hiba: GET 404 esetén a wizard működjön tovább global default fallbackkel.
- Ne tárolj titkot, tokent vagy lokális env értéket.

## Implementációs cél

A T1/T2/T3 backend és worker lánc már tudja kezelni a strategy truth-ot, de a frontend Step2 jelenleg nem küldi be. Ebben a taskban a frontendnek kell ráülni a meglévő contractra:

1. Strategy profilok és project default selection lekérése.
2. Strategy source kiválasztása Step2-ben.
3. Custom override-ok valid, constrained UI-val.
4. `createRunConfig(...)` strategy mezők beküldése.
5. `createRun(...)` `run_config_id` és strategy request mezők beküldése.
6. E2E payload assert mock API alapján.

## Részletes követelmények

### 1. Types

`frontend/src/lib/types.ts`:

Add hozzá legalább:

```ts
export type QualityProfileName = "fast_preview" | "quality_default" | "quality_aggressive";
export type EngineBackendHint = "sparrow_v1" | "nesting_engine_v2";
export type EngineBackendHintMode = "auto" | EngineBackendHint;

export interface NestingEngineRuntimePolicy {
  placer: "blf" | "nfp";
  search: "none" | "sa";
  part_in_part: "off" | "auto";
  compaction: "off" | "slide";
  sa_iters?: number;
  sa_temp_start?: number;
  sa_temp_end?: number;
  sa_seed?: number;
  sa_eval_budget_sec?: number;
}

export interface SolverConfigOverrides {
  quality_profile?: QualityProfileName;
  sa_eval_budget_sec?: number;
  nesting_engine_runtime_policy?: NestingEngineRuntimePolicy;
  engine_backend_hint?: EngineBackendHint;
}
```

Add hozzá a profile/version/selection response típusokat a backend response modellekhez igazítva:

- `RunStrategyProfile`
- `RunStrategyProfileVersion`
- `ProjectRunStrategySelection`

### 2. API client

`frontend/src/lib/api.ts`:

Add importokat az új típusokra.

Add metódusok:

```ts
listRunStrategyProfiles(token: string): Promise<RunStrategyProfile[]>
listRunStrategyProfileVersions(token: string, profileId: string): Promise<RunStrategyProfileVersion[]>
getProjectRunStrategySelection(token: string, projectId: string): Promise<ProjectRunStrategySelection | null>
setProjectRunStrategySelection(token: string, projectId: string, versionId: string): Promise<ProjectRunStrategySelection>
```

Endpointok a valós backend alapján:

- `GET /run-strategy-profiles`
- `GET /run-strategy-profiles/{profile_id}/versions`
- `GET /projects/{project_id}/run-strategy-selection`
- `PUT /projects/{project_id}/run-strategy-selection`

`getProjectRunStrategySelection(...)` 404 esetén térjen vissza `null`-lal. Ehhez használhatsz külön kis fetch helpert, de ne bontsd meg a meglévő `request<T>` működését más hívások alatt.

`createRunConfig(...)` payload bővítés:

```ts
run_strategy_profile_version_id?: string;
solver_config_overrides_jsonb?: SolverConfigOverrides;
```

`createRun(...)` requestPayload bővítés:

```ts
...(payload?.run_config_id ? { run_config_id: payload.run_config_id } : {}),
...(payload?.run_strategy_profile_version_id ? { run_strategy_profile_version_id: payload.run_strategy_profile_version_id } : {}),
...(payload?.quality_profile ? { quality_profile: payload.quality_profile } : {}),
...(payload?.engine_backend_hint ? { engine_backend_hint: payload.engine_backend_hint } : {}),
...(payload?.nesting_engine_runtime_policy ? { nesting_engine_runtime_policy: payload.nesting_engine_runtime_policy } : {}),
...(typeof payload?.sa_eval_budget_sec === "number" ? { sa_eval_budget_sec: payload.sa_eval_budget_sec } : {}),
```

A `run_config_id` mező beküldése regressziós követelmény, mert jelenleg a típusban megvan, de a JSON bodyból hiányzik.

### 3. NewRunPage Step2 UI

`frontend/src/pages/NewRunPage.tsx`:

Tartsd meg a meglévő 3-step wizard struktúrát.

Add állapotokat:

- strategy loading/error állapot;
- `strategySource`: `project_default | choose_profile | custom`;
- strategy profile list;
- version list / versions by profile;
- selected profile id;
- selected version id;
- project default selection;
- quality profile;
- engine backend hint mode;
- SA eval budget;
- runtime policy mezők.

A Step2-ben jelenjen meg:

- Strategy source radio/select blokk;
- project default státusz;
- profile/version select `choose_profile` és `custom` módban;
- custom advanced blokk csak `custom` módban.

Ne követeld meg strategy profile meglétét ahhoz, hogy `Project default` módban run indulhasson.

### 4. Payload builder

A `NewRunPage.tsx`-ben hozz létre kis helper(eke)t, hogy ne az inline JSX/handler legyen bonyolult:

- `buildNestingRuntimePolicy()`;
- `buildSolverConfigOverrides()`;
- `buildRunStrategyRequestPayload()`;
- vagy ezekkel egyenértékű tiszta lokális helper.

Elvárás:

- `Project default`: nincs explicit strategy mező.
- `Choose profile`: `run_strategy_profile_version_id` legyen a választott version id.
- `Custom`: selected version id, quality profile, engine backend hint ha nem `auto`, runtime policy, SA budget.
- `auto` engine mode esetén ne kerüljön `engine_backend_hint` se a run_config override-ba, se a run requestbe.
- Ha `search !== "sa"`, ne küldj SA-only runtime policy mezőket.

### 5. Submit-flow

A `handleSubmitRun()` sorrend maradjon:

1. token lekérése;
2. `createRunConfig(...)`;
3. part requirement sync;
4. `createRun(...)`;
5. navigate run detailre.

De a `createRunConfig(...)` eredményét tedd változóba:

```ts
const runConfig = await api.createRunConfig(...);
```

Majd:

```ts
const run = await api.createRun(token, projectId, {
  run_config_id: runConfig.id,
  time_limit_s: timeLimit,
  ...strategyRunPayload,
});
```

### 6. Mock API + E2E

`frontend/e2e/support/mockApi.ts`:

- Add mock profile/version/selection state-et.
- Add route handlereket:
  - `GET /run-strategy-profiles`,
  - `GET /run-strategy-profiles/{profileId}/versions`,
  - `GET /projects/{projectId}/run-strategy-selection`,
  - `PUT /projects/{projectId}/run-strategy-selection`.
- Add capture listákat:
  - `runConfigBodies: Array<Record<string, unknown>>`,
  - `runCreateBodies: Array<Record<string, unknown>>`.
- `POST /run-configs` tegye bele a request bodyt a `runConfigBodies` listába.
- `POST /runs` tegye bele a request bodyt a `runCreateBodies` listába, és a mock run `run_config_id` mezője a bodyból jöjjön.

Új spec:

`frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts`

Minimum flow:

1. mock project + két DXF file előkészítés;
2. mock strategy profile + active version előkészítés;
3. wizard megnyitása;
4. part kiválasztás;
5. Step2 -> Custom overrides;
6. profile/version kiválasztás;
7. quality profile `quality_aggressive`;
8. backend hint `nesting_engine_v2`;
9. SA eval budget pozitív szám;
10. summary ellenőrzés;
11. Start run;
12. assert `mock.state.runConfigBodies.at(-1)` és `mock.state.runCreateBodies.at(-1)` mezők.

### 7. Report

A reportban ne csak azt írd, hogy PASS. Legyen konkrét evidence:

- fájl + funkció / route / UI blokk;
- melyik payload mezőt hol rakja be;
- melyik E2E assertion bizonyítja;
- build és Playwright eredmény;
- verify AUTO_VERIFY blokk.

## Kötelező ellenőrzések

Futtasd:

```bash
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md
```

A végén frissítsd:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.verify.log`

## Elvárt végállapot

- A frontend Step2 már nem csak metadata-szinten létezik: a kiválasztott strategy bejut a backend requestekbe.
- A `run_config_id` elvesztése megszűnik.
- A T2 resolver a wizardból jövő adatokkal tud dolgozni.
- A T3 worker a snapshotolt `engine_backend_hint` alapján futtat.
- A regressziót mock API + Playwright payload assert védi.
