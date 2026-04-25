# DXF Prefilter E6-T2 — New Run Wizard project-ready file filtering

## Funkció

Ez a task a DXF Intake / Project Preparation és a New Run Wizard Step 1 közötti konzisztenciahibát javítja.

A felhasználói tesztben a Project Detail oldal már helyesen külön bontotta a file-okat:

- `Project-ready files`: accepted / already-created / linked part source DXF-ek;
- `Intake attention`: rejected / review-required / pending source uploadok.

A New Run Wizard Step 1 viszont továbbra is a régi nyers DXF listát használta, ezért a stock dropdownban és a part checkbox listában megjelentek az elutasított DXF-ek is. Ez hibás, mert rejected/review/pending source DXF nem alkalmas run indítására, és kiválasztás után a submit flow később `Selected file has no linked part revision` jellegű hibára futhat.

A task célja: a New Run Wizard Step 1 kizárólag run-indításra alkalmas, DXF Intake által elfogadott és partként/linkelt project-ready file-okat engedjen kiválasztani. Rejected, review-required és pending upload ne jelenjen meg stock/part inputként.

## Kiinduló valós repo-állapot

A friss repo alapján:

- `frontend/src/pages/NewRunPage.tsx`
  - `loadFiles()` jelenleg ezt hívja:
    - `api.listProjectFiles(token, projectId, { include_part_creation_projection: true })`
  - vagyis nem kéri le a preflight summaryt;
  - `isDxfSourceFile(file)` csak azt nézi, hogy DXF/source/part/stock file-e;
  - a part choice map minden DXF source file-ra létrejön;
  - a stock default candidate:
    - `fileResponse.items.find((file) => isDxfSourceFile(file)) ?? fileResponse.items[0] ?? null`
  - a stock dropdown és a part checkbox lista is ezt használja:
    - `files.filter((file) => isDxfSourceFile(file))`
  - így a rejected source DXF-ek is bekerülnek a wizardba;
  - a submit flow később már elvárja, hogy a kiválasztott part source file-hoz legyen part revision:
    - `resolvePartRevisionIdForFile(...)`
    - `Selected file has no linked part revision: ...`

- `frontend/src/lib/types.ts`
  - `ProjectFile` már tartalmazza:
    - `latest_preflight_summary?: ProjectFileLatestPreflightSummary | null`
    - `latest_part_creation_projection?: ProjectFileLatestPartCreationProjection | null`
  - `ProjectFileLatestPartCreationProjection` tartalmazza:
    - `acceptance_outcome`
    - `part_creation_ready`
    - `readiness_reason`
    - `geometry_revision_id`
    - `geometry_revision_status`
    - `existing_part_revision_id`
    - `existing_part_code`

- `frontend/src/lib/api.ts`
  - `listProjectFiles(...)` már támogatja:
    - `include_preflight_summary`
    - `include_part_creation_projection`
    - `include_deleted`
  - backend/API contract módosítás ehhez a taskhoz nem szükséges.

- `frontend/e2e/support/mockApi.ts`
  - már tartalmaz projekt/file mock logikát és több DXF Intake / New Run Wizard teszt használja.

## Scope

### Benne van

1. New Run Wizard Step 1 file betöltésének intake-aware módosítása:
   - `include_preflight_summary: true`
   - `include_part_creation_projection: true`
2. Project-ready helper bevezetése a wizardban:
   - part listába csak olyan source DXF kerülhet, amelyhez már van linked/existing part revision;
   - rejected/review/pending/preflight nélküli source upload nem kerülhet választható partként a listába.
3. Stock candidate szűrés javítása:
   - alapértelmezett stock file nem lehet rejected/review/pending source DXF;
   - a dropdownból is ki kell zárni az intake attention file-okat;
   - ha nincs eligible stock/source candidate, ne válasszon automatikusan első nyers DXF-et.
4. Submit flow védelme:
   - `selectedParts`, `wizardRevisionIds`, part requirement sync ne járja be a rejected/pending raw DXF-eket;
   - user-facing hiba legyen világos, ha nincs elég project-ready input.
5. Step 1 üres/blocked állapot UX:
   - ha nincs project-ready part, jelenjen meg egyértelmű üzenet:
     - `No project-ready parts yet. Open DXF Intake / Project Preparation and create parts first.`
   - legyen link vagy CTA a DXF Intake oldalra.
6. Mock API + Playwright E2E regresszió:
   - rejected file ne jelenjen meg stock dropdownban;
   - rejected file ne jelenjen meg part checkbox listában;
   - accepted/linked file jelenjen meg;
   - nincs submit-time `Selected file has no linked part revision` a filtered flowban.
7. Offline source-level smoke script.
8. Checklist + report + verify.

### Nincs benne

1. Backend run_config vagy run_create contract módosítása.
2. DXF Intake / Project Preparation oldal újratervezése.
3. Project Detail E6-T1 logika módosítása, kivéve ha a mock/E2E közös helper miatt minimális kompatibilitási igazítás szükséges.
4. Sheet/stock domain teljes újratervezése.
5. Project part creation flow módosítása.
6. Valódi Supabase vagy storage migráció.

## Implementációs követelmények

## 1. New Run Wizard: intake-aware file betöltés

Módosítandó fájl:

`frontend/src/pages/NewRunPage.tsx`

Kötelező:

1. `loadFiles()` a file listát így kérje:

```ts
api.listProjectFiles(token, projectId, {
  include_preflight_summary: true,
  include_part_creation_projection: true,
})
```

2. A fileResponse feldolgozás után ne minden `isDxfSourceFile(file)` file-ra épüljön a wizard.

## 2. Project-ready helper logika

Módosítandó fájl:

`frontend/src/pages/NewRunPage.tsx`

Kötelező új vagy egyenértékű helper-ek:

```ts
function hasLinkedPartRevision(file: ProjectFile): boolean {
  return resolveExistingPartRevisionId(file) !== null;
}

function isProjectReadyPartFile(file: ProjectFile): boolean {
  const projection = file.latest_part_creation_projection;
  return (
    isDxfSourceFile(file) &&
    projection?.readiness_reason === "accepted_existing_part" &&
    hasLinkedPartRevision(file)
  );
}
```

Elfogadható, ha a helper neve eltér, de a jelentés nem:

- csak DXF source file lehet;
- rejected/review/pending source upload kizárt;
- partként csak linked/existing part revisionnel rendelkező file választható;
- `existing_part_revision_id` nélkül nem kerülhet part checkbox listába.

Stock/sheet candidate esetén külön helper használható, például:

```ts
function isRunUsableStockFile(file: ProjectFile): boolean {
  const projection = file.latest_part_creation_projection;
  return (
    isDxfSourceFile(file) &&
    projection?.acceptance_outcome === "accepted_for_import" &&
    projection?.readiness_reason !== "not_eligible_rejected" &&
    projection?.readiness_reason !== "not_eligible_review_required" &&
    projection?.readiness_reason !== "not_eligible_preflight_pending" &&
    Boolean(projection?.geometry_revision_id)
  );
}
```

Ha a meglévő domain miatt a stock file ideiglenesen ugyanabból a project-ready source listából jön, az elfogadható. Nem elfogadható, hogy a stock candidate az első nyers DXF legyen.

## 3. New Run Wizard Step 1 listák javítása

Módosítandó fájl:

`frontend/src/pages/NewRunPage.tsx`

Kötelező:

1. A part choice map csak project-ready part file-okra készüljön.
2. A `selectedParts` csak project-ready part file-okból épüljön.
3. A `wizardRevisionIds` sync csak project-ready part file-okra fusson.
4. A stock dropdown ne ezt használja:

```ts
files.filter((file) => isDxfSourceFile(file))
```

hanem eligible stock/project-ready source listát.

5. A part file lista ne ezt használja:

```ts
files.filter((file) => isDxfSourceFile(file))
```

hanem `projectReadyPartFiles` vagy azzal egyenértékű memoizált listát.

6. A default stock candidate ne ez legyen:

```ts
fileResponse.items.find((file) => isDxfSourceFile(file)) ?? fileResponse.items[0] ?? null
```

hanem csak eligible stock/project-ready source candidate.

7. Ha a korábban kiválasztott `stockFileId` a frissítés után már nem eligible, törölni kell vagy eligible defaulttal pótolni.

## 4. UX blocked/empty state

Módosítandó fájl:

`frontend/src/pages/NewRunPage.tsx`

Kötelező:

1. Ha nincs project-ready part file, ne csak `No DXF source files uploaded yet.` jelenjen meg, mert ez félrevezető.
2. Jelenjen meg külön üzenet:

```text
No project-ready parts yet. Open DXF Intake / Project Preparation and create parts first.
```

3. Az üzenetben legyen link/CTA:

```tsx
<Link to={`/projects/${projectId}/dxf-intake`}>Open DXF Intake / Project Preparation</Link>
```

4. Ha vannak hidden/intake-attention source uploadok, opcionálisan jelenjen meg rövid nem-választható tájékoztatás, például:

```text
8 source uploads are rejected, review-required, or pending and are not eligible for run creation.
```

5. A `Continue to parameters` gomb maradjon disabled, ha nincs stock candidate vagy nincs kiválasztott project-ready part.

## 5. Mock API és E2E regresszió

Módosítandó/létrehozandó fájlok:

- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts`

Kötelező E2E állítások:

1. Mock projekt tartalmazzon legalább:
   - 2 accepted/linked source DXF-et `accepted_existing_part` + `existing_part_revision_id` értékkel;
   - 1 rejected source DXF-et;
   - 1 review-required vagy pending source DXF-et.
2. New Run Wizard Step 1 megnyitásakor:
   - accepted/linked file látszik a part listában;
   - rejected file nem látszik a stock dropdownban;
   - rejected file nem látszik a part listában;
   - review/pending file nem látszik választható inputként;
   - `Continue to parameters` csak project-ready part kiválasztása után enged tovább.
3. A filtered flow ne fusson `Selected file has no linked part revision` hibára.

## 6. Offline E6-T2 smoke script

Létrehozandó fájl:

`scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py`

Kötelező ellenőrzések:

- `NewRunPage.tsx` kéri az `include_preflight_summary` és `include_part_creation_projection` opciókat;
- létezik project-ready/eligible helper;
- helper ellenőrzi az `existing_part_revision_id` vagy `resolveExistingPartRevisionId(...)` meglétét;
- a part choice map nem minden nyers `isDxfSourceFile` file-ra épül;
- a stock candidate nem `fileResponse.items.find((file) => isDxfSourceFile(file)) ?? fileResponse.items[0]` mintára épül;
- a part listában nem marad közvetlen `files.filter((file) => isDxfSourceFile(file))` kontrollforrás;
- van user-facing `No project-ready parts yet` empty state;
- az E2E spec létezik és tartalmaz rejected-file exclusion assertet;
- nincs gyökérszintű duplikált E6-T2 canvas/yaml artefakt.

A smoke legyen offline source-level ellenőrzés, ne igényeljen Supabase-t, node_modules-t vagy futó frontend/backend szervert. Hiba esetén exit code != 0.

## 7. Checklist és report

Létrehozandó fájlok:

- `codex/codex_checklist/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`
- `codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`

Kötelező:

- Report Standard v2 szerint készüljön.
- PASS csak tényleges bizonyíték alapján szerepelhet.
- Dokumentálja:
  - New Run Wizard már nem listáz rejected/review/pending file-okat;
  - stock dropdown nem választ automatikusan rejected source DXF-et;
  - part listában csak linked part revisionnel rendelkező project-ready file jelenik meg;
  - E2E eredményt;
  - smoke eredményt;
  - frontend buildet;
  - verify eredményt.

## Tesztparancsok

Minimum:

```bash
python3 scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py
```

Ha a frontend dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts \
  frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts
```

Végül kötelező:

```bash
./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md
```

## DoD

A task akkor kész, ha:

1. New Run Wizard Step 1 nem mutat rejected/review/pending source DXF-et stock vagy part választóként.
2. Partként csak linked/existing part revisionnel rendelkező project-ready file választható.
3. Default stock candidate nem lehet az első nyers DXF; csak eligible/accepted source lehet.
4. Nincs submit-time `Selected file has no linked part revision` a normál filtered flowban.
5. Nincs félrevezető `No DXF source files uploaded yet` üzenet, ha DXF-ek vannak, csak még nincs project-ready part.
6. E2E regresszió védi a rejected file kizárását.
7. Offline smoke PASS.
8. `verify.sh` PASS vagy pontosan dokumentált blocker.
9. Nincs gyökérszintű duplikált E6-T2 canvas/yaml artefakt.
