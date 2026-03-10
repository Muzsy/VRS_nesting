# canvases/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md

# H0-E2-T1 enumok es core schema letrehozasa

## Funkcio
A feladat a web platform H0 core schema implementacios nyitasa: az `app` schema,
a szukseges extensionok, valamint a H0/H1 core enumok elso valodi migracios
csomagjanak letrehozasa.

Ez mar nem docs-only task, hanem tenyleges SQL migration task.
A cel, hogy a H0-E1-T1/T2/T3 soran lezart modulhatar, domain ownership es
snapshot-first szerzodes most valos Supabase/Postgres struktura alapot kapjon.

A task szandekosan szuk scope-u:
- most csak schema + enum + extension alap jon letre,
- tablak, RLS, trigger, bucket policy, worker queue implementacio meg nem.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `supabase/migrations/` fa bevezetese, ha meg nincs;
  - elso H0-E2-T1 migracio letrehozasa;
  - `app` schema letrehozasa;
  - H0/H1 core enum inventory SQL-szintu letrehozasa;
  - az enumok forrasanak osszehangolasa a H0-E1 source-of-truth dokumentumokkal;
  - minimalis docs szinkron, ha a korabbi architecture/H0 SQL-peldak egyszerusitettek
    vagy pontatlanok a vegleges enum-modellhez kepest;
  - checklist + report + verify.
- Nincs benne:
  - domain tablak letrehozasa (`profiles`, `projects`, `project_settings`, stb.);
  - RLS policy;
  - trigger/function a tabelaszintu `updated_at` kezeleshez;
  - storage bucket vagy file policy;
  - queue tabla vagy worker implementacio;
  - Phase 1 legacy SQL bootstrap atirasa.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a canonical enum keszlet, ami tenylegesen kell H0/H1-hez?
- [ ] Hol kell mar most szetvalasztani a run/request/attempt vilagot, es hol eleg
      kesobb tabla-szinten specializalni?
- [ ] Mely enumok maradjanak biztosan H0/H1-ben, es melyek H2/H3 future-only elemek?
- [ ] Hogyan keruljuk el, hogy a korabbi egyszerusitett SQL-pelda felulirja a
      H0-E1-T3 snapshot-first logikat?
- [ ] Hogyan legyen a migracio idempotens/robosztus annyira, hogy fejlesztoi
      kornyezetben ujrafuttatasnal se legyen folosleges torodes?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`.
- [ ] A migracio hozza letre az `app` schema-t es a szukseges alap extensiont.
- [ ] A migracio hozza letre a H0/H1 core enumokat, a H0-E1-T1/T2/T3 doksikkal
      konzisztens modon.
- [ ] A migracio ne hozzon letre meg domain tablakat.
- [ ] A task ne modositja a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- [ ] Minimalis docs szinkron tortenjen, ha a fo architecture/H0 dokumentumokban
      stale vagy leegyszerusitett enum-pelda maradt.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e2_t1_enumok_es_core_schema_letrehozasa.yaml`
- `codex/prompts/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa/run.md`
- `codex/codex_checklist/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
- `codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tartalom a migracioban
- `create extension if not exists ...`
- `create schema if not exists app`
- duplicate-safe enum letrehozas
- H0/H1 core enum inventory legalabb az alabbi domain-vilagokra:
  - project lifecycle
  - revision lifecycle
  - file kind
  - geometry role / validation
  - geometry derivative kind
  - sheet geometry/source/availability jellegu valasztasok
  - run lifecycle olyan bontasban, ami nem mond ellent a snapshot-first dokumentumnak
  - artifact kind
  - placement policy
- schema-qualified tipusnevek (`app.xyz`)
- egyertelmu komment vagy strukturalt blokk, hogy ez a H0-E2-T1 bazismigracio

### Fontos modellezesi elvek
- A H0-E1-T3 miatt ne legyen vakon atemelve a korabbi leegyszerusitett
  `run_status` modell, ha az mar nem eleg a request/snapshot/attempt szemantikahoz.
- A migracio most alapot rak le, nem teljes domain tablakepet.
- H2/H3-only enumokat ne eroltess be, ha azokhoz meg nincs stabil H0/H1 szukseg.
- A `api/sql/phase1_schema.sql` MVP/bootstrap artefakt maradjon erintetlen;
  ez a task a `supabase/migrations/` valodi core-schema iranyt nyitja meg.

### DoD
- [ ] Letrejon a `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
      fajl.
- [ ] A migracio letrehozza az `app` schema-t es a szukseges extension(ok)et.
- [ ] A migracio letrehozza a H0/H1 core enumokat a H0-E1-T1/T2/T3 dokumentumokkal
      osszhangban.
- [ ] A migracio nem hoz letre meg core domain tablakat.
- [ ] A task nem modositja a `api/sql/phase1_schema.sql` fajlt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret migracios irannyal, ha szukseges.
- [ ] A report DoD -> Evidence Matrix konkrét fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
      PASS.

### Kockazat + rollback
- Kockazat:
  - a korabbi architecture/H0 SQL peldak es a mostani valodi migracio eltérhetnek;
  - a Codex scope creep miatt tablakat is bevezetne;
  - a run-status modell tul egyszeru vagy tul bonyolult lesz.
- Mitigacio:
  - H0-E1-T1/T2/T3 legyen az elsosegi input;
  - csak schema + enum scope engedelyezett;
  - stale SQL-peldaknal minimal docs szinkron tortenjen;
  - a report kulon sorolja fel a vegleges enum inventoryt.
- Rollback:
  - a migracio + checklist/report + minimal docs edit egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t1_enumok_es_core_schema_letrehozasa.md`
- Manualis ellenorzes:
  - nincs tabla letrehozas;
  - nincs `api/sql/phase1_schema.sql` modositas;
  - az enum inventory nem mond ellent a snapshot-first dokumentumnak;
  - a migration fajl egyertelmuen a H0-E2-T1 bazis.

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