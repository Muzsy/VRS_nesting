# How To Run VRS Nesting

This guide describes the current, supported commands for local execution.

## Prerequisites
- Python 3.10+
- Rust toolchain (`cargo`, `rustc`)
- Python dependencies:
  - `python3 -m pip install --break-system-packages -r requirements-dev.txt`

## Required quality gate
- Local full gate:
  - `./scripts/check.sh`
- Codex/report wrapper:
  - `./scripts/verify.sh --report codex/reports/<path>/<task>.md`

## Web platform (API + worker + frontend)

### Additional prerequisites
- Node.js + npm (frontend dev server)
- API runtime dependencies:
  - `python3 -m pip install --break-system-packages -r api/requirements.txt`
- Frontend dependencies:
  - `cd frontend && npm install`

### Required environment variables
Create `.env.local` (or `.env`) in repo root with:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_PROJECT_REF`

Optional API/worker tuning:
- `API_ALLOWED_ORIGINS`
- `API_STORAGE_BUCKET` (default: `vrs-nesting`)
- `API_MAX_DXF_SIZE_MB` (default: `50`)
- `API_RATE_LIMIT_WINDOW_S`, `API_RATE_LIMIT_*`
- `API_SIGNED_URL_TTL_S` (default: `300`)
- `WORKER_ALERT_BACKLOG_SECONDS` (default: `300`)

### Start services
Recommended (single command):
```bash
./scripts/run_web_platform.sh start
```

Useful helper commands:
```bash
./scripts/run_web_platform.sh status
./scripts/run_web_platform.sh logs api
./scripts/run_web_platform.sh stop
```

Manual alternative (3 terminals):
Terminal 1 (API):
```bash
set -a; source .env.local; set +a
uvicorn api.main:app --reload --port 8000
```

Terminal 2 (worker):
```bash
set -a; source .env.local; set +a
python3 worker/main.py
```

Terminal 3 (frontend):
```bash
cd frontend
npm run dev
```

### Quick smoke checks (optional)
```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5173/
```

Expected:
- API health returns JSON with `status` (`ok` or `degraded`).
- Frontend returns HTTP `200`.

### Stop services
- Press `Ctrl+C` in each terminal where the process is running.

## CLI entrypoints

### 1) Table-solver flow (`v1`)
- Command:
```bash
python3 -m vrs_nesting.cli run <project_v1.json> --run-root runs
```
- Output contract on success:
  - stdout contains exactly one non-empty line: absolute `run_dir`.

### 2) DXF + Sparrow flow (`dxf_v1`)
- Command:
```bash
python3 -m vrs_nesting.cli dxf-run <project_dxf_v1.json> --run-root runs [--sparrow-bin /path/to/sparrow]
```
- Wrapper equivalent:
```bash
python3 scripts/run_real_dxf_sparrow_pipeline.py --project <project_dxf_v1.json> --run-root runs [--sparrow-bin /path/to/sparrow]
```
- Output contract on success:
  - stdout contains exactly one non-empty line: absolute `run_dir`.

## Sparrow resolution policy
Resolution order in `scripts/ensure_sparrow.sh`:
1. `SPARROW_BIN`
2. `SPARROW_SRC_DIR`
3. `vendor/sparrow`
4. fallback `.cache/sparrow` clone/build (disabled by default in CI)

CI default:
- `SPARROW_ALLOW_NETWORK_FALLBACK=0`

Local override (if needed):
- `SPARROW_ALLOW_NETWORK_FALLBACK=1 ./scripts/check.sh`

## Typical local run
1. Run gate:
```bash
./scripts/check.sh
```
2. Run DXF pipeline:
```bash
python3 -m vrs_nesting.cli dxf-run samples/project_rect_1000x2000.json --run-root runs
```
