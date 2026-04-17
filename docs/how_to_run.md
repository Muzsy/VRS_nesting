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
- Worker readiness: `run_web_platform.sh start` waits for `.cache/web_platform/worker.ready` before reporting success.

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

## Rust nesting engine kozvetlen hasznalata

A `nesting_engine` binary ket alparancsot tamogat:

### `inflate-parts` — geometria elofeldolgozas

Stdin-rol olvas `pipeline_v1` JSON-t, stdout-ra irja az inflated geometriat.

```bash
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml
cat pipeline_request.json | ./rust/nesting_engine/target/release/nesting_engine inflate-parts > pipeline_response.json
```

### `nest` — nesting solver

Stdin-rol olvas `nesting_engine_v2` JSON-t, stdout-ra irja az eredmenyt.

```bash
cat solver_input.json | ./rust/nesting_engine/target/release/nesting_engine nest [FLAGS] > solver_output.json
```

Tamogatott flag-ek:

| Flag | Ertekek | Default | Leiras |
|------|---------|---------|--------|
| `--placer` | `blf`, `nfp` | `blf` | Placement strategia |
| `--search` | `none`, `sa` | `none` | Keresesi mod (SA = Simulated Annealing) |
| `--part-in-part` | `off`, `auto` | `off` | Part-in-part cavity elhelyezes |
| `--compaction` | `off`, `slide` | `off` | Post-placement compaction |
| `--sa-iters` | `<u64>` | `256` | SA iteraciok szama (csak `--search sa`-val) |
| `--sa-temp-start` | `<u64>` | `10000` | SA kezdo homerseklet |
| `--sa-temp-end` | `<u64>` | `50` | SA veg homerseklet |
| `--sa-seed` | `<u64>` | input seed | SA PRNG seed override |
| `--sa-eval-budget-sec` | `<u64>` | — | Max masodperc egy SA evaluaciohoz |

Pelda — SA kereses, part-in-part, compaction:

```bash
cat solver_input.json | ./rust/nesting_engine/target/release/nesting_engine nest \
  --placer blf \
  --search sa --sa-iters 500 --sa-eval-budget-sec 5 \
  --part-in-part auto \
  --compaction slide \
  > solver_output.json
```

Az input/output JSON format leirasa: `docs/nesting_engine/io_contract_v2.md`.

## Nesting engine performance tuning (env var-ok)

Az alabbiak mind opcionalis env var-ok. Ha nincsenek beallitva, a motor backward-kompatibilis
default-okkal fut.

### Geometria elofeldolgozas (Python)

| Env var | Default | Leiras |
|---------|---------|--------|
| `NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM` | ki (nincs) | RDP polygon egyszerusites tolerancia mm-ben. Ajanlott: `0.2` (200 um). A DXF importbol jovo iv/gorbe konturok vertex-szamat ~60-70%-kal csokkenti. |

```bash
export NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM=0.2
python3 -m vrs_nesting.cli dxf-run samples/project_rect_1000x2000.json --run-root runs
```

### BLF placer cap-ek (Rust)

| Env var | Default | Leiras |
|---------|---------|--------|
| `NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP` | `0` (korlatlan) | Per-instance maximum jelolt-szam a cavity + grid fazisban egyutt. Cap eleresekor az instance `INSTANCE_CANDIDATE_CAP` unplaced reason-t kap es a kovetkezo instance-re ugrik. Ajanlott: `10000` SA kereseshez. |
| `NESTING_ENGINE_BLF_CAVITY_ANCHOR_CAP` | `0` (korlatlan) | Max cavity anchor jeloltek szama rotacionkent. Ajanlott: `200`–`500`. |

```bash
export NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP=10000
export NESTING_ENGINE_BLF_CAVITY_ANCHOR_CAP=300
cat solver_input.json | ./rust/nesting_engine/target/release/nesting_engine nest \
  --search sa --part-in-part auto > solver_output.json
```

### SA ido-tartalek (Rust)

| Env var | Default | Leiras |
|---------|---------|--------|
| `NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC` | `0.0` | A `time_limit_sec` hany szazalekat tartsa fenn output-szerializalasra. Tartomany: `[0.0, 0.5)`. Ajanlott: `0.05` (5%). |

### Diagnosztika es profiling

| Env var | Default | Leiras |
|---------|---------|--------|
| `NESTING_ENGINE_BLF_PROFILE` | ki (`!= "1"`) | BLF telemetria kimenet stderr-re JSON formatumban (`BLF_PROFILE_V1 {...}`). Ido- es szamlalo-metrikakat tartalmaz. |
| `NESTING_ENGINE_EMIT_NFP_STATS` | ki (`!= "1"`) | NFP placer statisztikak stderr-re. |

Pelda — profiling bekapcsolasa:

```bash
export NESTING_ENGINE_BLF_PROFILE=1
cat solver_input.json | ./rust/nesting_engine/target/release/nesting_engine nest \
  --search sa 2> blf_profile.json > solver_output.json
```

### Ajanlott production-konfig

Altalanos celra ajanlott beallitasok:

```bash
export NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM=0.2
export NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC=0.05
export NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP=10000
export NESTING_ENGINE_BLF_CAVITY_ANCHOR_CAP=300
```

## Typical local run

1. Run gate:
```bash
./scripts/check.sh
```
2. Run DXF pipeline:
```bash
python3 -m vrs_nesting.cli dxf-run samples/project_rect_1000x2000.json --run-root runs
```
3. Run DXF pipeline hangolt beallitasokkal:
```bash
export NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM=0.2
export NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP=10000
python3 -m vrs_nesting.cli dxf-run samples/project_rect_1000x2000.json --run-root runs
```

## Referenciak

- `docs/nesting_engine/io_contract_v2.md` — nesting engine input/output JSON contract
- `docs/nesting_engine/architecture.md` — belso architektura, modulok, policy-k
- `docs/nesting_engine/blf_performance_fixes_changelog.md` — performance fix changelog + benchmark eredmenyek
- `docs/dxf_project_schema.md` — DXF projekt JSON sema
- `docs/nesting_engine/tolerance_policy.md` — SCALE, touching, kontur-irany policy
