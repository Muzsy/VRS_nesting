# New Run Wizard Step2 Strategy — T6 Rollout closure + full-chain regression

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` fejlesztési lánc záró, integrációs és rollout-előkészítő lépése.

A T1–T5 után a fő elemek már külön-külön megvannak:

1. T1: backend contract, `run_configs` strategy mezők, `run_config_id` run persistence.
2. T2: strategy resolver + snapshot precedence.
3. T3: worker `WORKER_ENGINE_BACKEND=auto` + `engine_meta.json` auditmezők.
4. T4: frontend Step2 strategy UI + `createRunConfig(...)` → `createRun(...)` submit-flow.
5. T5: `viewer-data` response + Run Detail strategy/engine audit kártya.

A T6 célja nem új üzleti funkció, hanem a teljes lánc lezárása és regressziós védelme:

- legyen egy teljes mock frontend E2E, amely egyetlen scenario-ban végigviszi a Step2 strategy választást a Run Detail audit megjelenítésig;
- legyen offline closure smoke, amely source-szinten ellenőrzi a T1–T5 kritikus szerződéseit és artefaktjait;
- legyen rollout/kompatibilitási dokumentum a bevezetési sorrendről, fallbackekről és üzemeltetési ellenőrzésekről;
- legyen záró checklist/report, amely bizonyítja, hogy a feature-lánc deploy-ready állapotban van.

## Kiinduló valós repo-állapot T5 után

A friss repo alapján:

- `api/routes/run_configs.py`
  - a run-config contract már támogatja a strategy profile version és solver config override mezőket.

- `api/routes/runs.py`
  - `RunCreateRequest` már támogatja a T1/T2 strategy mezőket;
  - `ViewerDataResponse` már tartalmazza a T5 auditmezőket;
  - `get_viewer_data(...)` az `engine_meta_payload` alapján adja vissza a strategy/backend evidence mezőket.

- `api/services/run_strategy_resolution.py`
  - létezik a resolver;
  - a precedence lánc célja: request > run_config > project selection > global default.

- `api/services/run_creation.py`
  - a run creation hívja a strategy resolvert, és a resolved értékeket snapshot buildernek adja.

- `api/services/run_snapshot_builder.py`
  - a snapshot `solver_config_jsonb` tartalmazza a resolved strategy/backend truth mezőket és trace adatokat.

- `worker/main.py`
  - `WORKER_ENGINE_BACKEND=auto` támogatott;
  - snapshot `solver_config_jsonb.engine_backend_hint` alapján választ backend-et;
  - `engine_meta.json` tartalmazza a requested/effective backend és strategy trace mezőket.

- `frontend/src/pages/NewRunPage.tsx`
  - Step2 strategy UI létezik;
  - a `createRunConfig(...)` válaszából kapott `runConfig.id` továbbmegy a `createRun(...)` payloadba;
  - custom strategy esetén a strategy override mezők is bekerülnek a run requestbe.

- `frontend/src/pages/RunDetailPage.tsx`
  - non-fatal módon hívja az `api.getViewerData(...)` endpointot;
  - megjeleníti a `Strategy and engine audit` kártyát.

- `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts`
  - Step2 submit-flow külön védve van.

- `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`
  - Run Detail observability külön védve van.

A hiány: nincs egyetlen záró scenario, amely a frontendben egyben bizonyítja, hogy a Step2-ben kiválasztott strategy adat a run indítás után ugyanazon run Run Detail audit nézetében is visszaolvasható.

## Scope

### Benne van

1. Új full-chain Playwright E2E:
   - New Run Wizard Step2 custom strategy választás;
   - `createRunConfig(...)` body assert;
   - `createRun(...)` body assert;
   - navigáció Run Detail oldalra;
   - Run Detail `Strategy and engine audit` kártya assert ugyanahhoz a létrehozott runhoz.
2. Új offline closure smoke:
   - T1–T5 kritikus source contractok ellenőrzése;
   - kötelező T1–T5 artefakt könyvtárak és reportok ellenőrzése;
   - gyökérszintű duplikált artefaktok tiltása a new run wizard strategy taskokra.
3. Rollout és kompatibilitási dokumentum:
   - DB/backend/worker/frontend deploy sorrend;
   - env defaultok és fallbackek;
   - compatibility matrix régi runokra és hiányzó `engine_meta.json` esetekre;
   - smoke/E2E/verify parancslista;
   - rollback javaslat.
4. Checklist + report + standard verify.

### Nincs benne

1. Új DB migration.
2. Új strategy resolver precedence logika.
3. Worker backend resolution módosítása.
4. New Run Wizard Step2 UI újratervezése.
5. Strategy profile CRUD UI.
6. Viewer geometria vagy nesting engine algoritmus módosítása.
7. Production deploy tényleges végrehajtása.

## Frontend E2E követelmények

Új fájl:

`frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts`

A spec a meglévő mock API képességeire épüljön. Ne vezessen be külső szolgáltatásfüggést.

### Kötelező scenario: Step2 strategy → run create → Run Detail audit

1. Hozzon létre mock projectet és legalább egy valid DXF source file-t úgy, ahogy a T4 spec teszi.
2. Hozzon létre mock strategy profile-t és active version-t.
3. `installMockApi(...)` kapjon `createdRunStatus: "done"` beállítást.
4. A mock API `runCounter` indulása miatt a létrejövő run várhatóan `run-1`; ehhez előre állíts be:
   - `initialArtifactsByRun["run-1"]` engine_meta artifacttal;
   - `initialViewerDataByRun["run-1"]` strategy/backend audit payload-dal.
5. Nyisd meg a project oldalt, indítsd a `New run wizard` flow-t.
6. Step1-ben válassz legalább egy part file-t.
7. Step2-ben válaszd a `Custom overrides` módot.
8. Válaszd ki a profile-t és version-t.
9. Állítsd:
   - quality profile: `quality_aggressive`;
   - engine backend: `nesting_engine_v2`;
   - SA eval budget: `2` vagy egy kis pozitív integer.
10. Menj summary oldalra, indíts run-t.
11. Assertáld a `mock.state.runConfigBodies.at(-1)` body-ban:
   - `run_strategy_profile_version_id` a választott version id;
   - `solver_config_overrides_jsonb.quality_profile === "quality_aggressive"`;
   - `solver_config_overrides_jsonb.engine_backend_hint === "nesting_engine_v2"`;
   - `solver_config_overrides_jsonb.sa_eval_budget_sec` szám;
   - `solver_config_overrides_jsonb.nesting_engine_runtime_policy` létezik.
12. Assertáld a `mock.state.runCreateBodies.at(-1)` body-ban:
   - van `run_config_id`;
   - `run_strategy_profile_version_id` a választott version id;
   - `quality_profile === "quality_aggressive"`;
   - `engine_backend_hint === "nesting_engine_v2"`;
   - `sa_eval_budget_sec` szám;
   - `nesting_engine_runtime_policy` létezik.
13. Assertáld Run Detail oldalon:
   - `Strategy and engine audit` látszik;
   - `nesting_engine_v2` látszik;
   - `snapshot_solver_config` vagy a mockban megadott backend resolution source látszik;
   - a választott profile version id látszik;
   - `run_config` vagy a mockban megadott strategy resolution source látszik;
   - `quality_profile` látszik;
   - engine_meta artifact evidence látszik.

### Regressziós elvárás

Nem szükséges külön harmadik/negatív teszt, mert T4 és T5 már külön lefedi a project default payload és viewer-data fallback eseteket. A T6 spec célja a teljes pozitív lánc egyben tartása.

## Offline closure smoke követelmények

Új fájl:

`scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py`

A smoke legyen offline-barát. Ne igényeljen Supabase-t, DB-t, node_modules-t, workert vagy solver binárist.

Minimum ellenőrzések:

1. T1 migration és backend contract:
   - `supabase/migrations/*strategy*runconfig*` vagy a tényleges T1 migration tartalmazza a `run_strategy_profile_version_id` és `solver_config_overrides_jsonb` mezőket;
   - `api/routes/run_configs.py` tartalmazza a strategy mezőket és validációs whitelist kulcsokat;
   - `api/routes/runs.py` `RunCreateRequest` tartalmazza a `run_config_id` és strategy override mezőket.
2. T2 resolver/snapshot:
   - `api/services/run_strategy_resolution.py` létezik;
   - szerepelnek benne a precedence források: request, run_config, project selection/global default;
   - `api/services/run_creation.py` hívja a resolvert;
   - `api/services/run_snapshot_builder.py` tartalmazza a strategy trace mezőket.
3. T3 worker:
   - `worker/main.py` támogatja az `auto` backend módot;
   - használja a snapshot `engine_backend_hint` mezőt;
   - írja vagy továbbadja az engine_meta auditmezőket.
4. T4 frontend submit-flow:
   - `frontend/src/pages/NewRunPage.tsx` hívja a `createRunConfig(...)` és `createRun(...)` metódusokat;
   - `run_config_id` bekerül a run payloadba;
   - strategy mezők szerepelnek a payload mappingben;
   - `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts` létezik.
5. T5 observability:
   - `api/routes/runs.py` `ViewerDataResponse` tartalmazza az auditmezőket;
   - `frontend/src/pages/RunDetailPage.tsx` hívja az `api.getViewerData(...)` metódust és tartalmazza a `Strategy and engine audit` szöveget;
   - `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts` létezik.
6. T6 artefaktok:
   - ez a T6 canvas/yaml/runner az új alkönyvtárakban legyen;
   - az új T6 E2E spec létezzen;
   - az új T6 rollout doc létezzen.
7. Artefakt-fegyelem:
   - ne legyen `new_run_wizard_step2_strategy_t*` canvas/yaml gyökérszintű duplikátum a `canvases/web_platform` vagy `codex/goals/canvases/web_platform` alatt;
   - a T1–T6 canvas/yaml/runner mind saját slug alkönyvtárban legyen.

A script a végén írjon összesítést, például `PASS: 80 checks passed`, és hiba esetén nem nulla exit code-dal álljon le.

## Rollout és kompatibilitási dokumentum

Új fájl:

`docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`

Tartalom:

1. Feature áttekintés: T1–T5 mit kötött be.
2. Deploy sorrend:
   - DB migration;
   - backend;
   - worker `WORKER_ENGINE_BACKEND=auto`;
   - frontend;
   - smoke/E2E/verify.
3. Visszafelé kompatibilitás:
   - régi run create request mezők nélkül;
   - régi run_config strategy mezők nélkül;
   - hiányzó project strategy selection;
   - hiányzó vagy régi `engine_meta.json`;
   - `sparrow_v1` fallback.
4. Runtime ellenőrzési pontok:
   - snapshot `solver_config_jsonb`;
   - `engine_meta.json`;
   - `viewer-data` response;
   - Run Detail audit kártya.
5. Rollback stratégia:
   - frontend rollback;
   - worker env override `WORKER_ENGINE_BACKEND=sparrow_v1`;
   - backend optional mezők miatt compatibility megőrzés;
   - DB mezők optional jellege.
6. Known limitations:
   - Run Detail polling optimalizálható;
   - `strategy_field_sources` UI renderelése későbbi polish;
   - production valódi solver E2E külön infra-smoke marad.

## Checklist és report

Új/érintett fájlok:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log`

A report a `docs/codex/report_standard.md` szerint készüljön.

Kötelező evidence matrix sorok:

1. T6 E2E spec létezik és PASS.
2. T6 offline smoke létezik és PASS.
3. Rollout/compatibility doc létezik.
4. T1–T5 reportok léteznek és PASS státuszt tartalmaznak.
5. T1–T6 task artefaktok saját alkönyvtárban vannak.
6. Nincs new_run_wizard_step2_strategy gyökérszintű duplikált canvas/yaml.
7. `npm --prefix frontend run build` PASS vagy pontos környezeti blocker.
8. T4, T5 és T6 célzott Playwright spec PASS vagy pontos környezeti blocker.
9. `./scripts/verify.sh --report ...` PASS.

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

## Definition of Done

A T6 akkor kész, ha:

1. A T6 full-chain E2E egyben bizonyítja a Step2 custom strategy → run-config → run create → Run Detail audit láncot.
2. A T6 offline closure smoke PASS.
3. A rollout/compatibility dokumentum elkészült.
4. A T1–T5 eredményekre építő záró report evidence matrix-szal elkészült.
5. Nincs új gyökérszintű duplikált artefakt.
6. A standard verify gate PASS, vagy ha környezeti blocker van, az reportban pontosan dokumentált és nem hamis PASS.
