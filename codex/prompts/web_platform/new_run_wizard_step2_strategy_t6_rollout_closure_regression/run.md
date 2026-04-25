# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T6 Rollout Closure Regression

TASK_SLUG: new_run_wizard_step2_strategy_t6_rollout_closure_regression

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/fill_canvas_new_run_wizard_step2_strategy_t6_rollout_closure_regression.yaml`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`
- `api/routes/run_configs.py`
- `api/routes/runs.py`
- `api/services/run_strategy_resolution.py`
- `api/services/run_creation.py`
- `api/services/run_snapshot_builder.py`
- `worker/main.py`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, mezőt vagy enumot. Minden contractot a valós backend route-okból, frontend API kliensből és T1–T5 reportokból vezess le.
- Ez T6 closure/regression/rollout task. Nem DB migration task, nem worker backend resolution task, nem strategy resolver precedence task, nem New Run Wizard UI redesign.
- Runtime kódot csak akkor módosíts, ha a felderítés bizonyított regressziót talál, és a módosított fájl szerepel YAML outputként. Alapértelmezett cél: új E2E, új smoke, új rollout doc, checklist/report.
- A T4 és T5 teszteket ne rontsd el. A T6 E2E egészítse ki őket, ne helyettesítse.
- A T6 full-chain E2E mock-alapú closure scenario legyen; ne függj Supabase-től, valódi DB-től, workertől vagy solver bináristól.
- A reportban PASS csak ténylegesen lefutott gate esetén szerepelhet. Környezeti blocker esetén BLOCKED/FAIL legyen pontos okkal.
- Titok, token, lokális env érték nem kerülhet repo-ba.

## Implementációs cél

A T1–T5 után a strategy választás külön-külön védett, de még nincs záró scenario és rollout dokumentum, amely egyben bizonyítja és üzemeltetési szinten lezárja a teljes láncot.

Ebben a taskban ezt kell elkészíteni:

1. Full-chain Playwright E2E: Step2 custom strategy → run-config payload → run create payload → Run Detail strategy/engine audit.
2. Offline closure smoke: T1–T5 contractok, T6 artefaktok, duplikátum-tiltás.
3. Rollout/compatibility dokumentum.
4. Checklist + záró report + verify.

## Részletes követelmények

### 1. Full-chain Playwright E2E

Új fájl:

`frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts`

A spec egyetlen pozitív closure scenario-t tartalmazzon.

Kötelező elemek:

- `installMockApi` használata;
- mock project + valid source DXF file;
- active strategy profile + active strategy version;
- `createdRunStatus: "done"`;
- `initialArtifactsByRun["run-1"]` engine_meta artifact;
- `initialViewerDataByRun["run-1"]` audit payload;
- wizard flow: project page → New run wizard → Step1 file választás → Step2 custom overrides → summary → Start run;
- `runConfigBodies.at(-1)` assert: profile version id, solver_config_overrides_jsonb quality/backend/budget/runtime-policy;
- `runCreateBodies.at(-1)` assert: run_config_id, profile version id, quality/backend/budget/runtime-policy;
- Run Detail assert: `Strategy and engine audit`, `nesting_engine_v2`, backend resolution source, profile version id, strategy resolution source, `quality_profile`, engine_meta evidence.

### 2. Rollout/compatibility doc

Új fájl:

`docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`

Legyen benne:

- T1–T5 feature chain rövid áttekintés;
- deploy sorrend: DB migration → backend → worker `WORKER_ENGINE_BACKEND=auto` → frontend → smoke/E2E/verify;
- compatibility matrix: régi requestek, régi run_configok, hiányzó project selection, hiányzó/regi engine_meta, `sparrow_v1` fallback;
- runtime ellenőrzési pontok: snapshot, engine_meta, viewer-data, Run Detail;
- rollback stratégia;
- known limitations.

### 3. Offline T6 smoke

Új fájl:

`scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py`

Ne importáljon app modult. Source-szintű file/string ellenőrzéseket végezzen.

Minimum checkek:

- T1 migration/API mezők;
- T2 resolver/snapshot bekötés;
- T3 worker auto backend + engine_meta mezők;
- T4 NewRunPage submit-flow + T4 spec;
- T5 viewer-data/RunDetail audit + T5 spec;
- T6 E2E spec és rollout doc létezése;
- T1–T6 artefaktok saját alkönyvtárban;
- nincs `new_run_wizard_step2_strategy_t*` gyökérszintű canvas/yaml duplikátum.

### 4. Checklist/report/verify

Hozd létre/frissítsd:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log`

A reportban legyen DoD → Evidence matrix.

## Tesztparancsok

Minimum:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py
```

Ha a frontend dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.config.ts frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts
```

Végül kötelező:

```bash
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md
```

## Zárási elvárás

A végén a reportban legyen egyértelmű:

- T6 E2E PASS vagy pontos blocker;
- T6 smoke PASS;
- rollout doc elkészült;
- T1–T5 reportok és artefaktok rendben;
- nincs új gyökérszintű duplikált artefakt;
- verify PASS vagy pontosan dokumentált blocker.
