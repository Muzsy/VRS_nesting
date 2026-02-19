# canvases/web_platform/phase4_p3_playwright_e2e_stable_async.md

# Phase 4 P3 Playwright E2E stable+async

## Funkcio
A P4.3 celja egy determinisztikus, CI-kepes Playwright E2E suite kialakitasa, ami
kulon kezeli a stable (worker completion nelkuli) es async (viewer/export) flow-kat.

## Scope
- Benne van:
  - Playwright framework bootstrap a frontend appban;
  - stable E2E #1-#2 es async E2E #3-#5 tesztek;
  - CI workflow bekotes retry/time-budget parameterekkel;
  - e2e auth bypass mechanizmus kizarolag tesztkornyezethez.
- Nincs benne:
  - valos cloud backendes E2E futas;
  - P4.4-P4.8 blokkok implementacioja.

## Erintett fajlok
- `canvases/web_platform/phase4_p3_playwright_e2e_stable_async.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p3_playwright_e2e_stable_async.yaml`
- `codex/codex_checklist/web_platform/phase4_p3_playwright_e2e_stable_async.md`
- `codex/reports/web_platform/phase4_p3_playwright_e2e_stable_async.md`
- `codex/reports/web_platform/phase4_p3_playwright_e2e_stable_async.verify.log`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/playwright.config.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/e2e/phase4.stable.spec.ts`
- `frontend/e2e/phase4.async.spec.ts`
- `frontend/src/lib/supabase.ts`
- `frontend/src/components/AuthGuard.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/pages/AuthPage.tsx`
- `.github/workflows/frontend-e2e.yml`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] Playwright framework es local E2E futtatas beallitva.
- [ ] Stable E2E #1-#2 lefedett es PASS.
- [ ] Async E2E #3-#5 lefedett es PASS.
- [ ] CI workflow bekotes megtortent retry/time budget parameterekkel.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p3_playwright_e2e_stable_async.md` PASS.
