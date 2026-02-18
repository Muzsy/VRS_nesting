# canvases/web_platform/phase1_p5_p9_api_auth_projects_files_validation.md

# Phase 1 P1.5-P1.9 API/auth/projects/files/validation completion

## Funkcio
A feladat celja a Phase 1 fennmarado backend pontjainak (P1.5-P1.9)
megvalositasi es verifikacios zarasa: API middleware/auth konfig,
project/files endpoint workflow, es DXF validacios allapotkezeles.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - API endpoint runtime kompatibilitas javitasa (FastAPI 204 valaszkezeles);
  - authz hibaag erosites (`403`) file completion storage key ellenorzessel;
  - Supabase Auth config (email auth, verification, jwt lifecycle) ellenorzese/beallitasa;
  - integralt smoke script P1.5-P1.9 pontok bizonyitasara.
- Nincs benne:
  - frontend UI implementacio;
  - Phase 2 worker pipeline;
  - production observability/rate limiting hardening.

### Erintett fajlok
- `canvases/web_platform/phase1_p5_p9_api_auth_projects_files_validation.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase1_p5_p9_api_auth_projects_files_validation.yaml`
- `codex/codex_checklist/web_platform/phase1_p5_p9_api_auth_projects_files_validation.md`
- `codex/reports/web_platform/phase1_p5_p9_api_auth_projects_files_validation.md`
- `api/routes/projects.py`
- `api/routes/files.py`
- `scripts/smoke_phase1_api_auth_projects_files_validation.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] P1.5/a-e pontok (API skeleton + Supabase kliens + JWT + CORS + logging) bizonyitottan keszek.
- [ ] P1.6/a-d pontok (email auth + verification + jwt lifecycle + protected endpoint auth) bizonyitottan keszek.
- [ ] P1.7/a-f project endpoint pontok bizonyitottan keszek.
- [ ] P1.8/a-e file endpoint pontok bizonyitottan keszek.
- [ ] P1.9/a-e validacios pontok a backend scope-on belul bizonyitottan keszek.
- [ ] Master checklist P1.5-P1.9 frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase1_p5_p9_api_auth_projects_files_validation.md` PASS.

### Kockazat + rollback
- Kockazat: auth/storage viselkedes regresszio az endpoint valtozasok miatt.
- Mitigacio: explicit smoke script tobb felhasznalos auth flow-val.
- Rollback: route valtozasok visszavonasa (projects/files modulok), checklist/report revizio.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase1_p5_p9_api_auth_projects_files_validation.md`
- Feladat-specifikus:
  - `/tmp/vrs_api_venv/bin/python scripts/smoke_phase1_api_auth_projects_files_validation.py`

## Kapcsolodasok
- `api/main.py`
- `api/auth.py`
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/services/dxf_validation.py`
