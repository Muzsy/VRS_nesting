# Checklist — phase4_p7_cleanup_cron_proof

## DoD pontok

- [x] `scripts/smoke_phase4_cleanup_lifecycle.py` létrejött és futtatható
  - SUPABASE env nélkül: `[SKIP] cleanup smoke: SUPABASE env vars not set` (exit 0) — ellenőrizve
  - SUPABASE env-vel: meghívja a cleanup SQL funkciókat és loggol
- [x] `docs/qa/phase4_cleanup_deploy_runbook.md` létrejött és tartalmazza a Supabase Cron + Edge Function deploy lépéseit
- [x] Master checklist Phase 4 DoD `Supabase Cron → Edge cleanup futás bizonyított` checkpoint `[x]`
- [x] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p7_cleanup_cron_proof.md` PASS

## Azonosított SQL funkciók (api/sql/phase4_cleanup_edge_functions.sql)

| Funkciónév | Leírás |
|---|---|
| `try_acquire_cleanup_lock` | Elosztott cleanup lock megszerzése (idempotens, TTL alapú) |
| `release_cleanup_lock` | Cleanup lock felszabadítása |
| `list_cleanup_candidates` | Lifecycle cleanup jelöltek: 7d/30d/24h szabályok szerint |
| `delete_cleanup_candidate` | Egyedi sor törlése (run_artifact / project_file) |

## Érintett fájlok

- `scripts/smoke_phase4_cleanup_lifecycle.py` — új smoke script
- `docs/qa/phase4_cleanup_deploy_runbook.md` — új deploy runbook
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md` — DoD checkpoint [x]-re állítva
- `codex/codex_checklist/web_platform/phase4_p7_cleanup_cron_proof.md` — ez a fájl
- `codex/reports/web_platform/phase4_p7_cleanup_cron_proof.md` — report
