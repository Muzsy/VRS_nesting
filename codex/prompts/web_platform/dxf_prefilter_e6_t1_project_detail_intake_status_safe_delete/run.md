# DXF Nesting Platform Codex Task — DXF Prefilter E6-T1 Project Detail intake-aware status + safe delete/archive

TASK_SLUG: dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md`
- `codex/goals/canvases/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete/fill_canvas_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.yaml`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/dxfIntakePresentation.ts`
- `frontend/e2e/support/mockApi.ts`
- `api/routes/files.py`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260421100000_dxf_e3_t1_preflight_persistence_and_artifact_storage.sql`
- `supabase/migrations/20260424100000_dxf_e3_t4_replace_file_and_rerun_preflight_flow.sql`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, DB mezőt vagy frontend típust.
- Ez DXF Project Detail cleanup task. Nem New Run Wizard strategy task, nem solver/worker módosítás, nem storage garbage collector.
- Ne hard delete-eld az `app.file_objects` sort olyan domainben, ahol preflight/geometry/run lineage FK-k hivatkozhatnak rá.
- A `DELETE /projects/{project_id}/files/{file_id}` ebben a taskban FK-safe soft archive/hide művelet legyen.
- A Project Detail UI ne használja többé fő státuszként a `file.validation_status ?? "pending"` fallbacket.
- Rejected/review/pending source DXF-et ne mutass projekt-ready fájlként.
- A DXF Intake oldal meglévő működését, accepted files → parts flow-ját és review/diagnostics overlayeit ne rontsd el.
- Titok, token, lokális env érték nem kerülhet repo-ba.
- A reportban PASS csak ténylegesen lefutott gate esetén szerepelhet. Környezeti blocker esetén BLOCKED/FAIL legyen pontos okkal.

## Implementációs cél

A felhasználói tesztben a Project Detail oldalon minden feltöltött DXF `pending` státusszal látszott, pedig a DXF Intake oldalon a preflight már lefutott és 6 fájl accepted/part-created lett. Emellett a rejected source DXF-ek is projektfájlként jelentek meg, és a Delete gomb `{"detail":"delete file metadata failed"}` hibára futott.

A javítás célja:

1. Project Detail oldal intake-aware státuszokat mutasson.
2. Project Detail ne mutasson rejected/review/pending source uploadot projekt-ready fájlként.
3. File delete/hide FK-safe soft archive legyen.
4. A sikeres hide/archive után a sor tűnjön el az aktív listából.
5. E2E és offline smoke védje a regressziót.

## Részletes követelmények

### 1. DB migration

Hozd létre:

`supabase/migrations/20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql`

Legyen benne:

- `app.file_objects.deleted_at timestamptz null`
- aktív listázást segítő partial index `where deleted_at is null`
- komment, hogy ez soft archive / active-list hiding, nem lineage hard delete.

### 2. Backend files route

Módosítsd:

`api/routes/files.py`

Kötelező:

- `ProjectFileResponse.deleted_at`
- `_as_file_response(...).deleted_at`
- `list_project_files(..., include_deleted: bool = Query(default=False), ...)`
- selectben `deleted_at`
- default paramsban `deleted_at: "is.null"`, kivéve `include_deleted=true`
- `delete_project_file(...)` update_rows soft archive, nem delete_rows hard delete
- storage object removal ne legyen része a tasknak
- archive hibaüzenet legyen domainnyelvű, ne `delete file metadata failed`

### 3. Frontend API/types

Módosítsd:

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`

Kötelező:

- `ProjectFile.deleted_at?: string | null`
- `normalizeProjectFile` töltse
- `listProjectFiles` támogassa `include_deleted?: boolean`
- legacy `validation_status` kompatibilitás maradhat, de Project Detail nem erre épülhet.

### 4. ProjectDetailPage

Módosítsd:

`frontend/src/pages/ProjectDetailPage.tsx`

Kötelező:

- `api.listProjectFiles(token, projectId, { include_preflight_summary: true, include_part_creation_projection: true })`
- `Validation`/`pending` fallback helyett intake-aware státusz/next step
- státuszforrás: `latest_preflight_summary` + `latest_part_creation_projection`
- accepted/linked row mutasson `already created` / `part linked` jellegű státuszt
- accepted ready row mutasson `ready for part creation` jellegű státuszt
- rejected row ne projekt-ready itemként jelenjen meg; legyen `rejected`/`fix in DXF Intake` attention státusz vagy külön attention szekció
- review-required row hasonlóan ne projekt-ready legyen
- hard `Delete` copy helyett `Hide upload` / `Archive upload` / `Manage in DXF Intake`
- linked part rowokon ne legyen félrevezető hard delete action

### 5. E2E + mock

Módosítsd/létrehozd:

- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts`

Kötelező E2E állítások:

- 6 accepted/linked + 2 rejected/review/pending mock file mellett a Project Detail nem mutat minden sort pendingként;
- accepted/linked sorokon projection truth látszik;
- rejected/review source nem projekt-ready itemként látszik;
- `Hide upload` / archive action után nincs `delete file metadata failed` hiba;
- archived/hidden sor eltűnik az aktív UI-ból.

### 6. Smoke + report

Hozd létre:

- `scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md`
- `codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md`
- `codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.verify.log`

A smoke legyen offline source-level ellenőrzés, és hiba esetén exit code != 0.

## Tesztparancsok

Minimum:

```bash
python3 scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py
```

Ha a frontend dependency környezet rendelkezésre áll:

```bash
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts
```

Végül kötelező:

```bash
./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md
```

## Zárási elvárás

A végén a reportban legyen egyértelmű:

- a Project Detail oldal már nem hamis `pending` fallbacket mutat;
- az oldal DXF Intake/preflight/projection truth alapján dolgozik;
- rejected/review/pending source upload nem projekt-ready sor;
- file DELETE soft archive/hide művelet lett, nem hard delete;
- a `delete file metadata failed` regresszió nem jelenik meg normál hide/archive műveletnél;
- E2E PASS vagy pontos blocker;
- offline smoke PASS;
- verify PASS vagy pontosan dokumentált blocker;
- nincs gyökérszintű duplikált E6-T1 canvas/yaml.
