# Report - dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering

**Statusz:** PASS_WITH_NOTES

## 1) Meta
- **Task slug:** `dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering`
- **Kapcsolodo canvas:** `canvases/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.yaml`
- **Futas datuma:** 2026-04-26
- **Branch / commit:** `main@4ebeabd`
- **Fokusz terulet:** Mixed (Frontend + E2E + Smoke)

## 2) Scope
### 2.1 Cel
- A New Run Wizard Step 1 csak run-inditasra alkalmas, project-ready forrasfajlokat listazzon.
- Rejected/review/pending source DXF ne legyen valaszthato stock vagy part input.
- Part valasztas csak linked/existing part revisionnel rendelkezo file-okra szukitson.
- Step 1 blocked/empty allapot egyertelmuen a DXF Intake oldalra iranyitson.
- E2E + offline smoke vedje a regressziot.

### 2.2 Nem-cel
- Backend run_config/run_create contract modositas.
- DXF Intake / Project Detail viselkedes attervezese.
- Worker/solver vagy strategy Step2–Step3 logika atirasa.

## 3) Valtozasok osszefoglalasa
### 3.1 Erintett fajlok
- **Frontend:**
  - `frontend/src/pages/NewRunPage.tsx`
- **E2E:**
  - `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts`
- **Smoke:**
  - `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py`
- **Codex artefaktok:**
  - `codex/codex_checklist/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`
  - `codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md`

### 3.2 Miert valtoztak?
- A wizard korabban nyers DXF listabol dolgozott, ami intake-attention file-okat is bekergetett stock/part valasztasba.
- Bevezetett helper-ekkel a Step 1 lista forrasa explicit project-ready/eligible listakra kerult.
- A regresszio ellen E2E specifikacio es offline source-level smoke lett hozzaadva.

## 4) Verifikacio
### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md` -> PASS (AUTO_VERIFY blokk)

### 4.2 Opcionalis/feladatfuggo parancsok
- `python3 scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py` -> PASS
- `npm --prefix frontend run build` -> PASS
- `node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.config.ts frontend/e2e/dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete.spec.ts frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts` -> PASS

### 4.3 Ha valami kimaradt
- Nem maradt ki kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix
| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
|---|---|---|---|---|
| 1. Step 1 nem mutat rejected/review/pending source DXF-et stock vagy part valasztokent | PASS | `frontend/src/pages/NewRunPage.tsx:61`, `frontend/src/pages/NewRunPage.tsx:104`, `frontend/src/pages/NewRunPage.tsx:491`, `frontend/src/pages/NewRunPage.tsx:514`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:199` | A helper-ek explicit kizarnak nem-eligible readiness/allapotokat, a Step 1 render pedig csak `eligibleStockFiles` + `projectReadyPartFiles` listat hasznal. Az E2E kozvetlenul ellenorzi, hogy rejected/review/pending nincs a dropdownban es part listaban. | Playwright E6-T2 |
| 2. Partkent csak linked/existing part revisionnel rendelkezo project-ready file valaszthato | PASS | `frontend/src/pages/NewRunPage.tsx:80`, `frontend/src/pages/NewRunPage.tsx:84`, `frontend/src/pages/NewRunPage.tsx:274` | A `hasLinkedPartRevision` kotelezo feltetel a part-eligibilityhez; a `selectedParts` mar csak a project-ready listabol epul. | smoke + Playwright E6-T2 |
| 3. Default stock candidate nem lehet elso nyers DXF, csak eligible source | PASS | `frontend/src/pages/NewRunPage.tsx:265` | A `stockFileId` sync csak akkor tartja meg az erteket, ha tovabbra is eligible; kulonben az elso eligible file-ra vagy uresre all. Nincs legacy `find(isDxfSourceFile) ?? items[0]` fallback. | smoke |
| 4. Nincs submit-time `Selected file has no linked part revision` normal filtered flowban | PASS | `frontend/src/pages/NewRunPage.tsx:367`, `frontend/src/pages/NewRunPage.tsx:380`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:224` | A wizard revision sync mar csak project-ready file korre fut, es az E2E explicit ellenorzi, hogy a hiba uzenet nem jelenik meg filtered submit flowban. | Playwright E6-T2 |
| 5. Nincs felrevezeto `No DXF source files uploaded yet` uzenet, ha vannak DXF-ek de nincs project-ready part | PASS | `frontend/src/pages/NewRunPage.tsx:501`, `frontend/src/pages/NewRunPage.tsx:503`, `frontend/src/pages/NewRunPage.tsx:504` | Step 1 blocked allapotban az uj copy jelenik meg es DXF Intake CTA linket ad. | smoke |
| 6. E2E regresszio vedi a rejected file kizarasat | PASS | `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:76`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:202`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:209` | A spec tobb allapotu mock adattal validalja a Step 1 szurest, Continue gatinget es submit flow stabilitast. | Playwright E6-T2 |
| 7. Offline smoke PASS | PASS | `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:44`, `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:47` | A smoke script source-level invariansokat ellenoriz, futtatasi eredmenye PASS. | `python3 scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py` |
| 8. `verify.sh` PASS vagy blocker dokumentalva | PASS | AUTO_VERIFY blokk | A kotelezo repo gate wrapper futtatva lett, es a log/report automatikusan frissult. | `./scripts/verify.sh --report ...` |
| 9. Nincs gyokerszintu duplikalt E6-T2 canvas/yaml | PASS | `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:20`, `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:92` | A smoke explicit ellenorzi a root-level duplikalt task artefaktok hianyat. | smoke |

## 6) Advisory notes
- Playwright futas alatt `NO_COLOR` warning jelenik meg (`FORCE_COLOR` miatt), de ez nem funkcionalis regresszio.


<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-26T00:41:37+02:00 → 2026-04-26T00:44:28+02:00 (171s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.verify.log`
- git: `main@4ebeabd`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 frontend/src/pages/NewRunPage.tsx | 241 ++++++++++++++++++++++++++------------
 1 file changed, 168 insertions(+), 73 deletions(-)
```

**git status --porcelain (preview)**

```text
 M frontend/src/pages/NewRunPage.tsx
?? canvases/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.yaml
?? codex/prompts/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering/
?? codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md
?? codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.verify.log
?? frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts
?? scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py
```

<!-- AUTO_VERIFY_END -->
