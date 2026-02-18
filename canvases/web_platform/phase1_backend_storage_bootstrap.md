# canvases/web_platform/phase1_backend_storage_bootstrap.md

# Phase 1 backend + storage bootstrap

## Funkcio
A feladat a Phase 1 implementacio elinditasa a repo-ban: Supabase-kompatibilis API skeleton,
DB schema + RLS SQL, project/files endpoint alapok, es aszinkron DXF alapvalidacio flow.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `api/` FastAPI skeleton (config, auth, routes, supabase REST kliens);
  - SQL schema + RLS policy draft (`api/sql/phase1_schema.sql`, `api/sql/phase1_rls.sql`);
  - Project CRUD endpoint alapok;
  - file upload-url / file meta endpoint alapok;
  - async DXF alapvalidacio szolgaltatas.
- Nincs benne:
  - Supabase dashboard manual setup (projekt/bucket tenyleges letrehozas);
  - Phase 2 worker/queue implementacio;
  - frontend UI.

### Erintett fajlok
- `canvases/web_platform/phase1_backend_storage_bootstrap.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase1_backend_storage_bootstrap.yaml`
- `codex/codex_checklist/web_platform/phase1_backend_storage_bootstrap.md`
- `codex/reports/web_platform/phase1_backend_storage_bootstrap.md`
- `api/requirements.txt`
- `api/README.md`
- `api/__init__.py`
- `api/main.py`
- `api/config.py`
- `api/deps.py`
- `api/auth.py`
- `api/supabase_client.py`
- `api/services/dxf_validation.py`
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/sql/phase1_schema.sql`
- `api/sql/phase1_rls.sql`

### DoD
- [ ] Letrejott futtathato API skeleton a `api/` mappaban.
- [ ] Van SQL schema draft a Phase 1 tablakkal (`users`, `projects`, `project_files`, `run_configs`, `runs`, `run_artifacts`, `run_queue`).
- [ ] Van RLS policy draft az alap user-scope tablakra.
- [ ] Mukodnek a project CRUD endpoint alapok (kodszinten implementalt route-ok).
- [ ] Mukodik a file upload-url + file meta route alap (kodszinten implementalt route-ok).
- [ ] Van aszinkron DXF alapvalidacio szolgaltatas a feltoltott DXF-ekhez.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase1_backend_storage_bootstrap.md` PASS.

### Kockazat + rollback
- Kockazat: Supabase Storage signed-upload endpointek valtozhatnak tenant verzio szerint.
- Mitigacio: API strukturalt hibat ad, a `api/README.md` jelzi a konfiguracios elvarasokat.
- Rollback: az `api/` bootstrap fajlok es a task artefaktok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/phase1_backend_storage_bootstrap.md`

## Kapcsolodasok
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md`
