# H3-Quality-T4 Worker dual-engine runtime bridge

## Funkcio
Ez a task a H3 quality lane negyedik lepese.
A T3-ban elkeszult a `build_nesting_engine_input_from_snapshot(...)`, de a
worker runtime ut tovabbra is fixen a legacy v1 backendre van kotve:
- a worker csak `build_solver_input_from_snapshot(...)`-ot hiv;
- a subprocess mindig `vrs_nesting.runner.vrs_solver_runner`;
- az `engine_meta.json` mindig `sparrow_v1`-et ir;
- a raw artifact persist csak `solver_output.json`-t ismeri;
- a `normalize_solver_output_projection(...)` csak v1 `solver_output.json`
  contracttal tud dolgozni.

Ez a task ezt a runtime szakadast zarja le.
A cel **nem** a viewer teljes v2 tamogatasa es **nem** az A/B benchmark UX,
hanem az, hogy a worker mar tenylegesen tudjon ket backend kozt valtani, es a
`nesting_engine_v2` run is vegigjusson a `done` allapotig a projection/sheet
artifact lanc megtartasaval.

## Scope

### Benne van
- explicit worker backend valasztas (`sparrow_v1` default, `nesting_engine_v2`
  alternativ ut);
- backend-fuggo snapshot->input builder es runner invocation;
- `engine_meta.json` es canonical `solver_input` artifact backend-aware kitoltese;
- v2 raw output artifact persist (`nesting_output.json`) a worker raw artifact
  policy szerint;
- minimum v2 projection normalizer ut, hogy a worker a `nesting_engine_v2`
  kimenetbol is tudjon DB projection/sheet SVG/sheet DXF lancot csinalni;
- dedikalt task-smoke a v1 default es v2 switch sikeres worker-folyamatara.

### Nincs benne
- viewer-data endpoint, run detail UI vagy artifact UI v2 polish;
- trial tool A/B mode, benchmark diff vagy quality profile UX;
- run_config / DB schema szintu per-run backend valaszto bevezetese;
- H3-E4 remnant / inventory domain;
- nesting_engine output quality tuning.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `worker/main.py`
  - a `_process_queue_item(...)` most fixen `build_solver_input_from_snapshot(...)`-ot hiv;
  - a `_build_solver_runner_invocation(...)` fixen `python3 -m vrs_nesting.runner.vrs_solver_runner`;
  - az `engine_meta.json` fix `sparrow_v1` backend metadata-t ir.
- `worker/engine_adapter_input.py`
  - mar letezik `build_nesting_engine_input_from_snapshot(...)` es
    `nesting_engine_input_sha256(...)`;
  - a v1 es v2 snapshot->input boundary mar kulon el.
- `worker/result_normalizer.py`
  - jelenleg csak `solver_output.json` + `contract_version == "v1"` ag letezik.
- `worker/raw_output_artifacts.py`
  - a canonical raw artifact lista most csak `solver_output.json`-t ismeri;
    `nesting_output.json` nincs benne.
- `vrs_nesting/runner/nesting_engine_runner.py`
  - kulon deterministic runner boundary a `nesting_engine` binaryhoz;
  - `--input`, `--seed`, `--time-limit`, `--run-root` parametereket var;
  - a run_dir-ben `nesting_input.json`, `nesting_output.json`, `runner_meta.json`,
    `solver_stdout.log`, `solver_stderr.log` keletkezik.
- `scripts/validate_nesting_solution.py`
  - mar letezik `validate_nesting_engine_v2(...)`, tehat a v2 output contract nem uj.
- `scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
  - jo minta a fake worker/subprocess smoke szerkezetere.

## Jelenlegi runtime gap (felderites eredmenye)
A T3 utan a workerben mar rendelkezésre all a v2 input builder, de a runtime
lancon meg mindig ez a blokker maradt:
- nincs worker-level backend selector;
- nincs v2 runner invocation;
- nincs v2 output -> projection normalizer ut;
- nincs v2 raw output artifact persist;
- emiatt a `nesting_engine_v2` jelenleg csak adapter-szinten letezik, nem valodi
  worker executable backendkent.

## Konkret elvarasok

### 1. Vezess be explicit worker backend valasztast
A worker kapjon egy egyertelmu backend valasztot, peldaul `WORKER_ENGINE_BACKEND`
nevvel.

Kotelezo minimum viselkedes:
- default: `sparrow_v1`;
- tamogatott alternativ ertek: `nesting_engine_v2`;
- minden mas ertek kontrollalt, korai hibaval alljon meg.

A valasztas ebben a taskban worker-szintu / env-szintu lehet. Nem kell meg run-level
DB config.

### 2. A worker input payload backend-aware legyen
A `_process_queue_item(...)` ne fixen a v1 buildert hivja, hanem a backend alapjan:
- `sparrow_v1` -> `build_solver_input_from_snapshot(...)` + `solver_input_sha256(...)`
- `nesting_engine_v2` -> `build_nesting_engine_input_from_snapshot(...)` +
  `nesting_engine_input_sha256(...)`

A canonical `solver_input` artifact tovabbra is maradjon kozos truth artifact,
csak a payload contractja valtozhat backendtol fuggoen.

### 3. A runner invocation legyen backend-aware
A worker a backend alapjan valasszon runtime boundary-t:
- `sparrow_v1` -> marado `vrs_nesting.runner.vrs_solver_runner`
- `nesting_engine_v2` -> `vrs_nesting.runner.nesting_engine_runner`

Fontos:
- a v1 default ut maradjon teljesen kompatibilis;
- a v2 runnerhez `--run-root`-os semantika illeszkedik, nem a v1 fix `--run-dir`;
- a worker tovabbra is ugyanugy tudja visszaolvasni a stdout-bol a vegleges run_dir-t.

### 4. `engine_meta.json` legyen valodi backend truth
A persisted `engine_meta.json` backendtol fuggoen helyes adatot irjon:
- `engine_backend`
- `engine_contract_version`
- `engine_profile`
- `solver_runner_module`
- `solver_input_hash`

Minimum:
- v1: marado `sparrow_v1` + `vrs_solver_runner`
- v2: `nesting_engine_v2` + `nesting_engine_runner`

Ne maradjon fixen `sparrow_v1` beégetve a v2 runoknal.

### 5. Raw artifact persist ismerje a v2 outputot
A `worker/raw_output_artifacts.py` kapjon olyan bovitest, hogy a `nesting_engine_runner`
altal eloallitott `nesting_output.json` is persisted raw artifact legyen.

A taskban a helyes minimum:
- a v2 output ne vesszen el;
- a metadata egyertelmuen jelezze, hogy ez v2 output artifact;
- a meglevo v1 raw artifact policy ne torjon el.

### 6. Keszits minimum v2 normalizer utat a worker projection lancahoz
A worker run csak akkor hasznalhato, ha a subprocess utan a projection/DB/sheet
artifact lepesek is mukodnek.

Ezert a `worker/result_normalizer.py` kapjon explicit v2 agat.

Kotelezo minimum viselkedes:
- ha a run_dir-ben v1 `solver_output.json` van, a meglevo ut maradjon;
- ha a run_dir-ben v2 `nesting_output.json` van, a normalizer tudja azt projection
  formatumba forditani;
- a v2 placement mezok (`part_id`, `instance`, `sheet`, `x_mm`, `y_mm`,
  `rotation_deg`) helyesen kepezodjenek a projection sorokra;
- a v2 `unplaced.reason` atjojjon;
- a `metrics` / `summary` strukturaja maradjon kompatibilis a worker downstream
  hivashelyeivel.

Korrektsegi elv:
- a v2 projection ne egy buta bbox-only hack legyen, ha a snapshot geometry truth
  mar elerheto;
- a transform/bounds szamitas legyen determinisztikus;
- a single-sheet-family korlat tovabbra is a T3 adapter fail-fastja maradjon,
  nem csendes runtime veszteseg.

### 7. A v1 default ut ne torjon el
A task egyik fo kockazata, hogy a v2 bridge kozben a meglevo v1 worker path serul.
Ezert a smoke explicit bizonyitsa:
- backend nelkul vagy `sparrow_v1`-gyel a worker tovabbra is a legacy utat hasznalja;
- `nesting_engine_v2`-vel a worker a v2 builder+runner+normalizer utat hasznalja;
- mindket esetben `done` allapotig eljut a fake worker folyamat.

### 8. Legyen task-specifikus smoke
Keszits dedikalt smoke-ot, ami legalabb ezt bizonyitja:
- v1 default backendnel a worker tovabbra is `vrs_solver_runner`-t hivja;
- v2 backendnel a worker `nesting_engine_runner`-t hivja;
- v2 backendnel a canonical input artifact es az `engine_meta.json` helyes backend truthot ir;
- v2 backendnel a fake `nesting_output.json` projection-je `done` allapotig megy;
- invalid backend ertek kontrollalt hibaval megall.

A smoke ne kerjen valodi Supabase-ot es ne kerjen valodi solver binary-t.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t4_worker_dual_engine_runtime_bridge.yaml`
- `codex/prompts/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge/run.md`
- `worker/main.py`
- `worker/result_normalizer.py`
- `worker/raw_output_artifacts.py`
- `worker/engine_adapter_input.py`
- `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`
- `codex/codex_checklist/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`
- `codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`

## DoD
- a worker rendelkezik explicit backend selectorral, `sparrow_v1` defaulttal es
  `nesting_engine_v2` alternativaval;
- a worker a backend alapjan helyes input buildert, hash helpert es runner modult valaszt;
- a canonical `solver_input` artifact es az `engine_meta.json` v2 runnal is helyes truthot ad;
- a raw artifact persist a `nesting_output.json`-t sem vesziti el;
- letezik minimum v2 normalizer ut, amivel a worker a v2 outputbol is `done`
  projectiont tud epiteni;
- a v1 default worker ut nem torik el;
- a task-specifikus smoke zold;
- a standard verify wrapper lefut, report + log frissul.

## Kockazat + rollback
- Kockazat:
  - a task belelog a viewer/result normalizer teljes v2 rollout scope-jaba;
  - a v1 worker path regressziot kap;
  - a v2 projection jo output ellenere rossz belso bbox/projection truthot general.
- Mitigacio:
  - a scope worker runtime bridge maradjon, ne viewer task;
  - a smoke fedje a v1 es v2 worker agat is;
  - a v2 normalizer minimum bridge legyen, de determinisztikus es explicit.
- Rollback:
  - a backend selector + normalizer + smoke diff egy task-commitban visszavonhato;
  - a default backend tovabbra is `sparrow_v1`, ezert rollback nelkul is alacsony az
    immediate uzemi kockazat.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/raw_output_artifacts.py scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`
  - `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`

## Kapcsolodasok
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/result_normalizer.py`
- `worker/raw_output_artifacts.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/validate_nesting_solution.py`
- `scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
