# canvases/web_platform/phase2_p6_worker_timeout_retry_snapshot.md

# Phase 2 P2.6 worker timeout, retry, snapshot

## Funkcio
A Phase 2.6 celja a worker hibaturosegenek es reprodukalhatosaganak erositesa:
timeout enforcement, retry policy, input snapshot hash, ertelmezheto hibauzenet.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `time_limit_s + 120s` timeout enforcement;
  - retry flow max_attempts figyelembevetellel;
  - input snapshot hash tarolasa (`runs.input_snapshot_hash`);
  - ertelmezheto `error_message` kitoltes.
- Nincs benne:
  - dead-letter kulon tabla.

### Erintett fajlok
- `canvases/web_platform/phase2_p6_worker_timeout_retry_snapshot.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p6_worker_timeout_retry_snapshot.yaml`
- `codex/codex_checklist/web_platform/phase2_p6_worker_timeout_retry_snapshot.md`
- `codex/reports/web_platform/phase2_p6_worker_timeout_retry_snapshot.md`
- `worker/main.py`
- `worker/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] Timeout policy worker oldalon enforce-olva.
- [ ] Retry max_attempts szerinti atmenet megvan.
- [ ] Input snapshot hash tarolva runs tablaban.
- [ ] Ertheto hiba uzenetek mennek `runs.error_message`-be.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p6_worker_timeout_retry_snapshot.md` PASS.

### Kockazat + rollback
- Kockazat: timeout utani cleanup versenyhelyzet.
- Mitigacio: SIGTERM -> SIGKILL fallback es queue allapot konzisztencia.
- Rollback: timeout/retry/snapshot blokk visszavonasa.
