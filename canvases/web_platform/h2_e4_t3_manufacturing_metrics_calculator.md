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
reprodukalhato, auditalahato, gepfuggetlen metrics reteg jojjon letre.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_manufacturing_metrics` tabla bevezetese;
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
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - a meglevo `app.run_metrics` tabla; fontos kulon tartani ettol a H2 vilagot.
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
  - a `app.run_manufacturing_plans` es `app.run_manufacturing_contours` truth reteg.
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
  - a `app.geometry_contour_classes` perimeter/contour-kind truth tablaja.
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
  - a `app.cut_contour_rules` truth, benne a `pierce_count` mezo.
- `api/services/manufacturing_plan_builder.py`
  - a jelenlegi H2-E4-T2 builder; a metrics ennek persisted outputjara epul.
- `worker/result_normalizer.py`
  - a meglevo `run_metrics.metrics_jsonb` strukturalt aggregacios minta.

### Konkret elvarasok

#### 1. A calculator persisted plan truth-bol dolgozzon
A manufacturing metrics calculator a mar persisted manufacturing plan reteget tekintse
forrasnak:
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- kapcsolodo `geometry_contour_classes`
- kapcsolodo `cut_contour_rules`

#### 2. A `run_manufacturing_metrics` maradjon kulon tabla
A H1 `run_metrics` tovabbra is solver/run summary vilag.
A H2 manufacturing metrics kulon truth legyen sajat tablaban.

#### 3. A metrikak legyenek auditalahatok es reprodukalhatok
- `pierce_count`: matched rule truthbol;
- `outer_contour_count` / `inner_contour_count`: contour_kind alapjan;
- `estimated_cut_length_mm`: contour class perimeter_mm osszegzese;
- `estimated_rapid_length_mm`: determinisztikus proxy entry pontok kozti tavolsagbol;
- `estimated_process_time_s`: egyszeru proxy formula.

#### 4. A calculator legyen idempotens
Upsert per `run_id` primary key.

#### 5. A metrics_jsonb adjon bontott reteget
Tartalmazza: `calculator_scope`, `cut_length_by_contour_kind`,
`contour_count_by_kind`, `timing_model`, `timing_assumptions`.

#### 6. Ne csusszon at preview, export vagy costing scope-ba

#### 7. A smoke bizonyitsa a fo invariansokat

### DoD
- [ ] Letezik `app.run_manufacturing_metrics` persisted truth reteg.
- [ ] A calculator persisted manufacturing plan truthbol tud manufacturing metrikat kepezni.
- [ ] A H2 manufacturing metrics kulon marad a H1 `run_metrics` tablatol.
- [ ] A `pierce_count` matched rule truth alapjan szamolodik.
- [ ] Az `estimated_cut_length_mm` contour class perimeter truth alapjan szamolodik.
- [ ] Az `estimated_rapid_length_mm` determinisztikus, gepfuggetlen proxy.
- [ ] Az `estimated_process_time_s` dokumentalt, egyszeru proxy modellre epul.
- [ ] A calculator idempotens a persisted reteg szintjen.
- [ ] A task nem ir vissza korabbi truth tablaba.
- [ ] A task nem nyit preview / postprocessor / export / costing scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t3_manufacturing_metrics_calculator.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a calculator live state-bol kezd dolgozni persisted plan helyett;
  - gepresolver vagy anyagresolver logikat talal ki a process time-hoz;
  - a metrics reteg osszemosodik a H1 `run_metrics` tablaval;
  - a rapid/time proxy nem determinisztikus;
  - a task preview/export vagy pricing iranyba csuszik.
- Rollback:
  - migration + calculator service + smoke valtozasok egy task-commitban visszavonhatok;
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
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
- `api/services/manufacturing_plan_builder.py`
