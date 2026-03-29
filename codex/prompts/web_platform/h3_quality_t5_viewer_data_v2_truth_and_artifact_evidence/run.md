# DXF Nesting Platform Codex Task - H3-Quality-T5 viewer-data v2 truth es artifact evidence
TASK_SLUG: h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `api/routes/runs.py`
- `worker/main.py`
- `worker/raw_output_artifacts.py`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `canvases/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task API truth + parsing bridge. Nem frontend/UI task, nem worker runtime
  task, nem benchmark UX task es nem quality-tuning task.
- A `viewer-data` response schema bovites additive legyen; ne torj meg letezo
  klienst kotelezo uj mezokkel.
- A T1 snapshot fallback viselkedes maradjon meg.
- A v1 legacy viewer-data viselkedes nem torhet el.

Implementacios elvarasok:
- A `viewer-data` endpoint input truth preferenciaja legyen:
  formal `solver_input` artifact -> snapshot fallback.
- Az output truth valasztas tudja a v1 `solver_output.json` es a v2
  `nesting_output.json` vilagot is. Ha van olvashato `engine_meta.json`, azt
  hasznald backend/contract truthhoz; ha nincs, filename + artifact_type + stabil
  sorrend alapjan maradjon determinisztikus a valasztas.
- A solver input parse legyen v1+v2 kompatibilis:
  - v1: `parts[].width/height`, `stocks[]` maradjon;
  - v2: `parts[].outer_points_mm` bbox alapjan adjon viewer meretet;
  - v2: `sheet.width_mm/height_mm` alapjan adjon sheet meretet.
- A raw output parse legyen v1+v2 kompatibilis:
  - v1: legacy placement schema;
  - v2: `part_id`, `instance`, `sheet`, `x_mm`, `y_mm`, `rotation_deg`, `reason`.
- Az `instance_id` v2 esetben determinisztikusan kepzodjon (ajanlott: `part_id:instance`).
- A `ViewerDataResponse` additive optional evidence mezoket kapjon, legalabb:
  `engine_backend`, `engine_contract_version`, `engine_profile`,
  `input_artifact_source`, `output_artifact_filename`, `output_artifact_kind`.
- A sheet metrics (`width_mm`, `height_mm`, `placements_count`, `utilization_pct`)
  v2 runnal se maradjanak uresen, ha az input truth alapjan kiszamolhatok.

A smoke bizonyitsa legalabb:
- legacy v1 runnal a viewer-data tovabbra is helyes marad;
- v2 runnal a `nesting_output.json` helyesen parse-olodik;
- a snapshot fallback tovabbra is mukodik input artifact nelkul;
- az optional engine/artifact evidence mezok helyes truthot adnak, ha van
  `engine_meta.json`;
- az endpoint ismetelt hivasokra is determinisztikus.

A reportban kulon nevezd meg:
- milyen input/output truth valasztasi szabaly lett bevezetve;
- hogyan lett a v1/v2 parse helper reteg szetvalasztva vagy egysegesitve;
- milyen optional viewer-data evidence mezok jottek be;
- hogyan maradt backward kompatibilis a response schema;
- hogy ez a task tudatosan meg mindig nem frontend/UI rollout.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
