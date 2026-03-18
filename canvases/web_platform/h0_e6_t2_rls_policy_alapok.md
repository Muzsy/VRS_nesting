# H0-E6-T2 RLS policy alapok

## Funkcio
A feladat a web platform H0 security/storage blokkjanak masodik, implementacios lepese:
alap RLS es minimal storage access policy bevezetese.

Ez a task kozvetlenul a H0-E6-T1 utan kovetkezik.
A cel, hogy a mar meglevo schema ne legyen teljesen nyitott, hanem H0 szinten mar
ervenyesuljenek a legalapvetobb ownership- es project-bound hozzaferesi szabalyok.

A task egyszerre ket reteget kezel:
- `app.*` uzleti tablavilag RLS-e,
- `storage.objects` policy a H0 kanonikus bucket inventoryhoz.

Fontos modell-dontes ehhez a taskhoz:
- ez **migracios task**;
- most mar jon letre RLS policy migracio;
- a service-role boundary dokumentalva legyen, de a worker implementacio most sincs scope-ban;
- storage bucket provisioning most sem scope;
- a `geometry_derivatives` vedelme tovabbra is DB-RLS alapu, nem storage bucket/path alapu.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio az alap RLS policykkal az `app.*` tablavilagra;
  - helper SQL fuggvenyek/nezopontok, ha kellenek a policyk attekintheto megfogalmazasahoz;
  - `storage.objects` minimal policy a H0 bucket/path szerzodeshez;
  - dedikalt security/RLS source-of-truth dokumentum letrehozasa;
  - minimal docs szinkron a fo architecture es H0 roadmap dokumentumokban.
- Nincs benne:
  - auth auto-provisioning trigger;
  - teljes membership/collaboration modell;
  - worker vagy API implementacio;
  - signed URL/upload endpoint;
  - bucket provisioning script;
  - H1-es policy-tesztek teljes csomagja.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a minimalis, de mar biztonsagos H0 RLS matrix tablankent?
- [ ] Mely tablakat irhatja a user, es melyek legyenek csak olvashatok user oldalrol?
- [ ] Hogyan legyen egyszeru, de jol olvashato a project-owner alap logika a policykban?
- [ ] Hogyan kezeljuk az owner-alapu `part_*` / `sheet_*` definicio-vilagot?
- [ ] Hogyan legyen a `technology_presets` H0-ban authenticated read-only?
- [ ] Hogyan legyen a `storage.objects` policy osszhangban a H0-E6-T1 bucket/path szerzodessel?
- [ ] Hogyan mondjuk ki egyertelmuen a service-role boundaryt anelkul, hogy worker kodot irnank?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0 migracio az alap RLS policykkal.
- [ ] A migracio kapcsolja be a RLS-t a fo `app.*` uzleti tablavilagon.
- [ ] A migracio ne adjon uzleti tabla-hozzaferest `anon` role-nak.
- [ ] `app.profiles` self-row policy alatt alljon.
- [ ] `app.projects` owner-only policy alatt alljon.
- [ ] A projekthez kotott child tablavilag project-owner policy alatt alljon.
- [ ] A `part_definitions` / `sheet_definitions` es revisionjeik owner-only policy alatt alljanak.
- [ ] A `technology_presets` H0-ban authenticated read-only legyen.
- [ ] A `nesting_runs` user-oldalon owner-controlled legyen, de a snapshot/output tablavilag user-oldalon read-only maradjon.
- [ ] A `run_queue`, `run_logs`, `run_artifacts`, `run_layout_*`, `run_metrics` tablavilag user-oldalon read-only legyen.
- [ ] Minimal `storage.objects` policy jojjon letre a kanonikus bucket inventoryhoz.
- [ ] Dedikalt security/RLS source-of-truth dokumentum keszuljon.
- [ ] Minimal docs szinkron tortenjen a fo architecture es H0 roadmap iranyba.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e6_t2_rls_policy_alapok.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t2_rls_policy_alapok.yaml`
- `codex/prompts/web_platform/h0_e6_t2_rls_policy_alapok/run.md`
- `codex/codex_checklist/web_platform/h0_e6_t2_rls_policy_alapok.md`
- `codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `docs/web_platform/architecture/h0_security_rls_alapok.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart policy irany
A konkret policy-nevek es helper fuggvenyek finomithatok, de az irany ez legyen:

#### 1. Helper fuggvenyek / alap policy building blockok
A migracio szabadon hozhat letre par kicsi, attekintheto helper fuggvenyt, peldaul:
- `app.current_user_id()`
- `app.is_project_owner(project_uuid uuid)`
- `app.owns_part_definition(part_definition_uuid uuid)`
- `app.owns_sheet_definition(sheet_definition_uuid uuid)`
- `app.can_access_geometry_revision(geometry_revision_uuid uuid)`
- `app.can_access_run(run_uuid uuid)`
- opcionálisan `app.storage_object_project_id(object_name text)`

A helperek celja:
- a policyk olvashatobbak legyenek,
- ne legyen tul sok beagyazott `exists (...)` copy-paste.

#### 2. `app.profiles`
- `authenticated` user csak a sajat profil sorat olvashassa/irhassa;
- ha kell insert policy, csak `id = auth.uid()` iranyban engedjen.

#### 3. `app.projects` es direkt project child tablák
Legalabb ezek project-owner vedelmet kapjanak:
- `app.projects`
- `app.project_settings`
- `app.project_technology_setups`
- `app.project_part_requirements`
- `app.project_sheet_inputs`
- `app.file_objects`
- `app.geometry_revisions`
- `app.nesting_runs`

Policy irany:
- project owner olvashat;
- project owner irhat ott, ahol user-oldali iras ertelmes;
- `anon` ne lasson semmit.

#### 4. Owner-alapu definition/revision vilag
Legalabb ezek kapjanak owner-only policy-t:
- `app.part_definitions`
- `app.part_revisions`
- `app.sheet_definitions`
- `app.sheet_revisions`

Policy irany:
- definicio tulajdonosa olvashat/irhat;
- revision policy parent owneren keresztul menjen.

#### 5. Geometry audit / derivative vilag
Legalabb ezek kapjanak geometry/project alapu policy-t:
- `app.geometry_validation_reports`
- `app.geometry_review_actions`
- `app.geometry_derivatives`

Policy irany:
- user csak olyan geometry-hez kapcsolodo audit/derivative adatot lasson,
  amely egy altala birtokolt projekthez kotodik.

#### 6. Run snapshot + output vilag
Legalabb ezek kapjanak run/project alapu policy-t:
- `app.nesting_run_snapshots`
- `app.run_queue`
- `app.run_logs`
- `app.run_artifacts`
- `app.run_layout_sheets`
- `app.run_layout_placements`
- `app.run_layout_unplaced`
- `app.run_metrics`

Policy irany:
- a user ezeket csak akkor olvashassa, ha a kapcsolodo `run_id` egy sajat projekthez tartozik;
- H0-ban ezek user-oldalon read-only legyenek;
- service-role path dokumentalva legyen mint az irasi oldal.

#### 7. `app.technology_presets`
- H0-ban `authenticated` read-only;
- user-oldali insert/update/delete most ne legyen nyitva.

#### 8. `storage.objects` minimal policy
A H0-E6-T1 bucket/path szerzodesre epitve vezess be minimal policyt legalabb a kanonikus bucket inventoryra:
- `source-files`
- `geometry-artifacts`
- `run-artifacts`

Elvart irany:
- `anon` ne kapjon hozzaferest;
- authenticated user csak olyan objektumot olvashasson, amelynek pathja
  `projects/{project_id}/...` mintara illeszkedik, es a `project_id` sajat projekt;
- `source-files` esetben H0-ban megengedheto a sajat projekt-pathra iras is;
- `geometry-artifacts` es `run-artifacts` user-oldalon legalabb read-only maradjon,
  az irasi oldal service-role path.

#### 9. Service-role boundary
A dedikalt docs mondja ki egyertelmuen:
- service role bypass/belso futasi szerep hasznalhato a worker/output irasi oldalon;
- user-oldalon H0-ban a snapshot/output tablavilag read-only;
- az upload/export endpoint implementacio tovabbra is kulon task.

### Fontos modellezesi elvek
- `anon` ne lasson uzleti adatot.
- `authenticated` user csak sajat project- es owner-bound adatot lasson.
- A `technology_presets` H0-ban authenticated read-only.
- A `nesting_runs` user-oldalon owner-controlled lehet.
- A `nesting_run_snapshots` es output tablavilag user-oldalon read-only.
- A `run_queue` / `run_logs` / `run_artifacts` / `run_layout_*` / `run_metrics`
  irasi oldala service-role boundary marad.
- A `geometry_derivatives` tovabbra is DB-truth; storage policy ne ezt probalja vedeni.
- A storage policy a H0-E6-T1 bucket/path szerzodesre epuljon.
- Ez a task nem auth auto-provisioning task.
- Ez a task nem worker implementacios task.

### DoD
- [ ] Letrejon a `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql` fajl.
- [ ] A migracio bekapcsolja a RLS-t a fo `app.*` tablavilagon.
- [ ] `anon` nem kap uzleti tabla-hozzaferest.
- [ ] `app.profiles` self-row policy alatt all.
- [ ] `app.projects` owner-only policy alatt all.
- [ ] A projekthez kotott child tablavilag project-owner policy alatt all.
- [ ] A `part_*` / `sheet_*` definicio es revision vilag owner-only policy alatt all.
- [ ] A `geometry_validation_reports`, `geometry_review_actions`, `geometry_derivatives`
      geometry/project alapu policy alatt allnak.
- [ ] A `nesting_run_snapshots` es output tablavilag run/project alapu read-only policy alatt all user oldalrol.
- [ ] A `technology_presets` authenticated read-only.
- [ ] Minimal `storage.objects` policy letrejon a kanonikus bucket inventoryra.
- [ ] Letrejon a `docs/web_platform/architecture/h0_security_rls_alapok.md` fajl.
- [ ] A docs egyertelmuen leirja a service-role boundaryt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret H0-E6-T2 irannyal.
- [ ] A task nem vezet be auth auto-provisioning triggert.
- [ ] A task nem vezet be worker vagy API implementaciot.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a policyk tul szelesek maradnak, es valojaban nem vedik a project-bound adatot;
  - a policyk tul szigoruak lesznek, es a normal user-flow is megtorik;
  - a storage policy elter a H0-E6-T1 path szerzodestol;
  - a worker/output tablavilag user-oldalon irhatova valik veletlenul.
- Mitigacio:
  - helper fuggvenyekkel attekintheto policyk;
  - user-oldali iras csak ott, ahol H0-ban tenyleg kell;
  - snapshot/output tablavilag user-oldalon read-only;
  - storage policy explicit a `projects/{project_id}/...` prefixre epul.
- Rollback:
  - a migracio + security docs + checklist/report egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md`
- Manualis ellenorzes:
  - nincs `anon` uzleti tabla-hozzaferes;
  - owner csak sajat projectet latja;
  - project child tablavilag owner-bound;
  - `technology_presets` authenticated read-only;
  - snapshot/output tablavilag user-oldalon read-only;
  - `storage.objects` policy a kanonikus bucket inventoryra epul;
  - nincs auto-provisioning trigger;
  - nincs worker/API implementacio.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
