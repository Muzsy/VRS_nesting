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
- A Step 1 eligibility atkerult az aktualis preflight-igazsagra: csak `latest_preflight_summary.acceptance_outcome = accepted_for_import` allapotbol enged tovabb.
- A stale linkage regresszio (rejected file + meglevo `existing_part_revision_id`) kulon E2E esetre lett bovitve.
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
| 1. Step 1 nem mutat rejected/review/pending source DXF-et stock vagy part valasztokent | PASS | `frontend/src/pages/NewRunPage.tsx:75`, `frontend/src/pages/NewRunPage.tsx:87`, `frontend/src/pages/NewRunPage.tsx:95`, `frontend/src/pages/NewRunPage.tsx:115`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:226` | A helper-ek csak aktualis preflight accepted (`accepted_for_import`) allapotot engednek tovabb, majd erre epul a Step 1 lista (`eligibleStockFiles` + `projectReadyPartFiles`). Az E2E kozvetlenul ellenorzi, hogy rejected/review/pending nincs a dropdownban es part listaban. | Playwright E6-T2 |
| 2. Partkent csak linked/existing part revisionnel rendelkezo project-ready file valaszthato | PASS | `frontend/src/pages/NewRunPage.tsx:91`, `frontend/src/pages/NewRunPage.tsx:95`, `frontend/src/pages/NewRunPage.tsx:112`, `frontend/src/pages/NewRunPage.tsx:274` | A part-eligibilityhez egyszerre kotelezo az aktualis accepted preflight, a `projectDetailIntakeStatus` szerinti project-ready+linked allapot, es az `accepted_existing_part` readiness reason. | smoke + Playwright E6-T2 |
| 3. Default stock candidate nem lehet elso nyers DXF, csak eligible source | PASS | `frontend/src/pages/NewRunPage.tsx:265` | A `stockFileId` sync csak akkor tartja meg az erteket, ha tovabbra is eligible; kulonben az elso eligible file-ra vagy uresre all. Nincs legacy `find(isDxfSourceFile) ?? items[0]` fallback. | smoke |
| 4. Nincs submit-time `Selected file has no linked part revision` normal filtered flowban | PASS | `frontend/src/pages/NewRunPage.tsx:367`, `frontend/src/pages/NewRunPage.tsx:380`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:224` | A wizard revision sync mar csak project-ready file korre fut, es az E2E explicit ellenorzi, hogy a hiba uzenet nem jelenik meg filtered submit flowban. | Playwright E6-T2 |
| 5. Nincs felrevezeto `No DXF source files uploaded yet` uzenet, ha vannak DXF-ek de nincs project-ready part | PASS | `frontend/src/pages/NewRunPage.tsx:501`, `frontend/src/pages/NewRunPage.tsx:503`, `frontend/src/pages/NewRunPage.tsx:504` | Step 1 blocked allapotban az uj copy jelenik meg es DXF Intake CTA linket ad. | smoke |
| 6. E2E regresszio vedi a rejected file kizarasat | PASS | `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:156`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:227`, `frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts:235` | A spec kulon lefedi a stale linkage esetet (`Kor_D120-BodyPad.dxf`: rejected + meglevo linked revision), es igazolja, hogy ez sem stock, sem part listaba nem kerul be. | Playwright E6-T2 |
| 7. Offline smoke PASS | PASS | `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:47`, `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:53`, `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:84` | A smoke script explicit ellenorzi a preflight-truth helper tokeneket es a stale-linkage E2E lefedest. Futtatasi eredmenye PASS. | `python3 scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py` |
| 8. `verify.sh` PASS vagy blocker dokumentalva | PASS | AUTO_VERIFY blokk | A kotelezo repo gate wrapper futtatva lett, es a log/report automatikusan frissult. | `./scripts/verify.sh --report ...` |
| 9. Nincs gyokerszintu duplikalt E6-T2 canvas/yaml | PASS | `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:20`, `scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py:92` | A smoke explicit ellenorzi a root-level duplikalt task artefaktok hianyat. | smoke |

## 6) Advisory notes
- Playwright futas alatt `NO_COLOR` warning jelenik meg (`FORCE_COLOR` miatt), de ez nem funkcionalis regresszio.


<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-26T01:07:25+02:00 → 2026-04-26T01:10:18+02:00 (173s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.verify.log`
- git: `main@36c599b`
- módosított fájlok (git status): 6

**git diff --stat**

```text
 ..._new_run_wizard_project_ready_file_filtering.md |  1 +
 ..._new_run_wizard_project_ready_file_filtering.md | 35 ++++----
 ..._wizard_project_ready_file_filtering.verify.log | 92 +++++++++++-----------
 ...run_wizard_project_ready_file_filtering.spec.ts | 26 ++++++
 frontend/src/pages/NewRunPage.tsx                  | 48 ++++++-----
 ..._new_run_wizard_project_ready_file_filtering.py |  6 ++
 6 files changed, 126 insertions(+), 82 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/codex_checklist/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md
 M codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.md
 M codex/reports/web_platform/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.verify.log
 M frontend/e2e/dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.spec.ts
 M frontend/src/pages/NewRunPage.tsx
 M scripts/smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering.py
```

<!-- AUTO_VERIFY_END -->
