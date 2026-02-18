# canvases/web_platform/phase2_p7_run_configs_api_and_start_modes.md

# Phase 2 P2.7 run-configs API + run start modes

## Funkcio
A Phase 2.7 celja a run-config endpointek es a futasinditas ket modjanak
(preset run_config_id vagy manualis inline config) implementalasa.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `POST /projects/:id/run-configs`
  - `GET /projects/:id/run-configs`
  - `POST /projects/:id/runs` preset/manual mod tamogatassal.
- Nincs benne:
  - frontend wizard.

### Erintett fajlok
- `canvases/web_platform/phase2_p7_run_configs_api_and_start_modes.md`
- `codex/goals/canvases/web_platform/fill_canvas_phase2_p7_run_configs_api_and_start_modes.yaml`
- `codex/codex_checklist/web_platform/phase2_p7_run_configs_api_and_start_modes.md`
- `codex/reports/web_platform/phase2_p7_run_configs_api_and_start_modes.md`
- `api/routes/run_configs.py`
- `api/routes/runs.py`
- `api/main.py`
- `api/README.md`
- `codex/codex_checklist/web_platform/implementacios_terv_master_checklist.md`

### DoD
- [ ] Run-config create/list endpointek mukodnek.
- [ ] Run inditas mukodik preset (`run_config_id`) modban.
- [ ] Run inditas mukodik manual inline config modban.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/phase2_p7_run_configs_api_and_start_modes.md` PASS.

### Kockazat + rollback
- Kockazat: config/file referencia inkonzisztencia.
- Mitigacio: project-file ownership ellenorzes minden inditasnal.
- Rollback: run-config route es kapcsolodo branch visszavonasa.
