# H1-E4-T1 Run snapshot builder (H1 minimum)

## Funkcio
A feladat a H1-E4 run orchestration elso lepese: egy explicit snapshot builder
service letrehozasa, amely a projekt aktualis, solver-input szempontbol relevans
truth-jat determinisztikusan osszeolvassa es run snapshot payloadda formalja.

A H0 mar letette az `app.nesting_runs` es `app.nesting_run_snapshots` schema-
alapjat, a H1-E3 pedig mar letrehozta a projekt-szintu part requirement es sheet
input workflowkat. Ennek a tasknak a celja ezekre epitve egy olyan service
bevezetese, amely megmondja, hogy **mi kerulne egy futtathato snapshotba**.

Ez a task tudatosan **nem** run create API, **nem** queue insert, **nem** worker
lease mechanika es **nem** solver process futtatas. A scope most az, hogy a
solver-input relevans adatokat determinisztikusan, tiszta H0/H1 truth alapjan
osszerakjuk.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit `api/services/run_snapshot_builder.py` service bevezetese;
  - projekt-owner ellenorzes es projekt-hozzaferes validalasa;
  - project-level technology setup, aktív part requirementek es aktiv sheet
    inputok osszeolvasasa;
  - approved/hasznalhato part revision + derivative referencia validalasa;
  - hasznalhato sheet revision adatok snapshotba emelese;
  - determinisztikus manifest/solver-config payload kepzese;
  - determinisztikus `snapshot_hash_sha256` kepzese;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - `POST /runs` vagy barmilyen uj run API route;
  - `app.nesting_runs`, `app.nesting_run_snapshots` vagy `app.run_queue`
    rekordok tenyleges insertje;
  - worker lease / retry / heartbeat mechanika;
  - solver adapter vagy process inditas;
  - result normalizer, projection, artifact vagy manufacturing scope.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a H1-E4-T1 source-of-truth helye.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - a H1 run snapshot builder funkcionalis celjai.
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
  - a H0 snapshot payload canonical taroloja (`app.nesting_runs`,
    `app.nesting_run_snapshots`).
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
  - a queue/log tablakat mar letette, de ez a task meg nem kezel queue insertet.
- `api/services/project_part_requirements.py`
  - friss H1 minta a project-level requirement truthra.
- `api/services/project_sheet_inputs.py`
  - friss H1 minta a project-level sheet input truthra.
- `api/services/part_creation.py`
  - a `part_revisions.selected_nesting_derivative_id` es
    `source_geometry_revision_id` H1 truthja.
- `api/services/sheet_creation.py`
  - owner-szintu sheet revision workflow minta.
- `api/routes/runs.py`
  - legacy/korabbi run route; csak referencia, nem source-of-truth.
- `api/sql/phase4_run_quota_atomic.sql`
  - legacy bridge/helper, nem ez a task canonical szerzodese.

### Konkret elvarasok

#### 1. A snapshot builder a jelenlegi H0/H1 truthot olvassa
A service kizarolag a mar meglevo, aktualis tablavilagbol epitsen snapshotot:
- `app.projects`
- `app.project_settings`
- `app.project_technology_setups`
- `app.project_part_requirements`
- `app.part_revisions`
- `app.part_definitions`
- `app.project_sheet_inputs`
- `app.sheet_revisions`
- `app.sheet_definitions`
- ahol szukseges: `app.geometry_derivatives`

Ne vezessen vissza legacy `phase1_*` vagy regi `public.*` futasi modellhez.

#### 2. A technology selection legyen egyertelmu es determinisztikus
A builder valassza ki a snapshot technology truthjat a projekt sajat
`project_technology_setups` rekordjaibol.

H1 minimum szabaly:
- a projekthez tartozzon pontosan egy hasznalhato technology setup;
- preferaltan az `is_default = true` setup legyen a snapshot forrasa;
- ha nincs egyertelmu valaszthato setup, a service adjon ertelmes hibajat.

A snapshot technology resze legalabb ezeket vigye tovabb:
- `technology_setup_id`
- `machine_code`
- `material_code`
- `thickness_mm`
- `kerf_mm`
- `spacing_mm`
- `margin_mm`
- `rotation_step_deg`
- `allow_free_rotation`

#### 3. A part requirement manifest csak solverre tenylegesen alkalmas inputot vigyen
A builder az aktiv `project_part_requirements` rekordokbol kepezzen
`parts_manifest_jsonb` reszt ugy, hogy minden rekordhoz ellenorizze:
- a part revision a megfelelo definitionhoz tartozik;
- a revision lifecycle hasznalhato a solverhez (H1 minimum: `approved`);
- van explicit `selected_nesting_derivative_id`;
- a `required_qty` pozitiv es az input aktiv.

A manifest minimum soronként legalabb tartalmazza:
- `project_part_requirement_id`
- `part_revision_id`
- `part_definition_id`
- `part_code`
- `part_name`
- `revision_no`
- `required_qty`
- `placement_priority`
- `placement_policy`
- `selected_nesting_derivative_id`
- `source_geometry_revision_id` (ha elerheto a revisionrol)

#### 4. A sheet manifest csak aktiv, hasznalhato sheet inputot vigyen
A builder az aktiv `project_sheet_inputs` rekordokbol kepezzen
`sheets_manifest_jsonb` reszt ugy, hogy minden rekordhoz ellenorizze:
- a sheet revision a megfelelo definitionhoz tartozik;
- a revision lifecycle hasznalhato a snapshothoz (H1 minimum: `approved`);
- a `required_qty` pozitiv;
- a width/height valos, pozitiv ertek.

A manifest minimum soronként legalabb tartalmazza:
- `project_sheet_input_id`
- `sheet_revision_id`
- `sheet_definition_id`
- `sheet_code`
- `sheet_name`
- `revision_no`
- `required_qty`
- `is_default`
- `placement_priority`
- `width_mm`
- `height_mm`
- opcionálisan `grain_direction`

#### 5. A snapshot payload strukturaja a H0 snapshot modellhez igazodjon
A service ne talaljon ki uj fobb payload-vilagot. A kimenet legyen kozvetlenul a
`app.nesting_run_snapshots` H0 struktura logikai parja, minimum ezekkel:
- `snapshot_version`
- `project_manifest_jsonb`
- `technology_manifest_jsonb`
- `parts_manifest_jsonb`
- `sheets_manifest_jsonb`
- `geometry_manifest_jsonb`
- `solver_config_jsonb`
- `manufacturing_manifest_jsonb`
- `snapshot_hash_sha256`

A `geometry_manifest_jsonb` H1 minimum szinten ne a teljes canonical geometryt
masolja, hanem a solver-input szempontbol relevans geometry referenciakat
hordozza, elsosorban a `selected_nesting_derivative_id` es kapcsolodo lineage
azonositoit.

#### 6. A hash kepzes legyen determinisztikus
A builder ugyanarra az adatallapotra ugyanazt a `snapshot_hash_sha256` erteket
adja vissza.

Ehhez minimum:
- stabil rendezes legyen a `parts_manifest_jsonb` es `sheets_manifest_jsonb`
  listakban;
- ne keruljon a hashbe pillanatnyi `now()` jellegu vagy egyeb nem-determinisztikus
  adat;
- azonos logikai inputra bit-szinten stabil JSON serialization tortenjen.

#### 7. A task ne csusszon at run create / queue scope-ba
Ez a task meg **nem** hoz letre queued run flowt.

Tehat most ne legyen:
- `api/routes/runs.py` H0/H1 truth szerinti atirasa;
- `app.nesting_runs` insert;
- `app.nesting_run_snapshots` insert;
- `app.run_queue` insert;
- quota vagy worker lease logika.

Ezek a kovetkezo taskokba tartoznak.

#### 8. A smoke bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- sikeres snapshot build aktiv project + technology + requirements + sheets eseten;
- ugyanarra az inputra stabil `snapshot_hash_sha256` jon;
- hiba jon, ha nincs valaszthato technology setup;
- hiba jon, ha nincs aktiv part requirement;
- hiba jon, ha nincs aktiv sheet input;
- hiba jon, ha a part revision nem approved vagy nincs derivative binding.

### DoD
- [ ] Keszul explicit `api/services/run_snapshot_builder.py` service.
- [ ] A task a meglevo H0/H1 tablavilagra epul, nem legacy run modellre.
- [ ] A builder osszeolvassa a projekt-level technology selectiont.
- [ ] A builder osszeolvassa az aktiv project part requirementeket.
- [ ] A builder osszeolvassa az aktiv project sheet inputokat.
- [ ] A snapshotban minden solver-input relevans part/sheet/technology adat megjelenik H1 minimum szinten.
- [ ] A builder csak solverre alkalmas part revision + derivative referenciat enged tovabb.
- [ ] A builder determinisztikus `snapshot_hash_sha256` erteket kepez.
- [ ] A task nem vezet be run route-ot, queue insertet vagy worker logikat.
- [ ] Keszul task-specifikus smoke a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task visszacsuszik a legacy `runs.py` / `phase4_*` vilaghoz;
  - nem determinisztikus snapshot hash kepzodik;
  - a builder nem szuri ki a nem approved vagy hianyos part/sheet inputot;
  - a task atcsuszik queue/run create scope-ba.
- Mitigacio:
  - csak H0/H1 canonical tablakat es a friss H1-E3 service-ek logikajat hasznald;
  - stabil rendezes es kanonikus JSON serialization;
  - explicit guard a technology, part requirement, derivative es sheet input
    hianyokra;
  - route/queue/worker scope legyen kulon kimondva out-of-scope.
- Rollback:
  - a service + smoke + checklist/report valtozasok egy task-commitban
    visszavonhatok;
  - schema-modositas ne legyen ebben a taskban.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_snapshot_builder.py scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py`
  - `python3 scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `api/services/part_creation.py`
- `api/services/project_part_requirements.py`
- `api/services/sheet_creation.py`
- `api/services/project_sheet_inputs.py`
- `api/routes/runs.py`
- `api/sql/phase4_run_quota_atomic.sql`
