# DXF Nesting Platform Codex Task - H0-E2-T2 core projekt- es profile tablak
TASK_SLUG: h0_e2_t2_core_projekt_es_profile_tablak

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e2_t2_core_projekt_es_profile_tablak.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope tovabbra is szuk:
  most csak `app.profiles`, `app.projects`, `app.project_settings` johet letre.
- RLS, auth auto-provisioning, team/membership, technology/file/revision/run vilag
  nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo H0-E2-T1 migraciot ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- `profiles.id` kapcsolodjon az `auth.users(id)`-hez.
- `projects` az aggregate root.
- `project_settings` 1:1 child legyen `projects` alatt.
- A mezokeszlet legyen minimalis, de elegseges:
  ne legyen se tul sovany, se future-scope terhelt.
- Ha `updated_at` helper function/trigger kell, maradjon minimalis es additiv.

Kulon figyelj:
- ne vezess be technology profile, file metadata, geometry, revision, run,
  snapshot vagy artifact tablat;
- ne keruljon bele RLS policy;
- ne keruljon bele auth signup trigger vagy profile provisioning workflow;
- ha a fo architecture/H0 dokumentum meg `public.*` tablakat sugaroz ott, ahol
  mar `app.*` a vegleges irany, azt minimalisan szinkronizald.

A reportban kulon nevezd meg:
- a 3 tabla vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az indexeket;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md

Ez frissitse:
- codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md
- codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.