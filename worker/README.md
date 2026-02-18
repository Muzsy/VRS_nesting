# Worker Image (Phase 2.1)

This image is a packaging baseline for the Phase 2 worker runtime.

## What is included
- Python 3.12 runtime
- `requirements.txt` Python dependencies
- `vrs_nesting/` package and runtime assets (`scripts/`, `docs/`, `samples/`, `poc/`)
- `vrs_solver` binary at `/usr/local/bin/vrs_solver`
- `sparrow` binary at `/usr/local/bin/sparrow`

## Build locally
```bash
docker build -f worker/Dockerfile -t vrs-worker:phase2-p1 .
```

## Smoke run (image command)
```bash
docker run --rm vrs-worker:phase2-p1
```

## Publish via GitHub Actions
Use workflow: `.github/workflows/worker-image.yml`

- `workflow_dispatch` supports manual publish.
- On `main` branch push (paths under `worker/`, `vrs_nesting/`, `rust/vrs_solver/`, `requirements.txt`, `scripts/ensure_sparrow.sh`) the workflow builds and pushes to GHCR:
  - `ghcr.io/<owner>/vrs-worker`
