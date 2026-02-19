DONE

## 1) Meta
- Task slug: `phase4_p7_cleanup_cron_edge_lifecycle`
- Kapcsolodo canvas: `canvases/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_phase4_p7_cleanup_cron_edge_lifecycle.yaml`
- Fokusz terulet: `Phase 4 P7 cleanup cron + edge lifecycle`

## 2) Scope

### 2.1 Cel
- Cleanup orchestration kodszintu kialakitasa a 7/30/24 napos szabalyokkal.

### 2.2 Nem-cel
- Valos Supabase deploy/cron futas igazolasa ebben a lokalis repo futasban.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `api/sql/phase4_cleanup_edge_functions.sql`
- `api/sql/phase4_cleanup_cron_template.sql`
- `supabase/functions/cleanup-worker/index.ts`
- `supabase/functions/cleanup-worker/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`
- `canvases/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p7_cleanup_cron_edge_lifecycle.yaml`
- `codex/codex_checklist/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`
- `codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`

### 3.2 Miert valtoztak?
- A P4.7 checkpointok teljesitesere (cron trigger, edge cleanup, lifecycle rules, idempotens lockolt futas).

## 4) Verifikacio (How tested)

### 4.1 Statikus/strukturalis ellenorzes
- SQL helper fuggvenyek definialva: lock acquire/release, candidate list, candidate delete.
- Edge function lock acquisition + candidate feldolgozas + storage+DB torles logika implementalva.

### 4.2 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat |
| --- | --- | --- | --- |
| Cron->Edge trigger konfiguracio sablon | PASS | `api/sql/phase4_cleanup_cron_template.sql` | 15 perces cron HTTP trigger template letrehozva placeholderekkel. |
| Edge cleanup lock/batch/idempotens | PASS | `supabase/functions/cleanup-worker/index.ts`, `api/sql/phase4_cleanup_edge_functions.sql` | Lock acquisition, candidate listing, storage delete 404-idempotens kezeles, row delete RPC kesz. |
| 7/30/24 lifecycle szabalyok | PASS | `api/sql/phase4_cleanup_edge_functions.sql` | SQL candidate lista explicit 7 nap (failed/cancelled), 30 nap (archived), 24 ora (bundle_zip) szabalyokkal. |
| Cascade/logikai osszhang | PASS | `api/sql/phase4_cleanup_edge_functions.sql`, `supabase/functions/cleanup-worker/README.md` | Candidate torles run_artifact/project_file szinten, meglvo FK cascade-ekkel osszhangban. |
| Verify gate PASS | PASS | `codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.verify.log` | A kotelezo wrapper futas PASS. |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-19T20:38:18+01:00 → 2026-02-19T20:40:26+01:00 (128s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.verify.log`
- git: `main@741838b`
- módosított fájlok (git status): 63

**git diff --stat**

```text
 api/config.py                                      | 43 ++++++++++
 api/main.py                                        | 43 ++++++++--
 api/routes/files.py                                | 30 ++++++-
 api/routes/runs.py                                 | 98 +++++++++++++++++++---
 api/supabase_client.py                             | 38 +++++++++
 .../implementacios_terv_master_checklist.md        | 90 ++++++++++----------
 frontend/index.html                                |  4 +
 frontend/package.json                              |  5 +-
 frontend/src/components/AuthGuard.tsx              |  6 +-
 frontend/src/components/Layout.tsx                 | 11 ++-
 frontend/src/lib/supabase.ts                       |  5 ++
 frontend/src/pages/AuthPage.tsx                    |  7 +-
 worker/main.py                                     | 70 +++++++++++++++-
 13 files changed, 379 insertions(+), 71 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/config.py
 M api/main.py
 M api/routes/files.py
 M api/routes/runs.py
 M api/supabase_client.py
 M codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md
 M frontend/index.html
 M frontend/package.json
 M frontend/src/components/AuthGuard.tsx
 M frontend/src/components/Layout.tsx
 M frontend/src/lib/supabase.ts
 M frontend/src/pages/AuthPage.tsx
 M worker/main.py
?? .github/workflows/frontend-e2e.yml
?? .github/workflows/uptime-health-ping.yml
?? api/rate_limit.py
?? api/sql/phase4_cleanup_cron_template.sql
?? api/sql/phase4_cleanup_edge_functions.sql
?? api/sql/phase4_run_quota_atomic.sql
?? canvases/web_platform/phase4_p1_app_rate_limit_minimal.md
?? canvases/web_platform/phase4_p2_atomic_run_quota.md
?? canvases/web_platform/phase4_p3_playwright_e2e_stable_async.md
?? canvases/web_platform/phase4_p4_security_hardening_and_audit.md
?? canvases/web_platform/phase4_p5_load_profile_and_snapshot.md
?? canvases/web_platform/phase4_p6_observability_health_alerting.md
?? canvases/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md
?? codex/codex_checklist/web_platform/phase4_p1_app_rate_limit_minimal.md
?? codex/codex_checklist/web_platform/phase4_p2_atomic_run_quota.md
?? codex/codex_checklist/web_platform/phase4_p3_playwright_e2e_stable_async.md
?? codex/codex_checklist/web_platform/phase4_p4_security_hardening_and_audit.md
?? codex/codex_checklist/web_platform/phase4_p5_load_profile_and_snapshot.md
?? codex/codex_checklist/web_platform/phase4_p6_observability_health_alerting.md
?? codex/codex_checklist/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p1_app_rate_limit_minimal.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p2_atomic_run_quota.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p3_playwright_e2e_stable_async.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p4_security_hardening_and_audit.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p5_load_profile_and_snapshot.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p6_observability_health_alerting.yaml
?? codex/goals/canvases/web_platform/fill_canvas_phase4_p7_cleanup_cron_edge_lifecycle.yaml
?? codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md
?? codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.verify.log
?? codex/reports/web_platform/phase4_p2_atomic_run_quota.md
?? codex/reports/web_platform/phase4_p2_atomic_run_quota.verify.log
?? codex/reports/web_platform/phase4_p3_playwright_e2e_stable_async.md
?? codex/reports/web_platform/phase4_p3_playwright_e2e_stable_async.verify.log
?? codex/reports/web_platform/phase4_p4_security_hardening_and_audit.md
?? codex/reports/web_platform/phase4_p4_security_hardening_and_audit.verify.log
?? codex/reports/web_platform/phase4_p5_load_profile_and_snapshot.md
?? codex/reports/web_platform/phase4_p5_load_profile_and_snapshot.verify.log
?? codex/reports/web_platform/phase4_p6_observability_health_alerting.md
?? codex/reports/web_platform/phase4_p6_observability_health_alerting.verify.log
?? codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md
?? codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.verify.log
?? docs/qa/phase4_security_hardening_notes.md
?? docs/qa/vulnerability_exception_policy.md
?? frontend/e2e/
?? frontend/package-lock.json
?? frontend/playwright.config.ts
?? scripts/smoke_phase4_auth_security_config.py
```

<!-- AUTO_VERIFY_END -->
