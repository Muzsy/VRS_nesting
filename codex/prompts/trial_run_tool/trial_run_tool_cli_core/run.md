# Trial run tool Codex Task - CLI core
TASK_SLUG: trial_run_tool_cli_core

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
- `scripts/run_web_platform.sh`
- `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py`
- `scripts/smoke_h1_real_infra_closure.py`
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/routes/parts.py`
- `api/routes/sheets.py`
- `api/routes/project_part_requirements.py`
- `api/routes/project_sheet_inputs.py`
- `api/routes/runs.py`
- `canvases/trial_run_tool/trial_run_tool_cli_core.md`
- `codex/goals/canvases/trial_run_tool/fill_canvas_trial_run_tool_cli_core.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez local-only teszt-tool. Ne koss be semmit a frontendbe vagy a vegleges UI-ba.
- Ne hozz letre uj API route-ot a tool kedveert.
- Titok/token nem kerulhet plaintext formaban repo fajlba, reportba vagy summary-ba.

Implementacios elvarasok:
- A teljes futasi logika a `scripts/trial_run_tool_core.py` modulban legyen.
- A `scripts/run_trial_run_tool.py` legyen vekony CLI shell.
- A tool tamogassa az uj projekt es a meglevo projekt uzemmodot.
- A tool tudjon DXF directory alapjan futni, es kezeljen default vagy fajlankenti
  darabszamokat.
- A tool hozzon letre audit run directoryt `tmp/runs/...` alatt.
- Hibanal is hagyjon maga utan eleg evidence-et.
- A tool legfeljebb a meglevo `scripts/run_web_platform.sh` scriptet hivhatja a
  platform inditasara; ne alkalmazzon rejtett SQL vagy kozvetlen DB beavatkozast.

Kulon figyelj:
- a tool nem product feature;
- a GUI kulon task lesz, ezt a taskot ne terjeszd ki Tkinter widgetekre;
- a smoke legyen headless es fake transportos, ne igenyeljen elo infra-kornyezetet.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_cli_core.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
