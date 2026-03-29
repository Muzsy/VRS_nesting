# Trial run tool Codex Task - Tkinter GUI
TASK_SLUG: trial_run_tool_tkinter_gui

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `canvases/trial_run_tool/trial_run_tool_cli_core.md`
- `canvases/trial_run_tool/trial_run_tool_tkinter_gui.md`
- `codex/goals/canvases/trial_run_tool/fill_canvas_trial_run_tool_tkinter_gui.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez local desktop teszt-tool shell. Ne koss be semmit a `frontend/` ala.
- A GUI nem masolhatja le a core runner API logikajat.
- Plaintext token nem kerulhet configba, summary-ba vagy repo fajlba.

Implementacios elvarasok:
- Hasznalj `tkinter`-t, ne `PySide6`-ot.
- A GUI legyen vekony shell a core runner felett.
- A GUI tudjon DXF directoryt, tokennel adott runtime parametereket, tablmeretet,
  uj/meglevo projekt uzemmodot es DXF-enkenti mennyisegeket kezelni.
- A futas ne blokkolja teljesen az ablakot; hasznalj egyszeru hatterszal/queue
  mintat vagy ezzel egyenerteku megoldast.
- A smoke legyen headless-barati, ne nyisson valodi ablakot.

Kulon figyelj:
- ez nem vegleges product UI;
- ne terjeszkedj preview, drag&drop, packaging vagy settings persistence iranyba;
- a GUI csak a minimum tesztelesi kenyelmet adja.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/trial_run_tool/trial_run_tool_tkinter_gui.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
