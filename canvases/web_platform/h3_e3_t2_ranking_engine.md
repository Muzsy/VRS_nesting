# H3-E3-T2 Ranking engine

## Funkcio
Ez a task hozza be a H3 evaluation-vonal masodik, batch-szintu truth reteget.
A cel, hogy egy mar meglevo batch candidate runjai a mar persisted
`run_evaluations` truth alapjan stabil, reprodukalhato es indokolhato sorrendet
kapjanak, kulon `run_ranking_results` truth-ban tarolva.

A jelenlegi repoban mar megvan:
- a H3 batch truth (`app.run_batches`, `app.run_batch_items`);
- a H3 batch orchestrator, amely candidate runokat kot a batchhez;
- a H3 evaluation truth (`app.run_evaluations`), komponensbontasokkal,
  threshold eredmenyekkel es tie-breaker input snapshotokkal;
- a scoring profile/version domain, amely a tie-breaker es threshold policy
  forrasa.

Ez a task ezekre epulve **nem comparison projection**, **nem best-by-objective**,
**nem business metrics**, **nem remnant/inventory** es **nem human selection
workflow**, hanem a legelso persisted batch ranking truth-ot szallitja le.

A hangsuly most azon van, hogy:
- a ranking ne frontendben osszerakott lista legyen;
- a sorrend ugyanarra az inputra mindig ugyanugy keletkezzen;
- a tie-break dontesek visszakereshetok legyenek;
- a ranking ne szamoljon uj score-t, hanem a mar persisted evaluation truth-ra
  epuljon.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_ranking_results` tabla bevezetese;
  - dedikalt ranking service;
  - batchszintu ranking calculate/replace/read workflow;
  - deterministic tie-breaker logika es ranking reason payload;
  - minimalis ranking route a batch ranking ujraszamitasara es visszaolvasasara;
  - task-specifikus smoke a sikeres, hibas es hatarscope agakra.
- Nincs benne:
  - score ujraszamitas vagy `run_evaluations` write;
  - batch orchestrator ujranyitasa;
  - comparison projection vagy batch summary projection;
  - best-by-objective toplistak;
  - `project_selected_runs`, `run_reviews` vagy jovahagyasi workflow;
  - business metrics, remnant vagy inventory-aware input resolver;
  - worker/scheduler vagy H1/H2 truth pipeline modositas.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - source-of-truth task tree; a H3-E3-T2 outputja: `run_ranking_results`.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - a H3 detailed doc SQL-vazlata a `run_ranking_results` tablára, es a
    ranking engine felelossege: batchen beluli sorrend + tie-break + indoklas.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - a P2-B4 backlog megerositi: batch candidate-ek sorrendje,
    `run_ranking_results` es ranking reason.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a ranking kulon decision truth legyen, ne frontend-only
    lista es ne comparison/business workflow.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - fontos boundary: a ranking a mar letrejott run/evaluation truthra epul,
    nem nyitja ujra a snapshot builder vagy run create szerzodeseket.
- `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql`
  - a batch es batch-item truth, amelyhez a ranking kotodik.
- `api/services/run_batches.py`
  - a batch owner/project scope validalas referenciaja.
- `api/services/run_batch_orchestrator.py`
  - megerositi, hogy a candidate kontextus a batch-item truthban mar elerheto.
- `supabase/migrations/20260324140000_h3_e3_t1_run_evaluation_engine.sql`
  - a ranking input truthja: `app.run_evaluations`.
- `api/services/run_evaluations.py`
  - mutatja a persisted evaluation payload szerkezetet:
    `total_score`, `evaluation_jsonb.components`, `threshold_results`,
    `tie_breaker_inputs`, `warnings`, `scoring_profile_snapshot`.
- `api/routes/run_evaluations.py`
  - minta a dedicated H3-E3 route kontraktusra.
- `api/main.py`
  - ide kell majd az uj ranking route bekotese.

### Konkret elvarasok

#### 1. Kulon persisted ranking truth kell, de batchenkent canonical replace halmazzal
A task vezesse be a H3 detailed docban javasolt:
- `app.run_ranking_results`

Minimum elvart mezo-struktura:
- `id`
- `batch_id` (FK `app.run_batches`)
- `run_id` (FK `app.nesting_runs`)
- `rank_no`
- `ranking_reason_jsonb`
- `created_at`

A H3 doksi egyertelmu kontraktusat tartsd meg:
- egy batchhez egy canonical ranking halmaz tartozik;
- ujrarankolas ugyanarra a batchre replace-eli a korabbi ranking sorokat;
- egy run batchen belul legfeljebb egyszer szerepelhet;
- ugyanazon batchen belul egy `rank_no` csak egyszer fordulhat elo.

Ez a task **nem** vezet be ranking history tablat es nem tarol tobb alternativ
rangsort ugyanarra a batchre ugyanabban a truth retegben.

#### 2. A ranking kizarolag a mar persisted batch + evaluation truthra epuljon
A ranking engine ne szamoljon uj score-t, ne toltsn uj run metrikakat, es ne
hivja meg az evaluation calculate pathot.
A service legalabb ezeket a truthokat olvassa:
- `app.run_batches`
- `app.run_batch_items`
- `app.run_evaluations`
- opcionalisan a kapcsolodo `app.scoring_profile_versions`, ha a tie-breaker
  policy vagy indoklas ezt tenylegesen igenyli

A ranking task explicit boundary-je:
- nincs `run_evaluations` ujraszamitas;
- nincs H1/H2 metrika ujraolvasas scorekepzeshez;
- nincs batch auto-orchestration vagy uj queued run inditas.

Ha egy batch-item runjahoz nincs persisted evaluation, a ranking ne talaljon ki
reszleges sorrendet. Jo alapertelmezett irany:
- **fail-fast** a teljes batch rankingre, dokumentalt hibaokkal.

#### 3. Az evaluation es a batch-item scoring kontextus legyen konzisztens
A batch-item truth mar tarolhat `scoring_profile_version_id`-t.
A ranking engine legalabb ezt ellenorizze:
- ha a batch-itemben van `scoring_profile_version_id`, akkor a kapcsolodo
  `run_evaluations.scoring_profile_version_id` egyezzen vele;
- ha elteres van, a ranking hibat adjon, ne rangsoroljon csendes kevert
  allapottal;
- ha a batch-itemben nincs scoring version, de az evaluationben van,
  a ranking mukodhet, de a `ranking_reason_jsonb` jelezze, hogy a batch-item
  scoring context hianyos volt.

A task ne vezessen be evaluation-repair vagy batch-item backfill logikat.
A ranking itt csak validalja a konzisztenciat es a mar letrejott truthot
hasznalja.

#### 4. A sorrend legyen stabil es determinisztikus, expliciten dokumentalt tie-breakkel
A ranking alapja:
- elsoleges rendezes: `run_evaluations.total_score` csokkeno sorrendben.

Ha ket candidate azonos `total_score`-t kap, akkor deterministic tie-break kell.
Jo, repohoz illo minimum:
- eloszor probald alkalmazni a scoring profile / evaluation altal ismert
  tie-breaker inputokat a `evaluation_jsonb.tie_breaker_inputs` alapjan;
- csak ismert, osszehasonlithato kulcsokat hasznalj;
- ha ez nem dont, akkor canonical fallback legyen, peldaul:
  - `utilization_ratio` DESC
  - `unplaced_ratio` ASC
  - `used_sheet_count` ASC
  - `estimated_process_time_s` ASC, ha mindket oldalon van
  - `candidate_label` ASC
  - `run_id` ASC

Fontos:
- a fallback sorrend legyen kodban es reportban nevesitve;
- ugyanarra a batch truthra a ranking minden futasban ugyanazt a sorrendet adja;
- a task ne hasznaljon nem determinisztikus rendezesi fogasokat vagy SQL
  implicit orderre epulo logikat.

#### 5. A ranking_reason_jsonb legyen eleg reszletes az auditalthatosaghoz
A `ranking_reason_jsonb` minimum tartalmazza:
- a `total_score` snapshotjat;
- a hasznalt `scoring_profile_version_id`-t;
- a `candidate_label`-t, ha van;
- a tie-breakhez felhasznalt inputokat vagy a tie-break trace-et;
- azt, hogy profile-defined tie-break vagy canonical fallback dontott-e;
- relevans warningokat (peldaul hianyzo batch-item scoring context);
- olyan rovid score-summaryt, amibol latszik, hogy a ranking a persisted
  evaluation truthra epult.

Nem cel a teljes `evaluation_jsonb` duplikalasa a ranking sorban.
A ranking reason legyen tomor, de auditálhato.

#### 6. A route maradjon ranking-domain, ne csusszon at comparisonba
Keszits minimalis backend kontraktust legalabb erre:
- `POST /projects/{project_id}/run-batches/{batch_id}/ranking`
- `GET /projects/{project_id}/run-batches/{batch_id}/ranking`
- opcionálisan `DELETE /projects/{project_id}/run-batches/{batch_id}/ranking`

A POST ujraszamolhatja vagy replace-elheti a batch rankinget.
A GET rank szerint rendezett listat adjon vissza.

A route maradjon tisztan ranking-domain:
- ne gyartson comparison summaryt;
- ne adjon objective-specifikus toplistakat;
- ne allitson preferred/selected run allapotot.

#### 7. A task ne csusszon at H3-E3-T3 / H3-E5 / H3-E6 iranyba
Ez a task meg nem:
- `best-by-objective` projection;
- comparison dashboard jellegu summary;
- `project_selected_runs`;
- `run_reviews`;
- `run_business_metrics`;
- remnant vagy inventory truth.

A H3-E3-T2 csak azt szallitja le, hogy egy batch candidate-halmazbol legyen
persisted, stabil es indokolhato rangsor.

#### 8. A smoke script bizonyitsa a fo ranking agak teljes kepet
A task-specifikus smoke legalabb ezt bizonyitsa:
- tobb evaluated batch-itembol ranking sikeresen keletkezik;
- a `rank_no` egyedi es stabil;
- ujrarankolas replace-eli a korabbi ranking sorokat;
- azonos `total_score` eseten a tie-break determinisztikusan ugyanarra a
  sorrendre jut;
- hianyzo evaluation eseten a ranking hibat ad;
- evaluation / batch-item scoring version mismatch eseten a ranking hibat ad;
- idegen owner batch nem rangsorolhato;
- nincs `run_evaluations` write, comparison projection vagy selection side
  effect.

### DoD
- [ ] Letrejott az `app.run_ranking_results` persisted truth reteg.
- [ ] Egy batch candidate-halmazahoz reprodukalhato ranking kepezheto.
- [ ] A ranking kizarolag a mar persisted batch + evaluation truthra epul.
- [ ] Hianyzo evaluation eseten a task nem gyart reszleges sorrendet.
- [ ] A batch-item scoring context es az evaluation scoring context konzisztenciaja ellenorzott.
- [ ] Azonos `total_score` eseten deterministic tie-break logika ervenyesul.
- [ ] A `ranking_reason_jsonb` auditálhato indoklast es tie-break trace-et tarol.
- [ ] Keszult minimalis POST / GET (es ha kell DELETE) ranking backend contract.
- [ ] A task nem csuszik at comparison / selected-run / business-metrics scope-ba.
- [ ] Keszult task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t2_ranking_engine.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a ranking ujraszamolja vagy megkeruli az evaluation truthot;
  - implicit SQL order vagy instabil Python rendezesi kulcs miatt a sorrend nem
    reprodukalhato;
  - a task comparison vagy selected-run workflowt is becsempesz;
  - kevert batch-item / evaluation scoring context csendben atcsuszik;
  - a ranking reason tul sovany, es utolag nem magyarazhato vissza a sorrend.
- Mitigacio:
  - explicit persisted-input boundary (`run_batches`, `run_batch_items`,
    `run_evaluations`);
  - dokumentalt, kodolt tie-break sorrend;
  - mismatch es hianyzo evaluation fail-fast kezelese;
  - explicit no-comparison / no-selected-run / no-business-metrics boundary.
- Rollback:
  - a migration + service + route + smoke egy task-commitban visszavonhato;
  - a H3-E2 batch truth es a H3-E3-T1 evaluation truth erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t2_ranking_engine.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_rankings.py api/routes/run_rankings.py api/main.py scripts/smoke_h3_e3_t2_ranking_engine.py`
  - `python3 scripts/smoke_h3_e3_t2_ranking_engine.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql`
- `supabase/migrations/20260324140000_h3_e3_t1_run_evaluation_engine.sql`
- `api/services/run_batches.py`
- `api/services/run_batch_orchestrator.py`
- `api/services/run_evaluations.py`
- `api/routes/run_evaluations.py`
- `api/main.py`
