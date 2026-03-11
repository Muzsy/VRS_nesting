# canvases/web_platform/h0_e2_t3_technology_domain_alapok.md

# H0-E2-T3 technology domain alapok

## Funkcio
A feladat a web platform technology domainjenek elso tenyleges schema-szintu
letetele. A cel, hogy a projekt-gerinc ala bekeruljenek azok az alap entitasok,
amelyek a kesobbi geometry, validation, nesting es manufacturing folyamatokhoz
szukseges technologiai kontextust adjak, de meg mindig szuk, kontrollalt scope-ban.

Ez a task kozvetlenul a H0-E2-T2 `profiles/projects/project_settings` migracio utan
kovetkezik. Most mar van platform identity + project root, es erre lehet raepiteni
a projekt technologiai konfiguracios vilagat.

A task szandekosan meg mindig H0-bazis:
- nincs meg part/file/revision tabla,
- nincs run request/snapshot/attempt tabla,
- nincs manufacturing recipe teljes kibontasa,
- nincs RLS veglegesites.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - uj Supabase migracio letrehozasa a technology domain alap tablaival;
  - technology-szintu katalogus/alapbeallitas tabla(k) letetele;
  - projekthez rendelt technology profile / technology setup tabla letetele;
  - minimalis kapcsolatok a mar meglevo `app.projects` strukturahoz;
  - enum- es ownership-konzekvenciak ervenyesitese a H0-E1 dokumentumokkal
    osszhangban;
  - alap indexek es egyertelmu FK kapcsolatok;
  - minimal docs szinkron, ha a fo architecture/H0 doksikban a technology vilag
    meg stale vagy leegyszerusitett.
- Nincs benne:
  - part definition / part demand tabla;
  - uploaded file metadata tabla;
  - DXF/geometry/revision pipeline tabla;
  - run request / run snapshot / run attempt tabla;
  - remnant vagy stock inventory tabla;
  - export/manufacturing package tabla;
  - RLS policy;
  - API endpoint implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a technology domain legkisebb, de mar hasznalhato tablakeszlete?
- [ ] Mi a kulonbseg a global/szabvanyos technology catalog es a projekt-szintu
      technology setup/profile kozott?
- [ ] Mi kerul dedikalt oszlopba, es mi maradhat JSONB-ben?
- [ ] Hogyan modellaljuk a gep / anyag / vastagsag / spacing / margin / kerf
      kapcsolatot ugy, hogy a kesobbi szabalyalapu validacio es snapshot-build
      tamogathato legyen?
- [ ] Mi legyen H0-ban canonical truth, es mi maradjon kesobbi derivalt vilag?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a kovetkezo H0-E2 migracio a technology domain alapokhoz.
- [ ] A migracio hozzon letre legalabb egy technology catalog/sablon vilagot,
      es egy projekt-szintu technology setup/profile vilagot.
- [ ] A technology profile kapcsolodjon az `app.projects` tablaho.
- [ ] A technology domain ne csusszon at file/revision/run/manufacturing package
      iranyba.
- [ ] Az oszlopkeszlet legyen eleg konkret a kesobbi H0/H1 taskokhoz, de ne legyen
      future-scope tultolt.
- [ ] Minimal docs szinkron tortenjen, ha szukseges.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e2_t3_technology_domain_alapok.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t3_technology_domain_alapok.yaml`
- `codex/prompts/web_platform/h0_e2_t3_technology_domain_alapok/run.md`
- `codex/codex_checklist/web_platform/h0_e2_t3_technology_domain_alapok.md`
- `codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Javasolt modell
A task H0-bazis szinten ketretegu technology vilagot vezessen be:

1. **Technology Catalog / Recipe Preset**
   - olyan tabla, ami szabvanyosithato technology preseteket tarol
   - celja: gep + anyag + vastagsag + alap vagasi parameterek katalogusa
   - nem projekt-fuggő truth, hanem ujrafelhasznalhato sablonvilag

2. **Project Technology Setup**
   - projekthez tartozo aktiv technologiai konfiguracio
   - lehet sajat, projekt-specifikus override/pelda
   - kesobb innen tud epulni a validation es a run snapshot technology resze

### Elvart tabla-irany
A konkret nevek kod kozben finomithatok, de az irany ez legyen:

- `app.technology_presets`
  - reusable technology preset katalogus
  - gep/osztaly, anyag, vastagsag, kerf, spacing, margin, egyeb alap parameterek
  - opcionális `is_active`, `notes`
- `app.project_technology_setups`
  - `project_id` FK `app.projects(id)`
  - opcionális `preset_id` FK `app.technology_presets(id)`
  - projekt-szintu aktiv konfiguracio / override
  - spacing, margin, kerf, machine/code, material/code, thickness
  - egy projektnek lehessen legalabb egy aktiv setupja, de a kesobbi verziozas
    erdekeben ne zard le teljesen a tobb setup lehetoseget
  - lifecycle / is_default / display_name jellegu minimalis mezok, ha indokolt

### Fontos modellezesi elvek
- A technology preset es a projekt technology setup kulon vilag.
- Ne keverd a "catalog truth" es a "project-bound truth" reteget.
- A technology setup meg nem snapshot, hanem elo konfiguracios adat.
- A kesobbi run snapshot ezt masolja majd immutable futasi inputta.
- A task ne probalja most meg a teljes kerf-szabaly vagy manufacturing-rule engine-t
  bevezetni; csak a domain alapokat rakja le.
- Az `app` schema maradjon canonical celterulet.

### DoD
- [ ] Letrejon a `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
      fajl.
- [ ] A migracio letrehoz egy reusable technology catalog/preset tablavilagot.
- [ ] A migracio letrehoz egy projekt-szintu technology setup/profile tablavilagot.
- [ ] A technology setup megfelelo FK-val kapcsolodik az `app.projects` tablaho.
- [ ] A migracio nem hoz letre file/revision/run/remnant/export domain tablakat.
- [ ] A task nem ad hozza RLS policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a task tul sok future-scope technology szabalylogikat probalna bevinni;
  - a preset es a project-bound setup osszemosodik;
  - a technology setup tulsagosan JSON dump lesz;
  - manufacturing vagy run-domain mezok belecsusznak a schema-ba.
- Mitigacio:
  - kulon tabla a catalog es kulon tabla a project-bound setup vilagnak;
  - csak a H0/H1-hez szukseges alapmezok legyenek dedikaltan;
  - run/snapshot/manufacturing package explicit out-of-scope;
  - a report kulon sorolja fel a vegleges oszlopkeszletet es a kihagyott future-scope
    elemeket.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md`
- Manualis ellenorzes:
  - csak a technology catalog es project technology setup vilag jon letre;
  - nincs part/file/revision/run/remnant/export tabla;
  - a project FK kapcsolat helyes;
  - a modellezes nem keveri a setupot a snapshot vilaggal.

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
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`