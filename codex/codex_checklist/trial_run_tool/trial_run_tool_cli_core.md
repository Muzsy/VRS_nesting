# Codex Checklist - trial_run_tool_cli_core

**Task slug:** `trial_run_tool_cli_core`
**Canvas:** `canvases/trial_run_tool/trial_run_tool_cli_core.md`
**Goal YAML:** `codex/goals/canvases/trial_run_tool/fill_canvas_trial_run_tool_cli_core.yaml`

---

## Felderites

- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] `docs/qa/testing_guidelines.md` elolvasva
- [x] `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md` relevans reszei atnezve
- [x] `scripts/run_web_platform.sh` start/health viselkedes ellenorizve
- [x] API route-ok atnezve: `projects/files/parts/sheets/project_part_requirements/project_sheet_inputs/runs`

## Implementacio

- [x] GUI-fuggetlen orchestrator letrehozva: `scripts/trial_run_tool_core.py`
- [x] Vekony CLI shell letrehozva: `scripts/run_trial_run_tool.py`
- [x] Uj projekt es meglevo projekt uzemmod tamogatott
- [x] DXF directory + default/per-file darabszam tamogatott
- [x] Run evidence directory contract implementalva (`tmp/runs/...`)
- [x] Token redakcio implementalva (plaintext token nem mentodik)
- [x] Hibanal is marad audit trail + summary
- [x] Headless fake-transport smoke letrehozva: `scripts/smoke_trial_run_tool_cli_core.py`

## Ellenorzes

- [x] `python3 -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/smoke_trial_run_tool_cli_core.py` PASS
- [x] `python3 scripts/smoke_trial_run_tool_cli_core.py` PASS

## Gate

- [x] `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_cli_core.md` PASS
