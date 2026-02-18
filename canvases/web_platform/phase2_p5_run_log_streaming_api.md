# canvases/web_platform/phase2_p5_run_log_streaming_api.md

# Phase 2 P2.5 run log streaming API

## Funkcio
A Phase 2.5 celja, hogy a futasi log incremental (offset alapu) API endpointon
elerheto legyen, es worker futas kozben is frissuljon.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `GET /projects/:id/runs/:run_id/log?offset=&lines=` endpoint;
  - offset alapu incremental valasz;
  - stop polling jelzes DONE/FAILED/CANCELLED esetben;
  - worker oldali periodikus `run.log` sync Storage-ba.
- Nincs benne:
  - SSE/WebSocket log stream.

### Erintett fajlok
- `canvases/web_platform/phase2_p5_run_log_streaming_api.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p5_run_log_streaming_api.yaml`
- `codex/codex_checklist/web_platform/phase2_p5_run_log_streaming_api.md`
- `codex/reports/web_platform/phase2_p5_run_log_streaming_api.md`
- `api/routes/runs.py`
- `worker/main.py`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] Log endpoint offset/lines alapu incremental valaszt ad.
- [ ] Worker futas kozben is van frissulo `run.log` artifact.
- [ ] Polling leallitas jelzes terminalis allapotoknal adott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p5_run_log_streaming_api.md` PASS.

### Kockazat + rollback
- Kockazat: nagy log fajl gyakori ujrafeltoltesnel overhead.
- Mitigacio: periodikus sync interval.
- Rollback: endpoint + periodic sync reszek visszavonasa.
