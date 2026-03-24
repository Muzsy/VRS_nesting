# DXF Nesting Platform Codex Task - H2-E6-T2 H2 audit es hibajavitas
TASK_SLUG: h2_e6_t2_h2_audit_es_hibajavitas

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_master_roadmap_h0_h3.md`
- `docs/web_platform/roadmap/h1_lezarasi_kriteriumok_es_h2_entry_gate.md`
- `docs/known_issues/web_platform_known_issues.md`
- `canvases/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e6_t2_h2_audit_es_hibajavitas.yaml`
- `canvases/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`
- `codex/reports/web_platform/h2_e6_t1_end_to_end_manufacturing_pilot.md`
- `api/routes/project_manufacturing_selection.py`
- `api/routes/cut_rule_sets.py`
- `api/routes/cut_contour_rules.py`
- `api/routes/postprocessor_profiles.py`
- `api/routes/runs.py`
- `api/services/project_manufacturing_selection.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/geometry_contour_classification.py`
- `api/services/cut_rule_sets.py`
- `api/services/cut_contour_rules.py`
- `api/services/cut_rule_matching.py`
- `api/services/run_snapshot_builder.py`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/manufacturing_preview_generator.py`
- `api/services/postprocessor_profiles.py`
- `api/services/machine_neutral_exporter.py`
- `scripts/smoke_h2_e1_t2_project_manufacturing_selection.py`
- `scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
- `scripts/smoke_h2_e2_t2_contour_classification_service.py`
- `scripts/smoke_h2_e3_t1_cut_rule_set_model.py`
- `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
- `scripts/smoke_h2_e3_t3_rule_matching_logic.py`
- `scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py`
- `scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`
- `scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py`
- `scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py`
- `scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py`
- `scripts/smoke_h2_e5_t3_machine_neutral_exporter.py`
- `scripts/smoke_h2_e6_t1_end_to_end_manufacturing_pilot.py`

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez audit/stabilizacios task, nem feature-task.
- Uj H3 feature, scoring/remnant vagy strategy domain most nem johet letre.
- Az optionalis `H2-E5-T4` machine-specific adapter ag nem kotelezo H2 closure feltetel; ne minositsd blockernek pusztan a hianya miatt.
- Uj domain tabla vagy uj migracio csak akkor johetne letre, ha kritikus, kozvetlen H2-zaro inkonzisztencia miatt elkerulhetetlen lenne, de alapertelmezetten ne hozz letre uj migraciot.
- Ne csussz at altalanos docs-refaktorba vagy nagy cleanup hullamba.

Modellezesi elvek:
- A cel a H2 lezarhatosaganak bizonyitasa vagy oszinte cafolata.
- A H2 gate verdict csak evidence alapon mondhato ki.
- A kisebb, nem blokkolo elteresek advisory kategoriaban maradhatnak.
- A H3 csak akkor indulhat tisztan, ha a verdict `PASS` vagy `PASS WITH ADVISORIES`.
- A task tree, a source-of-truth docs, a pilot evidence es a tenyleges szolgaltatasok egymassal konzisztens kepet kell adjanak.
- Kulon valaszd szet:
  - manufacturing derivative truth,
  - contour classification truth,
  - rule matching,
  - run snapshot manufacturing/postprocess manifest,
  - run_manufacturing_* persisted truth,
  - preview/export artifact reteg.

Kulon figyelj:
- keszits completion matrixot a teljes H2 mainline-ra H2-E6-T1-ig;
- kulon valaszd szet a blokkolo es advisory eltereseket;
- ahol a docsban vagy known issues-ben maradt kisebb stale naming vagy allapotmaradvany, azt minimalisan tisztitsd ki;
- ne szepits `PASS`-ra, ha valami valojaban H3-blocking maradt;
- ne csempeszd vissza a machine-specific adapter hianyat kotelezo PASS feltetelnek.

A reportban kulon nevezd meg:
- a H2 completion matrix roviditett eredmenyet;
- a H2-E6-T1 pilot fo tanulsagait;
- a blokkolo vs advisory eltereseket;
- a H3 entry gate vegso iteletet;
- a javitott docs-konzisztencia pontokat;
- hogy mi maradt szandekosan out-of-scope;
- hogy az optionalis H2-E5-T4 miert nem resze a kotelezo H2 mainline closure-nak.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`

Ez frissitse:
- `codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md`
- `codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.verify.log`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
