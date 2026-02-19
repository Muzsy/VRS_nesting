# canvases/web_platform/phase4_p1_app_rate_limit_minimal.md

# Phase 4 P1 app-side rate limiting (minimal)

## Funkcio
A feladat celja a P4.1 blokk app-oldali reszenek implementalasa a jovahagyott stratgia szerint:
- gateway tovabbra is globalis vedohalo (repo-n kivul),
- app oldalon minimalis, celzott vedelmek kritikus mutacios route-okra.

## Scope
- Benne van:
  - app-side rate limit helper;
  - `POST /projects/{id}/runs` limit;
  - `POST /projects/{id}/runs/{run_id}/artifacts/bundle` limit;
  - `POST /projects/{id}/files/upload-url` limit;
  - 429 + `Retry-After` konzisztens valasz app oldalon;
  - rate-limit hit logging.
- Nincs benne:
  - gateway konfiguracio (infra oldali beallitas);
  - teljes quota implementacio (P4.2).

## Erintett fajlok
- `canvases/web_platform/phase4_p1_app_rate_limit_minimal.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p1_app_rate_limit_minimal.yaml`
- `codex/codex_checklist/web_platform/phase4_p1_app_rate_limit_minimal.md`
- `codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md`
- `codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.verify.log`
- `api/config.py`
- `api/rate_limit.py`
- `api/routes/runs.py`
- `api/routes/files.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] App-side rate limit helper implementalva konzisztens 429 + `Retry-After` valasszal.
- [ ] `POST /runs`, `POST /runs/:id/artifacts/bundle`, `POST /files/upload-url` route-ok vedettek app oldalon.
- [ ] Rate limit talalatok naplozasa mukodik.
- [ ] Master checklist P4.1 app-oldali pontjai frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p1_app_rate_limit_minimal.md` PASS.
