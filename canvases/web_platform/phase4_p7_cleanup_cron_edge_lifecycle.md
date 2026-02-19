# canvases/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md

# Phase 4 P7 cleanup cron + edge lifecycle

## Funkcio
A P4.7 celja a cleanup orchestration implementalasa: cron trigger, edge function lockolt batch futassal,
es a 7/30/24 napos lifecycle szabalyok kodszintu ervenyesitese.

## Scope
- Benne van:
  - cleanup lock + candidate SQL functions;
  - edge function cleanup worker implementacio;
  - cron setup SQL template;
  - rollout dokumentacio.
- Nincs benne:
  - tenyleges production deploy futtatasa ebben a repoban.

## Erintett fajlok
- `canvases/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p7_cleanup_cron_edge_lifecycle.yaml`
- `codex/codex_checklist/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`
- `codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md`
- `codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.verify.log`
- `api/sql/phase4_cleanup_edge_functions.sql`
- `api/sql/phase4_cleanup_cron_template.sql`
- `supabase/functions/cleanup-worker/index.ts`
- `supabase/functions/cleanup-worker/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] Cron->Edge trigger konfiguracio sablon kesz.
- [ ] Edge cleanup worker lock/batch/idempotens logikaval kesz.
- [ ] 7/30/24 napos szabalyok SQL candidate listaban ervenyesulnek.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p7_cleanup_cron_edge_lifecycle.md` PASS.
