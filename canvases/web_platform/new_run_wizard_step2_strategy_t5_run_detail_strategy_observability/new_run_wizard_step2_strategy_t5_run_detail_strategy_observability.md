# New Run Wizard Step2 Strategy — T5 Run detail strategy observability + integration smoke

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` fejlesztési lánc ötödik lépése.

A T1–T4 után a stratégia kiválasztása már végig tud menni a fő futtatási láncon:

1. T1: backend contract, `run_configs` strategy mezők, `run_config_id` run persistence.
2. T2: strategy resolver + snapshot precedence.
3. T3: worker `WORKER_ENGINE_BACKEND=auto` + `engine_meta.json` auditmezők.
4. T4: frontend Step2 strategy UI + `createRunConfig(...)` → `createRun(...)` submit-flow.

A T5 célja, hogy az eredmény a felhasználó és az auditor számára is látható legyen a run lezárása után:

- a backend `viewer-data` response adja vissza az `engine_meta.json` strategy/backend auditmezőit;
- a frontend típusok ismerjék ezeket a mezőket;
- a `RunDetailPage` jelenítse meg a tényleges strategy/engine auditot;
- legyen célzott frontend E2E és dedikált smoke, amely bizonyítja, hogy a T1–T4 által létrehozott truth nem csak elindul, hanem vissza is olvasható.

## Kiinduló valós repo-állapot T4 után

A friss repo alapján:

- `frontend/src/pages/NewRunPage.tsx`
  - Step2 strategy UI már létezik;
  - `createRunConfig(...)` válaszából kapott `runConfig.id` továbbmegy `createRun(...)` payloadba `run_config_id` néven;
  - custom strategy esetén a run-config és run request strategy mezők bekerülnek a request bodykba.

- `frontend/src/lib/api.ts`
  - létezik `getViewerData(token, projectId, runId)`;
  - léteznek a strategy profile/selection kliensmetódusok;
  - `createRun(...)` már beküldi a `run_config_id`-t és a strategy request mezőket.

- `frontend/src/lib/types.ts`
  - a `ViewerDataResponse` jelenleg csak alap viewer mezőket tartalmaz:
    - `run_id`, `status`, `sheet_count`, `sheets`, `placements`, `unplaced`;
  - a backend `ViewerDataResponse` viszont már korábbról tartalmaz néhány engine evidence mezőt:
    - `engine_backend`,
    - `engine_contract_version`,
    - `engine_profile`,
    - `input_artifact_source`,
    - `output_artifact_filename`,
    - `output_artifact_kind`;
  - a frontend típus tehát nincs teljesen szinkronban a backend válasszal.

- `api/routes/runs.py`
  - a `get_viewer_data(...)` már letölti az `engine_meta.json` artifactot, ha van;
  - ebből jelenleg csak néhány régi mezőt tesz ki a response-ba;
  - a T3 által bevezetett új auditmezők nem kerülnek ki a `ViewerDataResponse`-ba:
    - `requested_engine_backend`,
    - `effective_engine_backend`,
    - `backend_resolution_source`,
    - `snapshot_engine_backend_hint`,
    - `strategy_profile_version_id`,
    - `strategy_resolution_source`,
    - `strategy_field_sources`,
    - `strategy_overrides_applied`.

- `frontend/src/pages/RunDetailPage.tsx`
  - jelenleg `api.getRun(...)`, `api.listRunArtifacts(...)` és futás közben `api.getRunLog(...)` hívásokat használ;
  - nem hívja a `viewer-data` endpointot;
  - nem jelenít meg strategy/backend audit mezőket.

- `frontend/e2e/support/mockApi.ts`
  - van `viewer-data` mock route;
  - a `ViewerData` mock interface nem tartalmazza az engine/strategy observability mezőket;
  - a RunDetail oldalhoz nincs célzott strategy audit E2E.

## Scope

### Benne van

1. Backend `viewer-data` response bővítés az `engine_meta.json` T3/T4 auditmezőivel.
2. Frontend `ViewerDataResponse` típus szinkronizálása a backend válasszal.
3. `RunDetailPage` non-fatal `viewer-data` lekérése és strategy/engine audit kártya megjelenítése.
4. Mock API viewer-data típus és mock adatok bővítése.
5. Új Playwright E2E, amely bizonyítja, hogy a Run Detail oldal megjeleníti az auditmezőket.
6. Új dedikált smoke script, amely DB és valódi solver nélkül ellenőrzi a contractot/source-szintű bekötést.
7. Checklist + report + standard verify.

### Nincs benne

1. DB migration.
2. Worker backend resolution logika módosítása.
3. Strategy resolver precedence módosítása.
4. Strategy profile CRUD UI.
5. New Run Wizard Step2 újratervezése.
6. Viewer rajzolási logika módosítása.
7. Production rollout dokumentáció véglegesítése; az külön T6/polish task lehet.

## Backend követelmények

Fájl: `api/routes/runs.py`

### 1. `ViewerDataResponse` bővítés

A meglévő response model optional mezőkkel bővüljön:

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

Megjegyzés: `Any` már importálva van a fájlban; ha nincs, csak valós importtal bővítsd.

### 2. `get_viewer_data(...)` return bővítés

A meglévő `engine_meta_payload` alapján töltsd az új mezőket.

Elvárt viselkedés:

- Ha az `engine_meta.json` hiányzik vagy nem olvasható, a mezők `None` értéket kapjanak, ne legyen 500-as hiba.
- `effective_engine_backend` preferált forrása: `engine_meta_payload["effective_engine_backend"]`.
- Ha ez hiányzik, de `engine_backend` jelen van, használható fallbackként `engine_backend` a visszafelé kompatibilitás miatt.
- `strategy_field_sources` csak akkor legyen dict, ha az artifactban dictként szerepel.
- `strategy_overrides_applied` csak akkor legyen string lista, ha az artifactban listaként szerepel; más típusnál legyen `None` vagy normalizált string lista, de ne dobjon hibát.

## Frontend követelmények

### 1. Típusok

Fájl: `frontend/src/lib/types.ts`

A `ViewerDataResponse` kapja meg a backend response-ban létező régi és új optional mezőket:

```ts
engine_backend?: string | null;
engine_contract_version?: string | null;
engine_profile?: string | null;
input_artifact_source?: string | null;
output_artifact_filename?: string | null;
output_artifact_kind?: string | null;
requested_engine_backend?: string | null;
effective_engine_backend?: string | null;
backend_resolution_source?: string | null;
snapshot_engine_backend_hint?: string | null;
strategy_profile_version_id?: string | null;
strategy_resolution_source?: string | null;
strategy_field_sources?: Record<string, string> | null;
strategy_overrides_applied?: string[] | null;
```

### 2. RunDetailPage observability panel

Fájl: `frontend/src/pages/RunDetailPage.tsx`

A `RunDetailPage` bővüljön úgy, hogy:

1. A meglévő `refreshRunData(includeLogs)` továbbra is lekéri a run-t és artifacts listát.
2. Emellett próbálja lekérni a viewer-data endpointot `api.getViewerData(token, projectId, runId)` hívással.
3. A viewer-data hiba ne törje el a run detail oldalt:
   - ha a viewer-data még nem elérhető, ne állíts globális `error` állapotot;
   - az audit kártyán jelenjen meg, hogy az audit evidence még nem elérhető.
4. Jelenjen meg egy új kártya például `Strategy and engine audit` címmel.
5. A kártya jelenítse meg legalább:
   - requested backend,
   - effective backend,
   - backend resolution source,
   - snapshot backend hint,
   - strategy profile version id,
   - strategy resolution source,
   - strategy overrides applied,
   - artifact evidence státusz: van-e `engine_meta.json` / `engine_meta` artifact a run artifacts listában.
6. Régi runoknál, ahol nincs engine_meta/viewer-data evidence, az oldal ne omoljon össze; `-` vagy `Not available yet` fallback legyen.

## E2E követelmények

Fájlok:

- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`

### Mock API

Bővítsd a mock `ViewerData` interface-t ugyanazokkal az optional observability mezőkkel, mint a frontend `ViewerDataResponse`.

A meglévő `GET /projects/{projectId}/runs/{runId}/viewer-data` mock route maradjon, de tudjon ilyen mezőket visszaadni.

### Playwright scenario

Hozz létre célzott E2E-t, amely:

1. Létrehoz mock projectet.
2. Létrehoz egy `done` státuszú mock run-t.
3. Ad a runhoz artifact listát, benne legalább:
   - `artifact_type: "engine_meta"`,
   - `filename: "engine_meta.json"`.
4. Ad a runhoz `viewerDataByRun` payloadot ezekkel a mezőkkel:
   - `requested_engine_backend: "auto"`,
   - `effective_engine_backend: "nesting_engine_v2"`,
   - `backend_resolution_source: "snapshot_solver_config"`,
   - `snapshot_engine_backend_hint: "nesting_engine_v2"`,
   - `strategy_profile_version_id: "version-t5-1"`,
   - `strategy_resolution_source: "run_config"`,
   - `strategy_overrides_applied: ["quality_profile", "engine_backend_hint"]`.
5. Navigál közvetlenül a Run Detail oldalra.
6. Assertálja, hogy a UI-ban megjelenik:
   - `Strategy and engine audit`,
   - `nesting_engine_v2`,
   - `snapshot_solver_config`,
   - `version-t5-1`,
   - `run_config`,
   - `quality_profile`,
   - `engine_meta.json` vagy engine meta artifact present jelzés.

## Smoke követelmények

Új fájl:

`scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py`

A smoke legyen offline-barát. Ne igényeljen Supabase-t, DB-t, valódi workert vagy solver binárist.

Ajánlott ellenőrzések:

1. Source check: `api/routes/runs.py` `ViewerDataResponse` tartalmazza az új mezőket.
2. Source check: `get_viewer_data(...)` return blokk engine_meta_payloadból tölti az új mezőket.
3. Source check: `frontend/src/lib/types.ts` `ViewerDataResponse` tartalmazza az új mezőket.
4. Source check: `frontend/src/pages/RunDetailPage.tsx` hívja az `api.getViewerData(...)` metódust.
5. Source check: `RunDetailPage` tartalmazza a `Strategy and engine audit` UI szöveget.
6. Source check: `frontend/e2e/support/mockApi.ts` `ViewerData` interface tartalmazza az új mezőket.
7. Source check: az új Playwright spec tartalmazza a kötelező assertionöket.

A smoke a végén írjon összesítést, például `PASS: 20 checks passed`, és nem nulla exit code-dal álljon le hiba esetén.

## Tesztelés

Minimum célzott parancsok:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.config.ts frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md
```

Ha a lokális környezetben nincs `frontend/node_modules` vagy Playwright browser, azt a reportban környezeti blockernek kell jelölni, nem szabad PASS-nak hazudni. Ettől még a Python smoke és a repo verify eredményét külön kell rögzíteni.

## DoD

A T5 akkor kész, ha:

1. Backend `viewer-data` response kiteszi a T3 engine_meta strategy/backend auditmezőket.
2. Régi runoknál vagy hiányzó engine_meta esetén nincs 500-as hiba.
3. Frontend `ViewerDataResponse` típus szinkronban van a backend response-szal.
4. Run Detail oldal non-fatal módon lekéri a viewer-data-t.
5. Run Detail oldal megjeleníti a strategy/backend audit kártyát.
6. A kártya fallbackkel működik akkor is, ha még nincs viewer-data evidence.
7. Mock API viewer-data támogatja az új mezőket.
8. Új Playwright E2E PASS a strategy/engine audit UI-ra.
9. Dedikált T5 smoke PASS.
10. `./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md` PASS vagy reportban pontosan dokumentált környezeti blockerrel FAIL.
11. Checklist és report evidence matrix elkészült.
12. Nincs gyökérszintű duplikált canvas/yaml/runner artefakt; minden task artefakt saját alkönyvtárban van.

## Kockázatok és rollback

### Kockázat: viewer-data hiba elrontja a Run Detail oldalt

Mitigáció:

- A `api.getViewerData(...)` hívás legyen külön try/catch vagy `Promise.allSettled` jellegű.
- Hibája ne írja felül a fő run/artifact error állapotot.

Rollback:

- A Run Detail audit kártya és viewer-data fetch eltávolítható úgy, hogy a meglévő run/artifact/log flow változatlan marad.

### Kockázat: backend response régi runoknál hiányos engine_meta miatt hibázik

Mitigáció:

- Minden új mező optional.
- Típusellenőrzött dict/list normalizálás.

Rollback:

- Csak a response model és return mezők bővítése revertelhető; a meglévő `engine_backend` mezők maradnak.

### Kockázat: frontend típus / backend mezőnév eltérés

Mitigáció:

- A smoke explicit source checkkel ellenőrzi ugyanazokat a mezőneveket backendben, frontend típusban, RunDetail UI-ban és E2E mockban.

## Lokalizáció

Nem releváns. A meglévő frontend angol UI nyelvet követi.

## Kapcsolódások

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- `api/routes/runs.py`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/lib/types.ts`
- `frontend/e2e/support/mockApi.ts`
