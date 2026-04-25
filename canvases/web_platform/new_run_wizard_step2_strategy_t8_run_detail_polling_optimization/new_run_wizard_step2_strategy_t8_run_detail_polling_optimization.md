# New Run Wizard Step2 Strategy — T8 Run Detail polling optimization

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` T1–T7 lánc utáni frontend stabilizációs lépése.

T1–T7 után a stratégia-lánc működik:

1. Step2-ben strategy/profile/custom override választható.
2. `createRunConfig(...)` és `createRun(...)` továbbítja a strategy mezőket.
3. Backend resolver snapshotolja a végső strategy truth-ot.
4. Worker `auto` backend módban snapshotból választ backendet.
5. `engine_meta.json` és `viewer-data` visszaadja az auditmezőket.
6. Run Detail oldalon megjelenik a `Strategy and engine audit` kártya.
7. T7 óta a kártya a `strategy_field_sources` bontást is rendereli.

A T6/T7 rollout dokumentum még nyitva hagy egy valós polish/hatékonysági problémát: a `RunDetailPage` jelenleg 3 másodperces polling ciklusban újra és újra frissít, és a `viewer-data` auditadatot is feleslegesen ismételheti. A T8 célja, hogy a Run Detail oldal terminális állapotban ne terhelje tovább az API-t, és a `viewer-data` lekérés kontrollált, non-fatal, egyszeri terminális audit-fetch legyen.

## Kiinduló valós repo-állapot T7 után

A friss repo alapján:

- `frontend/src/pages/RunDetailPage.tsx`
  - `TERMINAL_STATUSES = new Set(["done", "failed", "cancelled"])` már létezik.
  - `refreshRunData(includeLogs: boolean)` minden frissítéskor meghívja:
    - `api.getRun(...)`
    - `api.listRunArtifacts(...)`
    - terminális státusztól függően `api.getRunLog(...)`
    - majd külön `try/catch` alatt `api.getViewerData(...)`.
  - A `viewer-data` hívás non-fatal, de jelenleg nincs terminális/egyszeri fetch guard.
  - A `useEffect` interval 3000 ms-onként fut, és a callback a renderkori `run` értékből számol `shouldPoll` értéket. Ez stale-closure jellegű ismételt refreshhez vezethet.
  - A T5/T7 audit kártya már megjeleníti a strategy/backend adatokat és a `strategy_field_sources` bontást.

- `frontend/e2e/support/mockApi.ts`
  - támogatja a `viewer-data` mock endpointot.
  - külön módosítás nélkül is mérhető Playwrightban, hogy hányszor ment ki `/viewer-data` GET request.

- `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`
  - Known Limitations alatt még nyitottként említi a Run Detail polling optimalizációt.

## Scope

### Benne van

1. `RunDetailPage.tsx` polling logika javítása:
   - terminális run állapotnál ne fusson tovább felesleges periodikus refresh;
   - `viewer-data` csak terminális állapotnál legyen lekérve;
   - adott `projectId/runId` párosra a terminális `viewer-data` fetch egyszer történjen meg;
   - hiányzó/404 viewer-data továbbra is non-fatal maradjon, és ne okozzon ismételt 404 spamet;
   - `runId` vagy `projectId` váltáskor az egyszeri-fetch guard resetelődjön.
2. Új T8 Playwright spec:
   - done run esetén a Run Detail auditadat megjelenik, de `/viewer-data` nem ismétlődik 3+ másodperc után;
   - running run esetén a Run Detail oldal tovább pollolhatja a run/log adatokat, de `/viewer-data` ne fusson addig, amíg nincs terminális állapot.
3. Új offline T8 smoke script source-szintű ellenőrzésekkel.
4. Rollout/compatibility doc frissítése: a Run Detail polling limitation T8-cal lezárva/covered státuszba kerül.
5. Checklist + report + verify.

### Nincs benne

1. Backend API contract módosítás.
2. DB migration.
3. Worker backend resolution módosítás.
4. Strategy resolver precedence módosítás.
5. New Run Wizard Step2 UI újratervezése.
6. Strategy profile CRUD/admin UI.
7. Production Supabase + real solver infra-smoke.

## Implementációs követelmények

## 1. Run Detail polling és viewer-data fetch guard

Módosítandó fájl:

`frontend/src/pages/RunDetailPage.tsx`

Kötelező viselkedés:

1. A Run Detail oldal kezdeti betöltéskor továbbra is lekéri a run állapotot és artifactokat.
2. Ha a run státusza `queued` vagy `running`, a periodikus refresh megmaradhat.
3. Ha a run státusza `done`, `failed` vagy `cancelled`:
   - a periodikus polling álljon le, vagy legalább ne indítson további hálózati frissítést;
   - a `viewer-data` egyszer, terminális állapotban legyen megpróbálva;
   - ha sikeres, `setViewerData(...)` frissüljön;
   - ha 404 vagy más hiba jön, a hiba non-fatal maradjon, és ne töltse meg a globális `error` bannert.
4. A `viewer-data` lekérés ne fusson minden `refreshRunData(...)` hívásban feltétel nélkül.
5. A guard resetelődjön `projectId` vagy `runId` váltáskor.
6. A T5/T6/T7 audit kártya tartalma nem romolhat:
   - `Strategy and engine audit` továbbra is látszik;
   - `Not available yet` fallback megmarad, amíg nincs `viewerData`;
   - `Strategy field sources` és `No field source evidence` fallback megmarad.

Javasolt implementációs irány:

- vezess be refeket, például:
  - `latestRunStatusRef`
  - `viewerDataFetchAttemptedRef`
  - opcionálisan `pollTimerRef`
- `refreshRunData(...)` adja vissza a frissített run státuszt, vagy külön helper döntse el a terminális állapotot;
- a `viewer-data` fetch logika legyen külön helperben, például `fetchViewerDataOnceForTerminal(...)`;
- a timer callback ne stale `run` closure-re támaszkodjon;
- terminális státusz után `window.clearInterval(...)` használható.

Nem kötelező pontosan ezeket a neveket használni, de a végeredmény legyen egyszerűen auditálható.

## 2. T8 Playwright spec

Új fájl:

`frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts`

Használd a meglévő `installMockApi` helper mintáit.

### Kötelező teszt 1 — done run viewer-data csak egyszer

1. Hozz létre done run-t mock state-ben.
2. Adj hozzá `engine_meta.json` artifactot.
3. Adj hozzá valid `initialViewerDataByRun` payloadot strategy/backend auditmezőkkel.
4. A tesztben számold a kimenő requesteket, amelyek URL-je tartalmazza:
   - `/projects/<projectId>/runs/<runId>/viewer-data`
5. Nyisd meg a Run Detail oldalt.
6. Assertáld, hogy a `Strategy and engine audit` kártya és egy jellemző auditérték megjelenik.
7. Várj legalább 3500–4200 ms-t, hogy a régi 3000 ms-os polling regresszió biztosan előjöjjön.
8. Assertáld, hogy a viewer-data request count nem nőtt 1 fölé.

### Kötelező teszt 2 — running run nem kér viewer-data-t

1. Hozz létre running run-t mock state-ben.
2. Ne adj hozzá `initialViewerDataByRun` payloadot.
3. Számold a `/viewer-data` requesteket.
4. Nyisd meg a Run Detail oldalt.
5. Assertáld, hogy a run oldal betölt és `RUNNING` státusz látszik.
6. Várj legalább 3200–4200 ms-t.
7. Assertáld, hogy viewer-data request count `0`.
8. Assertáld, hogy nincs globális fatal error banner viewer-data miatt.

Fontos:

- A teszt ne igényeljen valódi backend/Supabase/worker/solver környezetet.
- Ne módosítsd a mock API-t, ha request counting `page.on("request", ...)` alapján megoldható.
- A várakozási időt tartsd minimálisan elegendőn, hogy ne lassítsa túl a suite-ot.

## 3. Offline T8 smoke script

Új fájl:

`scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py`

Elvárások:

- Ne importáljon app modult.
- Ne igényeljen node_modules-t, Supabase-t, workert vagy solver binárist.
- Source-szinten ellenőrizze:
  - `RunDetailPage.tsx` már nem hívja feltétel nélkül a `api.getViewerData(...)` hívást minden refreshben;
  - van valamilyen explicit once/attempted guard a viewer-data fetch körül;
  - van terminális státuszra épülő viewer-data fetch feltétel;
  - a timer/polling logika nem stale `run` closure alapján dönt kizárólag;
  - a meglévő `Strategy and engine audit`, `Strategy field sources`, `No field source evidence` szövegek megmaradtak;
  - a T8 E2E spec létezik, és tartalmazza a done-once + running-no-viewer-data eseteket;
  - a rollout doc már nem nyitott limitationként kezeli a Run Detail polling problémát;
  - T8 artefaktok saját alkönyvtárban vannak, gyökérszintű duplikált canvas/yaml nélkül.
- Passed/failed összesítést írjon.
- Hiba esetén nem nulla exit code-dal álljon le.

## 4. Rollout dokumentum frissítése

Módosítandó fájl:

`docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md`

A Known Limitations szakaszban:

- a Run Detail polling optimalizáció ne maradjon nyitott limitation;
- dokumentáld röviden, hogy T8 után a terminal-state viewer-data audit fetch egyszeri és non-fatal;
- a valóban megmaradó limitationök maradhatnak:
  - production E2E real solver/Supabase ellen;
  - Strategy profile CRUD UI;
  - `choose_profile` edge case-ek, ha még valós kockázatok.

## 5. Checklist és report

Létrehozandó fájlok:

- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md`

A report legyen a `docs/codex/report_standard.md` szerinti, DoD → Evidence matrixszal.

PASS csak akkor szerepelhet, ha tényleges bizonyíték van. Ha a frontend dependency környezet vagy Playwright nem futtatható, a reportban pontosan jelöld `BLOCKED`-ként, ne állíts hamis PASS-t.

## Minőségkapu

Minimum célzott smoke:

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py
```

Frontend ellenőrzés, ha dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts
```

Kötelező repo gate:

```bash
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md
```

## Definition of Done

A task akkor kész, ha:

1. Terminális run állapot után nincs felesleges Run Detail periodikus API-refresh.
2. `viewer-data` csak terminális állapotban és adott runra egyszer kerül lekérésre.
3. Missing/404 viewer-data továbbra is non-fatal.
4. Running run állapotban nem történik viewer-data spam.
5. A T5/T6/T7 audit UI regressziómentesen működik.
6. T8 Playwright spec védi a done-once és running-no-viewer-data eseteket.
7. T8 offline smoke PASS.
8. Rollout doc frissült, a polling limitation lezárt/covered státuszban van.
9. Checklist + report + verify log evidence-alapon elkészült.
10. Nincs gyökérszintű duplikált T8 canvas/yaml artefakt.

## Kockázatok és mitigáció

1. **Kockázat:** A polling túl korán leáll, és a felület nem látja meg a terminal state-et.
   - **Mitigáció:** Csak a frissen lekért `runResponse.status` alapján állítsd le a pollingot, ne a régi state alapján.

2. **Kockázat:** A viewer-data 404 miatt többé nem próbálható újra, miközben artifact később jönne létre.
   - **Mitigáció:** Ez elfogadható T8 scope-ban, mert a backend viewer-data a completed run utáni audit response; ha productionban késleltetett artifact-készülés létezik, azt külön retry/backoff taskban kell kezelni. A T8 célja a jelenlegi 3s-es spam megszüntetése.

3. **Kockázat:** E2E teszt flaky a 3s timer miatt.
   - **Mitigáció:** A teszt csak 1 polling ciklusnál kicsit hosszabb ideig várjon, és request countot mérjen. Ne használjon túl szoros időzítést.

4. **Kockázat:** Existing T5/T6/T7 audit UI eltörik.
   - **Mitigáció:** A T8 Playwright mellett futtasd a T5/T6/T7 speceket is.
