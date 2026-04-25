# Report: New Run Wizard Step2 Strategy T8 — Run Detail Polling Optimization

**PASS**

---

## 1) Meta

- **Task slug:** `new_run_wizard_step2_strategy_t8_run_detail_polling_optimization`
- **Kapcsolódó canvas:** `canvases/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/fill_canvas_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.yaml`
- **Futás dátuma:** 2026-04-25
- **Branch / commit:** main
- **Fókusz terület:** Frontend polling guard + Playwright E2E + Offline smoke

---

## 2) Scope

### 2.1 Cél

1. `RunDetailPage` polling optimalizálása: `viewer-data` fetch egyszeri, terminális, non-fatal guarddal.
2. Stale `run` closure bug javítása: timer `isTerminalRef`-et használ a frissen lekért státusz alapján.
3. T8 Playwright spec: done-once (≤1 viewer-data hívás) + running-no-viewer-data (0 hívás).
4. Rollout doc frissítése: polling limitation lezárva.
5. Offline smoke (38 check) + build + verify gate.

### 2.2 Nem-cél

1. Backend API contract módosítás.
2. DB migration.
3. Strategy resolver, worker, vagy New Run Wizard módosítás.
4. Production infra-smoke valódi solver ellen.

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Frontend page:** `frontend/src/pages/RunDetailPage.tsx` — `viewerDataAttemptedRef` + `isTerminalRef` pattern; viewer-data csak terminális állapotnál, egyszer; timer leáll terminálisan
- **E2E spec:** `frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts` — új fájl (2 teszt)
- **Smoke:** `scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py` — új fájl (38 check)
- **Rollout doc:** `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` — Run Detail polling known limitation lezárva

### 3.2 Miért változtak?

A T7-ben az audit kártya teljesebb lett, de a viewer-data fetch minden 3 másodperces ciklusban futott, terminális állapotnál is. A timer stale `run` closure alapján döntött, ami azt jelentette, hogy az `isTerminalRef` nélkül a timer soha nem állt le. A T8 ezt a hiányosságot zárja le egyszeri, terminális fetch guarddal.

---

## 4) Verifikáció

### 4.1 Python smoke

```
python3 scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py
→ PASS: 38 checks passed (38 total)
```

### 4.2 Frontend build

```
npm --prefix frontend run build
→ PASS (TypeScript + Vite build, 0 hiba, 84 modul, 454 kB)
```

### 4.3 Playwright E2E — T5 + T6 + T7 + T8 (7 teszt)

```
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t7_strategy_field_sources_polish.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts
→ 7 passed (17.2s)
```

### 4.4 Automatikus verify blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-25T22:03:09+02:00 → 2026-04-25T22:05:55+02:00 (166s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.verify.log`
- git: `main@f36d5b0`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 ...tep2_strategy_rollout_and_compatibility_plan.md |  2 +-
 frontend/src/pages/RunDetailPage.tsx               | 34 +++++++++++++++-------
 2 files changed, 25 insertions(+), 11 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md
 M frontend/src/pages/RunDetailPage.tsx
?? canvases/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/
?? codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md
?? codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/
?? codex/prompts/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization/
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.md
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.verify.log
?? frontend/e2e/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.spec.ts
?? scripts/smoke_new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.py
```

<!-- AUTO_VERIFY_END -->

---

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path) | Magyarázat | Kapcsolódó teszt |
|----------|---------|-------------------|------------|------------------|
| #1 `viewerDataAttemptedRef` guard a viewer-data fetch körül | PASS | `frontend/src/pages/RunDetailPage.tsx` — `viewerDataAttemptedRef.current` check + set | Terminális állapotnál egyszer fut le, utána kihagyva | T8 done-once teszt |
| #2 `isTerminalRef` timer guard (nem stale closure) | PASS | `frontend/src/pages/RunDetailPage.tsx` — `if (cancelled \|\| isTerminalRef.current) return;` timer callbackban | Frissen lekért státusz alapján dönt, nem stale `run` closure-ről | T8 done-once teszt (4.5s várakozás) |
| #3 viewer-data hiba non-fatal | PASS | `frontend/src/pages/RunDetailPage.tsx` — belső try/catch `getViewerData` körül, `setError` nem hívódik | 404/hiba nem állítja be a globális error bannert | T8 running teszt (no error banner) |
| #4 Guard reset projektId/runId váltáskor | PASS | `frontend/src/pages/RunDetailPage.tsx` — `viewerDataAttemptedRef.current = false`, `isTerminalRef.current = false` useEffect-ben | Váltáskor tiszta állapot | smoke check #1 |
| #5 T5/T6/T7 audit UI szövegek megmaradtak | PASS | `frontend/src/pages/RunDetailPage.tsx` — mind a 4 szöveg jelen van | Regresszió nem tört el | smoke check #2 |
| #6 T8 done-once Playwright teszt PASS | PASS | `frontend/e2e/...t8...spec.ts` — 1/1 PASS | viewerDataRequestCount ≤ 1 after 4.5s | Playwright runner |
| #7 T8 running-no-viewer-data Playwright teszt PASS | PASS | `frontend/e2e/...t8...spec.ts` — 1/1 PASS | viewerDataRequestCount = 0 after 4.5s, no error banner | Playwright runner |
| #8 T8 offline smoke PASS | PASS | `scripts/smoke_..._t8_...py` → 38/38 PASS | 5 kategória: polling guard, UI szövegek, T8 spec, rollout doc, artefakt-fegyelem | python3 smoke |
| #9 Rollout doc frissült | PASS | `docs/.../new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` — Known Limitation #1 "Covered in T8" | Polling optimization limitation lezárva | smoke check #4 |
| #10 Nincs gyökérszintű T8 duplikált canvas/yaml | PASS | smoke check #5: `No root-level T8 canvas .md duplicate`, `No root-level T8 goal yaml duplicate` | T8 artefaktok saját alkönyvtárban | smoke PASS |
| #11 `npm --prefix frontend run build` PASS | PASS | TypeScript + Vite 0 hibával, 84 modul, 454 kB | Nincs típushiba | build output |
| #12 T5 + T6 + T7 + T8 Playwright spec PASS | PASS | T5: 2/2, T6: 1/1, T7: 2/2, T8: 2/2 → összesen 7/7 PASS | Regresszió nem tört el | Playwright runner |
| #13 `verify.sh` PASS | PASS | `codex/reports/web_platform/new_run_wizard_step2_strategy_t8_run_detail_polling_optimization.verify.log` | AUTO_VERIFY blokk a reportban | `./scripts/verify.sh` |

---

## 8) Advisory notes

- `getByText("RUNNING")` Playwright-ben alapértelmezetten case-insensitive részleges egyezést használ, ezért `{ exact: true }` szükséges a státusz badge egyértelmű azonosításához; a fix a T8 specben benne van.
- A `isTerminalRef` pattern teszi lehetővé, hogy a timer callback ne stale `run` closure-re támaszkodjon — ez a React `useEffect` closure-fogás klasszikus elkerülési módja.
- A T5/T6/T7 specek (összesen 5 teszt) változatlanul PASSolnak — a meglévő audit kártya tartalom érintetlen.
