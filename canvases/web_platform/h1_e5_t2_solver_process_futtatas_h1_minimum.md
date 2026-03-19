# H1-E5-T2 Solver process futtatas (H1 minimum)

## Funkcio
A feladat a H1-E5 masodik, szukitett lepese: a H1-E5-T1-ben bevezetett,
snapshotbol kepzett `solver_input.json` v1 payload tenyleges solver futtatasa
workerbol ugy, hogy a H1 minimum run lifecycle mar a canonical snapshot/input
vilagra uljon, ne a legacy `python -m vrs_nesting.cli dxf-run ...` agra.

Ez a task tudatosan **nem** raw output storage redesign, **nem** result
normalizer, **nem** viewer/projection pipeline es **nem** artifact workflow.
A cel kizarolag az, hogy a queued run a workerben a solver process futtatason
keresztul kontrollaltan `running` -> `succeeded` / `failed` / `cancelled`
allapotba mehessen, megtartva a lease/cancel/timeout vedelmeket.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit solver process helper / runner-bridge bevezetese a worker oldalon;
  - a H1-E5-T1 snapshot-inputbol kepzett payload tenyleges futtatasa;
  - a legacy `dxf-run` process-ut levaltas a canonical solver-input utvonalra;
  - run status es attempt status konzisztens kezelese a megl evo H1 run/queue
    truth-tal;
  - cancel / timeout / lease-lost agak kontrollalt kezelese a solver process
    futasa kozben;
  - task-specifikus smoke a sikeres, failed es timeout/lease/cancel fo agakra.
- Nincs benne:
  - raw stdout/stderr/storage artifact pipeline redesign;
  - `app.run_artifacts` ujratervezes vagy kulon raw-output persistencia;
  - result normalizer / projection / SVG / DXF export;
  - run list API vagy worker lease mechanika ujranyitasa;
  - solver input mapping tovabbi bovitese (az H1-E5-T1 scope-ja volt).

### Talalt relevans fajlok
- `worker/main.py`
  - jelenleg meg legacy `python -m vrs_nesting.cli dxf-run ...` subprocess aggal fut.
- `worker/engine_adapter_input.py`
  - canonical snapshot -> solver_input v1 helper.
- `worker/queue_lease.py`
  - claim / heartbeat / lost-lease mechanika, amit meg kell tartani.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - a valos solver-input v1 -> solver_output v1 futtato helper.
- `docs/solver_io_contract.md`
  - a `solver_input.json` / `solver_output.json` v1 source-of-truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - snapshot-first boundary elvek.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E5-T2 task source-of-truth.

### Konkret elvarasok

#### 1. A solver process a snapshot-input vilagra alljon at
A worker a H1-E5-T1-ben eloallitott solver-input payloadot hasznalja tenyleges
futtatashoz. A canonical bemenet a snapshotbol kepzett `solver_input.json` v1
legyen, ne a legacy `project_dxf_v1.json` + `dxf-run` koztes vilag.

A futtatasi ut legyen explicit es olvashato: a workerbol egyertelmuen latszodjon,
hogy a solver-input snapshotbol jon, es a tenyleges solver futtatasa mar nem az
ad hoc DXF pipeline entrypointra epul.

#### 2. Hasznalj explicit runner helper/bridge-et
A solver process inditas ne legyen ujabb nagy inline subprocess blokk.
Hasznalj explicit helper/modult vagy egyertelmu runner-bridge-et a worker es a
`vrs_nesting.runner.vrs_solver_runner` kozt. A cel az, hogy a tenyleges solver
futtatas kulon, tesztelheto boundary legyen.

Megengedett minimalis iranyok:
- uj `worker/solver_process_runner.py` helper;
- vagy mas, ezzel egyenerteku explicit worker-oldali wrapper.

#### 3. A status atmenetek legyenek H1 minimum szinten korrektek
A task DoD-ja szerint a runnak kontrollaltan kell `running` / `succeeded` /
`failed` allapotba mennie.

Ez minimum ezt jelentse:
- sikeres solver futas utan a run `succeeded` allapotba zarhato;
- nem nulla exit, invalid output vagy mapping/process hiba eseten `failed`;
- user cancel eseten `cancelled`;
- lease-lost eseten ne legyen hamis success.

A mar meglevo `attempt_status`, retry es dequeue/requeue logika ne seruljon.

#### 4. Timeout / cancel / lease mechanika maradjon meg
A H1-E4-T3-ban letett lease mechanika es a worker jelenlegi cancel/timeout
vedelmei maradjanak ervenyben.

Ha a solver runner hivasat ehhez minimalisan korbe kell csomagolni, tedd meg,
de ne nyiss uj queue mechanikat.

Kulonosen figyelj:
- periodikus heartbeat megmaradjon;
- cancel kerest a worker tovabbra is figyelje;
- timeout egyertelmu hibava forduljon;
- lease elvesztesnel a run ne menjen success-be.

#### 5. Ne csussz at raw-output / result scope-ba
Ebben a taskban meg nincs kulon raw output persistence redesign.
Attol, hogy a runner helyi `solver_output.json` / `solver_stdout.log` /
`solver_stderr.log` fajlokat allit elo, meg ne nyiss kulon artifact modellt es ne
tervezd ujra a `run_artifacts` vilagot.

A task csak addig menjen, ameddig a solver process futtatas a H1 minimum
run-lifecycle-t kiszolgalja.

#### 6. A smoke bizonyitsa a fo aga(ka)t
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- a worker/runner helper a snapshot-input utvonalat hasznalja, nem a legacy
  `dxf-run` commandot;
- sikeres runner visszateresnel a run completion success ag elerheto;
- runner hiba / invalid output / timeout eseten failed ag megy tovabb;
- cancel/lease-lost ag nem eredmenyez hamis success-t;
- a smoke ne igenyeljen valos solver binaryt: fake/mock runnerrel bizonyitson.

### DoD
- [ ] A worker tenyleges solver process futtatasa a H1-E5-T1 snapshot-input vilagra all at.
- [ ] A legacy `python -m vrs_nesting.cli dxf-run ...` ag kikerul a canonical futasi utbol.
- [ ] Keszul explicit worker-oldali solver process helper/runner bridge.
- [ ] A run lifecycle H1 minimum szinten kezeli a `running` / `succeeded` / `failed` / `cancelled` / lease-lost fo agakat.
- [ ] A megl evo queue lease + heartbeat + retry/requeue logika nem serul.
- [ ] A task nem csuszik at raw output storage / result normalizer / artifact scope-ba.
- [ ] Keszul task-specifikus smoke a fo sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a worker feleuton legacy es canonical process ut kozott marad;
  - a cancel/lease/timeout vedelmek megszakadnak a runner atallasnal;
  - a task atcsuszik raw-output vagy result normalizer scope-ba;
  - a fake smoke tul gyenge lesz es nem bizonyitja a status atmeneteket.
- Mitigacio:
  - explicit helper/bridge legyen a worker es a runner kozott;
  - a status- es queue-agakat smoke-ban fedni kell;
  - a report mondja ki vilagosan, hogy a task mit NEM vallal meg.
- Rollback:
  - a helper/worker/smoke/report/checklist diff egy task-commitban visszavonhato;
  - ha kell, a process atallas kulon helper-modullal izolalva legyen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/engine_adapter_input.py worker/queue_lease.py vrs_nesting/runner/vrs_solver_runner.py scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
  - `python3 scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/queue_lease.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
