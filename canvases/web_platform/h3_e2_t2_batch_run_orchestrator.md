# H3-E2-T2 Batch run orchestrator

## Funkcio
Ez a task hozza be a H3 batch-vonal elso aktiv vezérlési retegét.
A cel, hogy egy batch-hez több candidate run létrehozható legyen ugyanarra a
projektre, különböző strategy/scoring kombinációkkal és auditálható candidate
címkékkel, a meglévő H1 run-create flow újrahasználásával.

A task **azzal az explicit munkafeltetelezessel** keszul, hogy a
`H3-E1-T3 – Project-level selectionok` mar elkeszult, meg akkor is, ha a
mostani zipben ennek artefaktjai nem latszanak.

Ez a task szandekosan nem evaluation engine, nem ranking engine, nem comparison
projection es nem review workflow. A fokusz most azon van, hogy a H3-E2-T1-ben
letett batch truth-ra epulve kontrollaltan es reprodukalhatoan tobb queued run
keletkezzen, batch-item bindinggal es candidate metadata-val.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - dedikalt batch orchestrator service;
  - strategy/scoring kombinaciok vagy candidate lista alapjan tobb queued run
    letrehozasa ugyanarra a projektre;
  - a H1-E4-T2 canonical run creation service ujrahasznalata;
  - batch record es batch item rekordok osszehangolt letrehozasa;
  - candidate_label kezeles;
  - minimalis orchestrator endpoint a batch inditasahoz;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - evaluation engine;
  - ranking engine;
  - comparison projection;
  - selected/preferred run workflow;
  - remnant/inventory resolver;
  - worker/scheduler redesign.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H3-E2-T2 task: batch orchestrator service.
- `docs/web_platform/roadmap/dxf_nesting_platform_h3_reszletes.md`
  - a batch orchestrator kulcsfeladatai: tobb run, strategy/scoring kombinaciok,
    batch/item rekordok, candidate label.
- `docs/web_platform/roadmap/dxf_nesting_platform_priorizalt_sprint_backlog_p0_p1_p2.md`
  - a P2-B2 backlog-szekcio megerositi: strategy variansokkal tobb run.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - fontos boundary: a canonical run create tovabbra is snapshot-first.
- `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql`
  - a batch truth, amelyre az orchestrator raepul.
- `api/services/run_creation.py`
  - a canonical queued run create szolgaltatas H1-bol.
- `api/routes/runs.py`
  - referencia a mar meglevo run create API-hoz.
- `api/services/run_batches.py`
  - a batch CRUD truth-service, amelyhez az orchestrator itemeket kapcsol.
- `api/main.py`
  - route-regisztracios pont.

### Konkret elvarasok

#### 1. Az orchestrator a canonical run create-ra epuljon
Az uj batch orchestrator ne sajat maga epitsen inline run/snapshot/queue
rekordokat.
A canonical create mechanika mar letezik H1-E4-T2-ben.

Minimum elvaras:
- az orchestrator a batch candidate-ekhez a canonical run create service-t
  hivja;
- a keletkezo queued run-okat azonnal batch-itemekhez kotje;
- a batch/item truth maradjon az egyetlen binding source-of-truth.

#### 2. A candidate-ek strategy/scoring kombinaciokkal vagy explicit listaval jojjenek letre
Az orchestrator legalabb egy minimalis request contractot tamogasson, amelyben
megadhato:
- a `batch_kind`
- opcionális `notes`
- candidate lista, ahol kandidansonkent megadhato:
  - `candidate_label`
  - `strategy_profile_version_id`
  - `scoring_profile_version_id`
  - opcionálisan `run_purpose` / `idempotency_key` jellegu mezok, ha ez a
    canonical run create contracttal tisztan osszefesulheto.

Az orchestrator ne talaljon ki teljes H3 strategy-varians generatort.
A cel most egy kontrollalt, explicit candidate lista feldolgozasa.

#### 3. A projekt owner es version owner validacio legyen eros
Az orchestrator csak olyan candidate-et indithasson, ahol:
- a projekt a jelenlegi ownerhez tartozik;
- a strategy/scoring version a jelenlegi owner scope-jaban van;
- a candidate adatok konzisztensen batch-itembe irhatok.

Ha valamelyik candidate hibas, a tasknak explicit modon el kell dontenie, hogy:
- fail-fast tranzakciosan megall, vagy
- reszleges siker modot vallal.

A reportban ezt nev szerint ki kell mondani.
Jo alapertelmezett irany: **fail-fast**, hogy a batch truth ne maradjon
felemás candidate-allapottal.

#### 4. A task ne csusszon at evaluation/ranking iranyba
A batch orchestrator a runok inditasarol es batch-bindingrol szol.
Nem szabad ebben a taskban bevezetni:
- `run_evaluations`
- `run_ranking_results`
- score calculation
- ranking reason
- comparison view

#### 5. A smoke bizonyitsa a fo orchestrator agakra
A task-specifikus smoke legalabb ezt bizonyitsa:
- uj batch tobb candidate-del letrehozhato;
- minden candidate-hez queued run keletkezik a canonical H1 create flow-val;
- a keletkezo runok batch-itemkent visszakapcsolodnak a batchhez;
- a `candidate_label` es strategy/scoring kontextus tarolodik;
- idegen owner strategy/scoring versionnel a batch create elutasitodik;
- hiba eseten a fail-fast szemantika ervenyesul;
- nincs evaluation/ranking side effect.

### DoD
- [ ] Keszult dedikalt batch orchestrator service.
- [ ] Az orchestrator a canonical H1 run create szolgaltatasra epul.
- [ ] Egy batchhez tobb candidate queued run letrehozhato.
- [ ] A keletkezo runok batch-itemekkel ossze vannak kotve.
- [ ] A candidate_label es a strategy/scoring kontextus visszakeresheto.
- [ ] A project owner es version owner validacio eros.
- [ ] A task explicit fail-fast vagy dokumentalt partial-success szemantikat vallal.
- [ ] A task nem csuszik at evaluation / ranking / comparison scope-ba.
- [ ] Keszult task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon frissitve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t2_batch_run_orchestrator.md` PASS.

### Kockazat + rollback
- Kockazat:
  - az orchestrator megkeruli a canonical H1 run create flow-t;
  - a batch truth es a run create truth szetcsuszik;
  - a candidate lista kezeles reszleges hibanal felemás batch-allapotot hagy;
  - a task evaluation/ranking logikat is becsempesz.
- Mitigacio:
  - explicit H1-E4-T2 dependency es reuse;
  - batch item binding kozvetlenul a run create utan;
  - dokumentalt fail-fast szemantika;
  - explicit no-evaluation / no-ranking boundary.
- Rollback:
  - az orchestrator service + route + smoke egy task-commitban visszavonhato;
  - a H3-E2-T1 batch truth es a H1 run create gerinc erintetlen marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t2_batch_run_orchestrator.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_batch_orchestrator.py api/routes/run_batches.py scripts/smoke_h3_e2_t2_batch_run_orchestrator.py`
  - `python3 scripts/smoke_h3_e2_t2_batch_run_orchestrator.py`
