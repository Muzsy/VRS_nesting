# DXF Nesting Platform Codex Task - H1-E5-T2 Solver process futtatas (H1 minimum)
TASK_SLUG: h1_e5_t2_solver_process_futtatas_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/queue_lease.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `canvases/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t2_solver_process_futtatas_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t, DB mezot vagy worker konvenciot: a H0/H1
  docsbol, a meglevo migraciokbol es a repo aktualis worker/runner mintairol
  indulj ki.
- Ez a task H1 minimum **solver process futtatas** scope: ne csussz at raw
  output storage, result normalizer, projection vagy artifact redesign iranyba.
- A canonical process-ut a H1-E5-T1 snapshot-input vilagra epuljon, ne a legacy
  `python -m vrs_nesting.cli dxf-run ...` agra.
- Tartsd meg a meglevo queue lease / heartbeat / cancel / retry vedelmeket.
- A helper/bridge legyen explicit es tesztelheto; ne tegyel ujabb nagy inline
  subprocess blokkot a workerbe.

Implementacios elvarasok:
- A worker tenyleges solver futtatasa snapshot-input alapon tortenjen.
- Hasznalj explicit worker-oldali runner-bridge-et vagy helper modult.
- A sikeres futas tovabbra is kontrollaltan zarja a runt `succeeded` allapotba.
- Nem nulla exit, timeout, invalid output vagy runner-hiba eseten a run ne menjen
  hamis success-be.
- Cancel es lease-lost ag maradjon kontrollalt.
- A task ne vallalja fel kulon raw stdout/stderr/result artifact redesignjat.
- Keszits task-specifikus smoke scriptet, amely fake/mock runnerrel bizonyitja a
  fo status-atmeneteket es azt, hogy a canonical ut mar nem a legacy dxf-run.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum solver-process scope-ban;
- hogy a legacy dxf-run ag pontosan hogyan lett kivezetve a canonical futasi utbol;
- hogy a task mit NEM vallal meg (raw output storage, result normalizer,
  projection, artifact pipeline);
- hogy a cancel/timeout/lease-lost agak hogyan maradtak ervenyesek.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
