# canvases/web_platform/phase3_p1_p8_frontend_viewer_export.md

# Phase 3 frontend + viewer + export

## Funkcio
A feladat celja a Phase 3 teljes blokk implementalasa (P3.1-P3.8), a korabban rogzitett sorrenddel:
P3.1-P3.3, majd P3.7 elorehozva (viewer-data + artifact access alap), utana P3.4-P3.6, vegul P3.8.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - frontend projekt inicializalas (React+Vite+Tailwind);
  - auth oldalak + auth guard;
  - projects/project-detail/feltoltes UX;
  - run wizard + run detail + log polling;
  - viewer-data backend endpoint + artifact URL/proxy endpointek;
  - SVG/Canvas viewer fallback + multi-sheet navigacio;
  - export center + bundle endpoint;
  - Phase 3 checklist/report/master checklist DoD frissites.
- Nincs benne:
  - Phase 4 hardening/Playwright teljes E2E;
  - production deploy pipeline.

### Erintett fajlok
- `canvases/web_platform/phase3_p1_p8_frontend_viewer_export.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase3_p1_p8_frontend_viewer_export.yaml`
- `codex/codex_checklist/web_platform/phase3_p1_p8_frontend_viewer_export.md`
- `codex/reports/web_platform/phase3_p1_p8_frontend_viewer_export.md`
- `codex/reports/web_platform/phase3_p1_p8_frontend_viewer_export.verify.log`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
- `api/main.py`
- `api/routes/runs.py`
- `api/supabase_client.py`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `frontend/postcss.config.cjs`
- `frontend/tailwind.config.cjs`
- `frontend/src/main.tsx`
- `frontend/src/index.css`
- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/supabase.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/components/AuthGuard.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/ViewerCanvas.tsx`
- `frontend/src/pages/AuthPage.tsx`
- `frontend/src/pages/ProjectsPage.tsx`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/ViewerPage.tsx`
- `frontend/src/pages/ExportPage.tsx`

### DoD
- [ ] A Phase 3 checklist P3.1-P3.8 pontjai implementaltak es a relevans DoD checkpointok pipalhatok.
- [ ] Frontend build sikeres (`npm run build` a `frontend/` alatt).
- [ ] Backend uj endpointok mukodnek (`viewer-data`, artifact URL, bundle).
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase3_p1_p8_frontend_viewer_export.md` PASS.

### Kockazat + rollback
- Kockazat: frontend+backend egyszerre sok mozgo alkatresz, regresszio veszely.
- Mitigacio: endpointok altol felig smoke/ellenorzo futtatas + minimalis, fokuszalt UI.
- Rollback: egy commitban visszavonhato (uj frontend mappa + celzott api route bovitesek).
