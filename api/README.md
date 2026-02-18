# API Phase 1 Bootstrap

This directory contains the Phase 1 backend/storage scaffold for the web platform.

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

## Implemented in this Phase 1 bootstrap

- FastAPI app skeleton (`api/main.py`)
- Supabase-backed auth dependency (`api/auth.py`)
- Supabase REST/storage client (`api/supabase_client.py`)
- Projects CRUD routes (`api/routes/projects.py`)
- Files upload URL + metadata routes (`api/routes/files.py`)
- Run-configs routes (`api/routes/run_configs.py`)
- Runs + run-log routes (`api/routes/runs.py`)
- Async DXF validation service (`api/services/dxf_validation.py`)
- SQL schema + RLS drafts (`api/sql/phase1_schema.sql`, `api/sql/phase1_rls.sql`)

## Notes

- This is a scaffold focused on Phase 1 flow and contracts.
- Supabase dashboard provisioning steps (project creation, bucket creation, policy deployment)
  are out of repo scope and must be executed in Supabase separately.
