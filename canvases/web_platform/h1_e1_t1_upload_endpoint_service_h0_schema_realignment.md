# H1-E1-T1 Upload endpoint/service — H0 schema realignment

## Funkció
A feladat a H1 file ingest első, kötelező belépési pontja:
a meglévő upload endpoint és a kapcsolódó backend service réteg ráigazítása a lezárt H0 source-of-truth modellre.

Ez a task közvetlenül a H0 lezárása után indul.
A cél nem egy teljes geometry pipeline leszállítása, hanem annak biztosítása, hogy a feltöltési csatorna:

- a `app.projects` és `app.file_objects` H0-s táblákra épüljön,
- a H0 storage path policy szerinti `source-files` bucket/prefix világot használja,
- ne a legacy `owner_id` / `project_files` / `users/{user_id}/projects/...` modellre támaszkodjon,
- és tiszta alapot adjon a H1-E1-T2 hash/metadata, majd a H1-E2 geometry import pipeline taskoknak.

## Fejlesztési részletek

### Scope
- Benne van:
  - `api/routes/projects.py` H0 `app.projects` realignment;
  - `api/routes/files.py` H0 `app.file_objects` realignment;
  - a feltöltési path-policy igazítása a H0 storage source-of-truth doksihoz;
  - a DXF upload complete/list/delete flow minimális H0-kompatibilis megtartása;
  - task-specifikus smoke ellenőrzés a H0-s CRUD + upload-url + metadata flow bizonyítására;
  - checklist/report evidence-alapú lezárása.
- Nincs benne:
  - geometry parse / normalize / derivative pipeline;
  - `geometry_revisions`, `geometry_validation_reports` vagy `geometry_derivatives` tényleges bekötése;
  - part/sheet workflow;
  - run snapshot / queue / solver integráció;
  - új domain migráció, ha a H0 schema már elegendő;
  - teljes phase1/phase2 legacy ág kitakarítása a repóból.

### Fő kérdések, amiket le kell zárni
- [ ] A projects route a H0 `app.projects.owner_user_id` + `lifecycle` modellre ül rá?
- [ ] A files route a H0 `app.file_objects` mezőire ír/olvas?
- [ ] A canonical source file storage path a H0 policy szerinti `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}` minta?
- [ ] A backend már nem hivatkozik `project_files`, `owner_id`, `archived_at` vagy `users/{user_id}/projects/...` path logikára az upload flow-ban?
- [ ] A DXF upload flow továbbra is működőképes marad úgy, hogy nem lép át idő előtt a H1-E2 geometry pipeline scope-jába?
- [ ] A task végén a H1-E1-T2 és H1-E2-T1 tiszta, H0-kompatibilis belépési pontra építhet?

### Feladatlista
- [ ] Készüljön el a task artefaktlánca (canvas + YAML + runner + checklist + report).
- [ ] A `projects` route váltson át H0-s mezőkre (`owner_user_id`, `lifecycle`, `updated_at`).
- [ ] A `files` route váltson át H0-s `app.file_objects` metadata modellre.
- [ ] A source upload path és bucket használat kerüljön összhangba a H0 storage path policyvel.
- [ ] A jelenlegi DXF validációs háttérhívás ne maradjon a legacy `project_files` táblához kötve.
- [ ] Készüljön task-specifikus smoke script a H0-aligned upload flow bizonyítására.
- [ ] A checklist és a report DoD → Evidence alapon legyen kitöltve.
- [ ] Repo gate le legyen futtatva a reporton.

### Érintett fájlok
- `canvases/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.yaml`
- `codex/prompts/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment/run.md`
- `codex/codex_checklist/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
- `codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/services/dxf_validation.py`
- `api/config.py`
- `scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py`

### Konkrét igazítási elvek
#### 1. Projects route
A route legalább ezekhez igazodjon:
- `app.projects.owner_user_id` az ownership mező;
- `lifecycle` a státuszmező (`draft`, `active`, `archived`);
- soft-delete/archiválás `lifecycle='archived'` mintán menjen, ne `archived_at` timestampre;
- response modell ne találjon ki nem létező H0-s mezőket.

#### 2. Files route
A route legalább ezekhez igazodjon:
- tábla: `app.file_objects`;
- mezők: `id`, `project_id`, `storage_bucket`, `storage_path`, `file_name`, `mime_type`, `file_kind`, `byte_size`, `sha256`, `uploaded_by`, `created_at`;
- a source DXF-ekhez H0-kompatibilis `file_kind` érték legyen használva (`source_dxf`);
- a complete/list/delete flow ne hivatkozzon `validation_status` / `validation_error` mezőkre a `file_objects` táblában.

#### 3. Storage path policy
A kanonikus source file minta:
- `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}`

A taskban elfogadható minimális megoldás:
- a meglévő config bucket-beállítás H0-kanonikus `source-files` defaultot vegyen fel,
  és a files route ezt használja.

A taskban nem cél:
- teljes multi-bucket config-réteg bevezetése a későbbi run-artifacts/geometry-artifacts világhoz.

#### 4. Validációs háttérhívás
A jelenlegi `dxf_validation.py` legacy `project_files.validation_status` frissítési logikára épül.
Ebben a taskban ezt úgy kell H0-hoz igazítani, hogy:
- ne írjon nem létező oszlopokba;
- ne kényszerítse ki a H1-E2 geometry pipeline előrehozását;
- ha szükséges, minimalis H1-E1-kompatibilis viselkedésre egyszerűsödjön (pl. basic file readability check + log/hiba emelés),
  de ne sértse a H0 truth-ot.

### DoD
- [ ] A `projects` endpointok H0-s `app.projects` mezőkre épülnek.
- [ ] A `files` endpointok H0-s `app.file_objects` mezőkre épülnek.
- [ ] A source upload path a H0 storage policy szerinti `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}` mintát használja.
- [ ] Az upload flow nem használja többé a `project_files` táblát.
- [ ] Az upload flow nem használja többé a `owner_id` vagy `archived_at` mezőlogikát.
- [ ] A DXF validációs háttérhívás nem próbál nem létező legacy oszlopokat frissíteni.
- [ ] Készül task-specifikus smoke script, ami bizonyítja a H0-aligned project + upload flow működését.
- [ ] A checklist és report evidence-alapon ki van töltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md` PASS.

### Kockázat + rollback
- Kockázat:
  - a task félig áll át H0-ra, és vegyesen hagy legacy + H0 mezőket;
  - a file upload flow működése regressziót kap az átnevezett mezők/pathek miatt;
  - a validációs háttérhívás rejtett runtime hibát okoz.
- Mitigáció:
  - route-onként explicit mezőmapping;
  - task-specifikus smoke script;
  - H1-E2 scope korai beemelésének kerülése.
- Rollback:
  - route/config/validation módosítások egy task-commitban visszavonhatók.

## Tesztállapot
- Kötelező gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md`
- Feladat-specifikus ellenőrzés:
  - `/tmp/vrs_api_venv/bin/python scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py`

## Lokalizáció
Nem releváns.

## Kapcsolódások
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `api/routes/projects.py`
- `api/routes/files.py`
- `api/services/dxf_validation.py`
- `scripts/smoke_phase1_api_auth_projects_files_validation.py`
