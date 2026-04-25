# DXF Prefilter E6-T1 — Project Detail intake-aware státusz + safe delete/archive

## Funkció

Ez a task a DXF Intake / Project Preparation flow után a régi Project Detail oldal konzisztenciahibáit javítja.

A tesztelés alatt előjött valós hibák:

1. A Project Detail `Files` táblában minden DXF `pending` státusszal látszik, miközben a DXF Intake oldalon a preflight már lefutott, 6 fájl accepted/part-created, 2 fájl rejected.
2. A DXF Intake által elutasított, projektbe alkatrészként nem hozzáadott source DXF-ek is ugyanabban a régi `Files` listában jelennek meg, mintha projektben használható fájlok lennének.
3. A `Delete` gomb a preflightot már kapott file objecteknél `{"detail":"delete file metadata failed"}` hibával elhasal, mert a backend hard delete-et próbál az `app.file_objects` soron, miközben `app.preflight_runs.source_file_object_id` és más lineage táblák FK-val hivatkozhatnak rá.

A task célja: a Project Detail oldal legyen DXF Intake-aware, ne használja többé félrevezetően a legacy `validation_status` fallbacket, és a törlés domainhelyesen soft archive / hide művelet legyen, ne FK-kat megsértő hard delete.

## Kiinduló valós repo-állapot

A friss repo alapján:

- `frontend/src/pages/ProjectDetailPage.tsx`
  - jelenleg `api.listProjectFiles(token, projectId)` hívást használ include flag-ek nélkül;
  - a táblában `Validation` oszlop van;
  - a státuszt `file.validation_status ?? "pending"` alapján mutatja;
  - minden soron `Delete` gomb van;
  - emiatt a DXF Intake truth (`latest_preflight_summary`, `latest_part_creation_projection`) nem látszik.

- `frontend/src/lib/api.ts`
  - `listProjectFiles(...)` már támogatja:
    - `include_preflight_summary`
    - `include_preflight_diagnostics`
    - `include_part_creation_projection`
  - `normalizeProjectFile(...)` még a legacy `validation_status` mezőt is támogatja, de a modern backend response `ProjectFileResponse` ezt nem adja vissza.

- `frontend/src/lib/dxfIntakePresentation.ts`
  - már tartalmaz újrafelhasználható presentation helper-eket:
    - `acceptanceOutcomeBadge(...)`
    - `issueCountBadge(...)`
    - `partCreationReadinessBadge(...)`
    - `recommendedNextStep(...)`
    - `INTAKE_COPY`
  - ezek a DXF Intake oldalon már helyes státuszt adnak.

- `api/routes/files.py`
  - `list_project_files(...)` már képes preflight summary és part creation projection mezőket visszaadni include flag alapján;
  - `delete_project_file(...)` jelenleg hard delete-et csinál:
    - `supabase.delete_rows(table="app.file_objects", ...)`
  - ez FK violation esetén általános `delete file metadata failed` hibára fut.

- DB schema:
  - `app.file_objects` jelenleg nem tartalmaz `deleted_at` / `archived_at` oszlopot;
  - `app.preflight_runs.source_file_object_id` `on delete restrict` FK-val hivatkozik `app.file_objects(id)`-re;
  - `app.geometry_revisions.source_file_object_id` és `app.run_configs.stock_file_id` szintén lineage/snapshot oldali kötést hozhat létre;
  - ezért preflight/geometry/run után a hard delete nem domainhelyes művelet.

## Scope

### Benne van

1. `app.file_objects` soft archive mező bevezetése:
   - `deleted_at timestamptz null`;
   - aktív listázást segítő index.
2. Backend file listázás módosítása:
   - alapértelmezetten csak `deleted_at is null` file objecteket adjon vissza;
   - opcionális `include_deleted` query paraméterrel lehessen archív sort is lekérni, ha később audit/debug célból kell;
   - `ProjectFileResponse` tartalmazza a `deleted_at` mezőt.
3. Backend delete módosítása:
   - ne hard delete-et csináljon;
   - idempotens soft archive legyen `deleted_at` kitöltéssel;
   - FK violation ne történjen;
   - storage object törlése ne legyen része ennek a tasknak, mert a source DXF audit/lineage és preflight reprodukálhatóság miatt veszélyes.
4. Frontend Project Detail javítása:
   - `listProjectFiles(...)` hívás include flag-ekkel:
     - `include_preflight_summary: true`
     - `include_part_creation_projection: true`
   - a régi `Validation` oszlop helyett intake-aware státusz jelenjen meg;
   - ne legyen `file.validation_status ?? "pending"` alapú félrevezető fallback;
   - rejected/review/pending source DXF-ek ne legyenek projektben használható file-ként bemutatva;
   - a Project Detail oldalon világosan különüljön el:
     - project-ready / already-created / accepted source,
     - intake attention / rejected / review-required / pending source upload.
5. Delete/Hide UX javítása:
   - a gomb szövege ne sugalljon hard delete-et, ahol valójában archive/hide történik;
   - sikeres archive után a sor tűnjön el az aktív listából;
   - hibánál user-facing üzenet legyen értelmes, ne raw Supabase/FK-szerű `delete file metadata failed`.
6. Mock API + Playwright E2E:
   - Project Detail oldal jelenítse meg a preflight/projection truthot;
   - rejected fájl ne jelenjen meg projekt-ready fájlként;
   - hide/archive művelet után nincs `delete file metadata failed`, és a sor eltűnik.
7. Offline structural smoke script.
8. Checklist + report + verify.

### Nincs benne

1. Valódi storage object cleanup / garbage collector.
2. Preflight runok, geometry revisionök, part revisionök vagy run configok törlése.
3. Project part CRUD vagy part requirement törlése.
4. DXF Intake oldal újratervezése.
5. New Run Wizard módosítása, kivéve amennyiben az aktív file listázás a backend default `deleted_at is null` filterén keresztül automatikusan tisztul.
6. Production Supabase adat-migráció futtatása a lokális repo módosításán túl.

## Implementációs követelmények

## 1. DB migration: file object soft archive

Új migration fájl:

`supabase/migrations/20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql`

Követelmények:

- Add hozzá:

```sql
alter table app.file_objects
  add column if not exists deleted_at timestamptz null;
```

- Hozz létre aktív listázáshoz indexet, például:

```sql
create index if not exists idx_file_objects_project_active_created_at
  on app.file_objects(project_id, created_at desc)
  where deleted_at is null;
```

- RLS policy módosítás alapvetően nem kell, mert meglévő owner update policy használható, de a migration kommentben rögzítse, hogy ez soft archive, nem hard delete.

## 2. Backend: list endpoint active filter + response mező

Módosítandó fájl:

`api/routes/files.py`

Kötelező:

1. `ProjectFileResponse` kapjon `deleted_at: str | None = None` mezőt.
2. `_as_file_response(...)` töltse a `deleted_at` mezőt.
3. `list_project_files(...)` kapjon opcionális query paramétert:
   - `include_deleted: bool = Query(default=False)`
4. A Supabase select tartalmazza `deleted_at`-ot.
5. Alapértelmezésben a params tartalmazza:
   - `"deleted_at": "is.null"`
6. Ha `include_deleted=true`, ne szűrje ki az archív sorokat.
7. A preflight/projection include működése ne törjön el.

## 3. Backend: DELETE = idempotens soft archive

Módosítandó fájl:

`api/routes/files.py`

Kötelező:

1. `delete_project_file(...)` ne hívjon `supabase.delete_rows(table="app.file_objects", ...)`-t.
2. A művelet `supabase.update_rows(...)` legyen:
   - `deleted_at` aktuális UTC timestamp;
   - filter: `id=eq.<file_id>`, `project_id=eq.<project_id>`.
3. Ha a sor már `deleted_at`-tal rendelkezik, a DELETE legyen idempotens 204.
4. A storage object eltávolítását ne végezze el ebben a taskban.
5. Ha a file nem található, 404 maradjon.
6. Supabase update hiba esetén user-facing detail legyen domainnyelvű, például:
   - `archive file metadata failed`
   ne `delete file metadata failed`.

## 4. Frontend API/types

Módosítandó fájlok:

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`

Kötelező:

1. `ProjectFile` kapjon `deleted_at?: string | null` mezőt.
2. `normalizeProjectFile(...)` töltse ezt:
   - `deleted_at: raw.deleted_at ?? null`.
3. `listProjectFiles(...)` options bővülhet:
   - `include_deleted?: boolean`
4. Ha `include_deleted === true`, query paraméterként menjen:
   - `include_deleted=true`.
5. `deleteProjectFile(...)` maradhat `DELETE`, de a frontend copyban ne nevezzük hard delete-nek.

## 5. Frontend Project Detail UX

Módosítandó fájl:

`frontend/src/pages/ProjectDetailPage.tsx`

Kötelező:

1. `loadPageData()` a file listát így kérje:

```ts
api.listProjectFiles(token, projectId, {
  include_preflight_summary: true,
  include_part_creation_projection: true,
})
```

2. A table ne használja többé fő státuszforrásként:

```ts
file.validation_status ?? "pending"
```

3. A `Validation` oszlopot cseréld intake-aware státuszra.

Javasolt státuszforrások:

- `file.latest_preflight_summary?.acceptance_outcome`
- `file.latest_preflight_summary?.run_status`
- `file.latest_part_creation_projection?.readiness_reason`
- `file.latest_part_creation_projection?.existing_part_code`

4. Használd újra vagy egészítsd ki a `frontend/src/lib/dxfIntakePresentation.ts` helper-eit.

Elvárt user-facing jelentés:

- `accepted_existing_part` → `already created` / `part linked`
- `accepted_ready` → `ready for part creation`
- `accepted_geometry_import_pending` → `geometry import pending`
- `preflight_rejected` → `rejected — fix in DXF Intake`
- `preflight_review_required` → `review required — open DXF Intake`
- nincs preflight summary → `preflight pending`

5. Rejected/review/pending source DXF-ek ne legyenek projektben használható fájlként bemutatva.

Elfogadható megoldások:

- külön `Project-ready files` és `Intake attention` szekció;
- vagy egyetlen táblában világosan elkülönített státusz + next step, ahol a rejected/review rows nem számítanak project-ready itemnek.

Nem elfogadható:

- minden sort `Files` alatt `pending`-ként hagyni;
- rejected source DXF-et ugyanúgy projekt-ready fájlként mutatni, mint egy linked partot;
- raw JSON hibát megjeleníteni delete/archive hiba esetén.

6. Az action copy legyen domainhelyes:

- rejected/review/pending source upload: `Hide upload` vagy `Archive upload`;
- linked/accepted part soroknál ne legyen félrevezető hard `Delete`; ha nincs biztonságos művelet, disabled `Linked to part` vagy `Manage in DXF Intake` legyen.

7. A `DXF intake / preparation` CTA maradjon látható, ha `DXF_PREFLIGHT_ENABLED` true.

## 6. Mock API + E2E

Módosítandó / új fájlok:

- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts`

Kötelező:

1. Mock API kezelje:
   - `DELETE /projects/:projectId/files/:fileId`
   - törlésnél soft archive-szerűen vegye ki az aktív `filesByProject` listából;
   - ne adjon `delete file metadata failed` hibát.
2. Mock file típus maradhat kompatibilis, de támogassa a `deleted_at` mezőt, ha szükséges.
3. E2E scenario:
   - project detail oldal 6 accepted/linked és 2 rejected/review/pending source file-lal;
   - assert: nincs félrevezető minden-sor `pending` fallback;
   - assert: accepted/linked sorokon `already created` vagy ezzel ekvivalens státusz látszik;
   - assert: rejected source nem projekt-ready itemként látszik, vagy egyértelműen `rejected` / `fix in DXF Intake` attention státusszal;
   - `Hide upload` / archive action után a rejected sor eltűnik, és nem jelenik meg `delete file metadata failed`.

## 7. Offline smoke

Új fájl:

`scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py`

Kötelező source-level ellenőrzések:

1. Migration létezik és tartalmazza:
   - `deleted_at timestamptz`
   - aktív `deleted_at is null` indexet vagy partial indexet.
2. `api/routes/files.py`:
   - `ProjectFileResponse` tartalmaz `deleted_at` mezőt;
   - `list_project_files` támogatja `include_deleted` query paramétert;
   - default list params szűr `deleted_at is null` szerint;
   - `delete_project_file` `update_rows`-t használ soft archive-hoz;
   - a delete handlerben nincs `delete_rows(table="app.file_objects"` hard delete.
3. `frontend/src/pages/ProjectDetailPage.tsx`:
   - include flag-ekkel kéri a listát;
   - nem használja többé fő státuszként a `file.validation_status ?? "pending"` fallbacket;
   - megjelenít intake-aware státusz/next-step copyt;
   - delete/hide copy nem hard delete-et sugall.
4. `frontend/e2e/support/mockApi.ts` kezeli a file DELETE route-ot.
5. T6/T7/T8 stratégia oldali fájlokhoz ne nyúljon ez a task.
6. A task canvas/yaml/runner saját alkönyvtárban legyen, gyökérszintű duplikált canvas/yaml nélkül.

## DoD

A task akkor kész, ha:

1. A Project Detail oldal nem mutat minden DXF-et hamis `pending` státusszal.
2. A Project Detail oldal a DXF Intake truth alapján jelenít meg státuszt és next stepet.
3. A rejected/review/pending source DXF-ek nem projekt-ready fájlként jelennek meg.
4. A `DELETE /projects/{project_id}/files/{file_id}` nem hard delete-et végez preflight/geometry lineage mellett, hanem idempotens soft archive-ot.
5. A sikeres archive után az adott file nem jelenik meg az aktív listában.
6. A user nem kap `{"detail":"delete file metadata failed"}` hibát normál archive műveletnél.
7. E2E teszt lefedi a Project Detail státusz és hide/archive regressziót.
8. Offline smoke PASS.
9. `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md` PASS vagy pontosan dokumentált blocker.
10. Nincs gyökérszintű duplikált canvas/yaml artefakt.

## Kockázatok és mitigáció

1. **Kockázat:** soft archive elrejti az aktív listából a source DXF-et, miközben audit/lineage még hivatkozik rá.
   - **Mitigáció:** ez a cél; audit/lineage megmarad, csak aktív UI listából tűnik el.

2. **Kockázat:** linked part source upload elrejtése összezavarja a New Run Wizardot.
   - **Mitigáció:** Project Detail UI ne kínáljon félrevezető delete/hide actiont linked part sorokon; backend soft archive ettől még FK-safe marad.

3. **Kockázat:** régi phase1 validation smoke-ok még `validation_status` mezőt várnak.
   - **Mitigáció:** ne töröld ki a type/api kompatibilitási normalizálást, csak a Project Detail fő státuszforrását cseréld le.

4. **Kockázat:** storage cleanup hiánya hosszabb távon tárhelyet használ.
   - **Mitigáció:** storage cleanup külön későbbi maintenance/retention task, nem része ennek a javításnak.

## Tesztparancsok

Minimum:

```bash
python3 scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py
```

Frontend dependency környezet esetén:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts
```

Kötelező repo gate:

```bash
./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md
```
