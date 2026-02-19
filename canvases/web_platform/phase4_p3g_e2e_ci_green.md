# canvases/web_platform/phase4_p3g_e2e_ci_green.md

# Phase 4 P4.3/g E2E suite — CI zöld állapot igazolása

## 🎯 Funkció

A Playwright stable+async E2E suite lokálisan DONE (P4.3/a–f mind pipált). Az egyetlen nyitott pont:

- **P4.3/g** — `Stable + async E2E suite zöld CI-ban`

A feladat célja, hogy a `frontend-e2e` GitHub Actions workflow ténylegesen PASS állapotban fusson, és a DoD checkpoint lezárható legyen. A workflow és a tesztek megvannak — a feladat a CI futás stabilizálása és a lezárás dokumentálása.

## 🧠 Fejlesztési részletek

### Scope
- **Benne van:**
  - `.github/workflows/frontend-e2e.yml` ellenőrzése és szükség esetén javítása (env var-ok, timeout, retry policy)
  - `frontend/playwright.config.ts` CI-specifikus beállítások felülvizsgálata
  - `frontend/e2e/` tesztek robusztusság-ellenőrzése: nincs-e olyan assertion, ami valós Supabase-t vár CI-ban
  - CI futás indítása (workflow dispatch vagy push), PASS igazolás dokumentálása
  - Master checklist P4.3/g + Phase 4 DoD checkpoint lezárása

- **Nincs benne:**
  - Valós Supabase cloud backend CI-ba kötése
  - Új tesztek írása (a P4.3/a–f már lefedi a szükséges eseteket)
  - API backend CI-ba futtatása

### A mockolt E2E architektúra

A tesztek `VITE_E2E_BYPASS_AUTH=1` env var-ral futnak, ami auth bypass-t aktivál (`AuthGuard.tsx`, `supabase.ts`). Az API hívásokat a `frontend/e2e/support/mockApi.ts` mockApi adapter kezeli — **nincs szükség élő backendre CI-ban**.

A CI-ban ezért elegendő:
1. Node.js + Playwright telepítés
2. Frontend dev server indítás mock env-vel
3. Tesztek futtatása

### Ellenőrzendő CI-specifikus problémák

Az eddigi flakiness oka általában:
- `webServer` startup timeout túl rövid CI-ban → növelni kell
- `retries: 2` CI-ban már beállított, de `workers: 1` szükséges (nincs párhuzamosítás)
- Async tesztek `waitForSelector` timeout-jai mock válaszhoz optimalizálandók
- `npm run test:e2e:ci` script pontosan a CI-kompatibilis config-ot futtatja-e

### Érintett fájlok
- `canvases/web_platform/phase4_p3g_e2e_ci_green.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p3g_e2e_ci_green.yaml`
- `codex/codex_checklist/web_platform/phase4_p3g_e2e_ci_green.md`
- `codex/reports/web_platform/phase4_p3g_e2e_ci_green.md`
- `.github/workflows/frontend-e2e.yml` *(szükség esetén)*
- `frontend/playwright.config.ts` *(szükség esetén)*
- `frontend/e2e/phase4.stable.spec.ts` *(szükség esetén)*
- `frontend/e2e/phase4.async.spec.ts` *(szükség esetén)*
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] `npm run test:e2e:ci` lokálisan PASS (minden teszt zöld, CI env szimulálva: `CI=1`)
- [ ] `.github/workflows/frontend-e2e.yml` tartalmaz helyes env var-okat és timeout értékeket
- [ ] A workflow utolsó futásának eredménye PASS (igazolva a reportban: branch/commit/run URL)
- [ ] Master checklist P4.3/g + Phase 4 DoD `Stable + async E2E suite zöld CI-ban` checkpoint `[x]`
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p3g_e2e_ci_green.md` PASS

### Kockázat + rollback
- Kockázat: az async tesztek CI-ban timeout-olnak, ha a mock adapter nem elég gyors.
  - Mitigáció: mock válaszok szinkron/gyors legyen, `expect.timeout` növelhető CI-ban.
- Kockázat: a workflow-ban hiányzó env var miatt a frontend build sikertelen.
  - Mitigáció: a `webServer.env` blokkban minden `VITE_*` var explicit legyen.
- Rollback: ha a tesztjavítás instabilitást okozna, az e2e fájlok git alapon visszaállíthatók.

## 🧪 Tesztállapot

- Lokális előfuttatás: `CI=1 npm run test:e2e:ci` (workdir: `frontend/`)
- Kötelező gate: `./scripts/verify.sh --report codex/reports/web_platform/phase4_p3g_e2e_ci_green.md`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md`
- `canvases/web_platform/phase4_p3_playwright_e2e_stable_async.md` — előző P4.3 canvas
- `codex/reports/web_platform/phase4_p3_playwright_e2e_stable_async.md` — DONE report
- `.github/workflows/frontend-e2e.yml`
- `frontend/playwright.config.ts`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`