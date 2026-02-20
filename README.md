# VRS Nesting

DXF nesting pipeline + web platform (API, frontend, worker) with Codex workflow artifacts.

## Quick Start

1. Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r api/requirements.txt
```

2. Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

3. Configure environment variables in `.env.local` (or `.env`):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_ACCESS_TOKEN` (worker + management API scripts)
- `SUPABASE_SERVICE_ROLE_KEY` (worker/admin flows)
- `SUPABASE_PROJECT_REF`

Optional API/worker tuning:
- `API_ALLOWED_ORIGINS`
- `API_STORAGE_BUCKET` (default: `vrs-nesting`)
- `API_MAX_DXF_SIZE_MB` (default: `50`)
- `API_RATE_LIMIT_WINDOW_S`, `API_RATE_LIMIT_*`
- `API_SIGNED_URL_TTL_S` (default: `300`)
- `WORKER_ALERT_BACKLOG_SECONDS` (default: `300`)

4. Run services (recommended):

```bash
./scripts/run_web_platform.sh start
```

Useful commands:

```bash
./scripts/run_web_platform.sh status
./scripts/run_web_platform.sh logs api
./scripts/run_web_platform.sh stop
```

Manual alternative:

```bash
uvicorn api.main:app --reload --port 8000
python3 worker/main.py
cd frontend && npm run dev
```

## Phase 4 Operational Decisions

- Rate limit split:
  - gateway: general/global protection
  - app: critical mutations (`POST /runs`, bundle, upload-url)
- Soft quota:
  - atomic DB check+increment via SQL RPC (`enqueue_run_with_quota`)
- Cleanup orchestration:
  - Supabase Cron HTTP trigger -> Edge Function cleanup worker
  - lifecycle rules: failed/cancelled 7d, archived projects 30d, temp bundles 24h
- p95 strict gate and Sentry are currently out-of-scope in Phase 4 DoD.

## Verification Commands

- Full repo gate:

```bash
./scripts/check.sh
./scripts/verify.sh --report codex/reports/web_platform/<task>.md
```

- Phase 4 targeted checks:

```bash
python3 scripts/smoke_phase4_auth_security_config.py
python3 scripts/smoke_phase4_load_profile.py
python3 scripts/export_openapi_schema.py
```

- Frontend E2E:

```bash
cd frontend
npm run test:e2e
```

## API docs

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`
- Static exported schema: `docs/api_openapi_schema.json`
