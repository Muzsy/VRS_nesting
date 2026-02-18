# canvases/web_platform/phase2_p4_runs_api_endpoints.md

# Phase 2 P2.4 runs API endpoints

## Funkcio
A Phase 2.4 celja a futtatas-kezelo API endpointok implementalasa:
run inditas, listazas, lekerdezes, cancel, rerun.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `POST /projects/:id/runs`
  - `GET /projects/:id/runs`
  - `GET /projects/:id/runs/:run_id`
  - `DELETE /projects/:id/runs/:run_id`
  - `POST /projects/:id/runs/:run_id/rerun`
- Nincs benne:
  - viewer/export endpointok;
  - frontend integracio.

### Erintett fajlok
- `canvases/web_platform/phase2_p4_runs_api_endpoints.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p4_runs_api_endpoints.yaml`
- `codex/codex_checklist/web_platform/phase2_p4_runs_api_endpoints.md`
- `codex/reports/web_platform/phase2_p4_runs_api_endpoints.md`
- `api/routes/runs.py`
- `api/main.py`
- `api/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] Runs CRUD-like endpointek implementalva a terv szerint.
- [ ] Queue enqueue bekotes megtortenik run inditasnal.
- [ ] Cancel queued/running futasra kezelve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p4_runs_api_endpoints.md` PASS.

### Kockazat + rollback
- Kockazat: cancel/rerun status kezeles versenyhelyzetben.
- Mitigacio: worker oldali cancel figyeles + queue lock.
- Rollback: runs route + router bekotes visszavonasa.
