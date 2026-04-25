# New Run Wizard Step2 Strategy — T4 Frontend Step2 UI + API submit flow

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` fejlesztés negyedik lépése.

A T1 létrehozta a backend contract alapjait: `run_configs` strategy mezők, `RunCreateRequest` strategy mezők, `run_config_id` persistence és explicit snapshot override támogatás.
A T2 bekötötte a strategy resolver + snapshot precedence láncot.
A T3 bekötötte a worker `WORKER_ENGINE_BACKEND=auto` módot és az `engine_meta.json` auditmezőket.

A T4 célja, hogy a frontend `New Run Wizard` Step2 oldala ténylegesen ki tudja választani és beküldeni a stratégiát, valamint a jelenlegi submit-flow hiba megszűnjön: a létrehozott `run_config.id` menjen tovább a `createRun(...)` hívásba.

A T4 végeredménye:

- Step2-ben látható és használható strategy blokk jelenik meg;
- a frontend API kliens ismeri a strategy profile/version és project selection endpointokat;
- `createRunConfig(...)` képes beküldeni a T1 mezőket:
  - `run_strategy_profile_version_id`,
  - `solver_config_overrides_jsonb`;
- `createRun(...)` ténylegesen beküldi a `run_config_id`-t;
- `createRun(...)` képes beküldeni a T1/T2 run-level strategy request mezőket:
  - `run_strategy_profile_version_id`,
  - `quality_profile`,
  - `engine_backend_hint`,
  - `nesting_engine_runtime_policy`,
  - `sa_eval_budget_sec`;
- Step3 summary megmutatja a kiválasztott strategy állapotot;
- Playwright E2E mock API bizonyítja, hogy a request payloadok ténylegesen tartalmazzák a `run_config_id`-t és a strategy mezőket.

## Kiinduló valós repo-állapot T3 után

A friss repo alapján:

- `frontend/src/pages/NewRunPage.tsx`
  - jelenleg csak file selection + alap run paramétereket kezel;
  - Step2 mezők: `name`, `seed`, `timeLimit`, `spacing`, `margin`;
  - nincs strategy source selector;
  - nincs profile/version lista;
  - nincs quality profile selector;
  - nincs engine backend hint selector;
  - nincs runtime policy editor;
  - `handleSubmitRun()` meghívja a `api.createRunConfig(...)` metódust, de az eredményt nem menti el;
  - utána `api.createRun(token, projectId, { time_limit_s: timeLimit })` fut, tehát a létrehozott `run_config_id` jelenleg nem jut el a backendbe.

- `frontend/src/lib/api.ts`
  - `createRunConfig(...)` payload típusa még nem tartalmazza a strategy mezőket;
  - `createRun(...)` payload típusa már tartalmaz `run_config_id?: string`, de a `requestPayload` összeállítása jelenleg nem küldi be;
  - `createRun(...)` nem támogatja a strategy request mezőket;
  - nincs `listRunStrategyProfiles()`;
  - nincs `listRunStrategyProfileVersions(profileId)`;
  - nincs `getProjectRunStrategySelection(projectId)`;
  - nincs `setProjectRunStrategySelection(projectId, versionId)`.

- `frontend/src/lib/types.ts`
  - nincs `RunStrategyProfile` típus;
  - nincs `RunStrategyProfileVersion` típus;
  - nincs `ProjectRunStrategySelection` típus;
  - nincs közös strategy override / runtime policy típus.

- `frontend/e2e/support/mockApi.ts`
  - nem mockolja a strategy profile endpointokat;
  - nem mockolja a project run strategy selection endpointot;
  - nem tárolja külön a `run-configs` POST bodykat;
  - nem tárolja külön a `runs` POST bodykat, ezért payload assert csak bővítés után lehetséges.

- Backend contract T1/T2 után:
  - `POST /projects/{project_id}/run-configs` elfogadja:
    - `run_strategy_profile_version_id`,
    - `solver_config_overrides_jsonb`;
  - `POST /projects/{project_id}/runs` elfogadja:
    - `run_config_id`,
    - `run_strategy_profile_version_id`,
    - `quality_profile`,
    - `engine_backend_hint`,
    - `nesting_engine_runtime_policy`,
    - `sa_eval_budget_sec`;
  - API szinten az `engine_backend_hint` megengedett értékei: `sparrow_v1`, `nesting_engine_v2`.
  - Fontos: a worker `auto` módja környezeti worker runtime mód, nem API `engine_backend_hint`. Ezért frontendben az `Auto / resolver default` UI opciót úgy kell kezelni, hogy nem küld `engine_backend_hint` mezőt.

## Scope

### Benne van

1. Frontend típusok bővítése:
   - `RunStrategyProfile`,
   - `RunStrategyProfileVersion`,
   - `ProjectRunStrategySelection`,
   - `QualityProfileName`,
   - `EngineBackendHint`,
   - `EngineBackendHintMode` ahol `auto` csak UI mód és beküldéskor mezőkihagyást jelent,
   - `NestingEngineRuntimePolicy`,
   - `SolverConfigOverrides`,
   - `CreateRunStrategyPayload` / közös payload típusok, ha ez tisztábbá teszi az API kliens kódját.

2. Frontend API kliens bővítés:
   - `listRunStrategyProfiles(token)`,
   - `listRunStrategyProfileVersions(token, profileId)`,
   - `getProjectRunStrategySelection(token, projectId)`; 404 esetén adjon `null`-t, ne törje el a wizardot,
   - `setProjectRunStrategySelection(token, projectId, versionId)` mint kliensmetódus, UI-ból egyelőre nem kötelező használni,
   - `createRunConfig(...)` strategy mezők támogatása,
   - `createRun(...)` javítása: `run_config_id` ténylegesen kerüljön be a JSON bodyba,
   - `createRun(...)` strategy request mezők támogatása.

3. `NewRunPage.tsx` Step2 UI bővítés:
   - Strategy source blokk:
     - `Project default`,
     - `Choose profile`,
     - `Custom overrides`;
   - Profile/version selector `Choose profile` és `Custom overrides` módban;
   - Advanced overrides blokk `Custom overrides` módban:
     - quality profile dropdown: `fast_preview`, `quality_default`, `quality_aggressive`,
     - engine backend hint mód: `auto`, `sparrow_v1`, `nesting_engine_v2`, ahol `auto` nem kerül beküldésre,
     - SA eval budget mező,
     - constrained runtime policy editor:
       - `placer`: `blf | nfp`,
       - `search`: `none | sa`,
       - `part_in_part`: `off | auto`,
       - `compaction`: `off | slide`,
       - opcionális `sa_iters`, csak `search=sa` esetén.
   - Project default előtöltés:
     - Step2 betöltésekor / oldal betöltésekor próbálja lekérni a project default strategy selectiont;
     - ha nincs selection (404), az nem hiba, csak jelenjen meg: `No project default strategy selected`;
     - ha van selection, summary-ban mutassa a profile/version azonosítót, amennyire a kliens meg tudja nevezni.

4. Submit-flow javítás:
   - `handleSubmitRun()` először `createRunConfig(...)`-ot hívjon;
   - mentse el a visszakapott `runConfig.id` értéket;
   - part requirement sync maradjon a mostani sorrendben és logikával;
   - `createRun(...)` kapja meg a `run_config_id: runConfig.id` mezőt;
   - strategy mezők is menjenek át a run request payloadba a Step2 választás alapján;
   - `Project default` módban ne küldjön explicit strategy override-ot, csak a `run_config_id`-t, így T2 resolver project selection / global default ága dolgozhat;
   - `Choose profile` módban küldje a kiválasztott `run_strategy_profile_version_id`-t;
   - `Custom overrides` módban küldje a kiválasztott profile versiont, ha van, és a runtime override mezőket.

5. Step3 summary:
   - Strategy source,
   - selected profile/version,
   - quality profile,
   - engine backend hint mód,
   - SA eval budget,
   - runtime policy rövid összefoglaló.

6. Playwright mock + E2E:
   - `frontend/e2e/support/mockApi.ts` bővítése strategy endpointokkal és request body capture-rel;
   - új spec: `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts`;
   - minimum assert:
     - Step2 strategy UI megjelenik;
     - custom strategy kiválasztása után a summary mutatja a választást;
     - `POST /run-configs` body tartalmazza a `run_strategy_profile_version_id` mezőt és a `solver_config_overrides_jsonb` objektumot;
     - `POST /runs` body tartalmazza a `run_config_id` mezőt;
     - `POST /runs` body tartalmazza a strategy request mezőket.

7. Report/checklist:
   - `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`;
   - `codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`;
   - reportban DoD -> Evidence matrix.

### Nincs benne

- Új DB migration;
- backend route/service módosítás;
- worker módosítás;
- engine_meta módosítás;
- project default mentés UI checkboxból;
- strategy profile CRUD UI;
- run detail / viewer strategy megjelenítés;
- solver / nesting algoritmus módosítás.

## Implementációs részletek

### 1. Frontend API contract pontosítása

`frontend/src/lib/api.ts`:

- `createRunConfig(...)` payload típusa bővüljön:

```ts
run_strategy_profile_version_id?: string;
solver_config_overrides_jsonb?: SolverConfigOverrides;
```

- `createRun(...)` payload típusa bővüljön és a request body ténylegesen küldje tovább:

```ts
run_config_id?: string;
run_strategy_profile_version_id?: string;
quality_profile?: QualityProfileName;
engine_backend_hint?: EngineBackendHint;
nesting_engine_runtime_policy?: NestingEngineRuntimePolicy;
sa_eval_budget_sec?: number;
```

A mostani hiba kifejezetten itt van: a típusban már szerepelhet `run_config_id`, de a `requestPayload` nem teszi bele a bodyba. Ezt explicit javítani kell.

### 2. `auto` engine backend hint UI kezelés

Backend API validáció alapján `engine_backend_hint` csak:

- `sparrow_v1`,
- `nesting_engine_v2`.

A frontend UI-ban lehet `auto` opció, de ez csak azt jelenti: `omit engine_backend_hint`. Ne küldj `engine_backend_hint: "auto"` mezőt, mert a backend visszadobja.

### 3. Runtime policy editor

A runtime policy csak akkor legyen beküldve, ha `Custom overrides` mód aktív.

A beküldött objektum legyen valid a backend `validate_runtime_policy(...)` helperéhez:

```json
{
  "placer": "nfp",
  "search": "sa",
  "part_in_part": "auto",
  "compaction": "slide",
  "sa_iters": 768
}
```

Ha `search = "none"`, akkor SA mezőket ne küldj.

`sa_eval_budget_sec` menjen külön top-level mezőként is, ha a user megadta, mert T2 resolver ezt külön kezeli és beágyazza a runtime policyba.

### 4. Project default előtöltés

A `getProjectRunStrategySelection(...)` 404 esetén térjen vissza `null`-lal. Ez fontos, mert a project default hiánya normál állapot, nem blocking error.

A UI ne akadjon el, ha:

- nincs egyetlen strategy profile sem;
- van project default selection, de a profil listázás valamiért üres;
- a strategy endpoint átmenetileg hibázik.

Ilyenkor a fájl + alap paraméter workflow maradjon használható, és `Project default` / global default resolver fallback tovább működjön.

### 5. Submit payload elvárt minta

Custom overrides esetén a két request elvárt lényege:

`POST /projects/{project_id}/run-configs`:

```json
{
  "name": "run-config",
  "schema_version": "dxf_v1",
  "seed": 0,
  "time_limit_s": 60,
  "spacing_mm": 2,
  "margin_mm": 5,
  "stock_file_id": "...",
  "parts_config": [
    { "file_id": "...", "quantity": 1, "allowed_rotations_deg": [0, 90, 180, 270] }
  ],
  "run_strategy_profile_version_id": "...",
  "solver_config_overrides_jsonb": {
    "quality_profile": "quality_aggressive",
    "engine_backend_hint": "nesting_engine_v2",
    "sa_eval_budget_sec": 2,
    "nesting_engine_runtime_policy": {
      "placer": "nfp",
      "search": "sa",
      "part_in_part": "auto",
      "compaction": "slide",
      "sa_iters": 768
    }
  }
}
```

`POST /projects/{project_id}/runs`:

```json
{
  "run_config_id": "cfg-1",
  "time_limit_s": 60,
  "run_strategy_profile_version_id": "...",
  "quality_profile": "quality_aggressive",
  "engine_backend_hint": "nesting_engine_v2",
  "sa_eval_budget_sec": 2,
  "nesting_engine_runtime_policy": {
    "placer": "nfp",
    "search": "sa",
    "part_in_part": "auto",
    "compaction": "slide",
    "sa_iters": 768
  }
}
```

`Project default` módban a run request legalább ezt tartalmazza:

```json
{
  "run_config_id": "cfg-1",
  "time_limit_s": 60
}
```

## Minőségkapu

Kötelező:

```bash
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md
```

Ha a lokális környezetben Playwright browser nincs telepítve, azt a reportban külön kell jelölni, de a mock/spec fájloknak build-szinten akkor is át kell menniük.

## DoD

A task akkor kész, ha:

1. Step2-ben van strategy UI blokk.
2. Project default hiánya nem tör el wizardot.
3. Profile/version listázás működik API kliensből.
4. `createRunConfig(...)` tud strategy mezőket küldeni.
5. `createRun(...)` ténylegesen küldi a `run_config_id`-t.
6. `createRun(...)` strategy request mezőket is tud küldeni.
7. Step3 summary mutatja a strategy döntést.
8. E2E mock rögzíti a `run-configs` és `runs` POST bodykat.
9. E2E assert bizonyítja a `run_config_id` + strategy payload átadását.
10. `npm --prefix frontend run build` PASS.
11. A dedikált Playwright spec PASS vagy környezeti browser-hiány esetén egyértelműen dokumentált.
12. `verify.sh` report frissül.

## Kockázatok és mitigáció

1. Kockázat: `engine_backend_hint: "auto"` beküldése backend 400 hibát okozna.
   - Mitigáció: `auto` UI opció csak mezőkihagyást jelent.

2. Kockázat: strategy endpoint 404 miatt a wizard használhatatlanná válna.
   - Mitigáció: project default 404 = `null`, nem fatal error.

3. Kockázat: túl sok Step2 mező egyszerre zavaró.
   - Mitigáció: `Project default` legyen alapértelmezett; advanced override csak `Custom overrides` módban látszódjon.

4. Kockázat: request/run_config duplikált strategy mezők félreérthetők.
   - Mitigáció: reportban rögzíteni kell, hogy T2 precedence szerint a run request mezők nyernek, a run_config pedig a létrehozott konfiguráció auditálható mentése.

5. Kockázat: meglévő Phase 4 stable E2E törése.
   - Mitigáció: a default flow `Project default` módban ne követeljen strategy profilt, így a régi E2E interakció minimális módosítás nélkül továbbmehet.
