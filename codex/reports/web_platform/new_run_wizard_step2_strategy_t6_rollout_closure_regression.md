# Report: New Run Wizard Step2 Strategy T6 — Rollout Closure + Full-chain Regression

**PASS**

---

## 1) Meta

- **Task slug:** `new_run_wizard_step2_strategy_t6_rollout_closure_regression`
- **Kapcsolódó canvas:** `canvases/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/fill_canvas_new_run_wizard_step2_strategy_t6_rollout_closure_regression.yaml`
- **Futás dátuma:** 2026-04-25
- **Branch / commit:** main / 6c338a0
- **Fókusz terület:** Frontend E2E + Docs + Offline smoke + Verify

---

## 2) Scope

### 2.1 Cél

1. Full-chain Playwright E2E: Step2 custom strategy → run-config body → run create body → Run Detail strategy/engine audit.
2. Rollout/kompatibilitási dokumentum: deploy sorrend, backward compatibility, rollback, known limitations.
3. Offline closure smoke: T1–T5 kritikus contractok + T6 artefaktok + duplikátum-tiltás (86 check).
4. Záró checklist + report + standard verify gate.

### 2.2 Nem-cél

1. Új DB migration.
2. Worker backend resolution módosítása.
3. Strategy resolver precedence módosítása.
4. New Run Wizard UI újratervezése.
5. Production deploy tényleges végrehajtása.

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **E2E spec:** `frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts` — új fájl (1 closure teszt)
- **Rollout doc:** `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` — új fájl
- **Smoke:** `scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py` — új fájl (86 check)
- **Checklist:** `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md`
- **Report:** ez a fájl
- **Verify log:** `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log`

### 3.2 Miért változtak?

A T1–T5 chain elemei külön-külön védve vannak, de eddig nem volt záró scenario, amely egyetlen flow-ban bizonyítja, hogy a Step2-ben kiválasztott strategy valóban megjelenik a Run Detail audit nézetben. A T6 ezt zárja le, és dokumentumot ad a deploy sorrendhez és visszafelé kompatibilitáshoz.

---

## 4) Verifikáció

### 4.1 Python closure smoke

```
python3 scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py
→ PASS: 86 checks passed (86 total)
```

### 4.2 Frontend build

```
npm --prefix frontend run build
→ PASS (TypeScript + Vite build, 0 hiba, 84 modul, 453 kB)
```

### 4.3 Playwright E2E — T4 + T5 + T6 (5 teszt)

```
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts
→ 5 passed (9.0s)
```

### 4.4 Automatikus verify blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-25T21:16:34+02:00 → 2026-04-25T21:19:24+02:00 (170s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log`
- git: `main@6c338a0`
- módosított fájlok (git status): 8

**git status --porcelain (preview)**

```text
?? canvases/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/
?? codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/
?? codex/prompts/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression/
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md
?? codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log
?? docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md
?? frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts
?? scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py
```

<!-- AUTO_VERIFY_END -->

---

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path) | Magyarázat | Kapcsolódó teszt |
|----------|---------|-------------------|------------|------------------|
| #1 T6 full-chain E2E PASS | PASS | `frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts` — 1/1 passed | Step2 custom strategy → runConfigBodies + runCreateBodies assert → Run Detail audit kártya assert | T6 Playwright 1/1 PASS |
| #2 T6 offline closure smoke PASS | PASS | `scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py` → 86/86 PASS | T1–T6 contractok, artefaktok, duplikátum-tiltás, T1–T5 reportok | python3 smoke |
| #3 Rollout/compatibility doc elkészült | PASS | `docs/web_platform/architecture/new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md` | Deploy sorrend, compatibility matrix, rollback stratégia, known limitations | smoke check #6 |
| #4 T1–T5 reportok PASS státuszban | PASS | `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_...md` – `..._t5_...md` mind `PASS` | T1–T5 reportok mind megvannak és PASS-t tartalmaznak | smoke check #7 |
| #5 T1–T6 artefaktok saját alkönyvtárban | PASS | `canvases/web_platform/new_run_wizard_step2_strategy_t*/`, `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t*/` — 6 db dir | Nincs gyökérszintű duplikátum | smoke check #7 |
| #6 Nincs root-level duplikált canvas/yaml | PASS | smoke check #7: `no root-level canvas .md duplicates`, `no root-level goal yaml duplicates` | `canvases/web_platform/` és `codex/goals/canvases/web_platform/` alatt nincs `new_run_wizard_step2_strategy_t*.md/.yaml` root-szintű fájl | smoke PASS |
| #7 `npm --prefix frontend run build` PASS | PASS | TypeScript + Vite 0 hibával, 84 modul, 453 kB | Nincs típushiba | build output |
| #8 T4 + T5 + T6 Playwright spec PASS | PASS | T4: 2/2, T5: 2/2, T6: 1/1 → összesen 5/5 PASS | Teljes E2E regressziós szett | Playwright runner |
| #9 `verify.sh` PASS | PASS | `codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.verify.log` | AUTO_VERIFY blokk alább | `./scripts/verify.sh` |

---

## 8) Advisory notes

- A T6 spec `EXPECTED_RUN_ID = "run-1"` feltételezi, hogy a mock `runCounter` 1-ről indul. Ez az `installMockApi` belső invariáns; ha más tesztek ugyanabban a browser session-ban futnak, a counter növekedhet. A spec saját, izolált `installMockApi` példányt kap, tehát robusztus.
- A T4/T5 regressziós specek (összesen 4 teszt) változatlanul PASSolnak a T6 spec mellett.
- A rollout doc `strategy_field_sources` UI renderelést és production E2E-t known limitation-ként jelöl meg — mindkettő külön task keretében pótolható.

---

## 9) Follow-ups

- `strategy_field_sources` dict megjelenítése a Run Detail audit kártyán (polish).
- Production infra-smoke: valódi solver binary + Supabase ellen futó E2E.
- Strategy profile CRUD UI admin felületen.
