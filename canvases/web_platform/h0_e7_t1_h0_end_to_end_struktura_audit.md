# H0-E7-T1 H0 end-to-end struktúra audit

## Funkció
A feladat a web platform H0 záró auditja:
annak ellenőrzése, hogy a H0 teljes strukturális célrendszere valóban teljesült-e,
és a H1 tiszta alapra építhető-e.

Ez a task közvetlenül a H0-E6-T2 után következik.
A cél nem újabb feature leszállítása, hanem annak lezárása, hogy:

- a H0 dokumentációs source-of-truth rétegei konzisztensen együtt állnak,
- a H0 migrációs lánc ténylegesen lefedi a vállalt alaprétegeket,
- a H0 task tree végig lett vezetve,
- a security/storage/run/geometry világ között nincs kritikus szerkezeti ellentmondás,
- és a H1 belépési feltételek egyértelműen kimondhatók.

Ez a task tehát **audit gate** a H1 előtt.

## Fejlesztési részletek

### Scope
- Benne van:
  - H0 end-to-end szerkezeti audit a repo tényleges állapota alapján;
  - dedikált H0 lezárási / H1 entry gate dokumentum létrehozása;
  - H0 task completion matrix összeállítása;
  - docs vs migráció vs task tree konzisztenciaellenőrzés;
  - minimális docs-korrekciók, ha maradtak kisebb stale vagy naming jellegű eltérések;
  - záró report és checklist evidence alapon.
- Nincs benne:
  - új feature;
  - új domain tábla vagy migráció, hacsak nem feltétlen technikai javítás kellene a zárhatósághoz;
  - új storage/security modell;
  - H1 feature előkészítés implementációs mélységben;
  - worker/API kód.

### Fő kérdések, amiket le kell zárni
- [ ] A H0 task tree minden H0-s eleme ténylegesen végig lett vezetve?
- [ ] A H0 architecture/source-of-truth doksik és a tényleges migrációk összhangban vannak?
- [ ] Van-e még kritikus naming- vagy scope-ellentmondás a docsban?
- [ ] A run/snapshot/queue/output/security/storage világ egymással konzisztens?
- [ ] Egyértelműen ki lehet-e mondani a H1 entry gate feltételeit?
- [ ] A H0 lezárható-e most, vagy maradt még blokkoló hiány?

### Feladatlista
- [ ] Kész legyen a task teljes artefaktlánca.
- [ ] Készüljön el a dedikált H0 lezárási / H1 entry gate dokumentum.
- [ ] Készüljön el a H0 completion matrix a tényleges taskokkal.
- [ ] Történjen meg a docs vs migráció vs task tree audit.
- [ ] Történjen meg a H0 source-of-truth doksik minimális tisztítása, ha maradt nem blokkoló, de zavaró stale eltérés.
- [ ] A task mondja ki egyértelműen, hogy a H0 lezárható-e.
- [ ] A task mondja ki egyértelműen, hogy a H1 milyen belépési feltételekkel kezdhető meg.
- [ ] Repo gate le legyen futtatva a reporton.

### Érintett fájlok
- `canvases/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e7_t1_h0_end_to_end_struktura_audit.yaml`
- `codex/prompts/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit/run.md`
- `codex/codex_checklist/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md`
- `codex/reports/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md`
- `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`

### Elvárt auditdimenziók
A konkrét fejezetcímek finomíthatók, de legalább ezek legyenek benne:

#### 1. H0 completion matrix
Legalább az alábbi taskok státuszát és bizonyítékát rögzítse:
- H0-E1-T1
- H0-E1-T2
- H0-E1-T3
- H0-E2-T1
- H0-E2-T2
- H0-E2-T3
- H0-E2-T4
- H0-E2-T5
- H0-E3-T1
- H0-E3-T2
- H0-E3-T3
- H0-E3-T4
- H0-E5-T1
- H0-E5-T2
- H0-E5-T3
- H0-E6-T1
- H0-E6-T2

#### 2. Source-of-truth konzisztencia audit
Ellenőrizze legalább:
- `app.*` vs régi `public.*` maradványok állapotát;
- Run Request / Run Snapshot / Queue / Output naming konzisztenciát;
- projection vs artifact szétválasztást;
- geometry derivative vs storage-truth szétválasztást;
- technology/project/part/sheet ownership logika konzisztenciáját.

#### 3. Migrációs lefedettségi audit
Ellenőrizze, hogy a H0-s migrációk ténylegesen lefedik-e:
- core schema és enumok,
- core domain táblák,
- file/geometry/validation/review/derivative réteget,
- run/snapshot/queue/log/output réteget,
- security/RLS alapokat.

#### 4. Security/storage audit
Ellenőrizze, hogy a H0-E6-T1 és H0-E6-T2 együtt koherens-e:
- bucket inventory,
- path policy,
- storage.objects policy,
- service-role boundary,
- DB-truth vs storage-truth határok.

#### 5. H1 entry gate
A dokumentum mondja ki:
- mi tekinthető H0 structural PASS-nak,
- milyen advisory pontok maradhatnak még,
- és milyen feltételekkel indulhat a H1.

### Elvárt kimenet a dedikált H0 gate doksiban
A `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md` dokumentum legalább ezt tartalmazza:

1. **Cél és használat**
   - miért készült a dokumentum,
   - mire szolgál a H1 előtt.

2. **H0 lezárási kritériumok**
   - strukturális,
   - dokumentációs,
   - migrációs,
   - security/storage,
   - naming/konzisztencia.

3. **H0 completion matrix**
   - taskonként PASS / SOFT PASS / FAIL formában.

4. **Blokkoló vs advisory eltérések**
   - csak a ténylegesen maradt eltérések.

5. **H1 entry gate ítélet**
   - `PASS`, `PASS WITH ADVISORIES` vagy `FAIL`.

6. **Mit jelent ez a gyakorlatban?**
   - a H1 milyen tiszta alapra épülhet,
   - milyen dolgokat nem kell már H0-ban újranyitni,
   - milyen advisory pontokat kell H1 során fejben tartani.

### Fontos modellezési elvek
- Ez audit task, nem feature-task.
- A task célja a H0 lezárhatóságának bizonyítása vagy őszinte megcáfolása.
- Ha kritikus ellentmondás maradt, azt ki kell mondani, nem szabad „PASS”-ra szépíteni.
- A kisebb, nem blokkoló eltérések advisory kategóriában maradhatnak.
- A H1 csak akkor nyílhat meg, ha a H0 strukturális PASS vagy PASS WITH ADVISORIES.

### DoD
- [ ] Letrejön a `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md` fájl.
- [ ] A dokumentum tartalmaz H0 completion matrixot.
- [ ] A dokumentum tartalmaz blokkoló vs advisory bontást.
- [ ] A dokumentum egyértelmű H1 entry gate ítéletet ad.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`,
      a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      és a `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
      minimálisan szinkronba kerül a H0 lezárási állapottal.
- [ ] A task nem hoz létre új feature-t.
- [ ] A task nem hoz létre új domain migrációt, hacsak nem kritikus, közvetlen zárási ok lenne.
- [ ] A report DoD -> Evidence Matrix konkrét fájl- és line-hivatkozásokkal kitöltött.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task túl puhán auditál, és valójában nem mondja ki a még meglévő hibákat;
  - a task túl szélesen kezd docs-refaktort, és elveszti a H0 záró fókuszt;
  - a H0 lezárás kimondása bizonyíték nélkül történik.
- Mitigáció:
  - evidence-alapú completion matrix;
  - blokkoló vs advisory explicit szétválasztás;
  - csak minimális docs-tisztítás, ahol szükséges;
  - H1 gate verdict explicit formában.
- Rollback:
  - docs + checklist/report egy commitban visszavonható.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md`
- Manuális ellenőrzés:
  - a H0 completion matrix ténylegesen a repo állapotára épül;
  - a gate verdict nincs alátámasztatlanul kimondva;
  - a maradék eltérések blokkoló/advisory bontásban jelennek meg;
  - nincs új feature vagy fölösleges migráció.

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/h0_security_rls_alapok.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
