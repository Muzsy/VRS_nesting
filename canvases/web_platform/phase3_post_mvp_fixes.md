# canvases/web_platform/phase3_post_mvp_fixes.md

# Phase 3 post-MVP fixes

## Funkcio
A feladat celja a Phase 3 implementacio utani ismert hianyossagok teljes korrekcioja:
- Run detail cancel UX hiany potlasa.
- Viewer-data endpoint bovitese sheet meretekkel, per-sheet kihasznaltsaggal es signed URL mezokkel.
- Viewer signed URL lejart kezeles (automatikus refresh + hiba eseti ujrakeres).
- Viewer pont-alapu hit-test javitasa placement geometriaval.
- Bundle endpoint memoria-kockazat csokkentese (disk-stream orientalt zip/build+upload).
- API verziostring + README dokumentacios allapot igazitas.

## Scope
- Benne van: backend endpoint/transport javitasok, frontend viewer es run detail UX korrekciok, doksi igazitas.
- Nincs benne: Phase 4 teljes hardening (rate limit, quota, E2E, terheleses benchmark teljesites).

## Erintett fajlok
- `canvases/web_platform/phase3_post_mvp_fixes.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase3_post_mvp_fixes.yaml`
- `codex/codex_checklist/web_platform/phase3_post_mvp_fixes.md`
- `codex/reports/web_platform/phase3_post_mvp_fixes.md`
- `codex/reports/web_platform/phase3_post_mvp_fixes.verify.log`
- `api/routes/runs.py`
- `api/supabase_client.py`
- `api/main.py`
- `api/README.md`
- `frontend/src/lib/types.ts`
- `frontend/src/components/ViewerCanvas.tsx`
- `frontend/src/pages/ViewerPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] Run detail oldalon a cancel UX elerheto QUEUED/RUNNING statusznal.
- [ ] Viewer-data endpoint visszaad sheet mereteket + kihasznaltsagot + signed URL metadata mezoket.
- [ ] Viewer signed URL expiry kezelve automatikus refresh-sel es hiba eseti ujrakeressel.
- [ ] Viewer hit-test placement geometriat hasznal (nem csak pont markereket).
- [ ] Bundle keszites/upload nem tisztan in-memory BytesIO megoldas.
- [ ] API verziostring/README aktualizalva.
- [ ] `cd frontend && npm run build` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase3_post_mvp_fixes.md` PASS.
