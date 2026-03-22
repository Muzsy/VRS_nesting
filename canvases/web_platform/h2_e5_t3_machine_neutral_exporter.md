# H2-E5-T3 Machine-neutral exporter

## Funkcio
A feladat a H2 manufacturing/postprocess lanc kovetkezo, meg mindig szukitett
scope-u lepese.
A cel, hogy a mar meglevo, persisted manufacturing truth retegbel
(`run_manufacturing_plans`, `run_manufacturing_contours`, opcionalisan
`run_manufacturing_metrics`) valamint a snapshotolt manufacturing/postprocess
selectionbol eloalljon egy deterministic, gepfuggetlen,
`manufacturing_plan_json` export artifact.

A jelenlegi repoban mar megvan:
- a manufacturing plan persisted truth (`H2-E4-T2`);
- a manufacturing metrics truth (`H2-E4-T3`);
- a manufacturing preview SVG artifact (`H2-E5-T1`);
- a postprocessor profile/version domain aktivacio es snapshotolhato aktiv
  postprocessor selection (`H2-E5-T2`);
- a H1 generic `run_artifacts` list/download flow, valamint a hash-alapu,
  idempotens artifact persistence mintak.

Ez a task ezekre epulve egy elso, valos machine-neutral export artifactot vezet
be.

Ez a task szandekosan nem machine-specific adapter, nem G-code/NC emitter,
nem `machine_ready_bundle`, nem worker full auto-integracio, nem uj preview
route, es nem elo project-state resolver. A scope kifejezetten az, hogy a mar
persistalt H2 truth-bol auditalhato, gepfuggetlen export payload jojjon letre,
amelyet a kesobbi adapterek konzisztensen felhasznalhatnak.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.artifact_kind` bovitese `manufacturing_plan_json` ertekkel;
  - a legacy <-> enum bridge fuggvenyek frissitese, hogy a generic artifact
    lista / signed URL flow ezt a tipust is konzisztensen kezelje;
  - dedikalt `api/services/machine_neutral_exporter.py` service bevezetese;
  - owner-scoped run betoltes;
  - a service a persisted H2 truth-bol dolgozzon:
    - `run_manufacturing_plans`
    - `run_manufacturing_contours`
    - `nesting_run_snapshots.manufacturing_manifest_jsonb`
    - opcionálisan `run_manufacturing_metrics`
    - szukseg eseten a kapcsolodo `manufacturing_canonical` geometry derivative,
      ha a canonical export payloadhoz contour pontok is kellenek;
  - deterministic, canonical JSON payload eloallitasa egy runhoz;
  - artifact upload + `app.run_artifacts` regisztracio
    `manufacturing_plan_json` tipussal;
  - task-specifikus smoke a deterministic payload / idempotens replace /
    no-write-out-of-scope / no-machine-ready invariansokra.
- Nincs benne:
  - machine-specific adapter vagy celgep-csalad prototipus;
  - `machine_ready_bundle` vagy barmilyen G-code/NC output;
  - postprocessor config geometriai alkalmazasa a toolpathra;
  - worker automatikus export-generator hook, ha ez a scope-ot tul szelesitene;
  - kulon export UI vagy uj dedikalt download endpoint;
  - live `project_manufacturing_selection` olvasasa exporthoz;
  - visszairas korabbi truth tablaba (`run_manufacturing_plans`,
    `run_manufacturing_contours`, `run_manufacturing_metrics`,
    `geometry_contour_classes`, `postprocessor_profile_versions`).

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E5-T3 task: machine-neutral exporter.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - itt szerepel a machine-neutral manufacturing export contract, az uj
    artifact kindok es a postprocessor adapter iranya.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a postprocess/export kulon modul marad; az export
    artifact nem domain truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - export artifact != truth, snapshot-first, worker/adapter ne elo project
    allapotbol dolgozzon.
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
  - a persisted manufacturing plan truth schema-ja.
- `api/services/manufacturing_plan_builder.py`
  - a forras truth reteg szerkezete es scope-hatarai.
- `api/services/manufacturing_metrics_calculator.py`
  - a H2 metrics truth minta, amely opcionálisan exportba emelheto.
- `supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql`
  - artifact kind + bridge bovites mintaja.
- `api/services/manufacturing_preview_generator.py`
  - H2 truthbol derive-olt artifact persistence mintaja.
- `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
  - a postprocessor profile/version domain es a manufacturing -> postprocessor ref.
- `api/services/postprocessor_profiles.py`
  - a postprocessor domain mezoi, amelyekbol max metadata-szintu export info
    kerulhet be.
- `api/services/run_snapshot_builder.py`
  - a snapshotolt manufacturing/postprocess selection struktura forrasa.
- `worker/raw_output_artifacts.py`
  - canonical artifact metadata/storage minta JSON-jellegu artifactokhoz.
- `api/routes/runs.py`
  - a generic artifact list/download szerzodes; ezt nem szabad nagy scope-ban
    ujratervezni.

### Konkret elvarasok

#### 1. Az exporter persisted truth + snapshot alapjan dolgozzon
A service ne elo project-level selectionbol, es ne raw solver outputbol
allitsa elo az exportot.
A forrasok:
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- `nesting_run_snapshots.manufacturing_manifest_jsonb`
- opcionálisan `run_manufacturing_metrics`
- szukseg eseten `geometry_derivatives` (`manufacturing_canonical`) a contour
  pontlista exporthoz

Ne olvasson:
- `project_manufacturing_selection` live truthot;
- preview SVG artifactot mint forrast;
- worker run directory-t vagy solver raw stdout/stderr fajlokat.

#### 2. Az export artifact kind legyen repo-hu es visszakeresheto
A task vezesse be a `manufacturing_plan_json` artifact kindot.

Minimum elvaras:
- migration, amely hozzaadja az enum erteket;
- bridge-frissites, hogy a generic artifact lista es signed URL flow ezt is
  konzisztensen vigye;
- metadata legalabb:
  - `filename`
  - `size_bytes`
  - `content_sha256`
  - `legacy_artifact_type='manufacturing_plan_json'`
  - `export_scope='h2_e5_t3'`
  - opcionálisan `export_contract_version`.

#### 3. A payload legyen canonical, deterministic es adapter-kompatibilis
A cel nem egy vegso gepi program, hanem egy kanonikus gepfuggetlen export
szerzodes.

Minimum elvart tartalom:
- `export_contract_version`
- `run_id`, `project_id`
- `manufacturing_profile_version_id`
- `cut_rule_set_id` / plan szintu hivatkozasok, ha a truthban elerhetok
- opcionálisan `manufacturing_metrics`
- ha van snapshotolt aktiv postprocessor selection:
  - `active_postprocessor_profile_version_id`
  - `adapter_key`
  - `output_format`
  - `schema_version`
- per-sheet export blokk, amely legalabb ezt tartalmazza:
  - `sheet_index`
  - plan summary/meta
  - contour lista determinisztikus sorrendben
  - contour-szintu `contour_kind`, `feature_class`, `cut_order_index`,
    `entry_point_jsonb`, `lead_in_jsonb`, `lead_out_jsonb`
  - ha a kialakitott contract ezt igenyli: transformalt contour pontok/path
    adatok a `manufacturing_canonical` derivative-bol

Fontos:
- ne keruljon bele volatilis timestamp vagy olyan mezo, ami ugyanarra a truthra
  ujrageneralaskor byte-szinten mas payloadot eredmenyezne;
- a kulcsok es listak sorrendje legyen deterministic.

#### 4. Az artifact persistence legyen canonical es idempotens
A generalt export artifact az `app.run_artifacts` retegre keruljon.

Minimum elvart:
- bucket: `run-artifacts`;
- artifact kind / legacy type: `manufacturing_plan_json`;
- filename legyen stabil, peldaul `out/manufacturing_plan.json`;
- storage path hash-alapu es canonical legyen, peldaul
  `projects/{project_id}/runs/{run_id}/manufacturing_plan_json/{digest}.json`.

Ugyanarra a run truth allapotra ujrageneralaskor ne maradjon duplikalt export
artifact ugyanarra a logical targetre.

#### 5. A postprocessor selection csak metadata/input maradjon
A H2-E5-T2 dependency miatt az exporter mar lathat aktiv postprocessor
profilverziot, de ebben a taskban ez csak metadata vagy adapter-input szerepet
kapjon.

Nem cel most:
- a config toolpathra alkalmazasa;
- machine-specific emit;
- `machine_ready_bundle` letrehozasa;
- adapter failure/log artifact.

#### 6. A task maradjon kulon exporter service, ne teljes adapter workflow
Ez a task egy elso, onallo, gepfuggetlen exporter.

Ne vallalja:
- worker auto-trigger;
- uj dedikalt export route, ha a generic artifact list/download mar elegendo;
- preview + export kozotti UI orchestraciot;
- postprocessor CRUD tovabbfejleszteset.

#### 7. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- valid persisted manufacturing planbol `manufacturing_plan_json` artifact letrejon;
- a payload deterministic ugyanarra a truthra;
- a payload a plan truthra es a snapshotolt postprocessor selectionre epul;
- aktiv postprocessor ref eseten a metadata bekerul, de nincs machine-ready emit;
- postprocessor ref nelkul is keszul gepfuggetlen export;
- ujrageneralas nem hagy duplikalt artifactot;
- a service nem ir vissza korabbi truth tablaba;
- nincs `machine_ready_bundle`, `machine_log`, G-code vagy adapter-run side effect;
- hiba jon, ha a runhoz nincs manufacturing plan vagy ownership sertes van.

### DoD
- [ ] Letezik `manufacturing_plan_json` artifact kind a bridge-frissitessel egyutt.
- [ ] Keszul dedikalt `api/services/machine_neutral_exporter.py` service.
- [ ] A service owner-scoped runra a persisted H2 truth + snapshot alapjan
      gepfuggetlen export payloadot tud eloallitani.
- [ ] Az export payload deterministic es canonical.
- [ ] Az artifact `app.run_artifacts` ala regisztralodik `manufacturing_plan_json`
      tipussal.
- [ ] Aktiv postprocessor selection eseten a metadata bekerul, de nincs
      machine-specific emit.
- [ ] A task nem hoz letre `machine_ready_bundle` vagy mas machine-specific scope-ot.
- [ ] A task nem olvas live project selectiont, es nem ir vissza korabbi truth tablaba.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md` PASS.

### Kockazat + rollback
- Kockazat:
  - az export payload volatilis lesz, es elveszik a deterministic jelleg;
  - a service elo project-state-bol kezd dolgozni snapshot helyett;
  - a task atcsuszik machine-specific adapter vagy worker-auto scope-ba;
  - a postprocessor config geometriai alkalmazasa veletlenul koran belekerul;
  - az artifact kind bridge csak felig frissul, es a generic artifact list/lista
    nem kezeli konzisztensen az uj tipust.
- Mitigacio:
  - explicit truth-forras lista;
  - explicit no-live-selection / no-machine-ready / no-worker-auto boundary;
  - task-specifikus smoke a deterministic payload + idempotencia + no-write
    invariansokra;
  - canonical JSON serialization + hash-alapu storage path.
- Rollback:
  - migration + exporter service + smoke + task artefaktok egy task-commitban
    visszavonhatok;
  - a H2-E4 plan truth es a H2-E5-T2 postprocessor domain erintetlen marad,
    mert ez a task csak derived export artifactot allit elo.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/machine_neutral_exporter.py scripts/smoke_h2_e5_t3_machine_neutral_exporter.py`
  - `python3 scripts/smoke_h2_e5_t3_machine_neutral_exporter.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
- `supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql`
- `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/manufacturing_preview_generator.py`
- `api/services/postprocessor_profiles.py`
- `api/services/run_snapshot_builder.py`
- `worker/raw_output_artifacts.py`
- `api/routes/runs.py`
