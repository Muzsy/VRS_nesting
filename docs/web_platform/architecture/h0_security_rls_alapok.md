# H0 security/RLS alapok (H0-E6-T2)

## 1. Cel es scope

Ez a dokumentum a H0 DB-RLS es storage policy source-of-truth osszefoglaloja.

H0-E6-T2 celja:
- alap ownership/project-bound RLS vedelmek bevezetese az `app.*` tablavilagon;
- minimal storage policy bevezetese a kanonikus bucket inventoryra;
- service-role boundary egyertelmu rogzitese a run/snapshot/output irasi oldalra.

Out-of-scope H0-E6-T2-ben:
- auth auto-provisioning trigger;
- worker/API implementacio;
- signed URL/upload endpoint;
- bucket provisioning script;
- teljes H1/H2 jogosultsagi rendszer.

Rollout allapot (tenyleges):
- Source-of-truth modell: owner/project-bound DB-RLS + minimal storage policy matrix.
- Repo migracios allapot: a `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
  az `app.*` RLS rolloutot tartalmazza; a `storage.objects` policy DDL szegmens hosted owner-limit
  miatt kulon lett valasztva.
- Hosted Supabase allapot: az `app.*` RLS policyk migracios uton aktivak; a storage bucketek
  (`source-files`, `geometry-artifacts`, `run-artifacts`) private modon provisionalva vannak; a
  `storage.objects` H0 minimal policyk manualis Dashboard/Studio provisioninggel aktivak.

## 2. H0 szerepkor elvek

- `anon`: uzleti tabla-hozzaferes nincs.
- `authenticated`: csak sajat owner/project-bound adatokhoz ferhet.
- `service_role`: belso futasi irasi oldal (queue/log/snapshot/output/storage write path).

## 3. Policy helper fuggvenyek

A repo migracio (es a vele azonos szabalylogikara epulo storage provisioning) az alabbi helper
fuggvenyeket hasznalja:
- `app.current_user_id()`
- `app.is_project_owner(project_uuid uuid)`
- `app.owns_part_definition(part_definition_uuid uuid)`
- `app.owns_sheet_definition(sheet_definition_uuid uuid)`
- `app.can_access_geometry_revision(geometry_revision_uuid uuid)`
- `app.can_access_run(run_uuid uuid)`
- `app.storage_object_project_id(object_name text)`

## 4. H0 tablankenti access matrix

| Tabla / csoport | Authenticated select | Authenticated write | H0 policy irany |
| --- | --- | --- | --- |
| `app.profiles` | self-row | self-row | `id = auth.uid()` |
| `app.projects` | owner-only | owner-only | `owner_user_id = auth.uid()` |
| `app.project_settings`, `app.project_technology_setups`, `app.project_part_requirements`, `app.project_sheet_inputs`, `app.file_objects`, `app.geometry_revisions` | project-owner | project-owner | project-bound `app.is_project_owner(project_id)` |
| `app.part_definitions`, `app.sheet_definitions` | owner-only | owner-only | `owner_user_id = auth.uid()` |
| `app.part_revisions`, `app.sheet_revisions` | owner-only (parent owneron at) | owner-only (parent owneron at) | `app.owns_part_definition(...)` / `app.owns_sheet_definition(...)` |
| `app.geometry_validation_reports` | geometry/project-bound | user write nincs | `app.can_access_geometry_revision(...)` |
| `app.geometry_review_actions` | geometry/project-bound | geometry/project-bound insert | `app.can_access_geometry_revision(...)` |
| `app.geometry_derivatives` | geometry/project-bound | user write nincs | DB-RLS vedett derivative truth |
| `app.technology_presets` | authenticated read-only | user write nincs | authenticated select policy |
| `app.nesting_runs` | project-owner | project-owner | `app.is_project_owner(project_id)` |
| `app.nesting_run_snapshots`, `app.run_queue`, `app.run_logs`, `app.run_artifacts`, `app.run_layout_*`, `app.run_metrics` | run/project-bound read | user write nincs | `app.can_access_run(run_id)` |

Megjegyzes:
- A run/snapshot/output irasi oldal service-role boundary marad.
- A user-oldali run output read-only H0-ban szandekos.

## 5. Storage policy (H0-E6-T1 szerzodesre epitve)

Kanonikus bucket inventory:
- `source-files`
- `geometry-artifacts`
- `run-artifacts`

Path alapelv:
- `projects/{project_id}/...` prefix kotelezo;
- `project_id` csak sajat projektre mutathat authenticated user oldalon.

H0 minimal storage policy matrix (`storage.objects`):
- `source-files`:
  - authenticated select: owner-bound project path
  - authenticated insert: owner-bound project path
- `geometry-artifacts`:
  - authenticated select: owner-bound project path
  - user write nincs (service-role irasi oldal)
- `run-artifacts`:
  - authenticated select: owner-bound project path
  - user write nincs (service-role irasi oldal)
- `anon`: nincs policy

Rollout-megjegyzes:
- A fenti matrix funkcionalisan el a hosted projekten, de nem teljesen a
  `20260314113000` migracio storage szegmensebol, hanem manualis storage policy provisioninggel.
- A policynevek hosted oldalon roviditettek lehetnek (Supabase nevhossz-limit); a dokumentum
  a szabalylogikat tekinti source-of-truthnak.

## 6. Service-role boundary

A service role belso futasi szerepkor:
- queue/log/snapshot/output irasi oldal (`run_queue`, `run_logs`, `run_artifacts`, `run_layout_*`, `run_metrics`);
- geometry/run artifact storage irasi oldal (`geometry-artifacts`, `run-artifacts`).

Authenticated user H0-ban:
- sajat project adatait latja;
- run/snapshot/output vilagban olvasasi hozzaferest kap;
- output vilag irasi oldalat nem kapja meg.

## 7. Fontos modellhatar: `geometry_derivatives`

`app.geometry_derivatives` tovabbra is DB-ben tarolt derivalt truth.
A vedelme DB-RLS policyvel tortenik; nem storage bucket/path policyval.
