# DXF Nesting Platform Codex Task - H2-E2-T1 manufacturing_canonical derivative generation
TASK_SLUG: h2_e2_t1_manufacturing_canonical_derivative_generation

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `supabase/migrations/20260317110000_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.sql`
- `supabase/migrations/20260321120000_h1_e7_closure_lifecycle_and_storage_bucket_policies.sql`
- `api/services/geometry_derivative_generator.py`
- `api/services/dxf_geometry_import.py`
- `api/services/part_creation.py`
- `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`
- `scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`
- `canvases/web_platform/h2_e2_t1_manufacturing_canonical_derivative_generation.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e2_t1_manufacturing_canonical_derivative_generation.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A jelenlegi repoban a `geometry_derivative_kind` enum mar tartalmazza a
  `manufacturing_canonical` erteket, es a `app.geometry_derivatives` tabla mar
  letezik. Ezt a meglevo reteget kell aktivalni, nem uj derivative vagy
  manufacturing legacy tablakat kitalalni.
- A `geometry_derivative_generator.py` most tenylegesen csak
  `nesting_canonical` es `viewer_outline` derivativet general. A task ezt boviti,
  nem irja at H2 mas retegeire.
- A `part_creation.py` es az `app.create_part_revision_atomic(...)` jelenleg csak
  `selected_nesting_derivative_id`-re epit. Ezt kell minimalisan, same-geometry
  integritassal boviteni.
- A task scope-ja keskeny marad:
  - manufacturing_canonical derivative generation
  - part revision manufacturing derivative binding
  - task-specifikus smoke
- Kifejezetten out-of-scope:
  - `manufacturing_profiles`
  - `manufacturing_profile_versions`
  - `project_manufacturing_selection`
  - `cut_rule_sets`
  - `cut_contour_rules`
  - contour classification
  - snapshot / manufacturing manifest
  - worker / plan / preview / postprocess / export
- A `manufacturing_canonical` nem lehet a `nesting_canonical` masolata mas kinddel.
  Kulon payloadot kell kapnia, de tovabbra is geometry-derivative truth marad:
  nem manufacturing plan, nem projection, nem export artifact.
- A `part_revisions` manufacturing binding ugyanarra a
  `source_geometry_revision_id`-re maradjon felfuzve, ugyanazzal a
  same-geometry integritas-elvvel, mint a H1 `selected_nesting_derivative_id`
  minta.

Implementacios fokusz:
- Hasznald mintanak:
  - `supabase/migrations/20260317110000_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.sql`
  - `supabase/migrations/20260321120000_h1_e7_closure_lifecycle_and_storage_bucket_policies.sql`
  - `api/services/geometry_derivative_generator.py`
  - `api/services/dxf_geometry_import.py`
  - `api/services/part_creation.py`
  - `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`
  - `scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`

Vegrehajtas:
- Hajtsd vegre a YAML `steps` lepeseket sorrendben.
- A migration maradjon minimal-invaziv: csak azt a schema-bovitest tedd bele,
  ami a manufacturing derivative bindinghez tenylegesen szukseges.
- A smoke legyen bizonyito ereju, ne csak happy-path demo.
- A `dxf_geometry_import.py` valid geometry eseten automatikusan generalja a
  manufacturing derivativet is, de rejected geometry eseten ne kepezzen ilyet.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H2-E2-T1 derivative pipelinehoz;
- hogy mit NEM szallit le meg:
  - contour classification,
  - cut rule rendszer,
  - snapshot manufacturing bovites,
  - manufacturing plan builder,
  - preview / postprocess / export;
- ha a manufacturing payload kulonbsege minimum-szintu maradt, ezt nevezd meg
  oszinten, de bizonyitsd, hogy nem alias.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t1_manufacturing_canonical_derivative_generation.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
