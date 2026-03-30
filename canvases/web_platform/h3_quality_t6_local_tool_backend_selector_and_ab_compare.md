# H3-Quality-T6 Local tool backend selector es A/B compare lab

## Funkcio
Ez a task a H3 quality lane hatodik lepese.
A T4 ota a worker mar kepes `sparrow_v1` es `nesting_engine_v2` backend kozott
valtani, a T5 ota a `viewer-data` endpoint is backend-helyes truthot tud
visszaadni v1 es v2 runokra.

A helyi trial-run tool es a benchmark runner viszont tovabbra is egybackendes
laborkent mukodik:
- a CLI/GUI nem tud explicit backend-et kerni a helyi workerhez;
- a `run_h3_quality_benchmark.py` ugyan quality summary-t gyujt, de nem tud
  ugyanazt a case-t ket backenddel, egyutt, gepileg osszehasonlithato modon
  futtatni;
- a local auto-start/restart logika nem hordoz explicit worker backend override-ot,
  igy a tool jelenleg nem tud megbizhato A/B laborkent funkcionalni.

Ez a task ezt a gapet zarja le. A cel **nem** DB/API run-config schema valtoztatas,
hanem a helyi tesztelo es benchmark tooling felerositese ugy, hogy a ket backend
osszehasonlitasa tenylegesen hasznalhato legyen.

## Scope

### Benne van
- `TrialRunConfig` backend-selector bovites `auto | sparrow_v1 | nesting_engine_v2`
  vilaggal;
- CLI backend argumentum es GUI backend selector, amely determinisztikusan a core
  configba folyik;
- local platform start/restart subprocess env override ugy, hogy a worker a kert
  backenddel induljon, ha a tool auto-startot hasznal;
- run-level summary / quality summary bovites a kert backend es az effektiven
  visszaigazolt backend kulon jelolesere;
- benchmark runner case x backend matrix futtatas;
- `--compare-backends` vagy ezzel ekvivalens convenience mod, amely ugyanarra a
  fixture-re ket backendes futast szervez;
- gepileg olvashato compare summary / delta blokk a benchmark outputban;
- dedikalt fake smoke, amely valodi platform es valodi solver nelkul bizonyitja a
  backend selector + compare matrix viselkedest.

### Nincs benne
- run-config API, DB schema vagy migration az engine backend tarolasara;
- worker/main backend-selection policy tovabbi atalakitasa;
- quality profile-ok (`fast_preview`, `quality_default`, `quality_aggressive`)
  bevezetese;
- placement/minosegi algoritmus tuning;
- frontend termek-UI rollout vagy permanent operator dashboard.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `scripts/trial_run_tool_core.py`
  - mar gyujt `engine_meta` es `quality_summary` evidence-t;
  - platform auto-start/restart a `scripts/run_web_platform.sh` subprocessen megy;
  - jelenleg nincs explicit requested worker backend konfiguracio.
- `scripts/run_trial_run_tool.py`
  - CLI wrapper a core-hoz; meg nincs backend selector argumentum.
- `scripts/trial_run_tool_gui.py`
  - helyi Tkinter shell; meg nincs backend selector.
- `scripts/run_h3_quality_benchmark.py`
  - benchmark manifest alapjan futtat case-eket;
  - jelenleg egy futas/case logikat kezel, backend-matrix nelkul.
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
  - benchmark harness dokumentacio; meg nincs explicit A/B compare mod.
- `scripts/smoke_trial_run_tool_cli_core.py`
  - jo minta a fake transportos tool smoke-hoz.
- `scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`
  - jo minta a benchmark runner fake plan-only smoke-hoz.

## Jelenlegi tooling gap
A rendszer backend oldalon mar tul van a minimum dual-engine truthon, de a helyi
quality-lab oldalon meg mindig nincs egyetlen, ergonomikus es audit-olhato modja
annak, hogy ugyanazt a DXF/case halmazt a ket backenddel egymas melle tegyuk.

Ennek kovetkezmenyei:
- a benchmark eredmenyek ma backendankent nehezen reprodukalhatok;
- a tool nem tudja egyertelmuen jelezni, hogy a kert backend valoban ervenyesult-e;
- a helyi A/B osszeveteshez manualis worker restart es kezi jegyzeteles kell;
- a kovetkezo quality profile lane elott meg mindig nincs eleg eros local lab.

## Konkret elvarasok

### 1. Vezess be explicit backend selectort a core/CLI/GUI vilagban
A `TrialRunConfig` kapjon explicit requested backend mezot. Elfogadott ertekek:
- `auto`
- `sparrow_v1`
- `nesting_engine_v2`

Szabaly:
- `auto` eseten a core ne kenyszeritsen env override-ot;
- konkret backend eseten a local platform start/restart subprocess kapjon
  `WORKER_ENGINE_BACKEND=<...>` override-ot;
- a CLI-ben legyen explicit `--engine-backend` argumentum;
- a GUI-ban legyen konnyen valaszthato backend mező, default `auto`-val.

### 2. A tool irja ki a kert es az effektive visszaigazolt backendet
A summary markdown/json es a `quality_summary.json` kulon tudja:
- `requested_engine_backend`
- `effective_engine_backend`
- `engine_backend_match` (bool / tri-state jelleggel, ha nincs evidence)

Az `effective_*` ertek tovabbra is az `engine_meta.json` / viewer truth alapjan
legyen, ne a kert config alapjan kitalalva.

### 3. A benchmark runner tudjon case x backend matrixot futtatni
A `run_h3_quality_benchmark.py` kapjon explicit backend matrix kepesseget.
Kotelezo minimum:
- egy backend kifejezett valasztasa (`--engine-backend ...`);
- tobb backend futtatasanak repeatable CLI-je (`--engine-backend ... --engine-backend ...`)
  vagy ekvivalens megoldas;
- `--compare-backends` convenience mod, amely legalabb a `sparrow_v1` es
  `nesting_engine_v2` parra boviti a case-eket;
- `--plan-only` modban is latszodjon a kibovitett case x backend terv.

### 4. Keszits gepileg olvashato compare summary-t
Ha ugyanarra a `case_id`-ra ket backendes eredmeny van, a benchmark output tartalmazzon
kulon compare blokkot legalabb ezekkel:
- `case_id`
- `requested_backends`
- `effective_backends`
- `sheet_count_delta`
- `utilization_pct_delta`
- `runtime_sec_delta`
- `nonzero_rotation_delta`
- `winner_by_sheet_count`
- `winner_by_utilization`
- `notes` / `incomplete_reason`, ha valamelyik oldal nem teljes

Szabaly:
- ne gyarts "global optimality" allitast;
- csak evidence-first delta szamitas legyen;
- ha valamelyik side hianyzik vagy hibas, a compare blokk ezt explicit jelezze.

### 5. A task maradjon local tooling scope-ban
Ez a task **ne** nyuljon bele:
- `api/routes/run_configs.py`
- SQL migrationokba
- persistent project-level backend policy-ba

A backend selector ebben a korben local tool/runtime override, nem product feature.

### 6. Keszits dedikalt task-specifikus smoke-ot
A smoke bizonyitsa legalabb:
- a CLI/backend selector configja helyesen folyik a core configba;
- a GUI/backend selector configja helyesen normalizalodik;
- a platform-command helper a kert `WORKER_ENGINE_BACKEND` env override-ot adja at
  start/restart esetben;
- a benchmark runner `--plan-only --compare-backends` modban determinisztikus
  case x backend matrixot ir;
- a fake `run_trial` eredmenyekbol helyes compare delta blokk epul;
- valodi Supabase, valodi solver es valodi worker processz nelkul is PASS.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
- `codex/prompts/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare/run.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
- `codex/codex_checklist/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`

## DoD
- a local trial-run core/CLI/GUI tud explicit backend selectort kezelni;
- a platform start/restart env override bizonyitottan a kert worker backenddel fut;
- a summary/quality_summary kulon jelzi a kert es az effektive visszaigazolt backendet;
- a benchmark runner case x backend matrixot tud futtatni es `--plan-only` modban is
  helyesen kibontja a tervet;
- a benchmark output gepileg olvashato compare delta blokkot ad azonos case ket
  backendes futasahoz;
- a task-specifikus smoke zold;
- a standard verify wrapper lefut, report + log frissul.

## Kockazat + rollback
- Kockazat:
  - a local tool tul sok platform-control logikat kap;
  - a benchmark runner output schema tul gyorsan no;
  - a GUI selector konnyen deszinkronizalodhat a CLI/core configtol.
- Mitigacio:
  - maradj local tooling scope-ban, ne nyiss DB/API feature-kort;
  - a compare summary legyen additive, evidence-first;
  - a smoke kulon fedje a CLI, GUI, core es benchmark matrix viselkedest.
- Rollback:
  - a core/CLI/GUI/benchmark diff egy task-commitban visszavonhato;
  - nincs schema migration, nincs perzisztens adatmodell-kockazat.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/trial_run_tool_gui.py scripts/run_h3_quality_benchmark.py scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
  - `python3 scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
- Ajanlott regresszio:
  - `python3 scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`
  - `python3 scripts/smoke_trial_run_tool_tkinter_gui.py`

## Kapcsolodasok
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/trial_run_tool_gui.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/smoke_trial_run_tool_cli_core.py`
- `scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`
