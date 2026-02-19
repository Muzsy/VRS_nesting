# canvases/web_platform/phase4_p6_observability_health_alerting.md

# Phase 4 P6 observability + health + alerting

## Funkcio
A P4.6 celja az API/worker observability baseline formalizalasa: health endpoint, request/correlation ID
alapu naplozas, worker backlog alert, es scheduled uptime ping.

## Scope
- Benne van:
  - `/health` endpoint valos db/storage reachability statusszal;
  - API structured request logging `X-Request-Id`/`X-Correlation-Id` headerekkel;
  - worker oldali structured log + backlog alert (5 perc threshold);
  - GitHub Actions scheduled uptime health ping.
- Nincs benne:
  - Sentry integracio (optional/future).

## Erintett fajlok
- `canvases/web_platform/phase4_p6_observability_health_alerting.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p6_observability_health_alerting.yaml`
- `codex/codex_checklist/web_platform/phase4_p6_observability_health_alerting.md`
- `codex/reports/web_platform/phase4_p6_observability_health_alerting.md`
- `codex/reports/web_platform/phase4_p6_observability_health_alerting.verify.log`
- `api/main.py`
- `api/supabase_client.py`
- `worker/main.py`
- `scripts/uptime_health_ping.py`
- `.github/workflows/uptime-health-ping.yml`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] `/health` endpoint `status/db/storage` mezokkel PASS.
- [ ] API es worker oldalon structured request/correlation logging kesz.
- [ ] Backlog alert trigger logika kesz 5 perces threshold mellett.
- [ ] Scheduled uptime ping workflow konfiguralt.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p6_observability_health_alerting.md` PASS.
