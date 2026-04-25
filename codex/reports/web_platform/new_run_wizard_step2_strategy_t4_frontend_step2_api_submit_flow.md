# Report: New Run Wizard Step2 Strategy T4 — Frontend Step2 API Submit Flow

**PASS**

---

## 1) Meta

- **Task slug:** `new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow`
- **Kapcsolódó canvas:** `canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/fill_canvas_new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.yaml`
- **Futás dátuma:** 2026-04-25
- **Branch / commit:** main / c22dc6f
- **Fókusz terület:** Frontend (React/TypeScript/Playwright)

---

## 2) Scope

### 2.1 Cél

1. Frontend strategy típusok (`QualityProfileName`, `EngineBackendHint`, `EngineBackendHintMode`, `NestingEngineRuntimePolicy`, `SolverConfigOverrides`, `RunStrategyProfile`, `RunStrategyProfileVersion`, `ProjectRunStrategySelection`) hozzáadása.
2. API kliens bővítése: 4 új strategy metódus, `createRunConfig`/`createRun` payload javítás (főleg a `run_config_id` elvesztésének megszüntetése).
3. `NewRunPage` Step2 strategy UI: source radio, profile/version selector, custom advanced override blokk.
4. `handleSubmitRun` submit-flow javítás: `runConfig.id` megőrzése és átadása `createRun`-nak.
5. Playwright E2E: mock capture arrays, 2 új teszt (custom + project_default ág).

### 2.2 Nem-cél

1. Backend route/service módosítás.
2. DB migration.
3. Worker módosítás.
4. Strategy profile CRUD UI.
5. Run detail strategy megjelenítés.

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Frontend types:** `frontend/src/lib/types.ts` — strategy típus exportok hozzáadva (7 új export)
- **Frontend API client:** `frontend/src/lib/api.ts` — `requestOrNull<T>`, 4 új metódus, payload bővítések, `run_config_id` bug fix
- **Frontend page:** `frontend/src/pages/NewRunPage.tsx` — strategy state, UI, payload builderek, submit-flow
- **E2E mock:** `frontend/e2e/support/mockApi.ts` — strategy state + handlers + `runConfigBodies`/`runCreateBodies`
- **E2E spec:** `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts` — 2 új teszt (új fájl)

### 3.2 Miért változtak?

A T1/T2/T3 backend és worker lánc már kezeli a strategy truth-ot, de a frontend Step2 jelenleg nem küldte be. A submit-flow hibát (`run_config_id` elveszett) és a strategy UI hiányát ez a T4 task javítja.

---

## 4) Verifikáció

### 4.1 Build

```
npm --prefix frontend run build
→ PASS (TypeScript + Vite build, 0 hiba, 84 modul, 451 kB)
```

### 4.2 Playwright E2E

```
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts
→ 2 passed (13.6s)

node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/phase4.stable.spec.ts
→ 2 passed (8.0s) — regresszió nem tört el
```

### 4.3 Playwright környezeti blocker

A `playwright` bináris nem futtatható közvetlen `npm run test:e2e` hívásból (permissions), de `node frontend/node_modules/@playwright/test/cli.js` path-on keresztül működik. A tesztek lefutottak.

### 4.4 Automatikus verify blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-25T19:53:37+02:00 → 2026-04-25T19:56:27+02:00 (170s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.verify.log`
- git: `main@c22dc6f`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 frontend/e2e/support/mockApi.ts   | 101 +++++++++++-
 frontend/src/lib/api.ts           |  57 +++++++
 frontend/src/lib/types.ts         |  62 ++++++++
 frontend/src/pages/NewRunPage.tsx | 327 +++++++++++++++++++++++++++++++++++++-
 4 files changed, 542 insertions(+), 5 deletions(-)
```

**git status --porcelain (preview)**

```text
 M frontend/e2e/support/mockApi.ts
 M frontend/src/lib/api.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/NewRunPage.tsx
?? canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/
?? codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md
?? codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/
?? codex/prompts/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow/
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.md
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow.verify.log
?? frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts
```

<!-- AUTO_VERIFY_END -->

---

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path) | Magyarázat | Kapcsolódó teszt |
|----------|---------|-------------------|------------|------------------|
| #1 Step2 strategy UI blokk | PASS | `frontend/src/pages/NewRunPage.tsx:262-390` | Strategy source radio (`project_default`, `choose_profile`, `custom`), profile/version selector, advanced override blokk renderelve Step2-ben | T4 spec teszt #1: `await expect(page.getByText("Nesting strategy")).toBeVisible()` |
| #2 Project default 404 nem fatal | PASS | `frontend/src/lib/api.ts` — `requestOrNull<T>` helper; `NewRunPage.tsx:130-143` — `loadStrategyData` catch | `getProjectRunStrategySelection` 404 → `null`, UI megjeleníti "No project default strategy selected", wizard folytatható | T4 spec teszt #2: default flow fut stratégia nélkül is |
| #3 Profile/version listázás | PASS | `frontend/src/lib/api.ts:519-524`, `:526-529` | `listRunStrategyProfiles` → `GET /run-strategy-profiles`; `listRunStrategyProfileVersions` → `GET /run-strategy-profiles/{id}/versions` | T4 spec teszt #1: profile dropdown megjelenik, verzió auto-kiválasztódik |
| #4 `createRunConfig` strategy mezők | PASS | `frontend/src/lib/api.ts:448-455` (payload típus); `NewRunPage.tsx:175-179` (submit-flow összeállítás) | `run_strategy_profile_version_id` + `solver_config_overrides_jsonb` bekerül a POST bodyba custom módban | T4 spec teszt #1: `expect(configBody).toHaveProperty("run_strategy_profile_version_id", VERSION_ID)` |
| #5 `createRun` run_config_id bug fix | PASS | `frontend/src/lib/api.ts:480` — `...(payload?.run_config_id ? { run_config_id: payload.run_config_id } : {})` | Korábban a requestPayload-ból hiányzott a `run_config_id`. Most explicit bekerül. | T4 spec teszt #1 és #2: `expect(runBody).toHaveProperty("run_config_id")` |
| #6 `createRun` strategy request mezők | PASS | `frontend/src/lib/api.ts:481-487`; `NewRunPage.tsx:162-174` — `buildRunStrategyRequestPayload()` | 6 strategy mező opcionálisan kerül a run POST bodyba a stratégia forrás szerint | T4 spec teszt #1: `expect(runBody).toHaveProperty("quality_profile", "quality_aggressive")` + engine/sa asserts |
| #7 Step3 summary strategy megjelenítés | PASS | `NewRunPage.tsx:229-241` (`strategySummaryLabel` összeállítás); `NewRunPage.tsx:404-406` (summary renderelés) | Strategy source + quality profile + engine backend + sa_budget összefoglalóként jelenik meg | T4 spec teszt #1: `await expect(page.getByText(/Custom/)).toBeVisible()` |
| #8 E2E mock capture arrays | PASS | `frontend/e2e/support/mockApi.ts` — `state.runConfigBodies`, `state.runCreateBodies`; POST /run-configs és POST /runs handlerek push-olnak | Mock state tartalmazza a beérkező request bodykat | T4 spec: `mock.state.runConfigBodies.at(-1)` és `mock.state.runCreateBodies.at(-1)` assertek |
| #9 E2E payload assert | PASS | `frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts:98-130` | 12 assertion: configBody és runBody mezők ellenőrzése | 2/2 Playwright teszt PASS |
| #10 Build PASS | PASS | `npm --prefix frontend run build` → `✓ built in 3.99s` | TypeScript hibamentes, 84 modul, 0 warning | — |
| #11 Playwright spec PASS | PASS | `new_run_wizard_step2_strategy_t4.spec.ts` → 2/2 passed | Custom strategy ág + project_default ág | node playwright test |
| #12 Phase4 stable regresszió | PASS | `phase4.stable.spec.ts` → 2/2 passed | Default strategy source = project_default, 404 → null, wizard folytatható | — |

---

## 6) IO contract megjegyzések

A `auto` engine backend hint tilos a backend felé: a `buildRunStrategyRequestPayload()` és `buildSolverConfigOverrides()` helper csak `engineBackendHintMode !== "auto"` esetén teszi bele az `engine_backend_hint` mezőt. A T4 spec ezt az ágat az `nesting_engine_v2` értékkel teszteli.

---

## 7) Advisory notes

- A `requestOrNull<T>` nem módosítja a meglévő `request<T>` viselkedését; más hívók érintetlenek.
- A `loadProfileVersions` async és closure-ból hívható, de `void` visszatérési értékű — esetleges network hiba silent catch.
- Az SA iterations input (`saIters`) csak `search === "sa"` esetén jelenik meg, de az `sa_eval_budget_sec` top-level mező és a runtime policy többi mezője mindig renderelve van custom módban.
- A phase4 stable E2E nem törik el, mert az `installMockApi` már visszaad üres `strategyProfiles: []` és 404-t a selection endpointhoz.

---

## 8) Follow-ups

- Strategy profile CRUD UI (jelenleg nincs, admin kézzel hoz létre profilet).
- Run detail stratégia megjelenítés — melyik profile/version futott, engine backend audit.
- `setProjectRunStrategySelection` UI bekötése (az API kliens metódus már megvan).
