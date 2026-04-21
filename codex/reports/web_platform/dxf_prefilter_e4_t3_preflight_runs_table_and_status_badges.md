PASS

## 1) Meta
- Task slug: `dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges`
- Kapcsolódó canvas: `canvases/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`
- Kapcsolódó goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.yaml`
- Futás dátuma: `2026-04-21`
- Branch / commit: `main@2b9a55a`
- Fókusz terület: `Mixed (Backend projection + Frontend intake table)`

## 2) Scope

### 2.1 Cél
- A `/projects/{project_id}/files?include_preflight_summary=true` endpoint latest summary projectionjának T3 bővítése.
- `summary_jsonb` alapú issue/repair countok backend oldali lapos kivetítése.
- Stabil `recommended_action` mező bevezetése backend-projected mappinggel.
- `DxfIntakePage` jobb oldali kártya átalakítása T3 latest preflight runs table nézetre.
- Külön run status / acceptance / issue / repair badge helper-ek bevezetése.
- Route-level teszt és deterministic smoke frissítése.

### 2.2 Nem-cél (explicit)
- Új historical `GET /projects/{project_id}/preflight-runs` endpoint.
- Diagnostics drawer/modal, review modal, replace/rerun flow, accepted->parts flow.
- `NewRunPage.tsx` bővítése.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok
- Backend:
  - `api/routes/files.py`
- Frontend:
  - `frontend/src/lib/types.ts`
  - `frontend/src/lib/api.ts`
  - `frontend/src/pages/DxfIntakePage.tsx`
- Teszt / smoke:
  - `tests/test_project_files_preflight_summary.py`
  - `scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`
- Codex artefaktok:
  - `codex/codex_checklist/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`
  - `codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`

### 3.2 Miért ezek?
- A jelenlegi repo-truth szerint már létezik file-list route és file-onként latest preflight summary projection; T3 minimális lépése ennek bővítése.
- A `summary_jsonb` T7 szerkezetben már elérhetőek az issue/repair számlálók, ezért nem kellett új backend domaint nyitni.
- Az intake UI oldalon jelenlegi single-badge státusz túl kevés; a T3 cél külön badge + recommended action nézet.

## 4) Verifikáció

### 4.1 Kötelező parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`

### 4.2 run.md szerinti célzott futtatások
- `python3 -m py_compile api/routes/files.py tests/test_project_files_preflight_summary.py scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py` → OK
- `python3 -m pytest -q tests/test_project_files_preflight_summary.py` → `5 passed`
- `python3 scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py` → all scenarios passed
- `npm --prefix frontend run build` → success (`tsc -b && vite build`)

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| --- | --- | --- | --- | --- |
| A file-list latest summary projection T3 mezőkkel bővült. | PASS | `api/routes/files.py:105`; `api/routes/files.py:196` | A route `summary_jsonb`-t is lekéri és lapos issue/repair count + recommended_action mezőket ad vissza. | `pytest` + smoke |
| A projection null-safe marad hiányos/üres `summary_jsonb` esetén. | PASS | `api/routes/files.py:107`; `api/routes/files.py:121`; `tests/test_project_files_preflight_summary.py:252` | A parse kizárólag dict típusnál olvas, egyébként 0 alapértékre esik vissza. | `python3 -m pytest -q tests/test_project_files_preflight_summary.py` |
| A latest-run kiválasztás nem tört el. | PASS | `api/routes/files.py:198`; `api/routes/files.py:206`; `tests/test_project_files_preflight_summary.py:125` | A file-onként első (run_seq desc) rekord marad a kiválasztott latest run. | `pytest` |
| Frontend type/API boundary követi az új summary shape-et. | PASS | `frontend/src/lib/types.ts:39`; `frontend/src/lib/api.ts:63` | A típus és a normalizer tartalmazza az összes T3 mezőt optional-safe normalizációval. | `npm --prefix frontend run build`; smoke |
| Intake oldalon T3-kompatibilis latest runs table készült külön badge helper-ekkel. | PASS | `frontend/src/pages/DxfIntakePage.tsx:114`; `frontend/src/pages/DxfIntakePage.tsx:157`; `frontend/src/pages/DxfIntakePage.tsx:177`; `frontend/src/pages/DxfIntakePage.tsx:195`; `frontend/src/pages/DxfIntakePage.tsx:206`; `frontend/src/pages/DxfIntakePage.tsx:585` | Külön helper-ek lettek a run/acceptance/issues/repairs/recommended action megjelenítésre, és az oszlopok megfelelnek a T3 minimumnak. | `npm --prefix frontend run build`; smoke |
| Task-specifikus teszt + smoke bizonyíték elkészült. | PASS | `tests/test_project_files_preflight_summary.py:97`; `tests/test_project_files_preflight_summary.py:125`; `tests/test_project_files_preflight_summary.py:295`; `scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py:76` | Route-level szerződés és UI/API tokenek determinisztikusan lefedve. | `pytest`; smoke |

## 6) Külön kiemelések (run.md követelmények)

- Miért file-onként latest run projection a helyes T3 minimális modell:
  - A jelenlegi repo-ban a preflight összegzés a file-list route optional `latest_preflight_summary` ágán érhető el, historical runs endpoint nélkül, ezért a T3 bővítés itt történt.
- Pontos új backend summary mezők:
  - `blocking_issue_count`
  - `review_required_issue_count`
  - `warning_issue_count`
  - `total_issue_count`
  - `applied_gap_repair_count`
  - `applied_duplicate_dedupe_count`
  - `total_repair_count`
  - `recommended_action`
- `recommended_action` mapping:
  - `accepted_for_import` -> `ready_for_next_step`
  - `preflight_review_required` -> `review_required_wait_for_diagnostics`
  - `preflight_rejected` vagy `preflight_failed` -> `rejected_fix_and_reupload`
  - futó/queued státuszok -> `preflight_in_progress`
  - nincs értelmezhető státusz -> `preflight_not_started`
- Mi marad későbbi scope:
  - historical preflight runs endpoint,
  - diagnostics drawer/review modal,
  - replace/rerun és accepted->parts flow.

## 7) Advisory notes
- A `total_issue_count` a `blocking + review_required + warning + info` összegzésből áll.
- A `total_repair_count` jelenleg a `gap + duplicate dedupe` összeg (writer skipped külön mezőként nem került be T3-ba).
- `include_preflight_summary=false` ág változatlan, továbbra sem queryzi a `preflight_runs` táblát.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-21T23:22:03+02:00 → 2026-04-21T23:24:44+02:00 (161s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.verify.log`
- git: `main@2b9a55a`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 api/routes/files.py                           |  74 +++++++++++-
 frontend/src/lib/api.ts                       |  18 +++
 frontend/src/lib/types.ts                     |   8 ++
 frontend/src/pages/DxfIntakePage.tsx          | 162 +++++++++++++++++++++-----
 frontend/tsconfig.tsbuildinfo                 |   2 +-
 tests/test_project_files_preflight_summary.py | 111 ++++++++++++++++++
 6 files changed, 343 insertions(+), 32 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M frontend/src/lib/api.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/DxfIntakePage.tsx
 M frontend/tsconfig.tsbuildinfo
 M tests/test_project_files_preflight_summary.py
?? canvases/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.yaml
?? codex/prompts/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges/
?? codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md
?? codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.verify.log
?? scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py
```

<!-- AUTO_VERIFY_END -->
