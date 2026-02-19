# canvases/web_platform/phase4_p2_atomic_run_quota.md

# Phase 4 P2 atomic run quota

## Funkcio
A Phase 4 P4.2 celja a havi futasi kvota atomikus ervenyesitese, hogy konkurens kereskor
se lehessen a kvotat tullepni, es a `POST /runs` csak sikeres kvota commit utan enqueue-oljon.

## Scope
- Benne van:
  - SQL oldali atomic quota check+increment lockolassal;
  - `POST /v1/projects/{project_id}/runs` atallitasa DB RPC alapra;
  - kvota tullepes konzisztens `429` hibaval.
- Nincs benne:
  - gateway oldali rate limit;
  - E2E/load/security Phase 4 tovabbi blokkok.

## Erintett fajlok
- `canvases/web_platform/phase4_p2_atomic_run_quota.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p2_atomic_run_quota.yaml`
- `codex/codex_checklist/web_platform/phase4_p2_atomic_run_quota.md`
- `codex/reports/web_platform/phase4_p2_atomic_run_quota.md`
- `codex/reports/web_platform/phase4_p2_atomic_run_quota.verify.log`
- `api/sql/phase4_run_quota_atomic.sql`
- `api/supabase_client.py`
- `api/routes/runs.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] `users.quota_runs_per_month` default tovabbra is 50/honap.
- [ ] Atomic SQL function kesz lock-alapu check+increment + run+queue insert tranzakcioban.
- [ ] `POST /runs` az atomic kvota funkciora tamaszkodik.
- [ ] Kvota tullepeskor `429` + felhasznalobarat hibauzenet jon vissza.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p2_atomic_run_quota.md` PASS.
