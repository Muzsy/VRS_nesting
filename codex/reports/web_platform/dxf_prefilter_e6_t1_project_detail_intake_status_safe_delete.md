# Report - dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete

**Statusz:** PASS_WITH_NOTES

## 1) Meta
- **Task slug:** `dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete`
- **Kapcsolodo canvas:** `canvases/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.yaml`
- **Futas datuma:** 2026-04-25
- **Branch / commit:** `main@96c99ad`
- **Fokusz terulet:** Mixed (DB + API + Frontend + E2E + Smoke)

## 2) Scope
### 2.1 Cel
- `app.file_objects` soft archive/hide kepesseg bevezetese `deleted_at` mezovel.
- Project file list default aktivalis listara szukitese (`deleted_at is null`) es opcionis include deleted query.
- Project Detail oldal intake-aware statusz/next-step truthra allitasa.
- Rejected/review/pending source DXF-ek elkulonitese intake attention nezetbe.
- Hard delete copy kivaltasa domainhelyes hide/archive muveletre.

### 2.2 Nem-cel
- Storage object fizikai torlese.
- Preflight/geometry lineage hard delete.
- DXF Intake oldal redesign.
- New Run Wizard strategia vagy worker/solver modositas.

## 3) Valtozasok osszefoglalasa
### 3.1 Erintett fajlok
- **DB migration:**
  - `supabase/migrations/20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql`
- **Backend:**
  - `api/routes/files.py`
- **Frontend app:**
  - `frontend/src/lib/types.ts`
  - `frontend/src/lib/api.ts`
  - `frontend/src/lib/dxfIntakePresentation.ts`
  - `frontend/src/pages/ProjectDetailPage.tsx`
- **E2E/mock:**
  - `frontend/e2e/support/mockApi.ts`
  - `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts`
- **Smoke + Codex artefaktok:**
  - `scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py`
  - `codex/codex_checklist/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md`
  - `codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md`

### 3.2 Miert valtoztak?
- A backend hard delete FK-konfliktusos volt preflight/lineage mellett; ez lett cserelve idempotens soft archive-ra.
- A Project Detail legacy `validation_status` fallback miatt hamis pending keppel dolgozott; intake/projection truthra lett atkotve.
- A regressziot mock+E2E es offline smoke is vedi.

## 4) Verifikacio
### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md` -> PASS (AUTO_VERIFY blokk)

### 4.2 Opcionalis/feladatfuggo parancsok
- `python3 scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py` -> PASS
- `npm --prefix frontend run build` -> PASS
- `node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.config.ts frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts` -> PASS

### 4.3 Ha valami kimaradt
- Nem maradt ki kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix
| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
|---|---|---|---|---|
| 1. Project Detail nem mutat minden DXF-et hamis pending fallbackkel | PASS | `frontend/src/pages/ProjectDetailPage.tsx:90`, `frontend/src/pages/ProjectDetailPage.tsx:380`, `scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py:102` | Az oldal intake status oszlopot renderel, a legacy pending fallback tiltva van smoke-checkkel. | smoke + E2E |
| 2. Project Detail DXF Intake truth alapjan statusz/next-stepet mutat | PASS | `frontend/src/lib/dxfIntakePresentation.ts:294`, `frontend/src/pages/ProjectDetailPage.tsx:211`, `frontend/src/pages/ProjectDetailPage.tsx:394` | A status mapping a latest preflight/projection mezokbol tortenik. | E2E |
| 3. Rejected/review/pending source DXF nem project-ready sor | PASS | `frontend/src/lib/dxfIntakePresentation.ts:363`, `frontend/src/pages/ProjectDetailPage.tsx:405`, `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts:264` | Kulon `Intake attention` szekcio es explicit E2E assert biztositja az elkulonitest. | E2E |
| 4. DELETE endpoint soft archive, nem hard delete | PASS | `api/routes/files.py:845`, `api/routes/files.py:870`, `api/routes/files.py:965`, `supabase/migrations/20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql:5` | `deleted_at` mezot hasznalo active filter + `update_rows` archive van, hard delete nincs. | smoke |
| 5. Sikeres archive utan a file eltunik aktiv listabol | PASS | `api/routes/files.py:870`, `frontend/src/pages/ProjectDetailPage.tsx:190`, `frontend/e2e/support/mockApi.ts:418`, `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts:275` | API default aktiv listat ad vissza, UI ujratolt, E2E ellenorzi a sor eltuneset. | E2E |
| 6. Nincs `delete file metadata failed` regresszio normal archive eseten | PASS | `api/routes/files.py:996`, `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts:276` | A backend operation neve `archive file metadata`, E2E tiltja a regi hiba megjeleneset. | E2E |
| 7. E2E lefedi a status + hide/archive regressziot | PASS | `frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts:58` | A spec 6 accepted/linked + 2 rejected/review adattal fut es hide flow-t is ellenoriz. | Playwright targeted run |
| 8. Offline smoke PASS | PASS | `scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py:47` | A script migration/backend/frontend/mock/artefakt szerkezeti ellenorzeseket futtat. | python smoke |
| 9. `./scripts/verify.sh --report ...` PASS vagy blocker dokumentalva | PASS | AUTO_VERIFY blokk | A repo-gate wrapper lefutott, ellenorizte a standard quality gate-et. | verify.sh |
| 10. Nincs gyokerszintu duplikalt canvas/yaml | PASS | `scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py:128` | Smoke explicit ellenorzi, hogy csak web_platform pathon vannak task artefaktok. | smoke |

## 6) Advisory notes
- Playwright futas alatt a `NO_COLOR` warning megjelenik a worker processben; ez nem funkcionalis hiba.


<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-25T23:07:51+02:00 → 2026-04-25T23:10:46+02:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.verify.log`
- git: `main@96c99ad`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 api/routes/files.py                       |  34 +++--
 frontend/e2e/support/mockApi.ts           |  22 ++-
 frontend/src/lib/api.ts                   |   5 +
 frontend/src/lib/dxfIntakePresentation.ts | 136 +++++++++++++++++++
 frontend/src/lib/types.ts                 |   1 +
 frontend/src/pages/ProjectDetailPage.tsx  | 214 ++++++++++++++++++++++--------
 6 files changed, 340 insertions(+), 72 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M frontend/e2e/support/mockApi.ts
 M frontend/src/lib/api.ts
 M frontend/src/lib/dxfIntakePresentation.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/ProjectDetailPage.tsx
?? canvases/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.yaml
?? codex/prompts/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete/
?? codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.md
?? codex/reports/web_platform/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.verify.log
?? frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts
?? scripts/smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.py
?? supabase/migrations/20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql
```

<!-- AUTO_VERIFY_END -->
