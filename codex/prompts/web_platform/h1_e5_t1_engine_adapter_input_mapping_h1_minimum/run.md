# DXF Nesting Platform Codex Task - H1-E5-T1 Engine adapter input mapping (H1 minimum)
TASK_SLUG: h1_e5_t1_engine_adapter_input_mapping_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `api/services/run_snapshot_builder.py`
- `api/services/run_creation.py`
- `worker/main.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `canvases/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t, DB mezot vagy worker konvenciot: a H0/H1
  docsbol, a meglevo migraciokbol es a repo aktualis worker/runner mintairol
  indulj ki.
- Ez a task H1 minimum **engine adapter input mapping** scope: ne csussz at
  solver process start, raw output mentes, result normalizer, projection vagy
  artifact scope-ba.
- A canonical forras a run snapshot legyen, ne a legacy `run_config` /
  `parts_config` / `stock_file_id` vilag.
- Ha a snapshot jelenleg nem eleg a solver input mappinghez, minimalisan a
  snapshot builder/create flow-t igazitsd, ne a workerben vezess vissza elo DB
  roviditest.
- A kimeneti contract a `docs/solver_io_contract.md` szerinti
  `solver_input.json` v1 legyen.

Implementacios elvarasok:
- Vezess be explicit `worker/engine_adapter_input.py` helper/modult.
- A helper determinisztikusan allitson elo solver-input payloadot a snapshotbol.
- A parts shaped-mode a `nesting_canonical` derivative truth-bol jojjon:
  - polygon.outer_ring -> `outer_points`
  - polygon.hole_rings -> `holes_points`
  - bbox -> `width` / `height`
  - requirement -> `quantity`
- A stocks/sheets a snapshot `sheets_manifest_jsonb` vilagabol jojjenek.
- A rotation policy mapping legyen explicit es bizonyithato. Ha a snapshot
  policy nem kepezheto le biztonsagosan a solver v1 contractra, a helper adjon
  tiszta hibauzenetet.
- A helper ne inditson processzt.
- `worker/main.py`-t legfeljebb annyira igazitsd, hogy a legacy
  `_build_dxf_project_payload(...)` helyett vagy mellett explicit adapter
  helperre tudjon tamaszkodni. A tenyleges solver process futtatas a H1-E5-T2.
- Keszits task-specifikus smoke scriptet a sikeres es hibas agakra.
- Ha kiderul, hogy a snapshot builder minimalis bovitesere volt szukseg, azt a
  reportban nevezd meg expliciten es ne kend el.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum adapter-input scope-ban;
- hogy mit NEM szallit le meg (process start, raw output, result, artifact);
- hogy a rotation policy pontosan hogyan kepezodik le a solver v1 contractra;
- hogy a helper tenylegesen mennyire snapshot-only, es volt-e szukseg builder
  bovitesre.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
