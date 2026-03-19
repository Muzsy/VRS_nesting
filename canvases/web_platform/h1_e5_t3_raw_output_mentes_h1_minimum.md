# H1-E5-T3 Raw output mentes (H1 minimum)

## Funkcio
A feladat a H1-E5 harmadik, szukitett lepese: a H1-E5-T2-ben canonical solver
processre atallitott worker-futas nyers kimeneteinek visszakeresheto, H0-truth
szerinti tarolasa.

A scope most kifejezetten a **raw output** retegre korlatozodik:
- solver stdout/stderr,
- `solver_output.json`,
- minimalis runner meta/report,
- a mar meglevo `run.log` stabil, canonical kezelesenek rendbetetele.

Ez a task tudatosan **nem** result normalizer, **nem** projection feltoltes,
**nem** viewer artifact generalas es **nem** export pipeline. A cel az, hogy a
futas nyers bizonyiteka, hibalogja es nyers solver eredmenye visszakeresheto
legyen, fuggetlenul attol, hogy a kovetkezo H1-E6 normalizer blokk mikor fut.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit worker-oldali raw artifact persistence helper/service bevezetese;
  - canonical `run-artifacts` bucket + H0 path policy szerinti tarolas;
  - `app.run_artifacts` rekordok idempotens regisztralasa a raw outputokra;
  - success/failure/cancel/timeout esetekben is hasznos nyers bizonyitek
    megtartasa, ahol fajl tenylegesen rendelkezesre all;
  - task-specifikus smoke a canonical path, artifact-regisztracio es fo agak
    bizonyitasara.
- Nincs benne:
  - `run_layout_*` vagy `run_metrics` feltoltes;
  - solver output normalizalasa platformnyelvre;
  - SVG/DXF/export artifact generalas;
  - kulon artifact API vagy frontend viewer;
  - worker lease/run status mechanika ujranyitasa.

### Talalt relevans fajlok
- `worker/main.py`
  - jelenleg mar uploadal run-logot es teljes run_dir artifactokat, de ez a raw
    output scope szempontjabol meg inline/legacy jellegu es nem kovetkezetesen
    H0 canonical path-policy alapu.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - itt jon letre a `solver_output.json`, `solver_stdout.log`,
    `solver_stderr.log`, `runner_meta.json`.
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
  - canonical `run-artifacts` bucket + `projects/{project_id}/runs/{run_id}/...`
    path policy.
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - `app.run_artifacts` source-of-truth tabla.
- `supabase/migrations/20260318233000_worker_lifecycle_artifact_idempotency_guard.sql`
  - `(run_id, storage_path)` idempotency guard.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E5-T3 source-of-truth.

### Konkret elvarasok

#### 1. Legyen explicit raw artifact persistence boundary
A raw output mentes ne maradjon szetszorva a workerben.

Hasznalj explicit worker-oldali helper/modult, peldaul:
- `worker/raw_output_artifacts.py`
- vagy ezzel egyenerteku, jol tesztelheto boundary.

A helper felelossege legalabb:
- mely raw fajlok tarolandoak;
- hogyan keletkezik a canonical storage path;
- hogyan tortenik az idempotens `app.run_artifacts` regisztracio;
- milyen metadata kerul a rekordba.

#### 2. A path legyen H0 canonical
A run artifact storage path ne ad hoc `runs/{run_id}/...` prefixet hasznaljon,
hanem a H0 source-of-truth szerinti mintat:
- `projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`

A bucket defaultja `run-artifacts` legyen.

A `project_id` ne legyen kitalalva: a snapshot/project truth-bol jojjon.

#### 3. Csak a raw output reteg rendezodjon el
Minimum elvart raw outputok:
- `solver_stdout.log`
- `solver_stderr.log`
- `solver_output.json`
- `runner_meta.json`
- `run.log` (ha letezik)

Megengedett, ha a task a mar meglevo `solver_input_snapshot.json` kezeleset is
konzisztense teszi, de ez csak akkor jo, ha nem kell hozza uj enum/schema hack.

Kulonosen figyelj ra, hogy a raw output tarolasa **ne** keveredjen a H1-E6
normalizerrel. A `solver_output.json` meg most is raw truth, nem projection.

#### 4. Idempotencia es retry legyen korrekt
A raw output mentesnek retry/re-run mellett is stabilnak kell maradnia.

Minimum elvaras:
- ugyanarra a tartalomra ugyanaz a hash/path kepzodik;
- `(run_id, storage_path)` utesnel ne szorjon hamis hibat;
- a worker ne duplazza ertelmetlenul ugyanazt a run artifact rekordot.

#### 5. Hibas futasoknal is maradjon bizonyitek
A DoD lenyege, hogy a hibak es eredmenyek visszakereshetok legyenek.

Ez azt jelenti, hogy ahol ertelmesen elerheto fajl keletkezett:
- non-zero exitnel legyen meg stdout/stderr es runner meta;
- timeoutnal/cancelnel legalabb a rendelkezesre allo log/meta maradjon meg;
- lease-lost ne eredmenyezzen hamis success-t, de a mar rendelkezésre allo raw
  evidence ne vesszen el csak azert, mert a run nem sikeres.

Nem kotelezo minden agban ugyanannyi fajlt feltolteni, de a report mondja ki
pontosan, melyik agban milyen raw evidence garantalt.

#### 6. A smoke bizonyitsa a canonical raw output viselkedest
Legyen task-specifikus smoke, amely fake upload/client boundaryval legalabb ezt
bizonyitja:
- a canonical path `projects/{project_id}/runs/{run_id}/...` prefixet hasznal;
- a raw artifact helper a megfelelo fajlokat es artifact kind/metadata parokat
  regisztralja;
- ugyanazon tartalomra determinisztikus path/hashes jonnek;
- failed vagy timeout jellegu agban is megmarad a relevans raw evidence;
- a smoke nem igenyel valos solver binaryt.

### DoD
- [ ] Keszul explicit worker-oldali raw artifact persistence helper/boundary.
- [ ] A raw output mentes H0 canonical `run-artifacts` bucket + path policy szerint tortenik.
- [ ] A `solver_stdout.log` / `solver_stderr.log` / `solver_output.json` / `runner_meta.json` / `run.log` raw evidence visszakereshetoen tarolhato.
- [ ] Az `app.run_artifacts` regisztracio idempotens es retry-biztos.
- [ ] Hibas futasoknal is megmarad a lenyegi raw evidence a reportban tisztazott szabaly szerint.
- [ ] A task nem csuszik at result normalizer / projection / viewer artifact scope-ba.
- [ ] Keszul task-specifikus smoke a canonical raw-output mentes fo agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a worker egyszerre ket kulon path-policy szerint tarol run artifactot;
  - a raw artifact upload success-only agra korlatozodik, es hibanal elveszik a
    bizonyitek;
  - a task atcsuszik H1-E6 projection scope-ba;
  - idempotencia hiba miatt retry-nal fals duplicate vagy overwrite tortenik.
- Mitigacio:
  - explicit helper hasznalata;
  - hash/path kepzes es artifact tipus mapping smoke-ban fedve legyen;
  - a report mondja ki kulon, mely artifactok garantaltak success/failure
    esetekben.
- Rollback:
  - a helper/worker/smoke/report/checklist diff egy task-commitban
    visszavonhato;
  - a raw artifact helper kulon modulkent izolalva legyen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/queue_lease.py worker/engine_adapter_input.py vrs_nesting/runner/vrs_solver_runner.py scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py`
  - `python3 scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260318233000_worker_lifecycle_artifact_idempotency_guard.sql`
- `worker/main.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
