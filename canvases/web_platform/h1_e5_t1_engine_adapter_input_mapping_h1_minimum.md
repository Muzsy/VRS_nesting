# H1-E5-T1 Engine adapter input mapping (H1 minimum)

## Funkcio
A feladat a H1-E5 solver integracio elso, szukitett lepese: a H1-E4-ben letett
canonical run snapshotbol explicit, determinisztikus engine adapter input
kepzese ugy, hogy a worker kesobb mar ne a legacy `run_config` /
`parts_config` / `stock_file_id` vilagbol es ne elo projekt-tablak ad hoc
olvasasabol probalja osszerakni a solver futtatas bemenetet.

Ez a task tudatosan **nem** solver process inditas, **nem** raw output mentes,
**nem** result normalizer es **nem** artifact pipeline. A cel kizarolag az,
hogy a snapshotbol H1 minimum szinten stabil, bizonyithato engine input legyen.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit engine adapter input helper / module bevezetese;
  - a canonical H1 run snapshot mezokre epulo mapping;
  - a solver IO contract v1-hez igazodo input payload eloallitasa;
  - ha szukseges, a H1-E4 snapshot builder minimalis bovitese, hogy a snapshot
    tenylegesen tartalmazza a mappinghez szukseges immutable geometry adatokat;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - solver process start;
  - queue lease vagy worker pickup ujratervezese;
  - stdout/stderr/raw output mentes;
  - run status lifecycle teljes ujranyitasa;
  - result normalizer / projection / artifact scope.

### Talalt relevans fajlok
- `api/services/run_snapshot_builder.py`
  - canonical H1 snapshot truth (`project/technology/parts/sheets/geometry/solver_config`).
- `api/services/run_creation.py`
  - a snapshot perzisztalas jelenlegi canonical create flow-ja.
- `worker/main.py`
  - jelenleg meg legacy `_build_dxf_project_payload(...)` aggal dolgozik.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - a solver input/output boundary valos runner-oldali contractja.
- `docs/solver_io_contract.md`
  - `solver_input.json` v1 source-of-truth.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - snapshot-first boundary elvek.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E5-T1 task source-of-truth.

### Konkret elvarasok

#### 1. A canonical forras a run snapshot legyen
A H1 minimum adapter input **nem** olvashat vissza elo projekt/part/sheet truth-ot
ad hoc modon a workerbol. A bemenet alapja a `app.nesting_run_snapshots` sorban
rogzitett snapshot legyen.

Ha a jelenlegi snapshotban nincs eleg immutable geometry adat a solver-input
mappinghez, akkor ezt **minimalisan** a H1-E4 snapshot builder / create flow
oldalan kell potolni, nem a workerben uj elo DB-roviditessel.

#### 2. Explicit adapter input helper keszuljon
Keszuljon kulon helper/modul (pl. `worker/engine_adapter_input.py` vagy ezzel
egyerteku nevvel), amely egy run snapshot payloadbol determinisztikusan eloallit
egy solver-kompatibilis input payloadot.

A helper legyen tisztan tesztelheto/pure jellegu, ne process-startot vegezzen.

#### 3. A kimenet a valos solver IO contracthoz igazodjon
A H1 minimum target a `docs/solver_io_contract.md` szerinti `solver_input.json`
`contract_version = 'v1'` payload.

Legalabb ezek legyenek helyesen kitoltve:
- `contract_version`
- `project_name`
- `seed`
- `time_limit_s`
- `stocks`
- `parts`

A stock es part geometriaknal a shaped-mode legyen a canonical irany:
- `outer_points`
- `holes_points`
- `width`
- `height`
- `quantity`
- `allowed_rotations_deg`

#### 4. A part geometry a selected nesting derivative-bol jojjon
A part input **nem** source DXF path-bol es nem file download vilagbol alljon elo.
A canonical forras a `nesting_canonical` derivative truth legyen.

A mapping minimum elve:
- `selected_nesting_derivative_id` -> derivative geometry payload
- polygon.outer_ring -> `outer_points`
- polygon.hole_rings -> `holes_points`
- bbox -> `width` / `height`
- requirement -> `quantity`

Ha a snapshot geometry manifest jelenleg csak derivative referenciat/hashes-t tarol,
a tasknak ezt minimalisan korrigalnia kell ugy, hogy a worker mar snapshotbol tudjon
inputot epiteni.

#### 5. A sheet input a sheet manifestbol jojjon
A stock/sheet input a snapshot `sheets_manifest_jsonb` vilagabol jojjon.
H1 minimum szinten a teglalap sheet truth eleg:
- `id`
- `quantity`
- `width`
- `height`

Ne nyiss inventory/remnant/manufacturing iranyba.

#### 6. Rotation policy legyen explicit es kompatibilis
A solver IO contract jelenleg a `allowed_rotations_deg` mezoben jobbraforgatasos,
veges halmazt var (`0/90/180/270`).

Ezert a H1 minimum adapternek explicit szemantikaja legyen:
- ha a snapshot solver config `allow_free_rotation=false` es a rotation step a
  solver v1 contracttal osszeegyeztetheto, akkor determinisztikus rotaciohalmaz
  keletkezzen;
- ha a snapshot rotation policy nem kepezheto le biztonsagosan a solver v1
  contractra, akkor a helper adjon tiszta, determinisztikus hibat, ne csendes
  torzitast.

A report mondja ki pontosan, hogy a T1 milyen H1 minimum rotation-semantikat valosit meg.

#### 7. Determinizmus legyen bizonyithato
Az adapter input JSON ugyanazon snapshotbol bitstabil / determinisztikus
sorrenddel kepzodjon. Kulonosen figyelj:
- parts/stocks rendezese;
- JSON mezorend / canonical dump hash a smoke-ban;
- ne legyen `now()`/veletlen/elo DB sorrendfuggo branch.

#### 8. A task ne csusszon at process-runner scope-ba
Ebben a taskban meg nincs:
- `subprocess` / `vrs_solver_runner` tenyleges futtatas;
- stdout/stderr/raw artifact mentes;
- run allapot `running/succeeded/failed` teljes kezelese.

Ha `worker/main.py`-t erinted, legfeljebb annyira tedd, hogy a legacy
`_build_dxf_project_payload(...)` helyett vagy melle explicit adapter-helper
hivasra alkalmas legyen a kod. Process start redesign nem ide tartozik.

#### 9. Smoke script bizonyitsa a fo agakat
Legyen task-specifikus smoke, amely legalabb ezt bizonyitja:
- snapshotbol sikeresen eloall a solver_input v1 payload;
- a parts/stocks shaped-mode mezoi helyesen kepzodnek;
- a determinisztikus hash ket futasnal azonos;
- unsupported rotation policy kontrollalt hibaval all meg;
- hianyzo derivative geometry / hianyzo bbox / ures requirements hibat ad;
- a task nem hasznal legacy `run_config.parts_config` vagy `stock_file_id` bemenetet.

### DoD
- [ ] Keszul explicit engine adapter input helper/modul.
- [ ] A helper canonical run snapshotbol epit bemenetet.
- [ ] A kimenet a `docs/solver_io_contract.md` szerinti `solver_input.json` v1 contracttal kompatibilis.
- [ ] A part geometry a selected `nesting_canonical` derivative truth-bol jon.
- [ ] A sheet/stocks input a snapshot `sheets_manifest_jsonb` vilagabol jon.
- [ ] A rotation policy mapping explicit es dokumentalt.
- [ ] A mapping determinisztikus.
- [ ] A task nem csuszik at solver process / raw output / normalizer scope-ba.
- [ ] Keszul task-specifikus smoke a sikeres es hibas agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a worker tovabbra is legacy `run_config` vilagra ul;
  - a snapshot nem tartalmaz eleg immutable geometry adatot;
  - a rotation policy csendesen eltorzul a solver v1 contracthoz kepest;
  - a task atcsuszik process-runner vagy raw-output scope-ba.
- Mitigacio:
  - a canonical inputforras a snapshot legyen;
  - ha kell, minimalis snapshot-builder bovites tortenjen explicit reporttal;
  - unsupported rotation policy kapjon determinisztikus hibat;
  - a helper legyen tisztan tesztelheto es smoke-kal bizonyitott.
- Rollback:
  - helper/smoke/report/checklist valtozasok egy task-commitban visszavonhatok;
  - ha snapshot-builder bovites kell, az csak minimalis, reportban nevezett diff legyen.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/engine_adapter_input.py worker/main.py scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
  - `python3 scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `api/services/run_snapshot_builder.py`
- `api/services/run_creation.py`
- `worker/main.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
