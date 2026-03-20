# DXF Nesting Platform Codex Task - H1-E7-T1 End-to-end pilot projekt
TASK_SLUG: h1_e7_t1_end_to_end_pilot_projekt

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `canvases/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e7_t1_end_to_end_pilot_projekt.yaml`
- `api/routes/files.py`
- `api/services/file_ingest_metadata.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/part_creation.py`
- `api/services/sheet_creation.py`
- `api/services/project_part_requirements.py`
- `api/services/project_sheet_inputs.py`
- `api/services/run_snapshot_builder.py`
- `api/services/run_creation.py`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/sheet_svg_artifacts.py`
- `worker/sheet_dxf_artifacts.py`
- `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py`
- `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
- `scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py`
- `scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez pilot-task, nem altalanos stabilizacios/refaktor task.
- A cel a teljes H1 minimum flow tenyleges vegigvezetese egy reprodukalhato
  mintaprojekten.
- Ne nyiss H2/H3 scope-ot, manufacturingot, bundle workflow redesign-t vagy
  nagy frontend/API ujratervezest.
- Ha a pilot kozben blokkolo handshake hiba derul ki, csak minimalis,
  kozvetlenul szukseges kodigazitast vegezz; a tobbi hiany menjen H1-E7-T2-be.
- Ne talalj ki nem letezo schema-t, artifact kindot, route-ot vagy service
  boundaryt.

Implementacios elvarasok:
- Keszits dedikalt `scripts/smoke_h1_e7_t1_end_to_end_pilot_projekt.py` pilot
  scriptet.
- A pilot ne csak resz-smoke-ok futtatasa legyen, hanem tenyleges H1 lanchossz
  bizonyitas.
- Minimum bizonyitandó chain:
  `file ingest -> geometry -> validation -> derivatives -> part/sheet -> project inputs -> run create -> snapshot -> worker -> projection -> artifacts`.
- A pilot output evidence minimum:
  - run status/siker;
  - nem ures projection truth;
  - `run_metrics` ertelmes counts;
  - artifact lista legalabb `solver_output`, `sheet_svg`, `sheet_dxf` elemekkel.
- Keszits dedikalt `docs/qa/h1_end_to_end_pilot_runbook.md` runbookot a pilothoz.
- A reportban kulon nevezd meg, pontosan mely H1 boundaryk lettek tenylegesen
  vegigvezetve, es mi maradt szandekosan H1-E7-T2 scope-ban.

A reportban kulon nevezd meg:
- a pilot fixture rovid leirasat;
- a kulcs output evidence-eket;
- kellett-e minimalis core kodigazitas vagy sem;
- mi maradt stabilizacios/audit jelleggel a kovetkezo taskra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
