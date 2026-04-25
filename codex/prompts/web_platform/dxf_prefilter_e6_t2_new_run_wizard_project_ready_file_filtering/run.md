# DXF Nesting Platform Codex Task — DXF Prefilter E6-T2 New Run Wizard project-ready file filtering

TASK_SLUG: dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`
- `codex/goals/canvases/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering/fill_canvas_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.yaml`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/dxfIntakePresentation.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező endpointot, DB mezőt, route-ot vagy frontend típust.
- Ez New Run Wizard Step 1 filtering task. Nem Step2 strategy task, nem backend run_config contract task, nem worker/solver task.
- A T1–T8 New Run Wizard strategy flow-t nem ronthatod el: `run_config_id`, strategy payload, Step2 és Step3 működés maradjon.
- Az E6-T1 Project Detail safe archive/intake-aware UI működését nem ronthatod el.
- Rejected, review-required, pending vagy preflight nélküli source DXF nem jelenhet meg választható stock/part inputként a New Run Wizard Step 1-ben.
- Partként csak linked/existing part revisionnel rendelkező project-ready file választható.
- Ne oldd meg úgy, hogy a UI továbbra is mutatja a rejected file-t, csak submitkor dob hibát. A hibás file már a választólistába se kerüljön.
- A reportban PASS csak ténylegesen lefutott gate esetén szerepelhet. Környezeti blocker esetén BLOCKED/FAIL legyen pontos okkal.
- Titok, token, lokális env érték nem kerülhet repo-ba.

## Implementációs cél

A Project Detail oldal E6-T1 után már helyesen bontja a file-okat project-ready és intake-attention szekciókra. A New Run Wizard Step 1 viszont továbbra is nyers DXF source listából dolgozik, ezért rejected file-ok is látszanak a stock dropdownban és part checkbox listában.

A javítás célja:

1. A wizard Step 1 csak run-indításra alkalmas project-ready inputokat mutasson.
2. Rejected/review/pending source DXF ne legyen stock vagy part választási opció.
3. Partként csak olyan accepted/linked file legyen választható, amelyhez van `existing_part_revision_id` / linked part revision.
4. A default stock candidate ne az első nyers DXF legyen.
5. Ha nincs project-ready part, a wizard irányítsa a felhasználót a DXF Intake / Project Preparation oldalra.
6. E2E és offline smoke védje a regressziót.

## Részletes követelmények

### 1. NewRunPage betöltés

Módosítsd:

`frontend/src/pages/NewRunPage.tsx`

Kötelező:

```ts
api.listProjectFiles(token, projectId, {
  include_preflight_summary: true,
  include_part_creation_projection: true,
})
```

A jelenlegi csak `include_part_creation_projection: true` hívás nem elég, mert a Step 1-nek intake-aware állapotot kell tudnia megjeleníteni és tesztelhetően elkülöníteni.

### 2. Project-ready helper

Módosítsd:

`frontend/src/pages/NewRunPage.tsx`

Kötelező jelentés:

- `isDxfSourceFile(file)` önmagában nem elég eligibility feltételnek;
- part listába csak olyan file kerülhet, amely:
  - DXF/source file;
  - `latest_part_creation_projection.readiness_reason === "accepted_existing_part"` vagy ezzel egyenértékű accepted/linked állapot;
  - rendelkezik linked part revisionnel: `existing_part_revision_id` vagy `resolveExistingPartRevisionId(file)` nem null;
- rejected/review/pending/preflight nélküli file ne kerüljön part listába;
- stock/eligible source listából is zárd ki a rejected/review/pending file-okat.

Ne hagyj ilyen kontrollforrást a Step 1 stock/part renderelésben:

```ts
files.filter((file) => isDxfSourceFile(file))
```

Ez a helper belső építőköveként maradhat, de a UI lista forrása ne ez legyen.

### 3. State és submit sync

Módosítsd:

`frontend/src/pages/NewRunPage.tsx`

Kötelező:

- `choiceMap` csak project-ready part file-okra épüljön;
- `selectedParts` csak project-ready part file-okat vegyen figyelembe;
- a `wizardRevisionIds` ciklus csak project-ready part file-okra fusson;
- a default `stockCandidate` ne legyen:

```ts
fileResponse.items.find((file) => isDxfSourceFile(file)) ?? fileResponse.items[0] ?? null
```

- ha nincs eligible stock, `stockFileId` legyen üres és a Continue maradjon disabled;
- normál filtered flowban ne lehessen `Selected file has no linked part revision` hibát előidézni rejected file kiválasztásával, mert rejected file nem választható.

### 4. Step 1 UX

Módosítsd:

`frontend/src/pages/NewRunPage.tsx`

Kötelező:

- ha nincs project-ready part, jelenjen meg:
  - `No project-ready parts yet. Open DXF Intake / Project Preparation and create parts first.`
- legyen link a DXF Intake oldalra:
  - `/projects/${projectId}/dxf-intake`
- ne legyen félrevezető `No DXF source files uploaded yet.` olyan esetben, amikor vannak DXF source uploadok, csak nem eligible állapotúak;
- rejected/review/pending file-okat nem kell részletesen listázni a wizardban, de opcionálisan megjelenhet összesített attention count.

### 5. E2E + mock

Módosítsd/létrehozd:

- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts`

Kötelező E2E:

- mock project: legalább 2 accepted/linked file + 1 rejected + 1 review/pending source DXF;
- New Run Wizard Step 1:
  - accepted/linked file látszik;
  - rejected file nem látszik a part listában;
  - rejected file nem szerepel a stock dropdown optionök között;
  - review/pending file nem választható;
  - Continue csak accepted/linked part kiválasztása után aktív;
  - nincs `Selected file has no linked part revision` hiba a filtered submit/start flowban.

### 6. Smoke + report

Hozd létre:

- `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`
- `codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`
- `codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.verify.log`

A smoke offline source-level legyen, ne igényeljen Supabase-t, node_modules-t vagy futó szervert.

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

## Zárási elvárás

A végén a reportban legyen egyértelmű:

- a New Run Wizard Step 1 már nem nyers DXF listából dolgozik;
- rejected/review/pending source upload nem látszik stock vagy part opcióként;
- accepted/linked project-ready file-ok továbbra is választhatók;
- partként csak linked revisionnel rendelkező file kerülhet a submit flowba;
- default stock candidate nem lehet rejected első file;
- empty state a DXF Intake oldalra irányít;
- E2E PASS vagy pontos blocker;
- offline smoke PASS;
- verify PASS vagy pontosan dokumentált blocker;
- nincs gyökérszintű duplikált E6-T2 canvas/yaml.
