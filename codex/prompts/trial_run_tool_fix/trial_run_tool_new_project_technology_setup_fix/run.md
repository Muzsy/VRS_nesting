# Trial run tool Codex Task - new project technology setup fix
TASK_SLUG: trial_run_tool_new_project_technology_setup_fix

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/trial_run_tool/trial_run_tool_cli_core.md`
- `canvases/trial_run_tool/trial_run_tool_tkinter_gui.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/smoke_trial_run_tool_cli_core.py`
- `scripts/smoke_trial_run_tool_tkinter_gui.py`
- `api/services/run_snapshot_builder.py`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `api/supabase_client.py`
- `canvases/trial_run_tool_fix/trial_run_tool_new_project_technology_setup_fix.md`
- `codex/goals/canvases/trial_run_tool_fix/fill_canvas_trial_run_tool_new_project_technology_setup_fix.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez celzott hibajavitas a local-only trial run toolhoz. Ne hozz letre uj
  product API route-ot es ne nyulj a `frontend/` ala.
- A `run_snapshot_builder.py` prerequisite-jet ne lazitsd fel; a tool alkalmazkodjon
  a valos backend contracthoz.
- Plaintext token, anon key vagy mas titok nem kerulhet repo fajlba, reportba,
  summary-ba vagy smoke fixture-be.

Implementacios elvarasok:
- Uj projekt modban a core orchestrator seedeljen legalabb egy approved,
  default project technology setup rekordot a `project_id`-hez.
- A seedeleshez szukseges mezo-nevek pontosan a migration schema alapjan
  legyenek kezelve.
- A seedeleshez hasznalt runtime boundary maradjon local-only teszt-tool
  szintu; ne hozz letre uj publikus API endpointot csak emiatt.
- Ha a seedeleshez szukseges Supabase runtime adatok hianyoznak, a tool koran,
  erthetoen hibazzon, ne a `POST /runs` utan.
- A CLI es a GUI is kezelje a technology setup minimum parameterkeszletet vagy
  dokumentalt default test setup opciot.
- A GUI maradjon vekony shell; a tenyleges logika a core modulban legyen.
- A run directory evidence contract bovuljon a technology setup bizonyitekaival.

Kulon figyelj:
- `existing_project_id` uzemmodban a tool ne seedeljen feleslegesen uj setupot;
- a smoke fake transportja ne engedje at technology setup nelkul az uj projekt
  modot;
- a report kulon nevezze meg a root cause-t: a hianyzo approved project
  technology setup miatt allt meg korabban a `POST /runs`.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/trial_run_tool_fix/trial_run_tool_new_project_technology_setup_fix.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
