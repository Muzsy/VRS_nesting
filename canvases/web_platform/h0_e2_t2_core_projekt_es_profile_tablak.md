# canvases/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md

# H0-E2-T2 core projekt- es profile tablak

## Funkcio
A feladat a H0 core schema kovetkezo implementacios lepese:
a `profiles`, `projects` es `project_settings` tablak tenyleges letrehozasa
Supabase/Postgres oldalon, az elozo H0-E1-T1/T2/T3 dokumentumokkal es a
H0-E2-T1 enum baseline-nal osszhangban.

Ez a task mar tenyleges schema-implementacio.
A cel, hogy a platform identitas- es projekt-gerince valos adatmodell formajaban is
letezzen, de a scope tovabbra is szuk maradjon:
- nincs meg geometry/revision domain,
- nincs run orchestration tabla,
- nincs RLS veglegesites,
- nincs auth trigger/provisioning workflow.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa a `profiles`, `projects`, `project_settings`
    tablakhoz;
  - a tablak oszlopainak, PK/FK kapcsolatainak es alap indexeinek rogzitese;
  - a H0-E1 domain ownership elveknek megfelelo aggregate-hatar letetele:
    `projects` a projektvilag root-ja, `project_settings` 1:1 child;
  - `profiles.id -> auth.users(id)` kapcsolat;
  - `projects.owner_user_id -> app.profiles(id)` kapcsolat;
  - `project_settings.project_id -> app.projects(id)` kapcsolat;
  - minimalis timestamp-strategia (`created_at`, `updated_at`) es ha szukseges,
    kozos helper function/trigger mintazat bevezetese;
  - minimal docs szinkron, ha a fo architektura/H0 doksikban a konkret tabla-irany
    stale vagy public/app schema szempontbol pontatlan.
- Nincs benne:
  - RLS policy;
  - auth signup/profile auto-provision trigger;
  - project membership / team tabla;
  - technology domain tablak;
  - file / revision / geometry tablak;
  - run request / snapshot / attempt tablak;
  - storage bucket policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi a minimalis, de elegseges oszlopkeszlet a `profiles` tablaban?
- [ ] Mi a minimalis, de elegseges oszlopkeszlet a `projects` tablaban?
- [ ] Mi kerul `project_settings` ala, es mi nem?
- [ ] Mi maradjon JSONB, es mi legyen konkret oszlop?
- [ ] Kell-e mar most `updated_at` helper function/trigger, vagy eleg pusztan
      timestamp oszlopokat lerakni?
- [ ] Hogyan legyenek az alap indexek, hogy a tulajdonosi szures es a projekt lookup
      kesobb ne legyen attervezesre szorulo?
- [ ] Hogyan tartsuk a scope-ot annyira szuken, hogy ez tenyleg csak a projektvilag
      bazisa legyen?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a masodik H0-E2 migracio a core projekt- es profile tablakkal.
- [ ] A migracio letrehozza az `app.profiles` tablata.
- [ ] A migracio letrehozza az `app.projects` tablata.
- [ ] A migracio letrehozza az `app.project_settings` tablata.
- [ ] PK/FK kapcsolatok es alap indexek helyesen legyenek beallitva.
- [ ] A task ne hozzon letre meg technology/file/revision/run domain tablat.
- [ ] RLS es auth auto-provisioning ne keruljon bele.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t2_core_projekt_es_profile_tablak.yaml`
- `codex/prompts/web_platform/h0_e2_t2_core_projekt_es_profile_tablak/run.md`
- `codex/codex_checklist/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
- `codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tartalom a migracioban
- `app.profiles`
  - `id uuid primary key references auth.users(id) ...`
  - felhasznaloi alapmeta legalabb minimalis szinten
  - `created_at`, `updated_at`
- `app.projects`
  - `id uuid primary key default gen_random_uuid()`
  - `owner_user_id uuid not null references app.profiles(id)`
  - `name`
  - `description` opcionális
  - `lifecycle app.project_lifecycle`
  - `created_at`, `updated_at`
- `app.project_settings`
  - `project_id uuid primary key references app.projects(id) on delete cascade`
  - minimalis projekt-szintu konfiguracios mezok
  - `created_at`, `updated_at`
- alap indexek legalabb:
  - `projects(owner_user_id)`
  - ha indokolt: `projects(lifecycle)`
- ha triggeres `updated_at` helper kerul be, az scope-on belul maradjon,
  es csak erre a 3 tablára vonatkozzon
- semmi mas domain tabla ne jojjon letre

### Fontos modellezesi elvek
- `profiles` az auth userhez kapcsolt platform-szintu profil, nem team/member modell.
- `projects` az aggregate root.
- `project_settings` 1:1 kiterjesztes, nem altalanos JSON dump.
- Ne keruljon ebbe a taskba technology profile, file metadata, geometry, snapshot,
  run vagy artifact tabla.
- A `project_settings` csak olyan alapbeallitasokat kapjon, amelyek valoban a
  projekt-gerinchez tartoznak; a technology kivalasztas kulon task.
- Az `app` schema legyen a canonical celterulet, ne `public`.

### DoD
- [ ] Letrejon a `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
      fajl.
- [ ] A migracio letrehozza az `app.profiles`, `app.projects`, `app.project_settings`
      tablakat.
- [ ] A PK/FK kapcsolatok osszhangban vannak a H0-E1 domain es ownership doksikkal.
- [ ] A migracio nem hoz letre technology/file/revision/run domain tablakat.
- [ ] A task nem ad hozza RLS policyt es nem vezet be auth auto-provisioning logikat.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - scope creep: belecsuszik team/membership vagy auth provisioning logika;
  - a `project_settings` tul sok, ide nem tartozo mezot kap;
  - a fo architektura doksi tovabbra is `public.*` tablakat sugallna a mar `app.*`
    alapra epulo migracio utan;
  - a `profiles` tabla tul sovany vagy tul nehez lesz.
- Mitigacio:
  - csak a 3 tabla johet letre;
  - technology es run vilag explicit out-of-scope;
  - minimal docs sync a `public` vs `app` schema egyertelmusitesere;
  - a report kulon sorolja fel a vegleges oszlopkeszletet.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md`
- Manualis ellenorzes:
  - pontosan csak a 3 tabla jon letre;
  - a fuggosegek a megfelelo sorrendben vannak;
  - nincs RLS;
  - nincs provisioning trigger;
  - nincs technology/file/run/revision tabla.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`