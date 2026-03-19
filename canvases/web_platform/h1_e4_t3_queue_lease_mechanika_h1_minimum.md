# H1-E4-T3 Queue lease mechanika (H1 minimum)

## Funkcio
A feladat a H1-E4 run orchestration kovetkezo lepese: a H1-E4-T2-ben mar
queued allapotban letrejovo canonical runokat a worker oldalrol kontrollaltan
fel lehessen venni ugy, hogy ugyanaz a queue sor ne fusson egyszerre ket
workerrel.

Ez a task tudatosan **nem** solver futtatas, **nem** result normalizer,
**nem** artifact/projection workflow es **nem** teljes retry-policy redesign.
A cel kizarolag az, hogy a `app.run_queue` H0 truth alapjan legyen egy
stabil, H1 minimum lease mechanika.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit queue lease helper / service bevezetese worker-oldalon;
  - atomikus claim a kovetkezo futtathato queue sorra;
  - `lease_token`, `leased_by`, `leased_at`, `heartbeat_at`,
    `lease_expires_at`, `attempt_no`, `attempt_status` canonical kezelese;
  - controlled heartbeat a meglevo lease meghosszabbitasara;
  - minimalis expired-lease reclaim szemantika;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - solver process inditas;
  - raw output / result / projection / artifact pipeline;
  - terminalis `done` / `error` / `cancelled` lifecycle teljes bevezetese;
  - teljes retry-budget, backoff vagy worker scheduling ujratervezese;
  - run create flow ujranyitasa.

### Talalt relevans fajlok
- `worker/main.py`
  - letezo worker loop, benne inline claim/heartbeat SQL-lel.
- `worker/README.md`
  - worker runtime es queue loop dokumentacio.
- `api/services/run_creation.py`
  - H1-E4-T2 queued run create forras, ami a lease mechanika bemenetet adja.
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
  - `app.run_queue` canonical mezok es check-ek.
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
  - worker lease service celjai.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E4-T3 task source-of-truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - lease / retry / snapshot-first hatarok.

### Konkret elvarasok

#### 1. A task a H0 canonical queue truth-ra uljon
A lease mechanika kizarolag a meglevo canonical tablavilagra epuljon:
- `app.run_queue`
- `app.nesting_runs`
- `app.nesting_run_snapshots`

Ne vezess vissza public/phase1 queue vilagot es ne talalj ki kulon H1-only
queue tablat.

#### 2. Keszuljon explicit worker-side lease helper
A jelenlegi inline SQL a `worker/main.py`-ban tul sok mechanikat rejt egy helyre.
A task vezessen be explicit helper modult, peldaul `worker/queue_lease.py`, amely
legalabb ezt tudja:
- `claim_next_queue_lease(...)`
- `heartbeat_queue_lease(...)`

A `worker/main.py` ezeket hivja, ne sajat inline SQL stringek legyenek a
canonical lease truth.

#### 3. A claim legyen atomikus es duplafutas ellen vedett
A claim logika H1 minimum szinten is legyen atomikus:
- csak `available_at <= now()` sor johet szoba;
- csak `queue_state='pending'` vagy kontrollaltan lejart lease-elt sor
  veheto fel ujra;
- `for update skip locked` / ezzel egyenerteku atomikus mechanika maradjon;
- egy claim siker eseten a sor keruljon `queue_state='leased'` allapotba;
- toltsuk a canonical lease mezoket:
  - `leased_by`
  - `lease_token`
  - `leased_at`
  - `heartbeat_at`
  - `lease_expires_at`
  - `attempt_no`
  - `attempt_status='leased'`

A cel az, hogy ugyanazt a run-t ket worker egyszerre ne tudja ervenyesen
maganak claimelni.

#### 4. A lease idotartam legyen explicit es ne implicit 10 perces magic
A jelenlegi worker kodigozott, `leased_at < now() - interval '10 minutes'`
logikaja ne maradjon a canonical megoldas.

Legyen egy explicit H1 minimum lease ido, amelyet a helper kap meg (pl.
`lease_ttl_seconds`), es ebbol szamolja a `lease_expires_at` mezot.
A heartbeat ezt a mezot tolja tovabb, ne csak a `leased_at`-ot frissitse.

#### 5. Heartbeat legyen tokenhez kotott
A heartbeat csak akkor legyen ervenyes, ha a worker a megfelelo:
- `run_id`
- `lease_token`
- `leased_by`
- `queue_state='leased'`

kombinacioval hivja.

Ha a lease mar elveszett / atvette mas worker / lejart es visszakerult,
akkor a helper adjon kontrollalt visszajelzest, ne csendben irjon rossz sorba.

#### 6. Expired lease reclaim legyen minimalisan rendezett
H1 minimum szinten eleg a kontrollalt reclaim:
- lejart lease felveheto legyen uj worker altal;
- uj `lease_token` jojjon letre;
- a report mondja ki pontosan, hogy ilyenkor mi tortenik a
  `retry_count`-tal es az `attempt_no`-val.

Nem kell ebben a taskban teljes retry-policy vagy terminalis fail-flow.

#### 7. A task ne csusszon at solver / result scope-ba
Ebben a taskban meg nincs:
- snapshot -> solver input mapping;
- solver process start;
- stdout/stderr raw output mentes;
- `queue_state='done'/'error'` vegleges lifecycle;
- run result / layout / projection / artifact toltes.

A lease mechanika itt csak worker pickup + heartbeat + expired reclaim szinten
zarodjon.

#### 8. A smoke bizonyitsa a fo lease agak
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- pending sor sikeresen lease-elheto;
- masodik worker ugyanazt az aktiv lease-t nem tudja dupla-claimelni;
- heartbeat a jo tokennel meghosszabbitja a lease-t;
- rossz tokennel / rossz workerrel a heartbeat kontrollaltan elutasitodik;
- lejart lease ujra claimelheto mas worker altal;
- a claim payload tartalmazza legalabb a `run_id`, `snapshot_id`,
  `lease_token`, `lease_expires_at`, `attempt_no` mezoket.

### DoD
- [ ] Keszul explicit worker-side lease helper (pl. `worker/queue_lease.py`).
- [ ] A helper a H0 canonical `app.run_queue` mezokre epit.
- [ ] A claim logika atomikus es duplafutas ellen vedett.
- [ ] Sikeres claim eseten a sor `queue_state='leased'` allapotba kerul.
- [ ] A canonical lease mezok toltesre kerulnek (`leased_by`, `lease_token`, `leased_at`, `heartbeat_at`, `lease_expires_at`).
- [ ] A `attempt_no` / `attempt_status` legalabb H1 minimum szinten ertelmesen frissul.
- [ ] A heartbeat tokenhez kotott es kontrollaltan kezeli a lost-lease helyzetet.
- [ ] Van minimalis expired-lease reclaim szemantika.
- [ ] A `worker/main.py` a helperre van realignalva, nem inline SQL a canonical truth.
- [ ] A task nem csuszik at solver/result/artifact scope-ba.
- [ ] Keszul task-specifikus smoke script a fo lease agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a helper nem marad atomikus, es a duplafutas elleni vedelem gyengul;
  - a lease TTL tovabbra is implicit magic number marad;
  - a heartbeat rossz tokennel is ervenyesul;
  - a task atcsuszik solver-worker orchestration scope-ba.
- Mitigacio:
  - a helper a canonical H0 queue mezokre es lockolasra epuljon;
  - a TTL legyen explicit parameter / config;
  - a heartbeat legyen tokenhez kotott;
  - maradj claim + heartbeat + expired reclaim szinten.
- Rollback:
  - a helper + worker valtozasok egy task-commitban visszavonhatok;
  - schema-modositas csak akkor johet, ha bizonyithatoan elkerulhetetlen, es ezt a reportban ki kell mondani.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/queue_lease.py worker/main.py scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py`
  - `python3 scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `api/services/run_creation.py`
- `worker/main.py`
- `worker/README.md`
