# Report: New Run Wizard Step2 Strategy T5 — Run Detail Strategy Observability

**PASS**

---

## 1) Meta

- **Task slug:** `new_run_wizard_step2_strategy_t5_run_detail_strategy_observability`
- **Kapcsolódó canvas:** `canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/fill_canvas_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.yaml`
- **Futás dátuma:** 2026-04-25
- **Branch / commit:** main / ee67395
- **Fókusz terület:** Backend (Python/FastAPI) + Frontend (React/TypeScript/Playwright)

---

## 2) Scope

### 2.1 Cél

1. Backend `viewer-data` response kiteszi a T3 `engine_meta.json` strategy/backend audit mezőit (8 új optional mező).
2. Frontend `ViewerDataResponse` típus szinkronizálva a backend válasszal (14 mező összesen).
3. `RunDetailPage` non-fatal módon lekéri a viewer-data-t és megjeleníti a "Strategy and engine audit" kártyát fallbackkel.
4. Mock API `ViewerData` interface bővítve; új Playwright E2E spec (2 teszt).
5. Offline smoke script (60 check), frontend build, Playwright + verify gate.

### 2.2 Nem-cél

1. DB migration.
2. Worker backend resolution logika módosítása.
3. Strategy resolver precedence módosítása.
4. Strategy profile CRUD UI.
5. New Run Wizard Step2 újratervezése / viewer rajzolás.

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Backend:** `api/routes/runs.py` — `ViewerDataResponse` modell + `get_viewer_data()` return bővítés
- **Frontend types:** `frontend/src/lib/types.ts` — `ViewerDataResponse` interface bővítés
- **Frontend page:** `frontend/src/pages/RunDetailPage.tsx` — `ViewerDataResponse` import, viewer-data state, non-fatal fetch, audit kártya
- **E2E mock:** `frontend/e2e/support/mockApi.ts` — `ViewerData` interface bővítés
- **E2E spec:** `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts` — új fájl (2 teszt)
- **Smoke:** `scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py` — új fájl (60 check)

### 3.2 Miért változtak?

A T3 worker már létrehozza az `engine_meta.json` artifact-ban a strategy/backend audit mezőket, de a `viewer-data` API response eddig nem tette ki ezeket. A T5 task zárja ezt a rést: a backend response kiteszi az adatokat, a frontend típusok szinkronban vannak, a RunDetailPage megjeleníti őket.

---

## 4) Verifikáció

### 4.1 Python smoke

```
python3 scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py
→ PASS: 60 checks passed (60 total)
```

### 4.2 Frontend build

```
npm --prefix frontend run build
→ PASS (TypeScript + Vite build, 0 hiba, 84 modul, 453 kB)
```

### 4.3 Playwright E2E

```
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts
→ 2 passed (6.7s)

node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/phase4.stable.spec.ts
→ 2 passed (7.4s) — regresszió nem tört el
```

### 4.4 Automatikus verify blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-25T20:14:26+02:00 → 2026-04-25T20:17:13+02:00 (167s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.verify.log`
- git: `main@ee67395`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/routes/runs.py                   | 33 ++++++++++++++++++++
 frontend/e2e/support/mockApi.ts      | 14 +++++++++
 frontend/src/lib/types.ts            | 14 +++++++++
 frontend/src/pages/RunDetailPage.tsx | 60 +++++++++++++++++++++++++++++++++++-
 4 files changed, 120 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/runs.py
 M frontend/e2e/support/mockApi.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/RunDetailPage.tsx
?? canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/
?? codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/
?? codex/prompts/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability/
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.verify.log
?? frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts
?? scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py
```

<!-- AUTO_VERIFY_END -->

---

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path) | Magyarázat | Kapcsolódó teszt |
|----------|---------|-------------------|------------|------------------|
| #1 Backend viewer-data response kiteszi T3 audit mezőket | PASS | `api/routes/runs.py:153-173` (model), `:1478-1519` (return) | 8 új optional mező a `ViewerDataResponse`-ban, `engine_meta_payload`-ból töltve | smoke check #1-2; T5 Playwright teszt #1 |
| #2 Régi runoknál / hiányzó engine_meta nincs 500 | PASS | `api/routes/runs.py:1478-1519` — minden mező `or None` fallbackkel; `engine_meta_payload = {}` esetén üres dict-ből olvas | Minden új mező optional, type-checked normalizálással | smoke check #2 |
| #3 Frontend ViewerDataResponse típus szinkronban | PASS | `frontend/src/lib/types.ts:322-345` | 14 mező (6 régi + 8 új) optional mezőként | smoke check #3 |
| #4 RunDetailPage non-fatal viewer-data lekérés | PASS | `frontend/src/pages/RunDetailPage.tsx:54-72` (refreshRunData, belső try/catch) | Külön try/catch a viewer-data hívás köré; hiba nem írja felül a főoldalhibát | T5 Playwright regressziós teszt |
| #5 RunDetailPage Strategy and engine audit kártya | PASS | `frontend/src/pages/RunDetailPage.tsx:309-356` | "Strategy and engine audit" heading; 8 mező (requested/effective backend, resolution source, snapshot hint, profile version id, strategy source, overrides, engine_meta artifact státusz) | T5 Playwright teszt #1 |
| #6 Fallback hiányzó viewer-data esetén | PASS | `frontend/src/pages/RunDetailPage.tsx:312` — "Not available yet" szöveg | `viewerData === null` esetén fallback szöveg jelenik meg | T5 Playwright regressziós teszt |
| #7 Mock API viewer-data új mezők | PASS | `frontend/e2e/support/mockApi.ts:114-137` | `ViewerData` interface tartalmazza mind a 8 új optional audit mezőt | smoke check #6 |
| #8 Playwright E2E PASS | PASS | `frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts` — 2/2 passed | Fő teszt: audit mezők megjelennek; regressziós teszt: fallback megjelenik, fő oldal nem omlik össze | 2/2 Playwright PASS |
| #9 Dedikált T5 smoke PASS | PASS | `scripts/smoke_new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.py` → 60/60 PASS | 7 kategória, 60 ellenőrzés (model, return, ts típus, RunDetail fetch, audit UI, mock API, spec) | python3 smoke script |
| #10 verify.sh PASS | PASS | `codex/reports/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.verify.log` | AUTO_VERIFY blokk alább | `./scripts/verify.sh` |
| #11 Checklist és report evidence matrix | PASS | `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.md`, ez a fájl | Mindkét artifact létezik | — |
| #12 Nincs gyökérszintű duplikált artefakt | PASS | Minden T5 artefakt saját alkönyvtárban van (`canvases/web_platform/new_run_wizard_step2_strategy_t5_.../`) | Repo-struktúra T1–T4 mintát követ | — |

---

## 8) Advisory notes

- A `RunDetailPage` a viewer-data-t minden refresh-cikluson lekéri (3s polling), ami felesleges lehet terminal state után. Optimalizálható: terminal state-nél egyszer kérni le és utána nem pollolni.
- A `strategy_field_sources` dict a T5 audit kártyán még nem renderelt (csak a type-ban és backendben van); ha szükséges, T6/polish task keretében adható hozzá.
- A `phase4.stable.spec.ts` regresszió fut (2/2 PASS); a T4 spec is érintetlen.
