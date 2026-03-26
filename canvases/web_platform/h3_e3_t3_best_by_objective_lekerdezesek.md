# H3-E3-T3 Best-by-objective lekerdezesek

## Funkcio
Ez a task hozza be a H3 evaluation/ranking vonal harmadik, kifejezetten
**read-side comparison query** reteget.
A cel, hogy egy mar persisted rankinggel rendelkezo batchbol objective-specifikus
"best" nezetek kerhetoek legyenek anelkul, hogy uj score szamitas, uj ranking
kepzes, selected-run workflow vagy teljes comparison dashboard epulne.

A jelenlegi repoban mar megvan:
- a H3 batch truth (`app.run_batches`, `app.run_batch_items`);
- a persisted evaluation truth (`app.run_evaluations`);
- a persisted ranking truth (`app.run_ranking_results`);
- a H1 run projection truth (`app.run_metrics`, `app.run_layout_unplaced`);
- a H2 manufacturing metrics truth (`app.run_manufacturing_metrics`);
- a run snapshot truth (`app.nesting_run_snapshots`), benne a
  `parts_manifest_jsonb`-val, amely tartalmazza a `required_qty` es
  `placement_priority` adatokat.

Ez a task ezekre epulve **nem** uj persisted comparison tabla, **nem**
ranking engine ujranyitas, **nem** evaluation engine, **nem** business metrics
calculator, **nem** selected run workflow, es **nem** remnant/inventory task.

A hangsuly most azon van, hogy:
- a top candidate objective szerint ne frontend-only osszerakas legyen;
- az objective nezetek a mar persisted truthokra epuljenek;
- a dontes magyarazhato legyen objective-level reason payloadban;
- a task ne talaljon ki olyan uzleti metrikat, amihez meg nincs truth reteg.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - dedikalt read-side service objective-specifikus top candidate queryhez;
  - objective projection route batch-szinten;
  - `material-best`, `time-best`, `priority-best` nezetek a mar letezo truthok
    alapjan;
  - `cost-best` query contract expliciten kezelt, de **nem kitalalt** uzleti
    koltsegkeplettel;
  - objective-level reason payload, source trace, tie/fallback leiras;
  - task-specifikus smoke a sikeres, unsupported es boundary esetekre.
- Nincs benne:
  - uj migration vagy uj persisted comparison tabla;
  - `app.run_evaluations` ujraszamitas vagy write;
  - `app.run_ranking_results` ujraszamitas vagy write;
  - comparison summary / batch dashboard projection;
  - `project_selected_runs`, `run_reviews`, human approval workflow;
  - `run_business_metrics` vagy barmilyen uj cost truth;
  - remnant extractor, stock sheet vagy inventory-aware resolver.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - source-of-truth task tree; a H3-E3-T3 outputja: comparison queries /
    projections, objective-specifikus toplistakkal.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - a H3 detailed doc kulon emliti a top candidate listakat es a
    best-by-objective nezeteket, de a teljes comparison projection builder csak
    kesobbi task.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - a P2-B5 backlog nevesiti: `material-best / time-best / priority-best`
    nezetek.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - fontos boundary: decision layer comparison/selection iranyba nohet, de nem
    irhatja vissza a solver outputot vagy projection truthot.
- `supabase/migrations/20260324150000_h3_e3_t2_ranking_engine.sql`
  - a T3 elsodleges input truthja: `app.run_ranking_results`.
- `api/services/run_rankings.py`
  - referencia a persisted ranking reason payloadra es a canonical fallback
    gondolkodasra.
- `api/routes/run_rankings.py`
  - minta a batch-szintu H3-E3 route kontraktusra.
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - itt vannak a H1 projection truthok: `run_metrics`, `run_layout_unplaced`.
- `supabase/migrations/20260322030000_h2_e4_t3_manufacturing_metrics_calculator.sql`
  - itt van a `run_manufacturing_metrics`, amely a `time-best` objektivhoz
    mar letezo truth.
- `api/services/run_snapshot_builder.py`
  - megerositi, hogy a snapshot `parts_manifest_jsonb` tartalmazza a
    `required_qty` + `placement_priority` adatokat.
- `worker/result_normalizer.py`
  - megerositi, hogy az unplaced projection `part_revision_id` szinten
    persisted, igy a priority-fulfilment read-side szamithato.
- `api/main.py`
  - ide kell majd az uj objective query route bekotese.

### Konkret elvarasok

#### 1. Ez a task read-side query/projection legyen, ne uj persisted truth
A T3 ne vezessen be uj DB truth tablat csak azert, hogy objective-toplistat
adjon. A task outputja itt minimalisan:
- dedikalt service;
- dedikalt route;
- objective projection payload(ok).

Ez a task szandekosan **nem** H3-E5-T2 comparison projection builder.
Itt meg nincs full batch summary, nincs dashboard payload, nincs comparison
history.

#### 2. A query csak a mar letezo persisted truthokra epuljon
A service csak read-side modon dolgozzon. Minimum input truthok:
- `app.run_batches`
- `app.run_batch_items`
- `app.run_ranking_results`
- `app.run_evaluations`
- `app.run_metrics`
- `app.run_manufacturing_metrics`

A `priority-best` objectivehoz megengedett tovabbi read-side truthok:
- `app.nesting_run_snapshots` (`parts_manifest_jsonb`)
- `app.run_layout_unplaced`

Tiltas:
- ne toltsd le a nyers solver artifactokat es ne viewer-route parse-bol
  epits objective view-t, ha a persisted truth mar eleg;
- ne triggereld automatikusan a ranking vagy evaluation service-t;
- ne irj vissza semmilyen comparison, ranking, evaluation vagy selection tablat.

Ha a batchhez nincs persisted ranking, a task ne gyartson hallgatozo fallbackot.
Jo irany:
- `batch ranking not found` jellegu hiba, vagy egyertelmu `status=unavailable`
  valasz, de **ne** on-the-fly ranking.

#### 3. Legyen explicit objective-contract, de ne legyen kitalalt uzleti koltseg
A task kezelje minimum ezeket az objective kulcsokat:
- `material-best`
- `time-best`
- `priority-best`
- `cost-best`

A valos repo truthok alapjan:
- `material-best` aktiv es kiszamithato;
- `time-best` aktiv es kiszamithato;
- `priority-best` aktiv es kiszamithato read-side modon snapshot + unplaced
  projection alapjan;
- `cost-best` **queryelheto objective nevkent**, de ne talalj ki hozza ad-hoc
  pseudo-koltseg formulat, mert a koltseg truth a H3-E5 business metrics
  felelossege.

Ezert a `cost-best` elvart kezelese:
- route- es service-szinten letezo objective legyen;
- a valasz legyen explicit pl. `status="unsupported_pending_business_metrics"`
  vagy ezzel egyenerteku allapot;
- reason payload mondja ki, hogy a `run_business_metrics` / explicit cost truth
  hianyzik, es a task nem gyart koltseg-proxyt.

#### 4. A `material-best` projection a jelenlegi H1/H2 truthon alapuljon
A `material-best` ne a persisted `total_score` aliasa legyen.
A projection minimum hasznalja:
- `run_metrics.utilization_ratio` DESC
- `run_metrics.used_sheet_count` ASC
- `run_metrics.unplaced_count` vagy azzal ekvivalens hianymertek ASC
- `run_metrics.remnant_value` DESC, ha jelen van
- terminal fallbackkent a persisted `run_ranking_results.rank_no` ASC es
  `run_id` ASC

A reason payloadban latszodjon:
- a felhasznalt metric snapshot;
- hogy objective-level rendezes tortent, nem uj total_score kepzes;
- hogy az utolso fallback a persisted ranking lett.

#### 5. A `time-best` projection a manufacturing truthon alapuljon
A `time-best` minimum a mar letezo manufacturing truthra epuljon:
- `run_manufacturing_metrics.estimated_process_time_s` ASC

Javasolt fallback:
- `run_metrics.used_sheet_count` ASC
- `run_metrics.utilization_ratio` DESC
- `run_ranking_results.rank_no` ASC
- `run_id` ASC

A task ne talaljon ki kulon scheduler-, labor- vagy operator-koltseg modellt.
Itt csak az explicit H2 manufacturing timing truth az elfogadott forras.

#### 6. A `priority-best` legyen egyszeru, de valos read-side priority fulfilment
A priority objectivehoz ne vezess be uj business metrics tablat.
A jelenlegi truthokbol mar kiszamithato egy minimalis, deterministic
`priority_fulfilment_ratio` projection.

Jo, repohoz illo minimum:
- a service loadolja a run snapshot `parts_manifest_jsonb` tartalmat;
- a snapshotban levo `required_qty` es `placement_priority` alapjan kepezzen
  per-part demand sulyt;
- a `run_layout_unplaced` alapjan szamolja ki a meg nem teljesult mennyiseget;
- a teljesitett mennyiseg = `required_qty - remaining_qty`;
- a sulyozas legyen explicit es kodban dokumentalt, peldaul:
  - `priority_weight = 101 - placement_priority`
    (mivel kisebb `placement_priority` jelenti a fontosabb elemet);
- a `priority_fulfilment_ratio` = teljesitett sulyozott mennyiseg /
  teljes sulyozott igeny;
- tie/fallback:
  - `priority_fulfilment_ratio` DESC
  - magas-prioritasu hiany suly ASC
  - `run_metrics.unplaced_count` ASC
  - `run_ranking_results.rank_no` ASC
  - `run_id` ASC

A reason payload mutassa:
- a priority ratio szamitas rovid kepletet;
- a teljes demand es fulfilled demand snapshotjat;
- a legfontosabb hianyzo tetel(ek)et, ha vannak;
- hogy ez read-side projection, nem persisted business metric truth.

#### 7. Az objective projection payload legyen auditálhato
A projection response minimum tartalmazza:
- `objective`
- `status`
- `batch_id`
- `run_id` (ha van winner)
- `rank_no` (ha van)
- `candidate_label` (ha van)
- `objective_value`
- `objective_reason_jsonb`

Az `objective_reason_jsonb` minimum tartalma:
- `source_tables`
- `metric_snapshot`
- `ordering_trace`
- `used_fallbacks`
- `unsupported_reason` vagy `missing_sources`, ha relevans

Nem cel a teljes evaluation/ranking payload duplikalasa.
A projection legyen tomor, de visszakeresheto.

#### 8. A route maradjon objective-query domain, ne teljes comparison API
Keszits minimalis backend kontraktust legalabb erre:
- `GET /projects/{project_id}/run-batches/{batch_id}/best-by-objective`
- opcionálisan: `GET /projects/{project_id}/run-batches/{batch_id}/best-by-objective/{objective}`

A route viselkedese:
- egy batch persisted ranking halmazara epit;
- read-only;
- objective projectiont ad;
- nem ad full comparison summaryt;
- nem allit be preferred/selected run allapotot;
- nem nyit review workflowt.

#### 9. A task ne csusszon at H3-E5 / H3-E6 / H3-E7 iranyba
Ez a task meg nem:
- `run_business_metrics`;
- comparison dashboard summary;
- selected run / approved run workflow;
- multi-run pilot;
- remnant reuse dontestamogatas.

A T3 csak annyit szallit le, hogy a batch ranking truth folott legyenek
objective-specifikus, magyarazhato top-candidate queryk.

#### 10. A smoke bizonyitsa a fo objective-agakat
A task-specifikus smoke legalabb ezt bizonyitsa:
- `material-best` visszaadja a vart top run-t a run metrics alapjan;
- `time-best` visszaadja a vart top run-t a manufacturing timing alapjan;
- `priority-best` kiszamithato snapshot + unplaced truthbol;
- `cost-best` explicit unsupported/allapotolt valaszt ad, nem kitalalt proxy-t;
- a batchhez ranking hianyaban nem indul csendes fallback ranking;
- idegen owner batch nem queryzheto;
- az objective route read-only, nincs ranking/evaluation/selection/business write;
- ismetelt hivasra az objective winner deterministicen ugyanaz.

### DoD
- [ ] Keszult dedikalt best-by-objective service reteg.
- [ ] Keszult dedikalt best-by-objective route.
- [ ] A route be van kotve az `api/main.py`-ba.
- [ ] A task nem vezet be uj persisted comparison truth tablat.
- [ ] A query a mar letezo persisted ranking/evaluation/metrics truthra epul.
- [ ] `material-best` lekerdezheto valos metric orderinggel.
- [ ] `time-best` lekerdezheto valos manufacturing timing orderinggel.
- [ ] `priority-best` lekerdezheto read-side projectionkent snapshot + unplaced truth alapjan.
- [ ] `cost-best` expliciten kezelt, de nem kitalalt uzleti koltsegformula.
- [ ] A projection payload auditálhato objective reason-t ad.
- [ ] A task nem ir `run_evaluations`, `run_ranking_results`, `project_selected_runs` vagy `run_business_metrics` tablaba.
- [ ] Keszult task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t3_best_by_objective_lekerdezesek.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task full comparison projection builderre hizik;
  - a `cost-best` objectivehez ad-hoc uzleti formula lesz kitalalva;
  - a priority objective raw artifact parse-ra tamaszkodik a persisted truth
    helyett;
  - a service csendben rankinget/evaluationt triggerel, ha hianyos az input;
  - a route selected-run vagy business metrics side effectet okoz.
- Mitigacio:
  - explicit no-migration / no-write boundary;
  - objective-szintu source trace;
  - `cost-best` unsupported contract;
  - persisted truth-first priority fulfilment szamitas;
  - smoke no-write es no-fallback ranking agakkal.
- Rollback:
  - service + route + smoke + docs egy task-commitban visszavonhato;
  - nincs uj DB truth, igy a rollback egyszerubb.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t3_best_by_objective_lekerdezesek.md`
