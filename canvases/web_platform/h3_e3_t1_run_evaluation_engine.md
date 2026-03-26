# H3-E3-T1 Run evaluation engine

## Funkcio
Ez a task hozza be a H3 evaluation reteg elso, onallo truth-jat.
A cel, hogy egy mar lefutott run a meglevo H1/H2 persisted metrikak alapjan
reprodukalhato, komponensekre bonthato score-t kapjon, es ez a score kulon
persisted truth-kent visszakeresheto legyen.

A jelenlegi repoban mar megvan:
- a H1 canonical projection truth (`app.run_layout_*`, `app.run_metrics`);
- a H2 manufacturing metrics truth (`app.run_manufacturing_metrics`);
- a H3 scoring profile/version domain (`app.scoring_profiles`,
  `app.scoring_profile_versions`);
- a H3 project-level scoring selection truth;
- a H3 batch es orchestrator alap.

Ez a task ezekre epulve **nem rankinget**, **nem batch-osszehasonlitast** es
**nem business decision layer-t** szallit, hanem a legelso, egy-runos,
auditálhato evaluation truth-ot.

A hangsuly most azon van, hogy:
- a score ne frontend-hardcode legyen;
- a komponensek es input metrikak visszakereshetok legyenek;
- az evaluation ne talaljon ki olyan H3 jeleket, amelyekhez meg nincs persisted
  adatforras.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_evaluations` tabla bevezetese;
  - dedikalt `api/services/run_evaluations.py` evaluation service;
  - minimalis route a run evaluation letrehozasara/ujraszamitasara es
    visszaolvasasara;
  - explicit scoring profile version alapu evaluation;
  - optionalis fallback a projekt aktiv scoring selectionjere, ha az mar
    letezik es a kereso nem ad explicit version id-t;
  - H1 `run_metrics` + H2 `run_manufacturing_metrics` read-only felhasznalasa;
  - komponens-szintu score bontas es threshold eredmenyek eltárolasa
    `evaluation_jsonb` alatt;
  - task-specifikus smoke a sikeres, hibas es hatarscope agakra.
- Nincs benne:
  - `run_ranking_results`;
  - batch-level ranking vagy comparison projection;
  - `run_batches` vagy `run_batch_items` automatikus bejarasa;
  - strategy profile runtime alkalmazasa;
  - remnant domain, inventory-aware resolver, business metrics vagy review
    workflow;
  - `run_snapshot_builder`, worker vagy H1/H2 truth tablák modosítása.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - source-of-truth task tree; a H3-E3-T1 outputja: `run_evaluations`.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - a H3 detailed doc SQL-vazlata a `run_evaluations` tablára, es a DoD:
    reprodukalhato, komponensenkent indokolhato score.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - a P2-B3 backlog megerositi: metrikakbol score, komponensbontas tarolasa.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: evaluation kulon domain legyen, ne frontend-only es ne
    CAM/manufacturing scope.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - fontos boundary: a run truth mar snapshot-first letrejott, ezt a taskot nem
    szabad snapshot-builder redesignga csusztatni.
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - H1 `app.run_metrics` truth; elerheto jelek: `placed_count`,
    `unplaced_count`, `used_sheet_count`, `utilization_ratio`, `remnant_value`,
    `metrics_jsonb`.
- `worker/result_normalizer.py`
  - mutatja, hogy a H1 run-metrikak honnan es milyen szemantikaval jonnek.
- `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql`
  - H2 `app.run_manufacturing_metrics` truth; elerheto jelek:
    `estimated_process_time_s`, `estimated_cut_length_mm`,
    `estimated_rapid_length_mm`, `pierce_count`.
- `api/services/manufacturing_metrics_calculator.py`
  - megerositi a H2 timing proxy modelljet es a truth boundaryt.
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
  - a scoring profile version schema:
    `weights_jsonb`, `tie_breaker_jsonb`, `threshold_jsonb`, `is_active`.
- `api/services/scoring_profiles.py`
  - a scoring profile/version owner-scoped truth olvasasi forrasa.
- `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql`
  - optionalis projekt-szintu scoring selection fallback truth.
- `api/services/project_strategy_scoring_selection.py`
  - minta az owner-validalt project-level scoring selection olvasasara.
- `canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md`
  - a scoring domain kulcsai es scope-hatarai.
- `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
  - fontos boundary: a selection persisted truth, nem maga az evaluation.
- `canvases/web_platform/h3_e2_t2_batch_run_orchestrator.md`
  - fontos kontextus: a batch-item mar tarol scoring kontextust, de ezt a taskot
    nem szabad ranking vagy batch bejaras iranyba tolni.
- `api/main.py`
  - ide kell majd az uj route bekotese.

### Konkret elvarasok

#### 1. Kulon persisted evaluation truth kell, de egy runhoz egy canonical evaluation
A task vezesse be a H3 detailed docban javasolt:
- `app.run_evaluations`

Minimum elvart mezo-struktura:
- `run_id` (PK, `app.nesting_runs` FK)
- `scoring_profile_version_id`
- `total_score`
- `evaluation_jsonb`
- `created_at`

A H3 doksi PK-valol felfogasat tartsd meg:
- egy runhoz egy canonical persisted evaluation tartozik;
- ha ugyanazt a run-t ujraertekeljuk, az elozo evaluation replace-elodik;
- ez a task **nem** vezet be multi-profile evaluation history tablat.

#### 2. Az evaluation service explicit scoring versionnel is mukodjon
A H3-E3-T1 task tree dependency-je nem teszi kotelezove a project-level
selectiont vagy a batch worldot, ezert az evaluation service-nek legalabb ezt
kell tudnia:
- explicit `scoring_profile_version_id` alapjan egy run kiertekelese;
- optionalisan, ha nincs explicit version, megprobalhat fallbackolni a
  `app.project_scoring_selection` aktiv versionjere.

Fontos:
- az explicit version path legyen az elso rendu, stabil kontraktus;
- a selection fallback csak convenience legyen, ne egyetlen ut;
- ne legyen batch-item auto-discovery, ranking side effect vagy batch-bejaras.

#### 3. Csak a mar letezo persisted metrikakra szabad score-t epiteni
A scoring profile smoke-jaban mar megjelentek ilyen kulcsok:
- `utilization_weight`
- `unplaced_penalty`
- `sheet_count_penalty`
- `remnant_value_weight`
- `process_time_penalty`
- `priority_fulfilment_weight`
- `inventory_consumption_penalty`

A jelenlegi repoban tenyleges persisted input csak ezekhez van:
- H1-bol:
  - `utilization_ratio`
  - `placed_count`
  - `unplaced_count`
  - `used_sheet_count`
  - `remnant_value` (lehet `null`)
- H2-bol:
  - `estimated_process_time_s`
  - `estimated_cut_length_mm`
  - `estimated_rapid_length_mm`
  - `pierce_count`

Ezert az evaluation engine minimum elvart viselkedese:
- a tenylegesen letezo jelekre alkalmaz score-komponenst;
- a meg nem letezo vagy meg nem normalizalhato jeleket **nem talalja ki**;
- az ilyen kulcsokat `evaluation_jsonb` alatt
  `status: "unavailable_metric"` / `status: "not_applied_yet"` jelleggel rogzitese,
  `contribution = 0` mellett;
- ne vezessen be uj H3-E4/H3-E5 truth readeket csak azert, hogy minden weight
  "mukodjon".

#### 4. A score legyen komponens-szinten indokolhato es bounded
A `total_score` ne nyers countok vagy mas skala nelkuli ertekek osszege legyen.
A task legalabb egy dokumentalt, bounded H3 minimum formulat vezessen be.

Javasolt minimum:
- `utilization_weight`
  - raw signal: `run_metrics.utilization_ratio`
  - normalized signal: 0..1 kozotti utilization
  - contribution: pozitiv
- `unplaced_penalty`
  - raw signal: `unplaced_ratio = unplaced_count / max(placed_count + unplaced_count, 1)`
  - normalized signal: 0..1
  - contribution: negativ
- `sheet_count_penalty`
  - raw signal: `used_sheet_count`
  - normalized signal: `0`, ha `used_sheet_count <= 1`,
    kulonben `1 - (1 / used_sheet_count)`; igy bounded 0..1
  - contribution: negativ
- `remnant_value_weight`
  - csak akkor alkalmazhato pozitiv komponenskent, ha `remnant_value` nem null es
    a thresholdok adnak hozza ertelmes normalizalasi pontot
    (peldaul `target_remnant_value` vagy `max_remnant_value`);
  - egyebkent keruljon `not_applied` allapotba.
- `process_time_penalty`
  - csak akkor alkalmazhato negativ komponenskent, ha van
    `run_manufacturing_metrics` sor es threshold oldali normalizalasi pont
    (peldaul `max_estimated_process_time_s`);
  - egyebkent keruljon `not_applied` / `missing_threshold_or_metric` allapotba.

A `evaluation_jsonb` minimum tartalmazza:
- a felhasznalt scoring profile payloadokat;
- az input metric snapshotot;
- komponensenkenti `raw_value`, `normalized_value`, `weight`, `contribution`,
  `status`;
- threshold eredmenyeket;
- tie-breakerhez hasznalhato nyers inputokat;
- figyelmezteteseket / kihagyott komponenseket.

#### 5. A threshold es tie-breaker kezeles "alap" legyen, ne ranking
A H3 detailed doc szerint a T1 a threshold/tie-breaker kezeles **alapjat**
rakja le. Ezt ugy kell ertelmezni, hogy:
- a `threshold_jsonb` ismert kulcsaira boolean pass/fail eredmeny keletkezik
  `evaluation_jsonb.threshold_results` alatt;
- a `tie_breaker_jsonb` ismert kulcsaihoz a relevans metric inputok
  `evaluation_jsonb.tie_breaker_inputs` alatt elerhetok;
- a task **nem** hoz letre sorrendet, nem szamol `rank_no`-t,
  es nem gyart `run_ranking_results` sort.

Pelda ismert threshold kulcsokra:
- `min_utilization`
- `max_unplaced_ratio`
- `max_used_sheet_count`
- `max_estimated_process_time_s`
- `min_remnant_value`

Ismeretlen threshold / tie-breaker kulcs ne legyen csendben eldobva:
- keruljon warnings / unsupported bucket ala.

#### 6. A write viselkedes legyen idempotens, es csak `run_evaluations`-be irjon
A service:
- validalja a run owner/project scope-ot;
- validalja a scoring profile version owner-scope-jat es ervenyes allapotat;
- betolti a H1/H2 persisted truthot;
- ugyanarra a `run_id`-ra delete-then-insert vagy ezzel egyenerteku
  deterministic replace viselkedest adjon;
- csak `app.run_evaluations` tablaba irjon.

A task ne irjon:
- `app.run_metrics`
- `app.run_manufacturing_metrics`
- `app.run_batches`
- `app.run_batch_items`
- `app.project_scoring_selection`
- `app.run_ranking_results`

#### 7. Minimalis, de tiszta route contract kell
Keszits dedikalt route-ot, peldaul:
- `POST /projects/{project_id}/runs/{run_id}/evaluation`
- `GET /projects/{project_id}/runs/{run_id}/evaluation`
- optionalisan `DELETE /projects/{project_id}/runs/{run_id}/evaluation`

A POST:
- explicit `scoring_profile_version_id`-t elfogad;
- ha ez nincs megadva, fallbackolhat a projekt aktiv scoring selectionjere;
- visszaadja a persisted evaluation truth-ot es a felhasznalt scoring profile
  verzio azonositot.

A GET:
- a persisted truthot adja vissza;
- ne szamoljon ujra automatikusan.

A route maradjon tisztan evaluation-domain:
- ne nyisson batch/ranking/comparison workflowt;
- ne rewire-olja a meglevo `runs.py` nagy route-fajlt.

#### 8. A smoke script bizonyitsa a fo evaluation agak teljes kepet
A task-specifikus smoke legalabb ezt bizonyitsa:
- explicit scoring profile versionnel evaluation sikeresen letrehozhato;
- ugyanannak a runnak az ujraertekelese replace-eli az elozo evaluation sort;
- a `total_score` es a komponensbontas determinisztikusan ugyanaz azonos inputra;
- `run_metrics` hianyaban az evaluation hibat ad;
- `run_manufacturing_metrics` hianyaban a H1-komponensek mukodnek, de a
  `process_time_penalty` komponens `not_applied` / `missing_metric` lesz;
- idegen owner scoring profile versionnel az evaluation elutasitodik;
- ha van project-level scoring selection, explicit version nelkul is mukodhet a
  fallback;
- `priority_fulfilment_weight` es `inventory_consumption_penalty` nem talal ki
  nem letezo adatot, hanem zero contribution + unsupported status kerul rogzitese;
- nincs `run_ranking_results`, batch vagy selection write side effect.

### DoD
- [ ] Letrejott az `app.run_evaluations` persisted truth reteg.
- [ ] Az evaluation egy runhoz reprodukalhato `total_score`-t tud kepezni.
- [ ] A score komponensekre bontva, indokolhatoan kerul az `evaluation_jsonb`-be.
- [ ] Az engine explicit `scoring_profile_version_id` alapu kontraktussal mukodik.
- [ ] Optionalis project-level scoring selection fallback dokumentalt es ellenorzott.
- [ ] Csak a mar letezo H1/H2 persisted metrikakra epul score-komponens.
- [ ] A meg nem letezo H3 jelek nem kerulnek kitalalasra; unsupported/not_applied allapotban latszanak.
- [ ] A threshold eredmenyek es tie-breaker inputok elerhetok, de ranking nem keszul.
- [ ] Az evaluation write viselkedese run-szintu idempotens replace.
- [ ] A task nem nyul a H1/H2 truth tablákhoz es nem csuszik at ranking/comparison scope-ba.
- [ ] Keszult dedikalt service, route es task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a score nyers, skala nelkuli countokra epul, es instabil lesz;
  - a task rankinget vagy batch comparisont is becsempesz;
  - a service H3-E4/H3-E5 metrikakat talal ki, hogy "teljesebb" legyen;
  - a project-level selection fallback egyetlen kotelezo uttá valik;
  - az evaluation write side effectkent mas truth tablakat is modosit.
- Mitigacio:
  - bounded, dokumentalt H3 minimum formula;
  - explicit no-ranking / no-batch-comparison boundary;
  - unsupported/not_applied status a meg nem letezo metrikakra;
  - explicit scoring version path elsosege;
  - delete-then-insert csak `app.run_evaluations`-re.
- Rollback:
  - a migration + service + route + smoke egy task-commitban
    visszavonhato;
  - a H1/H2 metric truth, a H3 scoring profile truth es a batch domain
    erintetlen marad, mert ez a task csak uj evaluation reteget vezet be.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_evaluations.py api/routes/run_evaluations.py scripts/smoke_h3_e3_t1_run_evaluation_engine.py`
  - `python3 scripts/smoke_h3_e3_t1_run_evaluation_engine.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `worker/result_normalizer.py`
- `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql`
- `api/services/manufacturing_metrics_calculator.py`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
- `api/services/scoring_profiles.py`
- `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql`
- `api/services/project_strategy_scoring_selection.py`
- `canvases/web_platform/h3_e1_t2_scoring_profile_modellek.md`
- `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
- `canvases/web_platform/h3_e2_t2_batch_run_orchestrator.md`
- `api/main.py`
