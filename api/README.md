# API Backend (Phase 3 baseline + fixes)

This directory contains the backend API for the web platform through Phase 3, including post-MVP fixes.

## Local setup

1. Install dependencies:

```bash
python3 -m pip install -r api/requirements.txt
```

2. Ensure environment variables are set (read from process env, `.env.local`, then `.env`):

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_PROJECT_REF` (optional)
- `SUPABASE_DB_PASSWORD` (optional)
- `DATABASE_URL` (optional)
- `API_ALLOWED_ORIGINS` (optional, comma-separated)
- `API_STORAGE_BUCKET` (optional, default: `vrs-nesting`)
- `API_MAX_DXF_SIZE_MB` (optional, default: `50`)

3. Run the server:

```bash
uvicorn api.main:app --reload --port 8000
```

## Implemented baseline

- FastAPI app skeleton (`api/main.py`)
- Supabase-backed auth dependency (`api/auth.py`)
- Supabase REST/storage client (`api/supabase_client.py`)
- Projects CRUD routes (`api/routes/projects.py`)
- Files upload URL + metadata routes (`api/routes/files.py`)
- Run-configs routes (`api/routes/run_configs.py`)
- Runs + run-log + viewer-data + artifact URL/proxy + bundle routes (`api/routes/runs.py`)
- Async DXF validation service (`api/services/dxf_validation.py`)
- SQL schema + RLS drafts (`api/sql/phase1_schema.sql`, `api/sql/phase1_rls.sql`)

## Notes

- The API intentionally keeps storage private and uses short-lived signed URLs for artifact access.
- Bundle creation uses temporary disk-backed processing to reduce memory pressure for larger artifacts.
- Supabase dashboard provisioning steps (project creation, bucket creation, policy deployment)
  are out of repo scope and must be executed in Supabase separately.
