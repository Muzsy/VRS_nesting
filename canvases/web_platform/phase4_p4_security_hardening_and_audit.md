# canvases/web_platform/phase4_p4_security_hardening_and_audit.md

# Phase 4 P4 security hardening + audit

## Funkcio
A P4.4 celja a security baseline megerositese API/frontend oldalon, valamint a dependency audit
es vulnerability exception policy formalizalasa.

## Scope
- Benne van:
  - API security headers + CORS szigoritas;
  - frontend CSP policy;
  - signed URL TTL konfig centralizalas;
  - filename path traversal vedelmek erositese;
  - auth security config guard script;
  - `pip-audit` + `npm audit` futtatas es policy dokumentacio.
- Nincs benne:
  - load/perf hardening;
  - lifecycle cleanup implementacio.

## Erintett fajlok
- `canvases/web_platform/phase4_p4_security_hardening_and_audit.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase4_p4_security_hardening_and_audit.yaml`
- `codex/codex_checklist/web_platform/phase4_p4_security_hardening_and_audit.md`
- `codex/reports/web_platform/phase4_p4_security_hardening_and_audit.md`
- `codex/reports/web_platform/phase4_p4_security_hardening_and_audit.verify.log`
- `api/config.py`
- `api/main.py`
- `api/routes/files.py`
- `api/routes/runs.py`
- `frontend/index.html`
- `scripts/smoke_phase4_auth_security_config.py`
- `docs/qa/phase4_security_hardening_notes.md`
- `docs/qa/vulnerability_exception_policy.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

## DoD
- [ ] P4.4/a-f checkpointok implementalva es master checklistben jelolve.
- [ ] Auth config guard script PASS.
- [ ] `npm audit` es `pip-audit` eredmeny dokumentalva, nincs critical.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase4_p4_security_hardening_and_audit.md` PASS.
