# DXF Prefilter E1-T4 State machine es lifecycle modell
TASK_SLUG: dxf_prefilter_e1_t4_state_machine_and_lifecycle_model

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `api/routes/files.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `canvases/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez **docs-only state-machine freeze** task. Ne vezess be Python, TypeScript,
  SQL, migration, enum, route, service vagy UI implementacios valtoztatast.
- Ne talalj ki mar implementaltkent olyan `preflight_pending`, `accepted_for_import`,
  `quarantined` vagy hasonlo status mezot/enumot/tabat, amely jelenleg meg nem letezik a repoban.
- Ne csusztasd at a taskot data model, API payload, route contract vagy UI state implementacioba.
- A dokumentumnak a jelenlegi kodra kell epulnie: meglevo enum migrationok, file object / geometry revision
  / validation report statuszvilag, files route es geometry import/validation service konkret figyelembevetelevel.

A dokumentacios elvarasok:
- Kulonitsd el a **file ingest lifecycle**, **preflight run lifecycle**,
  **acceptance outcome lifecycle** es **geometry revision status** retegeket.
- Rogzitsd a V1 minimum future canonical prefilter allapotokat docs-szinten,
  nem SQL enumkent.
- Rogzitsd a meglevo `app.geometry_validation_status` truth es a future prefilter
  state machine kozotti mappinget.
- Rogzitsd, hogy a state machine es a persistence modell kulon feladat.
- Legyen explicit transition tabla trigger/esemeny -> kovetkezo allapot szerkezettel.
- Legyen explicit tiltott atmenet / anti-pattern lista.
- Kulonitsd el a current-code truth, future canonical contract es later extension reszeket.
- Nevezd meg, hogy a future prefilter lifecycle domain szerkezetileg igazodhat a repo
  meglevo lifecycle/status szemleletehez, de ebben a taskban nincs migration vagy CRUD.
- Legyen explicit anti-scope lista, hogy mit nem fagyaszt le ez a task.

A reportban nevezd meg kulon:
- melyik meglevo enumokra es migrationokra epul a lifecycle dokumentum;
- mely allapotok current-code truth es melyek csak future canonical node-ok;
- miert kell kulon kezelni a file ingest, preflight run, acceptance outcome es geometry status reteget;
- miert fontos, hogy a state machine ne valjon ebben a taskban adatmodell- vagy API-implementaciova.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t4_state_machine_and_lifecycle_model.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
