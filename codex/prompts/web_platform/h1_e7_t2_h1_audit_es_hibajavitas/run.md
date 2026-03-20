# DXF Nesting Platform Codex Task - H1-E7-T2 H1 audit es hibajavitas
TASK_SLUG: h1_e7_t2_h1_audit_es_hibajavitas

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e7_t2_h1_audit_es_hibajavitas.yaml
- canvases/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md
- codex/reports/web_platform/h1_e7_t1_end_to_end_pilot_projekt.md
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/known_issues/web_platform_known_issues.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- docs/solver_io_contract.md
- api/main.py
- api/routes/files.py
- api/routes/parts.py
- api/routes/sheets.py
- api/routes/project_part_requirements.py
- api/routes/project_sheet_inputs.py
- api/routes/runs.py
- api/services/file_ingest_metadata.py
- api/services/dxf_geometry_import.py
- api/services/geometry_validation_report.py
- api/services/geometry_derivative_generator.py
- api/services/part_creation.py
- api/services/sheet_creation.py
- api/services/project_part_requirements.py
- api/services/project_sheet_inputs.py
- api/services/run_snapshot_builder.py
- api/services/run_creation.py
- worker/main.py
- worker/queue_lease.py
- worker/engine_adapter_input.py
- worker/raw_output_artifacts.py
- worker/result_normalizer.py
- worker/sheet_svg_artifacts.py
- worker/sheet_dxf_artifacts.py

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez audit/stabilizacios task, nem feature-task.
- Uj H2 feature, uj nagy architekturális refaktor vagy altalanos scope-bovites nem johet letre.
- Uj domain migracio csak akkor johetne letre, ha kritikus, kozvetlen H1-zaro ok miatt elkerulhetetlen lenne,
  de alapertelmezetten ne hozz letre uj migraciot.
- Csak pilotbol vagy auditbol kozvetlenul kovetkezo hibajavitas fér bele.

Modellezesi elvek:
- A cel a H1 lezarhatosaganak bizonyitasa vagy oszinte cafolata.
- A H2 gate verdict csak evidence alapon mondhato ki.
- A kisebb, nem blokkolo elteresek advisory kategoriaban maradhatnak.
- A H2 csak akkor indulhat tisztan, ha a verdict `PASS` vagy `PASS WITH ADVISORIES`.
- A projection es artifact vilag maradjon szetvalasztva; a task ne nyisson uj export/manufacturing feature-t.

Kulon figyelj:
- keszits completion matrixot a teljes H1-re;
- kulon valaszd szet a blokkolo es advisory eltereseket;
- a pilotbol kijovo bugfixek legyenek minimal diffek, egyenes indoklassal;
- frissitsd a `web_platform_known_issues.md` fajlt, ha marad ismert korlat;
- ne szepitsd PASS-ra, ha a H2-t valami valojaban blokkolna.

A reportban kulon nevezd meg:
- a H1 completion matrix roviditett eredmenyet;
- a H1-E7-T1 pilot fo tanulsagait;
- a konkret mostani hibajavitasokat;
- a blokkolo vs advisory eltereseket;
- a H2 entry gate vegso iteletet;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e7_t2_h1_audit_es_hibajavitas.md

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
