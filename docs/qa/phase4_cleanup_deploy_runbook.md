# Phase 4 Cleanup — Supabase Cron + Edge Function deploy runbook

**Státusz:** DOKUMENTÁLT (manuális infra lépés)
**Vonatkozó blokk:** P4.7

---

## Előfeltételek

- Supabase CLI telepítve (`npm install -g supabase` vagy `brew install supabase/tap/supabase`)
- `SUPABASE_PROJECT_REF` env var beállítva (Supabase dashboard → Settings → General → Reference ID)
- `SUPABASE_ACCESS_TOKEN` env var beállítva (Supabase dashboard → Account → Access Tokens)
- `DATABASE_URL` env var beállítva (Supabase dashboard → Settings → Database → Connection string)
- `pg_cron` extension engedélyezve a Supabase projektben (Database → Extensions → pg_cron)

---

## Lépések

### 1. Edge Function deploy

A cleanup worker Edge Function forrása: `supabase/functions/cleanup-worker/`

```bash
supabase functions deploy cleanup-worker --project-ref ${SUPABASE_PROJECT_REF}
```

A deploy sikeres, ha a Supabase dashboard → Edge Functions listájában megjelenik a `cleanup-worker` és státusza `Active`.

### 2. SQL cleanup funkciók deploy

A cleanup helper SQL funkciók: `api/sql/phase4_cleanup_edge_functions.sql`

Tartalmaz:
- `try_acquire_cleanup_lock(p_lock_name, p_owner, p_ttl_seconds)` — elosztott cleanup lock
- `release_cleanup_lock(p_lock_name)` — lock felszabadítás
- `list_cleanup_candidates(p_limit)` — lifecycle cleanup jelöltek listája (7d/30d/24h szabályok)
- `delete_cleanup_candidate(p_candidate_type, p_row_id)` — egyedi sor törlése

```bash
psql "${DATABASE_URL}" -f api/sql/phase4_cleanup_edge_functions.sql
```

Vagy Supabase SQL Editor-ban futtatható közvetlenül.

### 3. Cron trigger aktiválás

A cron template: `api/sql/phase4_cleanup_cron_template.sql`

Aktiválja a Supabase Cron → Edge Function HTTP trigger-t. A pg_cron extensiont és a `EDGE_FUNCTION_URL` / `SERVICE_ROLE_KEY` értékeket kell beállítani a template alapján.

```bash
psql "${DATABASE_URL}" -f api/sql/phase4_cleanup_cron_template.sql
```

### 4. Smoke ellenőrzés

A cleanup flow helyes működése ellenőrizhető a smoke scripttel (SUPABASE_SERVICE_ROLE_KEY szükséges):

```bash
SUPABASE_URL="https://${SUPABASE_PROJECT_REF}.supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key" \
python3 scripts/smoke_phase4_cleanup_lifecycle.py
```

Elvárt kimenet:
```
[INFO] Supabase URL: https://...supabase.co
[INFO] Running cleanup lifecycle smoke...
[list_cleanup_candidates] status=200 candidates=0
[try_acquire_cleanup_lock] status=200 acquired=True
[release_cleanup_lock] status=200
[PASS] cleanup lifecycle smoke passed
```

---

## Lifecycle szabályok

| Lifecycle szabály | Feltétel | Törlési határidő |
|---|---|---|
| FAILED/CANCELLED futás artifactjai | `runs.status IN ('failed', 'cancelled')` | 7 nap után |
| Archivált projektek fájljai | `projects.archived_at IS NOT NULL` | 30 nap után |
| Ideiglenes bundle ZIP-ek | `run_artifacts.artifact_type = 'bundle_zip'` | 24 óra után |

---

## Megjegyzés

Ez a deploy **manuális lépés**, nem automatizált a CI/CD pipeline-ból. A kódbeli implementáció (SQL funkciók, Edge Function, smoke script) teljes — a Supabase-specifikus deploy lépések (Cron konfiguráció, service-role permissions) infra-oldali felelősség.

A smoke script (`scripts/smoke_phase4_cleanup_lifecycle.py`) SUPABASE env var nélkül `SKIP` (exit 0) státusszal tér vissza, így CI-ban nem blokkol.
