# DXF Nesting Platform Codex Task - H2-E6-T1 End-to-end manufacturing pilot
TASK_SLUG: h2_e6_t1_end_to_end_manufacturing_pilot

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `api/services/run_snapshot_builder.py`
- `api/services/project_manufacturing_selection.py`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/manufacturing_preview_generator.py`
- `api/services/postprocessor_profiles.py`
- `api/services/machine_neutral_exporter.py`
- `api/routes/runs.py`
- `scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`
- `scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py`
- `scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py`
- `scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py`
- `scripts/smoke_h2_e5_t3_machine_neutral_exporter.py`
- `canvases/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e6_t1_end_to_end_manufacturing_pilot.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez pilot-task, nem altalanos H2 audit/cleanup es nem machine-specific
  adapter task.
- A `H2-E5-T4` optionalis; ne tedd a PASS feltetelei koze a
  `machine_ready_bundle`, `machine_program`, G-code/NC vagy egyeb
  machine-specific output letet.
- A pilot source-of-truth-ja a snapshotolt manufacturing/postprocess manifest,
  a persisted manufacturing truth es a H2 artifact reteg. Ne olvass live
  project-state-et a snapshot utan, ha nem feltetlenul szukseges.
- Ne nyiss uj schema/migration scope-ot, hacsak blokkolo pilot-futtathatosagi
  hiba ezt minimalis mertekben ki nem kenyszeriti. Alapvetoen ez a task
  schema-bovites nelkul zarja a H2 fo lancot.
- Ne csussz at H3 strategy/scoring/remnant scope-ba.

Implementacios elvarasok:
- Keszits dedikalt `scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`
  pilot scriptet.
- A pilot ne csak kulon smoke-ok shelles egymas utan futtatasa legyen, hanem
  kozos seeded scenario, amely ugyanabbol a mintarunbol bizonyitja a H2 mainline-t.
- Minimum bizonyitando chain:
  `manufacturing/postprocess snapshot -> manufacturing plan builder -> manufacturing metrics -> manufacturing_preview_svg -> manufacturing_plan_json`.
- A pilot output evidence minimum:
  - persisted `run_manufacturing_plans` jelenlet;
  - persisted `run_manufacturing_contours` jelenlet;
  - persisted `run_manufacturing_metrics` jelenlet;
  - artifact lista legalabb `manufacturing_preview_svg` es
    `manufacturing_plan_json` elemekkel;
  - nincs machine-specific artifact, ha a T4 nincs implementalva.
- Keszits dedikalt `docs/qa/h2_end_to_end_manufacturing_pilot_runbook.md`
  runbookot a pilothoz.
- Ha a pilot kozben blokkolo handshake hiba derul ki, csak minimalis,
  kozvetlenul szukseges korrekciot vegezz a YAML outputs listaban szereplo
  service fajlokban.
- Ne talalj ki nem letezo schema-t, route-ot, artifact kindot vagy worker-flow-t.

A smoke script bizonyitsa legalabb:
- a H2 fo manufacturing chain vegigfuthat egy mintarunon;
- a plan/contour/metrics truth letrejon;
- a preview SVG es a machine-neutral export artifact letrejon;
- a snapshotolt postprocessor metadata - ha jelen van - metadata marad, nem
  machine-specific emit;
- nincs `machine_ready_bundle`, `machine_program`, G-code vagy egyeb
  optionalis adapter-side effect a PASS feltetelek kozott;
- hiba eseten boundary-specifikus uzenet keletkezik.

A reportban kulon nevezd meg:
- a pilot fixture rovid leirasat;
- pontosan mely H2 boundaryk lettek vegigvezetve;
- a key truth/artifact evidence-eket;
- kellett-e minimalis core korrekcio vagy sem;
- mi maradt szandekosan H2-E6-T2 audit scope-ban;
- hogy a `H2-E5-T4` optionalis, es ezert miert nem resze a pilot PASS-nak.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence Matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
