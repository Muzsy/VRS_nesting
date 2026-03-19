# H1-E4-T2 Run create API/service (H1 minimum)

## Funkcio
A feladat a H1-E4 run orchestration kovetkezo lepese: a H1-E4-T1-ben letett
explicit snapshot builderre epitve tenyleges run create flow bevezetese, amely
projekt truth-bol snapshotot epit, letrehozza a `nesting_runs` +
`nesting_run_snapshots` + `run_queue` rekordokat, majd queued allapotban
visszaadja a run-ot.

Ez a task tudatosan **nem** worker lease, **nem** solver futtatas, **nem**
result normalizer es **nem** artifact workflow. A cel kizarolag az, hogy a
projekt aktualis H0/H1 truth-jabol egy szabalyos, queued run keletkezzen.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit run creation service bevezetese;
  - a H1-E4-T1 snapshot builder hasznalata canonical forraskent;
  - `app.nesting_runs`, `app.nesting_run_snapshots`, `app.run_queue` rekordok
    letrehozasa H0 schema szerint;
  - minimalis create endpoint a queued run inditasahoz;
  - idempotencia / snapshot-dedup kezeles H1 minimum szinten;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - worker lease mechanika;
  - solver process inditas;
  - queue worker altali felvetel;
  - run result / projection / artifact toltese;
  - run list / log / artifact endpoint teljes ujratervezese.

### Talalt relevans fajlok
- `api/services/run_snapshot_builder.py`
  - a H1-E4-T1 canonical snapshot builder service.
- `api/routes/runs.py`
  - letezo run route, benne legacy create flow-val.
- `api/sql/phase4_run_quota_atomic.sql`
  - legacy / referencia helper, de nem source-of-truth a H0/H1 run create-hoz.
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
  - `app.nesting_runs` es `app.nesting_run_snapshots` truth.
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
  - `app.run_queue` truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - snapshot lifecycle + idempotencia / dedup elvek.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E4-T2 task source-of-truth.

### Konkret elvarasok

#### 1. A task a H0/H1 canonical tablavilagra uljon
A task kizarolag ezekre a meglevo tablákra epuljon:
- `app.nesting_runs`
- `app.nesting_run_snapshots`
- `app.run_queue`
- valamint a H1-E4-T1 builder altal olvasott canonical input truth.

Ne vezess vissza phase1/phase4 legacy run-config vagy ad hoc solver-input
vilagot a H1 minimum create flow-ba.

#### 2. A run create a H1-E4-T1 snapshot builderre epuljon
A run create service ne probaljon ujra sajat magatol projekt/technology/part/sheet
adatokat olvasni es manifestet epiteni. A canonical forras a
`build_run_snapshot_payload(...)` legyen.

A service folyamata H1 minimum szinten legyen egyertelmu:
1. project owner guard;
2. snapshot payload builder meghivasa;
3. run record letrehozasa;
4. snapshot record letrehozasa a builder payloadjabol;
5. queue record letrehozasa pending allapotban;
6. a run queued allapotban torteno visszaadasa.

#### 3. A run/snapshot statuszok legyenek H0 truth-kompatibilisek
A task ne talaljon ki uj statuszokat.
A minimum elvart kimenet:
- `app.nesting_runs.status = 'queued'`
- `app.nesting_run_snapshots.status = 'ready'`
- `app.run_queue.queue_state = 'pending'`

A `queued_at` / `available_at` mezok toltesenek H1 minimum szinten is
ertelmesnek es kovetkezetesnek kell lennie.

#### 4. Minimalis request contract, legacy inline config nelkul
A create flow H1 minimum szinten mar a projekt truth-bol dolgozik, ezert a
legacy inline `run_config` / `parts_config` / `stock_file_id` vilag ne maradjon
canonical create path.

A minimalis request kontraktus legyen egyszeru, peldaul:
- opcionális `idempotency_key`
- opcionális `run_purpose` (alapertelmezetten `nesting`)

Ha a letezo `POST /projects/{project_id}/runs` route marad, akkor a create agat
igazitsd a H1 minimum truth-hoz, de ne bontsd meg a list/log/artifact reszeket.

#### 5. Idempotencia es snapshot-dedup legyen explicit kezelve
Ez a pont itt kritikus, mert a H0 schema szerint a
`nesting_run_snapshots.snapshot_hash_sha256` unique.

Ezert a tasknak explicit modon kezelnie kell legalabb ezt:
- ha ugyanazzal az `idempotency_key`-jel ugyanarra a snapshotra mar letezik run,
  ne jojjon letre duplikat run;
- ha a canonical snapshot hash mar letezik, a service adjon egyertelmu,
  kontrollalt viselkedest (pl. meglevo run visszaadasa / dedup branch), ne nyers
  DB hibaval alljon meg;
- a report mondja ki, hogy a T2 pontosan milyen H1 minimum idempotencia
  szemantikat valosit meg.

#### 6. A task ne csusszon at lease / worker / result scope-ba
Ebben a taskban meg nincs:
- lease token kiosztas;
- `attempt_status` kezeles;
- worker pickup;
- solver process start;
- run result / layout / artifact toltes.

A queue rekord itt csak pending enqueue legyen.

#### 7. A smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- sikeres create eseten run + snapshot + queue rekord keletkezik;
- a snapshot builder payload valoban bekerul a snapshot sorba;
- a final run status queued, a snapshot ready, a queue pending;
- azonos idempotencia / dedup helyzet kontrollaltan kezelt;
- hiba jon idegen projektre;
- hiba jon builder-hibara (pl. missing technology / requirement / sheet input),
  es ilyenkor nem marad felig letrehozott queued run.

### DoD
- [ ] Keszul explicit `api/services/run_creation.py` service.
- [ ] A task a H0 `nesting_runs` + `nesting_run_snapshots` + `run_queue` tablavilagra epul.
- [ ] A service a H1-E4-T1 `build_run_snapshot_payload(...)` builderre epit.
- [ ] Sikeres create eseten queued run keletkezik.
- [ ] A snapshot row `status='ready'` allapotban jon letre a builder payloadjaval.
- [ ] A queue row `queue_state='pending'` allapotban jon letre.
- [ ] Az idempotencia / snapshot-dedup viselkedes explicit es kontrollalt.
- [ ] A task nem csuszik at lease/worker/result/artifact scope-ba.
- [ ] Ha a create endpoint marad a `api/routes/runs.py` alatt, csak a create agat igazitsa a canonical H1 flow-hoz.
- [ ] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task tovabbra is a legacy `enqueue_run_with_quota` helperre ul;
  - a snapshot hash unique miatt a create flow nyers DB hibaval elszall;
  - a create endpoint felig letrehozott run/snapshot/queue allapotot hagy maga utan;
  - a task atcsuszik lease/worker scope-ba.
- Mitigacio:
  - a canonical flow alapja a H1-E4-T1 builder + H0 tablavilag legyen;
  - dedup/idempotencia legyen kimondottan kezelve;
  - a create flow legyen egyertelmu es smoke-kal bizonyitott;
  - maradj pending enqueue szinten, lease nelkul.
- Rollback:
  - service/route/smoke valtozasok egy task-commitban visszavonhatok;
  - schema-modositas csak akkor johet, ha tenyleg elkerulhetetlen, es ezt a reportban ki kell mondani.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_creation.py api/routes/runs.py scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py`
  - `python3 scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `api/services/run_snapshot_builder.py`
- `api/routes/runs.py`
- `api/sql/phase4_run_quota_atomic.sql`
