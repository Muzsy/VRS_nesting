# H0-E6-T1 storage bucket strategia es path policy

## Funkcio
A feladat a web platform H0 security/storage blokkjanak elso, docs-first lepese:
a kanonikus bucket inventory es path naming policy formalizalasa.

Ez a task kozvetlenul a H0-E5-T3 utan kovetkezik.
A cel, hogy a mar meglevo `storage_bucket` / `storage_path` mezok ne csak
szabad szoveges helyek legyenek, hanem legyen mogottuk egy egyertelmu,
source-of-truth tarolasi szerzodes.

Kulonosen most kell kimondani:

- mely bucketek kanonikusak H0-ban,
- melyik bucketet melyik tabla / entitas hasznalhatja,
- hogyan nez ki a path naming minta,
- mi immutable es mi nem,
- es hogyan marad kulon a storage vilag a DB-truth derivalt retegektol.

Fontos modell-dontes ehhez a taskhoz:
- ez **docs-only task**;
- most **nem** jon letre Supabase migracio;
- most **nem** jon letre storage provisioning script;
- most **nem** jon letre RLS policy;
- most a source-of-truth bucket + path policy dokumentalasa a cel.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - dedikalt storage source-of-truth dokumentum letrehozasa;
  - bucket inventory formalizalasa H0 szinten;
  - entitas -> bucket mapping formalizalasa;
  - path naming policy formalizalasa;
  - immutable / mutabilis tarolasi szabalyok formalizalasa;
  - minimal docs szinkron a fo architecture es H0 roadmap dokumentumokban.
- Nincs benne:
  - uj tabla vagy migracio;
  - valos bucket create/provisioning;
  - Supabase Storage policy implementacio;
  - RLS policy;
  - upload endpoint vagy artifact export implementacio.

### Fo kerdesek, amiket le kell zarni
- [ ] Mi legyen a kanonikus H0 bucket inventory?
- [ ] Melyik bucketet melyik tabla/entitas hasznalhatja?
- [ ] Hogyan nezzen ki a projekt-, file-, geometry- es run-alapu path naming?
- [ ] Mit jelent az immutabilitas a storage path szintjen?
- [ ] Hogyan legyen explicit, hogy a `geometry_derivatives` nem bucket/path truth?
- [ ] Hogyan keszitjuk elo a H0-E6-T2 RLS taskot anelkul, hogy azt most mar ide behuznank?

### Feladatlista
- [ ] Kesz legyen a task teljes artefaktlanca.
- [ ] Letrejojjon a dedikalt storage source-of-truth dokumentum.
- [ ] A dokumentum rogzitese a kanonikus H0 bucket inventoryt.
- [ ] A dokumentum rogzitese az entitas -> bucket mappinget.
- [ ] A dokumentum rogzitese a path naming policy-t.
- [ ] A dokumentum kimondja, hogy a `geometry_derivatives` DB-truth, nem storage-truth.
- [ ] A dokumentum elokesziti a kesobbi RLS/storage policy taskot, de nem implementalja.
- [ ] Minimal docs szinkron tortenjen a fo architecture es H0 roadmap iranyba.
- [ ] Repo gate le legyen futtatva a reporton.

### Erintett fajlok
- `canvases/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- `codex/goals/canvases/web_platform/fill_canvas_h0_e6_t1_storage_bucket_strategia_es_path_policy.yaml`
- `codex/prompts/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy/run.md`
- `codex/codex_checklist/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- `codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

### Elvart tartalmi irany a dedikalt storage doksiban
A konkret fejezetcimek finomithatok, de legalabb ezek legyenek benne:

1. **Cel es scope**
   - miert kell kulon storage source-of-truth;
   - mely tablakat/entitasokat erinti most a policy.

2. **Kanonikus H0 bucket inventory**
   - `source-files`
   - `geometry-artifacts`
   - `run-artifacts`

3. **Entitas -> bucket mapping**
   - `app.file_objects`
     - alapertelmezett bucket: `source-files`
   - `app.run_artifacts`
     - alapertelmezett bucket: `run-artifacts`
   - `geometry-artifacts`
     - reserved/canonical bucket jovobeli file-backed geometry/viewer/manufacturing artifactokhoz
   - expliciten mondd ki:
     - `app.geometry_derivatives` nem bucket/path alapu truth

4. **Path naming policy**
   - projekt-prefix kotelezo legyen;
   - bucketenkent legalabb egy kanonikus path minta legyen;
   - a stabil identity ne az eredeti fajlnev legyen;
   - hash/verzio/run/file/revision alap ott hasznalando, ahol ertelmes;
   - path mintak legyenek lower-case / slash-separated / migralhato szerkezetuek.

5. **Javasolt path mintak**
   Legalabb ilyen iranyban:

   - `source-files`
     - `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}`
     - vagy ennek hash-alapu valtozata, ha a doksiban jobban indokolt

   - `geometry-artifacts`
     - `projects/{project_id}/geometry/{geometry_revision_id}/{artifact_kind}/{content_hash}.{ext}`
     - de itt mondd ki, hogy ez a jovobeli file-backed geometry artifactokra vonatkozik,
       nem a `geometry_derivatives` tabla tartalmara

   - `run-artifacts`
     - `projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`

6. **Immutabilitas es overwrite szabalyok**
   - generalt artifactot ne overwrite-oljunk in-place, ahol hash/verzio adheto;
   - source uploadnal is a stable identity ne pusztan a fajlnev legyen;
   - a path naming keszuljon audit/migracio-baratra.

7. **Environment es ownership elvek**
   - az environment szeparacio ne bucket-nev-hack legyen,
     hanem deployment/supabase project szeparacio;
   - a project ownership legyen a kesobbi RLS/storage policy alapja.

8. **Kovetkezo taskhoz valo kapcsolat**
   - H0-E6-T2 majd erre epitve hozza a hozzaferes-vedelmi szabalyokat.

### Fontos modellezesi elvek
- A `file_objects` storage-reference truth.
- A `run_artifacts` file/blob output truth.
- A `geometry_derivatives` tovabbra is DB-ben tarolt derivalt truth,
  nem storage bucket-path alap entitas.
- A `geometry-artifacts` bucket reserved/canonical hely jovobeli file-backed geometry artifactokhoz.
- A bucket-nevek stabilak legyenek es ne feature-onkent novekedjenek kontroll nelkul.
- Ez a task nem storage provisioning task.
- Ez a task nem RLS task.
- Ez a task nem upload/export implementacios task.

### DoD
- [ ] Letrejon a `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md` fajl.
- [ ] A dokumentum rogzitese a kanonikus H0 bucket inventoryt.
- [ ] A dokumentum rogzitese az entitas -> bucket mappinget.
- [ ] A dokumentum rogzitese legalabb egy kanonikus path mintat minden H0 buckethez.
- [ ] A dokumentum explicit kimondja, hogy az `app.geometry_derivatives` nem storage-truth.
- [ ] A dokumentum rogzitese az immutabilitas / overwrite alapelveket.
- [ ] A dokumentum elokesziti a H0-E6-T2 RLS/storage policy taskot, de nem implemental policyt.
- [ ] A `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
      es a `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
      minimalisan szinkronba kerul a konkret H0-E6-T1 irannyal.
- [ ] A task nem hoz letre migraciot.
- [ ] A task nem hoz letre storage provisioning scriptet.
- [ ] A task nem hoz letre RLS policyt.
- [ ] A report DoD -> Evidence Matrix konkret fajl- es line-hivatkozasokkal kitoltott.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task osszemossa a DB-truth derivative reteget a storage artifact reteggel;
  - bucket inventory tul sok vagy tul keves bucketre esik szet;
  - a path policy tul laza marad es nem lesz kesobb enforce-olhato;
  - a task belecsuszik storage provisioning vagy RLS implementacios iranyba.
- Mitigacio:
  - kulon source-of-truth storage dokumentum;
  - explicit mapping `file_objects` vs `run_artifacts` vs reserved geometry-artifacts;
  - explicit mondat a `geometry_derivatives` nem-storage szereperol;
  - provisioning/RLS explicit out-of-scope.
- Rollback:
  - a docs + checklist/report egy commitban visszavonhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md`
- Manualis ellenorzes:
  - van dedikalt storage source-of-truth doksi;
  - benne van a 3 bucketes H0 inventory;
  - benne van az entitas -> bucket mapping;
  - benne vannak a kanonikus path mintak;
  - explicit, hogy `geometry_derivatives` nem storage-truth;
  - nincs migracio;
  - nincs RLS policy;
  - nincs provisioning script.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
