# API Backend (Phase 4)

This directory contains the backend API for the web platform through Phase 4 hardening tasks.

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
- `API_RATE_LIMIT_WINDOW_S` + `API_RATE_LIMIT_*` (optional)
- `API_SIGNED_URL_TTL_S` (optional, default: `300`)
- `API_ENABLE_SECURITY_HEADERS` (optional, default: enabled)

3. Run the server:

Preferred (from repo root, manages API + worker + frontend together):

```bash
./scripts/run_web_platform.sh start
```

API-only manual command:

```bash
uvicorn api.main:app --reload --port 8000
```

## Implemented baseline

- FastAPI app skeleton + `/health` endpoint + security headers (`api/main.py`)
- Supabase-backed auth dependency (`api/auth.py`)
- Supabase REST/storage client (`api/supabase_client.py`)
- Projects CRUD routes (`api/routes/projects.py`)
- Files upload URL + metadata routes (`api/routes/files.py`)
- Run-configs routes (`api/routes/run_configs.py`)
- Runs + run-log + viewer-data + artifact URL/proxy + bundle routes (`api/routes/runs.py`)
- Async DXF validation service (`api/services/dxf_validation.py`)
- SQL schema + RLS + cleanup helpers (`api/sql/*.sql`)

## Notes

- The API keeps storage private and uses short-lived signed URLs for artifact access.
- Bundle creation uses temporary disk-backed processing to reduce memory pressure.
- Phase 4 quota path uses DB RPC (`enqueue_run_with_quota`) for atomic check+enqueue.
- Supabase dashboard provisioning steps (project creation, bucket creation, policy deployment)
  are out of repo scope and must be executed in Supabase separately.
