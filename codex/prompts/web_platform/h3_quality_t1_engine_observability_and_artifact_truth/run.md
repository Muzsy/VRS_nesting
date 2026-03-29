# DXF Nesting Platform Codex Task - H3-Quality-T1 Engine observability es artifact truth
TASK_SLUG: h3_quality_t1_engine_observability_and_artifact_truth

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `api/routes/runs.py`
- `scripts/trial_run_tool_core.py`
- `scripts/smoke_trial_run_tool_cli_core.py`
- `scripts/smoke_h1_real_solver_artifact_chain_closure.py`
- `canvases/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task observability / artifact truth task. Nem nesting_engine_v2 adapter,
  nem dual-engine switch, nem v2 result normalizer, nem H3-E4 remnant task.
- A task maradjon a jelenlegi worker/viewer/trial tool truth rendberakasanal.
- Ne talalj ki uj, repoban nem letezo run truth tablat csak az engine meta miatt.
- Ne vezesd be ebben a taskban:
  - `worker/engine_adapter_input_v2.py`
  - worker backend valto kapcsolot
  - v2 output parse logikat
  - frontend nagyobb UI atalakitasokat
  - remnant vagy inventory domain valtozasokat

Implementacios elvarasok:
- A `worker/main.py`-ban tedd egyertelmuve, melyik a canonical solver input
  artifact/source of truth.
- A run evidence vilagban minimum visszaolvashato legyen:
  - `engine_backend`
  - `engine_contract_version`
  - `engine_profile` vagy explicit default allapot
- Az `api/routes/runs.py` viewer-data logika elso korben a canonical solver
  input artifactot olvassa, de legyen determinisztikus fallback snapshot jellegu
  inputra is.
- A `scripts/trial_run_tool_core.py` summary mondja ki minimum:
  - backend
  - contract version
  - input artifact jelenlet
  - output artifact jelenlet
  - run.log / runner_meta / stderr jelenlet
  - artifact completeness

A dedikalt smoke bizonyitsa legalabb:
- a canonical input artifact truth egyertelmu;
- a viewer vissza tudja olvasni a sheet mereteket az input artifactbol;
- fallback esetben is determinisztikus a viselkedes;
- a trial tool summary tartalmazza a min. quality-debug mezoket.

A reportban kulon nevezd meg:
- mi volt a korabbi artifact truth zavar;
- mi lett a task utan a canonical input artifact/source of truth;
- hogyan kezeli a viewer a canonical vs fallback inputot;
- milyen engine meta lett visszakeresheto a run evidence-ben;
- miert fontos ez a kovetkezo v2 adapter / dual-engine taskok elott.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
