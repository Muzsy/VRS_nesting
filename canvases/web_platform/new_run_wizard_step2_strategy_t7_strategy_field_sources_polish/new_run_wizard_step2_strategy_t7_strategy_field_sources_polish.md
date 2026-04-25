# New Run Wizard Step2 Strategy — T7 Strategy field sources polish

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` lánc T6 utáni polish/observability lépése.

T1–T6 után a teljes stratégia-lánc működik és záró regresszióval védett:

1. Step2-ben strategy/profile/custom override választható.
2. `createRunConfig(...)` és `createRun(...)` payload továbbítja a strategy mezőket.
3. Backend resolver snapshotolja a végső strategy truth-ot.
4. Worker `auto` backend módban snapshotból választ backendet.
5. `engine_meta.json` és `viewer-data` visszaadja az auditmezőket.
6. Run Detail oldalon megjelenik a `Strategy and engine audit` kártya.

A T6 rollout dokumentum known limitationként jelöli, hogy a `strategy_field_sources` dict már backend/type/mock szinten elérhető, de a Run Detail audit kártya még nem rendereli. A T7 célja ennek a hiánynak a lezárása: a felhasználó és az auditor lássa, hogy az egyes strategy mezők melyik forrásból jöttek (`request`, `run_config`, `project_selection`, `global_default`, stb.).

## Kiinduló valós repo-állapot T6 után

A friss repo alapján:

- `api/routes/runs.py`
  - `ViewerDataResponse` már tartalmazza a `strategy_field_sources` mezőt.
  - `get_viewer_data(...)` már az `engine_meta_payload.strategy_field_sources` értékét normalizálja és visszaadja.

- `frontend/src/lib/types.ts`
  - `ViewerDataResponse` már tartalmazza: `strategy_field_sources?: Record<string, string> | null`.

- `frontend/e2e/support/mockApi.ts`
  - a mock `ViewerData` típus már tartalmazza: `strategy_field_sources?: Record<string, string> | null`.

- `frontend/src/pages/RunDetailPage.tsx`
  - a `Strategy and engine audit` kártya megjeleníti:
    - requested/effective backend;
    - backend resolution source;
    - snapshot backend hint;
    - strategy profile version id;
    - strategy resolution source;
    - strategy overrides applied;
    - `engine_meta.json` artifact presence.
  - viszont nem rendereli a `strategy_field_sources` dictet.

- `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts`
  - a Run Detail audit kártyát védi, de nem assertálja a field source sorokat.

- `frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts`
  - full-chain Step2 → Run Detail closure-t védi, de a field source dict UI-renderelése nincs ellenőrizve.

## Scope

### Benne van

1. `RunDetailPage.tsx` audit kártya bővítése `strategy_field_sources` megjelenítéssel.
2. Új T7 Playwright spec, amely ellenőrzi:
   - több field source megjelenik;
   - üres/null field source esetén stabil fallback látszik;
   - a meglévő audit kártya nem törik.
3. Új offline smoke script, amely source-szinten ellenőrzi a T7 UI/test/doc/report contractot.
4. A T6 rollout dokumentum frissítése: a `strategy_field_sources` UI known limitationt át kell mozgatni lezárt / covered státuszba, és csak a valóban megmaradó limitationök maradjanak.
5. Checklist + report + standard verify.

### Nincs benne

1. Backend API contract módosítás.
2. DB migration.
3. Strategy resolver precedence módosítás.
4. Worker backend resolution módosítás.
5. New Run Wizard Step2 UI újratervezése.
6. Strategy profile CRUD/admin UI.
7. Production infra-smoke valódi Supabase/solver ellen.

## Implementációs követelmények

## 1. Run Detail UI bővítés

Módosítandó fájl:

`frontend/src/pages/RunDetailPage.tsx`

A `Strategy and engine audit` kártyán belül jelenjen meg egy új szekció vagy mezőcsoport:

- címke: `Strategy field sources`
- ha `viewerData.strategy_field_sources` objektum és van legalább egy kulcsa:
  - renderelje determinisztikusan, kulcs szerint rendezve;
  - minden sor tartalmazza a field nevét és source értékét;
  - javasolt formátum: `quality_profile: run_config`, `engine_backend_hint: request`, stb.
- ha hiányzik, null vagy üres:
  - jelenjen meg stabil fallback: `-` vagy `No field source evidence`.

Fontos:

- A meglévő fallback viselkedés nem romolhat: ha `viewerData` nincs, továbbra is `Not available yet` jelenjen meg.
- A meglévő auditmezők ne tűnjenek el.
- Ne legyen runtime exception akkor sem, ha `strategy_field_sources` nem sima objektumként érkezik. A frontend típusa ugyan `Record<string, string>`, de a UI legyen védett a null/undefined állapotra.
- A renderelés legyen stabil Playwright asserthez: használj kiszámítható szöveget, ne csak ikon/táblázat nélküli vizuális jelzést.

## 2. Új T7 Playwright spec

Új fájl:

`frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts`

A spec a meglévő `installMockApi` mintára épüljön.

### Kötelező teszt 1 — field sources renderelés

1. Hozz létre mock projectet és done run-t.
2. Adj `initialArtifactsByRun` alatt `engine_meta.json` artifactot.
3. Adj `initialViewerDataByRun` payloadot ezekkel:
   - `requested_engine_backend: "auto"`
   - `effective_engine_backend: "nesting_engine_v2"`
   - `backend_resolution_source: "snapshot_solver_config"`
   - `snapshot_engine_backend_hint: "nesting_engine_v2"`
   - `strategy_profile_version_id: "version-t7-1"`
   - `strategy_resolution_source: "run_config"`
   - `strategy_overrides_applied: ["quality_profile", "engine_backend_hint"]`
   - `strategy_field_sources: { quality_profile: "run_config", engine_backend_hint: "request", nesting_engine_runtime_policy: "global_default" }`
4. Nyisd meg a Run Detail oldalt.
5. Assertáld:
   - `Strategy and engine audit` látszik;
   - `Strategy field sources` látszik;
   - `quality_profile` és `run_config` látszik;
   - `engine_backend_hint` és `request` látszik;
   - `nesting_engine_runtime_policy` és `global_default` látszik;
   - `version-t7-1` és `nesting_engine_v2` továbbra is látszik.

### Kötelező teszt 2 — fallback üres field sources esetén

1. Ugyanilyen Run Detail mock, de `strategy_field_sources: {}` vagy `null`.
2. Assertáld:
   - a Run Detail oldal betölt;
   - `Strategy and engine audit` látszik;
   - `Strategy field sources` látszik;
   - a fallback szöveg látszik (`-` vagy `No field source evidence`, a választott implementáció szerint).

## 3. Offline T7 smoke

Új fájl:

`scripts/smoke_new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.py`

Legyen offline-barát, ne importáljon app modult, ne igényeljen DB-t, Supabase-t, node_modules-t vagy workert.

Minimum ellenőrzések:

1. `frontend/src/pages/RunDetailPage.tsx`
   - tartalmazza a `strategy_field_sources` használatát;
   - tartalmazza a `Strategy field sources` UI szöveget;
   - tartalmaz fallbacket (`No field source evidence` vagy a választott stabil fallback);
   - továbbra is tartalmazza a `Strategy and engine audit` szöveget.
2. `frontend/src/lib/types.ts`
   - tartalmazza a `strategy_field_sources?: Record<string, string> | null` mezőt.
3. `frontend/e2e/support/mockApi.ts`
   - mock `ViewerData` tartalmazza a `strategy_field_sources` mezőt.
4. T7 E2E spec létezik, és tartalmazza:
   - `strategy_field_sources` payloadot;
   - `quality_profile`;
   - `engine_backend_hint`;
   - `global_default`;
   - fallback tesztet.
5. T6 rollout doc frissült:
   - ne maradjon olyan known limitation, ami azt állítja, hogy a `strategy_field_sources` UI-renderelés még hiányzik.
6. Artefakt-fegyelem:
   - T7 canvas/yaml/runner saját alkönyvtárban van;
   - nincs `new_run_wizard_step2_strategy_t7*` gyökérszintű duplikált canvas/yaml.

A script a végén írjon összesítést, például `PASS: <n> checks passed`, és hiba esetén nem nulla exit code-dal álljon le.

## 4. Rollout dokumentum frissítés

Módosítandó fájl:

`docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`

Elvárás:

- A `strategy_field_sources` UI-renderelés ne maradjon nyitott known limitationként.
- Röviden dokumentáld, hogy a Run Detail audit kártya most már megjeleníti a field-source breakdown-t.
- A megmaradó limitationök maradhatnak:
  - production E2E valódi solver/Supabase ellen;
  - strategy profile CRUD UI;
  - esetleges polling optimalizáció.

## 5. Checklist és report

Új fájlok:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.verify.log`

A report a `docs/codex/report_standard.md` szerint készüljön, DoD → Evidence matrixszal.

A reportban PASS csak akkor lehet, ha:

- T7 smoke lefutott és PASS;
- frontend build lefutott vagy pontosan BLOCKED-ként dokumentált;
- T7 Playwright spec lefutott vagy pontosan BLOCKED-ként dokumentált;
- `./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md` lefutott és PASS, vagy pontosan dokumentált blocker van.

## Tesztterv

Minimum célzott ellenőrzés:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.py
```

Frontend ellenőrzés, ha dependency környezet elérhető:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts
```

Standard repo gate:

```bash
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.md
```

## DoD

A task akkor kész, ha:

1. Run Detail `Strategy and engine audit` kártya megjeleníti a `Strategy field sources` breakdown-t.
2. Üres/null `strategy_field_sources` esetén stabil fallback jelenik meg, runtime hiba nélkül.
3. T7 Playwright spec lefedi a pozitív és fallback esetet.
4. T7 offline smoke létezik és PASS.
5. T6 rollout doc már nem állítja, hogy a `strategy_field_sources` UI renderelés hiányzik.
6. Checklist/report/verify log elkészült.
7. Nincs gyökérszintű duplikált T7 canvas/yaml artefakt.
8. Standard `verify.sh` PASS vagy pontosan dokumentált blocker.

## Kockázatok és mitigáció

1. **Kockázat:** a field source dict sorrendje instabil, E2E flaky lesz.
   - **Mitigáció:** kulcs szerinti rendezés renderelés előtt.
2. **Kockázat:** túl sok auditadat zsúfolja a kártyát.
   - **Mitigáció:** compact list/table, csak key/source párok.
3. **Kockázat:** null/undefined viewer data runtime hibát okoz.
   - **Mitigáció:** meglévő `!viewerData` fallback megtartása, field source fallback külön kezelése.
4. **Kockázat:** T6 closure regresszió törik.
   - **Mitigáció:** T5/T6/T7 E2E együtt futtatása.

## Rollback

Ha a UI polish problémát okoz:

1. revertáld a `frontend/src/pages/RunDetailPage.tsx` T7 módosítását;
2. hagyd érintetlenül a backend/viewer-data contractot;
3. a T7 spec/smoke/report maradhat FAIL/BLOCKED állapotban, amíg a polish javítása nem kész.
