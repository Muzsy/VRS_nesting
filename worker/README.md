# Worker Image (Phase 2.1-P2.7)

This image packages the worker runtime and starts the queue loop by default.
The worker now handles live log sync, timeout/retry, cancellation, input snapshot
hashing, and SVG fallback generation.

## What is included
- Python 3.12 runtime
- `requirements.txt` Python dependencies
- `vrs_nesting/` package and runtime assets (`scripts/`, `docs/`, `samples/`, `poc/`)
- `worker/` package (`worker.main` queue loop)
- `vrs_solver` binary at `/usr/local/bin/vrs_solver`
- `sparrow` binary at `/usr/local/bin/sparrow`

## Build locally
```bash
docker build -f worker/Dockerfile -t vrs-worker:phase2-p2 .
```

## Run worker loop
```bash
docker run --rm \
  -e SUPABASE_URL=... \
  -e SUPABASE_PROJECT_REF=... \
  -e SUPABASE_ACCESS_TOKEN=... \
  -e SUPABASE_SERVICE_ROLE_KEY=... \
  -e API_STORAGE_BUCKET=vrs-nesting \
  vrs-worker:phase2-p2
```

Single-pass mode (one queue item max):
```bash
docker run --rm ... vrs-worker:phase2-p2 python3 -m worker.main --once
```

## Required worker env vars
- `SUPABASE_URL`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_ACCESS_TOKEN` (Management API SQL query access)
- `SUPABASE_SERVICE_ROLE_KEY` (Storage signed upload/download)

Optional:
- `API_STORAGE_BUCKET` (default: `vrs-nesting`)
- `WORKER_ID` (default: `worker-<pid>`)
- `WORKER_POLL_INTERVAL_S` (default: `5`)
- `WORKER_RETRY_DELAY_S` (default: `30`)
- `WORKER_TIMEOUT_EXTRA_S` (default: `120`)
- `WORKER_RUN_LOG_SYNC_INTERVAL_S` (default: `2`)
- `WORKER_TEMP_ROOT` (default: `/tmp/vrs_worker`)
- `WORKER_RUN_ROOT` (default: `runs`)
- `SPARROW_BIN` (default from image: `/usr/local/bin/sparrow`)

## Publish via GitHub Actions
Use workflow: `.github/workflows/worker-image.yml`

- `workflow_dispatch` supports manual publish.
- On `main` branch push (paths under `worker/`, `vrs_nesting/`, `rust/vrs_solver/`, `requirements.txt`, `scripts/ensure_sparrow.sh`) the workflow builds and pushes to GHCR:
  - `ghcr.io/<owner>/vrs-worker`
