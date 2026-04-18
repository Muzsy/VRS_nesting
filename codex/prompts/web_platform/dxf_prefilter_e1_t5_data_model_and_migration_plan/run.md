# DXF Prefilter E1-T5 Data model es migration terv
TASK_SLUG: dxf_prefilter_e1_t5_data_model_and_migration_plan

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `api/routes/files.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `canvases/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t5_data_model_and_migration_plan.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez **docs-only data-model es migration-plan freeze** task. Ne vezess be Python,
  TypeScript, SQL migration, enum, route, service, RLS vagy UI implementacios valtoztatast.
- Ne talalj ki mar implementaltkent olyan `app.dxf_rules_profiles`,
  `app.dxf_rules_profile_versions`, `app.preflight_runs`, `app.preflight_artifacts`,
  `app.preflight_diagnostics` vagy `app.preflight_review_decisions` tablakat,
  amelyek jelenleg meg nem leteznek a repoban.
- Ne csusztasd at a taskot konkret DDL, migration file, API payload, CRUD vagy UI
  state implementacioba.
- A dokumentumnak a jelenlegi kodra kell epulnie: meglevo enum migrationok,
  file object / geometry revision / validation report / review action truth es
  profile/version migration mintak konkret figyelembevetelevel.

A dokumentacios elvarasok:
- Kulonitsd el a **current-code truth** es a **future canonical prefilter data-model** reteget.
- Rogzitsd, hogy a future rules profile domain owner-scoped + versioned mintat kovessen.
- Rogzitsd, hogy a preflight run persistence kulon truth a geometry revision es validation truthhoz kepest.
- Legyen legalabb magas szintu, table-by-table adatmodell-javaslat a future canonical tablakhhoz.
- Rogzits ownership / FK / uniqueness / indexing elveket docs-szinten.
- Legyen migration slicing terv logikai szeletekre bontva.
- Kulonitsd el a current-code truth, future canonical contract es later extension reszeket.
- Nevezd meg, hogy a lifecycle mar T4-ben van rogzitve, az API payload majd T6-ban jon,
  es ez a task csak persistence truth es migration slicing.
- Legyen explicit anti-scope lista, hogy mit nem fagyaszt le ez a task.

A reportban nevezd meg kulon:
- melyik meglevo tablakhhoz es migrationokhoz kapcsolodik a data-model dokumentum;
- mely entitasok current-code truth es melyek csak future canonical tablajeloltek;
- miert kell kulon preflight truth a geometry revision / validation truth mellett;
- miert fontos, hogy ez a task ne valjon konkret SQL migrationne vagy API implementaciova.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t5_data_model_and_migration_plan.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
