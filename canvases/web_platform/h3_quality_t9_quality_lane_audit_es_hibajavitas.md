# H3-Quality-T9 Quality lane audit es hibajavitas

## Funkcio
Ez a task a H3 quality T1-T8 audit utan kovetkezo **stabilizacios es closure-fix** kor.
A cel nem uj quality feature, nem uj roadmap-ag, es nem altalanos cleanup, hanem a
bizonyitottan feltart hibak minimal-invaziv javitasa ugy, hogy a T1-T8 quality lane
vegre tenylegesen lezarhato legyen.

A jelenlegi, bizonyitott problemahalmaz:
- a `vrs_nesting.runner.nesting_engine_runner` Python CLI parser **nem fogadja el**
  a `--compaction off|slide` flaget, mikozben a T7/T8 profile registry es a worker
  mar ilyen CLI args listat allit elo a `nesting_engine_v2` futashoz;
- a T1 dedikalt smoke elavult, mert fix literal `"engine_backend": "sparrow_v1"`
  stringet var, mikozben a worker `engine_meta` truth ma backend-agnosztikus es
  dinamikus;
- a T1 es T6 historical task artefaktok kozott outputs-szerzodesi elteres van:
  a report olyan fajlmodositast allit, amely nincs benne a megfelelo task YAML
  `outputs` listajaban.

Ez a task egyszerre:
- **runtime bridge fix** a T7/T8 blokkolo CLI parser hibara,
- **regresszios smoke-fix** a T1 elavult assertjere,
- **task-szerzodesi konzisztencia-fix** a T1/T6 YAML/report driftre,
- es **closure stabilizacio** a H3 quality lane vegehez.

## Scope

### Benne van
- a Python oldali `nesting_engine_runner` CLI parser es arg-build logika minimalis
  javitasa, hogy a `--compaction off|slide` flag tenylegesen elfogadott es tovabbitott
  legyen;
- a T1 dedikalt smoke frissitese ugy, hogy az a valodi `engine_meta` truthot ellenorizze,
  ne egy stale literal stringet;
- egy uj, kifejezetten erre a stabilizacios korre keszitett regresszios smoke, amely
  bizonyitja:
  - a `--compaction` parser fixet,
  - a T1 smoke regresszio javitasat,
  - a T1/T6 task-szerzodesi konzisztenciat;
- a T1/T6 historical task artefaktok minimalis, evidence-first rendezese ugy, hogy a
  repo mar ne hordozzon bizonyitott YAML/report ellentmondast;
- a standard verify wrapper futtatasa es uj report/checklist kitoltese.

### Nincs benne
- uj SQL migration vagy REST schema;
- a Rust `nesting_engine` CLI tovabbi feature-bovitese (a Rust oldali `--compaction`
  itt mar adottnak tekintendő);
- uj quality profile, tuning vagy T9 utani feature;
- benchmark harness nagy refaktor;
- historical taskok teljes ujrairasa vagy nagy docs-cleanup;
- H3-on tuli roadmap-munka.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `vrs_nesting/runner/nesting_engine_runner.py`
  - ma mar kezeli a `--placer`, `--search`, `--part-in-part` es SA flag-eket,
    de a `--compaction` meg hianyzik;
  - emiatt a `python3 -m vrs_nesting.runner.nesting_engine_runner --input ... --compaction slide`
    jelenleg parser szinten elhasal.
- `vrs_nesting/config/nesting_quality_profiles.py`
  - a registry mar kanonikusan general `--compaction <mode>` CLI argot;
  - a problema tehat nem itt, hanem a Python runner parser / main oldalon van.
- `worker/main.py`
  - a runtime policy alapjan mar atadja a `nesting_engine_cli_args` listat;
  - ezt nem kell ujratervezni, csak a Python runnerrel ossze kell zarni.
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
  - jelenleg stale literal assertet tartalmaz a worker `engine_meta` payloadra.
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`
  - a T1 YAML outputs listaja jelenleg nem tartalmazza a `scripts/smoke_trial_run_tool_cli_core.py`
    fajlt, mikozben a historical report erre hivatkozik modositott fajlkent.
- `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
  - a report modositott fajlkent / evidence-forraskent hivatkozik a fenti smoke-ra.
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
  - a T6 YAML outputs listaja jelenleg nem tartalmazza a `scripts/smoke_trial_run_tool_tkinter_gui.py`
    fajlt, mikozben a report erre modositott fajlkent hivatkozik.
- `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
  - a T6 report szinten driftet hordoz.
- `scripts/check.sh`
  - a standard gate jelenleg nem ved egy ilyen Python oldali quality-lane integration
    regressziot dedikalt smoke-kal.

## Konkret elvarasok

### 1. Zard ossze a quality-profile -> worker -> Python runner CLI lancot
A `vrs_nesting/runner/nesting_engine_runner.py` parser fogadja el explicit modon:
- `--compaction off|slide`

Kovetelmenyek:
- az argumentum ugyanugy `choices`-al validaljon, mint a tobbi explicit enum flag;
- a `main()` a parserbol kapott `compaction` mezot tegye bele a `nesting_engine_cli_args`
  listaba;
- a `run_nesting_engine()` tovabbra is ugyanazt az `extra_cli_args` listat adja at a
  subprocessnek, ne legyen kulon hardcode vagy special path;
- invalid ertek fail-fast maradjon parser szinten;
- a fix ne nyuljon a worker profile-feloldasi logikajahoz, ha arra nincs kozvetlen ok.

A minimalis bizonyitas itt nem az, hogy a binary le is fut, hanem az, hogy a Python
runner parser mar **nem** `unrecognized arguments` hibaval all meg, es a flag tenylegesen
belekerul a tovabbitott CLI args listaba.

### 2. Javitsd a T1 dedikalt smoke-ot backend-agnosztikus truthra
A `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` frissuljon ugy,
  hogy ne fix `sparrow_v1` literal stringet keressen a `worker/main.py` szovegeben.

Evidence-first elvaras:
- a smoke a valodi `engine_meta` truthot ellenorizze, pl. a `engine_backend` mezot,
  a `requested_engine_profile` / `effective_engine_profile` / `nesting_engine_cli_args`
  mezok jelenletet, vagy a canonical artifact truthot;
- ne fuggjon attol, hogy a worker eppen melyik backend stringet ir literalban;
- a viewer fallback es a trial tool evidence minimumait tovabbra is tartsa meg.

### 3. Keszits dedikalt T9 regresszios smoke-ot, es kotosd be a gate-be
Legyen uj smoke script, peldaul:
- `scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`

A smoke legalabb ezeket bizonyitsa valodi Supabase / worker / solver nelkul:
- a `nesting_engine_runner` parser elfogadja a `--compaction slide` flaget;
- a `main()` vagy az ekvivalens arg-build ut tenylegesen tovabbitja a `--compaction`
  flaget a `nesting_engine_cli_args` listaba;
- a frissitett T1 smoke zold lehet ugyanabban a repo-allapotban;
- a T1/T6 historical task artefaktok kozott mar nincs outputs/report drift.

A `scripts/check.sh` legyen ugy bovitve, hogy ez a smoke a standard gate reszekent is fusson.
A bovites maradjon olcso, pure-Python jellegu, ne igenyeljen Rust buildet vagy kulso szervizt.

### 4. Rendezd a T1/T6 task-szerzodesi driftet evidence-first modon
A T1 es T6 historical taskoknal a repo jelenleg bizonyitott ellentmondast hordoz a
YAML `outputs` lista es a report allitasai kozott.

Ezt **ne vakon** kezeld.

Elvaras:
- ne automatikusan szelesitsd ki a historical YAML outputs listat, ha arra nincs valos ok;
- ne automatikusan vagd ki a report allitast sem, ha a repo evidenciak inkabb azt mutatjak,
  hogy a historical smoke fajl tenyleg a task resze volt;
- minimalis, truth-preserving korrekciot csinalj.

A task elfogadhato megoldasa barmelyik lehet, ha evidence-first es kovetkezetes:
- vagy a historical YAML outputs lista bovul minimalisan a hianyzo smoke fajllal,
- vagy a report szovege / modified-files resze javul ugy, hogy mar nem allit nem engedelyezett
  modositast,
- vagy ezek kombinalt, de kovetkezetes rendezese.

A lenyeg: a task vegen a repo mar ne tartalmazzon olyan bizonyitott historical
YAML/report ellentmondast, amit az audit blokkolo megjegyzesnek minositett.

### 5. Uj closure-fix report legyen oszinte es konkret
Az uj task report kulon nevezze meg:
- mi volt a T7/T8 blokkolo parser hiba;
- pontosan hogyan lett a `--compaction` fix bekotve;
- miert volt hibas a T1 smoke eredeti assertje;
- hogyan lett rendezve a T1/T6 outputs drift;
- hogy a task szandekosan nem hozott letre uj quality feature-t, csak a closure fixeket.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t9_quality_lane_audit_es_hibajavitas.yaml`
- `codex/prompts/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas/run.md`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`
- `scripts/check.sh`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`
- `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
- `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `codex/codex_checklist/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`
- `codex/reports/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`

## DoD
- a `vrs_nesting.runner.nesting_engine_runner` parser elfogadja a `--compaction off|slide` flaget;
- a Python runner a `--compaction` erteket tenylegesen tovabbitja a `nesting_engine_cli_args` listaba;
- a T1 dedikalt smoke mar nem stale literal backend-stringre epit;
- van uj, dedikalt T9 regresszios smoke, amely a parser fixet es a task-szerzodesi konzisztenciat is ellenorzi;
- a `scripts/check.sh` futtatja ezt az uj smoke-ot;
- a T1/T6 historical YAML/report drift evidence-first modon rendezve van;
- a standard verify wrapper lefut, report + log frissul;
- az uj report oszinten kimondja, hogy ez closure-fix task, nem uj quality feature.

## Kockazat + rollback
- Kockazat:
  - a historical task artefaktok javitasanal konnyu tul sokat atirni;
  - a parser fix latszolag kesz lehet akkor is, ha a `main()` nem tovabbitja a flaget;
  - a T1 smoke konnyen ateshet a lo tuloldalara, ha tul gyenge assertion lesz.
- Mitigacio:
  - minimal-invaziv, evidence-first korrekciok;
  - uj dedikalt smoke a parser -> arg-build utra;
  - a T1 smoke-ban konkret strukturakat ellenorizz, ne ures substringeket.
- Rollback:
  - a parser fix + smoke + historical task korrekciok egy task-commitben visszavonhatok;
  - nincs schema vagy migration kockazat.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md`
- Feladat-specifikus minimum:
  - `python3 -m py_compile vrs_nesting/runner/nesting_engine_runner.py scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`
  - `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
  - `python3 scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`
- Celozott parser regresszio-check:
  - `python3 -m vrs_nesting.runner.nesting_engine_runner --input /tmp/missing.json --seed 1 --time-limit 1 --compaction slide`
    - az elfogadhato hiba ezutan mar csak input/binary runtime hiba lehet;
      `unrecognized arguments: --compaction slide` **nem** maradhat.

## Kapcsolodasok
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`
- `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
- `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- `canvases/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `canvases/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `worker/main.py`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `scripts/check.sh`
