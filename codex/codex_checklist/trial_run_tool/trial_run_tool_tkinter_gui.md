# Codex Checklist - trial_run_tool_tkinter_gui

**Task slug:** `trial_run_tool_tkinter_gui`
**Canvas:** `canvases/trial_run_tool/trial_run_tool_tkinter_gui.md`
**Goal YAML:** `codex/goals/canvases/trial_run_tool/fill_canvas_trial_run_tool_tkinter_gui.yaml`

---

## Felderites

- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] `docs/qa/testing_guidelines.md` elolvasva
- [x] `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md` relevans reszei atnezve
- [x] `scripts/trial_run_tool_core.py` es `scripts/run_trial_run_tool.py` API/futtatasi mintai atnezve
- [x] `canvases/trial_run_tool/trial_run_tool_cli_core.md` referencia atnezve

## Implementacio

- [x] Vekony Tkinter GUI shell letrehozva: `scripts/trial_run_tool_gui.py`
- [x] A GUI a core runnerre delegal (nincs duplikalt API logika)
- [x] Uj projekt / meglevo projekt mod tamogatott
- [x] DXF directory alapjan automatikus lista + fajlonkenti qty mezok megjelennek
- [x] Nem-blokkolo futas (hatterszal/queue) implementalva
- [x] Token mező maszkolt, plaintext token nem mentodik
- [x] Headless smoke letrehozva: `scripts/smoke_trial_run_tool_tkinter_gui.py`

## Ellenorzes

- [x] `python3 -B -m py_compile scripts/trial_run_tool_gui.py scripts/smoke_trial_run_tool_tkinter_gui.py` PASS
- [x] `python3 -B scripts/smoke_trial_run_tool_tkinter_gui.py` PASS

## Gate

- [x] `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_tkinter_gui.md` PASS
