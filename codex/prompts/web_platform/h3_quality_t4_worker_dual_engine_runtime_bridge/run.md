# DXF Nesting Platform Codex Task - H3-Quality-T4 Worker dual-engine runtime bridge
TASK_SLUG: h3_quality_t4_worker_dual_engine_runtime_bridge

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/result_normalizer.py`
- `worker/raw_output_artifacts.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/validate_nesting_solution.py`
- `scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
- `canvases/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t4_worker_dual_engine_runtime_bridge.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task worker runtime bridge. Nem viewer-data UI task, nem benchmark UX task,
  nem H3-E4 domain task es nem quality-tuning task.
- A default worker backend tovabbra is `sparrow_v1` maradjon.
- A v2 ag csak akkor tekintheto kesznek, ha a worker a fake/patched folyamatban
  tenylegesen `done` allapotig eljut a projection/sheet artifact lepesekkel egyutt.

Implementacios elvarasok:
- Vezess be explicit worker backend valasztast (ajanlott: `WORKER_ENGINE_BACKEND`).
  Tamogatott minimum ertekek: `sparrow_v1`, `nesting_engine_v2`. Minden mas ertek
  korai, kontrollalt hibaval alljon meg.
- A worker a backend alapjan valassza ki a snapshot->input buildert es a hash helpert:
  v1 -> `build_solver_input_from_snapshot` + `solver_input_sha256`,
  v2 -> `build_nesting_engine_input_from_snapshot` + `nesting_engine_input_sha256`.
- A canonical `solver_input` artifact maradjon kozos truth artifact, ne csinalj kulon
  ad hoc input artifact csaladot a v2-nek.
- A runner invocation v1-ben maradjon a `vrs_solver_runner`, v2-ben menjen a
  `nesting_engine_runner` boundary-ra. A v2 run_dir felfedezes illeszkedjen a
  `--run-root` szemantikahoz.
- Az `engine_meta.json` tobbe ne fix `sparrow_v1` legyen: a valos backendet,
  contract verziót, runner modult es input hash-et irja.
- A raw artifact persist ne veszitse el a `nesting_output.json`-t.
- A `worker/result_normalizer.py` kapjon explicit v2 agat, hogy a worker a
  `nesting_output.json`-bol is tudjon projection sorokat, metrics-et es summary-t epiteni.
- A v1 ut ne torjon el.

A smoke bizonyitsa legalabb:
- default / explicit `sparrow_v1` backendnel a worker tovabbra is a legacy runner utat hivja;
- `nesting_engine_v2` backendnel a worker a v2 builder+runner agra valt;
- v2 backendnel a canonical input artifact es az `engine_meta.json` helyes backend truthot ad;
- fake `nesting_output.json` mellett a worker `done` allapotig eljut;
- invalid backend ertek kontrollalt hibaval megall.

A reportban kulon nevezd meg:
- milyen backend selector lett bevezetve es hol;
- hogyan ter el a v1 es v2 runner invocation;
- hogyan lett megoldva a `nesting_output.json` raw artifact persist;
- mi a v2 normalizer minimum bridge scope;
- hogy ez a task tudatosan meg mindig nem viewer-data / UI rollout.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
