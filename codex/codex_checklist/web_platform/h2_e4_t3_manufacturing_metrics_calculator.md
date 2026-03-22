# H2-E4-T3 Manufacturing metrics calculator

## Funkcio
A feladat a H2 manufacturing plan reteg masodik, kozvetlenul raepulo lepese.
A cel, hogy a mar persisted `run_manufacturing_plans` +
`run_manufacturing_contours` truth-bol egy kulon, lekerozheto
`run_manufacturing_metrics` reteg alljon elo, amely alap gyartasi metrikakat ad:
`pierce_count`, konturszamok, becsult vagi hossz, rapid hossz es egyszeru,
gepfuggetlen ido-proxy.

A jelenlegi repoban mar megvan:
- a snapshotolt manufacturing selection (`H2-E4-T1`),
- a persisted manufacturing plan truth (`H2-E4-T2`),
- a contour class perimeter/area adatok (`H2-E2-T2`),
- a matched rule truth, benne a `pierce_count` mezovel (`H2-E3-T2`).

Ez a task ezekre epulve egy kulon manufacturing metrics truth reteget vezet be.

Ez a task szandekosan nem preview generator, nem postprocessor adapter,
nem machine-neutral export, es nem vegleges ipari ido-/koltsegmodell.
A scope kifejezetten az, hogy a persisted manufacturing plan alapjan
reprodukalhato, auditálhato, gepfuggetlen metrics reteg jojjon letre.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_manufacturing_metrics` tabla bevezetese vagy a docs-proposalhoz
    igazitott implementacioja;
  - dedikalt manufacturing metrics calculator service bevezetese;
  - owner-scoped run betoltes, persisted manufacturing plan es contour truth olvasas;
  - contour class es matched rule adatok osszefesulese a metrikakhoz;
  - per-run metrics rekord letrehozasa vagy idempotens ujraepitese;
  - alap metrikak szamitasa:
    - `pierce_count`
    - `outer_contour_count`
    - `inner_contour_count`
    - `estimated_cut_length_mm`
    - `estimated_rapid_length_mm`
    - `estimated_process_time_s`
  - `metrics_jsonb` feltoltese bontott reszletekkel;
  - task-specifikus smoke a no-resolver / idempotencia / no-preview invariansokra.
- Nincs benne:
  - manufacturing preview SVG;
  - postprocessor profile/version aktivacio;
  - machine-neutral vagy machine-specific export artifact;
  - gep- vagy anyagkatalogus resolver logika;
  - vegleges CAM-idomodel vagy koltsegmotor;
  - write-back `run_manufacturing_plans`, `run_manufacturing_contours`,
    `geometry_contour_classes`, `cut_contour_rules` vagy mas korabbi truth tablaba.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E4-T3 task: manufacturing metrics calculator.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 detailed roadmap; itt szerepel a `run_manufacturing_metrics` javasolt
    schemaja es a minimum metrikak.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - kulon kiemeli: pierce count, cut length, alap idobecsles.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a manufacturing metrics kulon derivalt/osszefoglalo reteg,
    nem postprocessor output es nem export artifact.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - a manufacturing metrics a persisted run truthra epuljon, ne live project state-re.
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - a meglevo `app.run_metrics` tabla; fontos kulon tartani ettol a H2
    manufacturing metrics vilagot.
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
  - a `app.run_manufacturing_plans` es `app.run_manufacturing_contours` truth reteg.
- `api/services/manufacturing_plan_builder.py`
  - a jelenlegi H2-E4-T2 builder; a metrics ennek persisted outputjara epul.
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
  - a `app.geometry_contour_classes` perimeter/contour-kind truth tablája.
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
  - a `app.cut_contour_rules` truth, benne a `pierce_count` mezo.
- `api/services/cut_contour_rules.py`
  - a rule truth mezoinek validacios forrasa.
- `worker/result_normalizer.py`
  - a meglevo `run_metrics.metrics_jsonb` strukturalt aggregacios minta.

### Konkret elvarasok

#### 1. A calculator persisted plan truth-bol dolgozzon, ne projectionbol vagy live state-bol
A manufacturing metrics calculator a mar persisted manufacturing plan reteget tekintse
forrasnak:
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- kapcsolodo `geometry_contour_classes`
- kapcsolodo `cut_contour_rules`

A calculator ne legyen manufacturing profile resolver, es ne olvasson live
`project_manufacturing_selection` allapotot.

#### 2. A `run_manufacturing_metrics` maradjon kulon tabla, ne olvadjon bele a H1 `run_metrics`-be
A H1 `run_metrics` tovabbra is solver/run summary vilag.
A H2 manufacturing metrics kulon truth legyen sajat tablaban.

A minimum elvart schema:
- `run_id` primary key
- `pierce_count`
- `outer_contour_count`
- `inner_contour_count`
- `estimated_cut_length_mm`
- `estimated_rapid_length_mm`
- `estimated_process_time_s`
- `metrics_jsonb`
- `created_at`
- opcionálisan `updated_at`, ha a repo mintakhoz jol illeszkedik

#### 3. A metrikak legyenek auditálhatok es reprodukalhatok
A minimum elvart szamitas:
- `pierce_count`:
  - matched rule alapjan, a `cut_contour_rules.pierce_count` osszegzesebol;
- `outer_contour_count` / `inner_contour_count`:
  - `run_manufacturing_contours.contour_kind` alapjan;
- `estimated_cut_length_mm`:
  - a kapcsolodo `geometry_contour_classes.perimeter_mm` osszegzese;
- `estimated_rapid_length_mm`:
  - alap, gepfuggetlen proxy az egymas utani `entry_point_jsonb` pontok kozti tavolsagbol;
- `estimated_process_time_s`:
  - egyszeru, dokumentalt proxy formula a cut length + rapid length + pierce count alapjan,
    fix default sebessegekkel, gepresolver nelkul.

A formula legyen oszinte, egyszeru, dokumentalt es reprodukalhato.
Ne talalj ki gepkatalogus vagy anyagprofil lookupot.

#### 4. A calculator legyen idempotens
Ugyanarra a runra ujrageneralaskor a metrics rekord frissuljon vagy cserelodjon,
de ne maradjon duplikalt rekord.
A `run_id` primary key erre jo alap.

#### 5. A metrics_jsonb adjon bontott bizonyiteki reteget
A `metrics_jsonb` legalabb tartalmazza:
- `builder_scope` vagy `calculator_scope`
- `cut_length_by_contour_kind`
- `contour_count_by_kind`
- `sheet_metrics` vagy sheet-szintu bontas, ha ez egyszeruen es tisztan eloallithato
- `timing_model`
- `timing_assumptions`

A cel az, hogy a summary mezok mogott visszakeresheto legyen a szamitas modja.

#### 6. Ne csusszon at preview, export vagy vegleges costing scope-ba
Ebben a taskban ne keletkezzen:
- preview artifact
- export artifact
- machine-specific timing
- pricing / costing / quote logika
- postprocessor aktivacio

Ez meg mindig egy gepfuggetlen, manufacturing-planbol kepzett metrics reteg.

#### 7. A smoke bizonyitsa a fo H2-E4-T3 invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- valid persisted manufacturing planbol metrics rekord letrejon;
- a `pierce_count` a matched rule truthbol szamolodik;
- a cut length a contour class perimeter truthbol szamolodik;
- a rapid length determinisztikus proxy;
- ujrageneralas nem hoz letre duplikalt metrics rekordot;
- a calculator nem ir vissza korabbi truth tablaba;
- a task nem hoz letre preview/export artifactot;
- ha nincs manufacturing plan, explicit hiba jon.

### DoD
- [x] Letezik `app.run_manufacturing_metrics` persisted truth reteg.
- [x] A calculator persisted manufacturing plan truthbol tud manufacturing metrikat kepezni.
- [x] A H2 manufacturing metrics kulon marad a H1 `run_metrics` tablátol.
- [x] A `pierce_count` matched rule truth alapjan szamolodik.
- [x] Az `estimated_cut_length_mm` contour class perimeter truth alapjan szamolodik.
- [x] Az `estimated_rapid_length_mm` determinisztikus, gepfuggetlen proxy.
- [x] Az `estimated_process_time_s` dokumentalt, egyszeru proxy modellre epul.
- [x] A calculator idempotens a persisted reteg szintjen.
- [x] A task nem ir vissza korabbi truth tablaba.
- [x] A task nem nyit preview / postprocessor / export / costing scope-ot.
- [x] Keszul task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a calculator live state-bol kezd dolgozni persisted plan helyett;
  - gepresolver vagy anyagresolver logikat talal ki a process time-hoz;
  - a metrics reteg osszemosodik a H1 `run_metrics` tablaval;
  - a rapid/time proxy nem determinisztikus;
  - a task preview/export vagy pricing iranyba csuszik.
- Mitigacio:
  - explicit input: `run_id`, persisted plan truth olvasas;
  - fix, dokumentalt default sebessegek a timing proxyhoz;
  - kulon `run_manufacturing_metrics` tabla;
  - task-specifikus smoke idempotencia es no-write bizonyitassal.
- Rollback:
  - migration + calculator service + smoke valtozasok egy task-commitban
    visszavonhatok;
  - a H2-E4-T2 plan truth erintetlen marad, mert a metrics kulon reteg.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/manufacturing_metrics_calculator.py scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py`
  - `python3 scripts/smoke_h2_e4_t3_manufacturing_metrics_calculator.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
- `api/services/manufacturing_plan_builder.py`
- `api/services/cut_contour_rules.py`
- `worker/result_normalizer.py`
