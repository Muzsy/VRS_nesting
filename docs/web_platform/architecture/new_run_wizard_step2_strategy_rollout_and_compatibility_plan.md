# New Run Wizard Step2 Strategy — Rollout and Compatibility Plan

## 1. Feature Chain Overview (T1–T5)

This document covers the deployment and compatibility considerations for the five-task `New Run Wizard Step2 — Nesting Strategy + Settings` feature chain.

### What was built

| Task | Scope | Key artifacts |
|------|-------|---------------|
| **T1** | Backend contract: `run_configs` strategy fields, `run_config_id` run persistence | `supabase/migrations/20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`, `api/routes/run_configs.py`, `api/routes/runs.py` |
| **T2** | Strategy resolver + snapshot precedence | `api/services/run_strategy_resolution.py`, `api/services/run_creation.py`, `api/services/run_snapshot_builder.py` |
| **T3** | Worker `WORKER_ENGINE_BACKEND=auto` + `engine_meta.json` audit fields | `worker/main.py` |
| **T4** | Frontend Step2 strategy UI + `createRunConfig(...)` → `createRun(...)` submit-flow | `frontend/src/pages/NewRunPage.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts` |
| **T5** | `viewer-data` response strategy/backend audit fields + `RunDetailPage` audit card | `api/routes/runs.py` (`ViewerDataResponse`), `frontend/src/pages/RunDetailPage.tsx` |

The full chain: Step2 strategy selection → `run_config` with strategy fields → run creation with resolver precedence → worker backend auto-resolution → `engine_meta.json` artifact → `viewer-data` API → Run Detail audit card.

---

## 2. Deploy Order

The chain has dependencies that must be respected in production deployment.

### Step 1 — DB migration

Run the T1 migration before any backend code change:

```bash
supabase db push
# or
psql -f supabase/migrations/20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql
```

The migration adds `run_strategy_profile_version_id` (nullable UUID) and `solver_config_overrides_jsonb` (jsonb, default `{}`) to `app.run_configs`. Both columns are optional — existing rows are unaffected.

### Step 2 — Backend

Deploy the updated FastAPI application after the migration is confirmed:

- `api/routes/run_configs.py` — accepts new strategy fields in `RunConfigCreateRequest`
- `api/routes/runs.py` — `RunCreateRequest` strategy override fields; `ViewerDataResponse` T5 audit fields
- `api/services/run_strategy_resolution.py` — resolver with precedence chain
- `api/services/run_creation.py` — resolver invocation
- `api/services/run_snapshot_builder.py` — strategy trace fields in snapshot `solver_config_jsonb`

All new request fields are optional. Old API callers sending no strategy fields continue to work.

### Step 3 — Worker

Set `WORKER_ENGINE_BACKEND=auto` on the worker process/container.

```bash
export WORKER_ENGINE_BACKEND=auto
```

The worker already supports `auto`, `sparrow_v1`, and `nesting_engine_v2` as values. With `auto`, the worker reads `engine_backend_hint` from the run snapshot's `solver_config_jsonb` to select the actual backend.

Before setting `auto`, verify the existing worker binary supports it:

```bash
python3 -c "from worker.main import ENGINE_BACKEND_AUTO; print(ENGINE_BACKEND_AUTO)"
```

### Step 4 — Frontend

Deploy the updated frontend bundle after the backend is confirmed healthy:

- Step2 strategy UI is additive — existing wizard flow works unchanged
- `run_config_id` bug fix is included (previously lost in transit)

### Step 5 — Smoke / E2E / Verify

```bash
python3 scripts/smoke_new_run_wizard_step2_strategy_t6_full_chain_closure.py
npm --prefix frontend run build
node frontend/node_modules/@playwright/test/cli.js test \
  --config=frontend/playwright.config.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t4.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts \
  frontend/e2e/new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts
./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t6_rollout_closure_regression.md
```

---

## 3. Backwards Compatibility

### 3.1 Old run create requests (no strategy fields)

`RunCreateRequest` strategy fields are all optional:

```python
run_config_id: UUID | None = None
run_strategy_profile_version_id: UUID | None = None
quality_profile: str | None = None
engine_backend_hint: str | None = None
nesting_engine_runtime_policy: dict | None = None
sa_eval_budget_sec: int | None = None
```

A request omitting all strategy fields resolves via the precedence chain's fallback: `global_default` quality profile and `nesting_engine_v2` engine backend hint. Existing callers are unaffected.

### 3.2 Old `run_config` rows (no strategy columns)

Rows created before the T1 migration have `NULL` for `run_strategy_profile_version_id` and `{}` (empty jsonb) for `solver_config_overrides_jsonb`. The resolver treats `NULL` version and `{}` overrides as "no run_config strategy" and falls through to the request fields or project selection. No 500 errors are produced.

### 3.3 Missing project strategy selection

`api/services/run_strategy_resolution.py` queries `app.project_run_strategy_selection` and returns `None` if no row exists. The resolver falls through to `global_default` without error. The frontend also handles a 404 from `getProjectRunStrategySelection` by returning `null` (via `requestOrNull`).

### 3.4 Missing or old `engine_meta.json`

`api/routes/runs.py` `get_viewer_data(...)` handles a missing `engine_meta.json` gracefully: `engine_meta_payload` defaults to `{}`, all T5 audit fields are `None`, no 500 is raised. The `RunDetailPage` shows "Not available yet" fallback when `viewerData` is `null` or when audit fields are missing.

### 3.5 `sparrow_v1` fallback

If `WORKER_ENGINE_BACKEND=auto` and the snapshot has no `engine_backend_hint` (old run configs), the worker falls back to `sparrow_v1`. This is logged as `backend_resolution_source = "fallback_missing_snapshot_engine_backend_hint"`. The fallback is safe: `sparrow_v1` was the only backend before this feature chain.

---

## 4. Runtime Verification Points

After deployment, verify the chain is healthy at these checkpoints:

### 4.1 Snapshot `solver_config_jsonb`

For a new run with a strategy profile version set, the snapshot's `solver_config_jsonb` must contain:

```json
{
  "quality_profile": "...",
  "engine_backend_hint": "nesting_engine_v2",
  "nesting_engine_runtime_policy": {...},
  "strategy_profile_version_id": "...",
  "strategy_resolution_source": "run_config",
  "strategy_field_sources": {...},
  "strategy_overrides_applied": [...]
}
```

Query directly: `SELECT solver_config_jsonb FROM app.run_snapshots WHERE run_id = '<id>'`.

### 4.2 `engine_meta.json`

After a run completes with `WORKER_ENGINE_BACKEND=auto`, the `engine_meta.json` artifact must exist and contain `requested_engine_backend`, `effective_engine_backend`, and `backend_resolution_source`. Check via Run Detail → Artifacts table → engine_meta.json download, or:

```bash
SELECT filename, artifact_type FROM app.run_artifacts WHERE run_id = '<id>';
```

### 4.3 `viewer-data` response

```bash
curl -H "Authorization: Bearer <token>" \
  "$API_BASE/v1/projects/<project_id>/runs/<run_id>/viewer-data" | jq '.effective_engine_backend, .strategy_profile_version_id'
```

Both should be non-null for runs completed after this deployment.

### 4.4 Run Detail audit card

Open the Run Detail page in the browser for a completed run. The "Strategy and engine audit" card must show:

- Effective backend: `nesting_engine_v2` (or `sparrow_v1` if fallback)
- Backend resolution source: `snapshot_solver_config`
- Strategy profile version ID: the version UUID
- Strategy overrides applied: list of applied override keys

---

## 5. Rollback Strategy

### 5.1 Frontend rollback

Re-deploy the previous frontend bundle. The Step2 strategy UI is self-contained in `NewRunPage.tsx` and the Run Detail audit card is in `RunDetailPage.tsx`. Rolling back the frontend does not affect in-flight runs or stored data.

### 5.2 Worker env override

If the worker causes issues with `auto` backend selection, override immediately:

```bash
WORKER_ENGINE_BACKEND=sparrow_v1
```

This forces all subsequent runs to use `sparrow_v1` regardless of snapshot hints. Already-running jobs are unaffected.

### 5.3 Backend rollback

Rolling back the backend preserves database compatibility because:

- New `run_configs` columns (`run_strategy_profile_version_id`, `solver_config_overrides_jsonb`) are optional
- `RunCreateRequest` strategy fields are optional
- `ViewerDataResponse` new fields are additive optional fields

The old backend simply ignores the new columns and returns `null` for the new viewer-data fields. The frontend degrades gracefully to the "Not available yet" fallback.

### 5.4 DB rollback

The T1 migration uses `ADD COLUMN IF NOT EXISTS` with nullable types. To roll back:

```sql
ALTER TABLE app.run_configs DROP COLUMN IF EXISTS run_strategy_profile_version_id;
ALTER TABLE app.run_configs DROP COLUMN IF EXISTS solver_config_overrides_jsonb;
```

Only do this if no production data in these columns needs to be preserved.

---

## 6. Known Limitations

1. **Run Detail polling**: Covered in T8. The `viewer-data` audit fetch is now guarded by a once-only flag (`viewerDataAttemptedRef`) that is set only when the run reaches a terminal status (`done`, `failed`, `cancelled`). The polling timer skips further API refreshes once terminal state is confirmed via `isTerminalRef`, preventing redundant calls. The fetch remains non-fatal: a 404 or network error from `viewer-data` does not set the global error banner.

2. **`strategy_field_sources` UI**: Covered in T7. The Run Detail audit card now renders the field-source breakdown as sorted key/source pairs (e.g. `quality_profile: run_config`). An empty or null `strategy_field_sources` value shows a stable "No field source evidence" fallback.

3. **Production E2E with real solver**: The T4/T5/T6 Playwright specs use mock APIs. End-to-end validation against a real solver binary and Supabase instance is not covered by this task and requires a separate infra-smoke pipeline.

4. **Strategy profile CRUD UI**: Profiles and versions are created manually by an admin. No self-service UI exists yet.

5. **`choose_profile` mode**: The "Choose profile (no overrides)" strategy source mode wires the version ID but uses the profile's stored `solver_config_jsonb` as overrides. If the profile version has no `solver_config_jsonb`, it falls through to global defaults. Edge cases with malformed profile JSONs are not covered by current E2E.
