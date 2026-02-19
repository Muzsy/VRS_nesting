# cleanup-worker (Phase 4 P4.7)

## Purpose
Edge Function that enforces lifecycle cleanup rules:
- run artifacts for `FAILED/CANCELLED` runs older than 7 days
- files in archived projects older than 30 days
- temporary `bundle_zip` artifacts older than 24 hours

## Prerequisites
1. Apply SQL helpers:
   - `api/sql/phase4_cleanup_edge_functions.sql`
2. Deploy function:
   - `supabase functions deploy cleanup-worker`
3. Set function secrets:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - optional:
     - `API_STORAGE_BUCKET` (default `vrs-nesting`)
     - `CLEANUP_LOCK_NAME` (default `cleanup-worker`)
     - `CLEANUP_LOCK_TTL_SECONDS` (default `600`)
     - `CLEANUP_BATCH_SIZE` (default `200`)

## Cron trigger
Use `api/sql/phase4_cleanup_cron_template.sql` and replace placeholders:
- `<PROJECT_REF>`
- `<EDGE_FUNCTION_BEARER_TOKEN>`

The cron trigger calls the Edge Function every 15 minutes.

## Idempotency + lock
- Lock acquisition via `try_acquire_cleanup_lock(...)`
- Candidates fetched in bounded batches via `list_cleanup_candidates(...)`
- Row deletion is explicit by candidate type via `delete_cleanup_candidate(...)`
- Missing storage object delete (`404`) is treated as safe/idempotent
