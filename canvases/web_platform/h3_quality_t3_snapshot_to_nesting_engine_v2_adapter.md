# H3-Quality-T3 Snapshot -> nesting_engine_v2 adapter

## Funkcio
Ez a task a H3 quality lane harmadik lepese.
A T1-ben rendbe lett rakva a run truth / artifact evidence, a T2-ben keszult
benchmark harness es `quality_summary.json`. A kovetkezo hiany most az, hogy a
web_platform snapshot vilaga meg mindig csak a legacy v1 solver inputot tudja
eloallitani, mikozben a repoban mar letezik kulon `nesting_engine_v2` contract
es kulon `nesting_engine_runner`.

Ez a task **nem** worker backend switch es **nem** actual engine rollout.
A cel most az, hogy a canonical run snapshotbol legyen egy kulon,
determinisztikus, auditálhato `nesting_engine_v2` input adapter, amire a T4
backend-valtas mar tisztan ra tud ulni.

## Scope

### Benne van
- explicit snapshot -> `nesting_engine_v2` input helper / builder a worker oldali
  adapter modulban;
- a v2 contracthoz tartozo seed / time_limit / sheet / parts mapping tiszta
  rogzitese;
- explicit, dokumentalt fail-fast korlatok a jelenlegi snapshot -> v2 mappinghez;
- determinisztikus canonical dump/hash helper a v2 inputhoz;
- task-specifikus smoke a sikeres es hibas agakra.

### Nincs benne
- worker `vrs_solver_runner` -> `nesting_engine_runner` valtas;
- dual-engine backend switch vagy feature flag;
- viewer/result normalizer v2 tamogatas;
- benchmark runner A/B diff logika;
- H3-E4 remnant / inventory domain;
- DXF preflight / normalize implementacio.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `worker/engine_adapter_input.py`
  - jelenleg csak `build_solver_input_from_snapshot(...)` letezik;
  - a rotation policy v1 korlat miatt csak `0/90/180/270` fokokat enged;
  - ide logikus tenni a v2 buildert is, hogy a snapshot mapping egy helyen maradjon.
- `worker/main.py`
  - jelenleg a `_process_queue_item(...)` fixen a v1 buildert hivja es a
    `vrs_nesting.runner.vrs_solver_runner` modult futtatja;
  - ez ebben a taskban meg NEM valtozik.
- `vrs_nesting/runner/nesting_engine_runner.py`
  - kulon runner boundary a `nesting_engine` binaryhoz;
  - a CLI `--input`, `--seed`, `--time-limit` parametereket var.
- `docs/nesting_engine/io_contract_v2.md`
  - a normativ v2 input contract source-of-truth;
  - kulcs pont: egyetlen `sheet` objektum van, nem `stocks[]` lista.
- `scripts/validate_nesting_solution.py`
  - mar ismeri a `nesting_engine_v2` boundary-t validator oldalon.
- `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
  - jo minta a snapshot adapter smoke szerkezetere.
- `scripts/smoke_platform_determinism_rotation.sh`
  - jo minta arra, milyen alakban varja a `nesting_engine` a v2 inputot.

## Jelenlegi adapter-res (felderites eredmenye)
A snapshot mar tartalmazza a v2-hoz szukseges legtobb adatot:
- `solver_config_jsonb.seed`
- `solver_config_jsonb.time_limit_s`
- `solver_config_jsonb.kerf_mm`
- `solver_config_jsonb.spacing_mm`
- `solver_config_jsonb.margin_mm`
- `solver_config_jsonb.rotation_step_deg`
- `solver_config_jsonb.allow_free_rotation`
- `parts_manifest_jsonb.required_qty`
- `parts_manifest_jsonb.selected_nesting_derivative_id`
- `geometry_manifest_jsonb[].polygon.outer_ring`
- `geometry_manifest_jsonb[].polygon.hole_rings`
- `sheets_manifest_jsonb[].width_mm` / `height_mm`

A fo gap most ez:
- nincs kulon v2 builder;
- nincs kimondva, hogyan kepezheto a snapshot sheet vilaga a v2 egyetlen `sheet`
  objektumara;
- nincs kimondva, milyen rotation policy tamogathato a v2 preview adapterben;
- nincs kulon determinisztikus smoke erre a boundary-ra.

## Konkret elvarasok

### 1. Keszits explicit v2 buildert
A `worker/engine_adapter_input.py` kapjon kulon helper(eke)t, peldaul:
- `build_nesting_engine_input_from_snapshot(snapshot)`
- `nesting_engine_input_sha256(payload)`
- ha kell, kulon kisebb parser/helper fuggvenyeket.

A v2 builder ne torje el a meglevo v1 build utat.

### 2. Seed / time limit / manufacturing parameterek forrasa legyen explicit
A v2 inputban:
- `version = "nesting_engine_v2"`
- `seed` a snapshot `solver_config_jsonb.seed` mezobol jojjon;
- `time_limit_sec` a snapshot `solver_config_jsonb.time_limit_s` mezobol jojjon;
- `sheet.kerf_mm`, `sheet.spacing_mm`, `sheet.margin_mm` a snapshot
  `solver_config_jsonb` manufacturing mezoi alapjan kepzodjenek.

Ne talalj ki uj konfiguracios forrast.

### 3. Rotation policy a v2 boundary-n legyen tágabb, de veges es determinisztikus
A v2 contract a `parts[].allowed_rotations_deg` tombben explicit, veges rotaciohalmazt var.

Ebben a taskban a helyes minimum viselkedes:
- ha `allow_free_rotation=true`, akkor fail-fast, mert a snapshot nem ad veges
  halmazt a v2 JSON boundaryhoz;
- ha `allow_free_rotation=false`, akkor a `rotation_step_deg` alapjan kepezd le a
  teljes 0..359 ciklust determinisztikusan (pelda: 90 -> `[0,90,180,270]`,
  45 -> `[0,45,90,135,180,225,270,315]`, 17 -> teljes veges ciklus modulo 360);
- ne maradjon benne a v1-es 0/90/180/270 korlat a v2 builderben.

### 4. Part geometry mapping legyen mm- és topology-hu
A v2 input minden `part` bejegyzese tartalmazza:
- `id`
- `quantity`
- `allowed_rotations_deg`
- `outer_points_mm`
- `holes_points_mm`

Az outer/hole geometriak a snapshot `geometry_manifest_jsonb` selected nesting
 derivative truth-jabol jojjenek. Ne bbox-only adaptert keszits.

### 5. Sheet mappingnel legyen kimondott fail-fast korlat
A v2 contract jelenleg egyetlen `sheet` objektummal dolgozik. Emiatt a taskban ne
 legyen hallgatozos, veszteseges mapping.

A minimum korrekt viselkedes:
- ha a snapshot pontosan egy hasznalhato sheet-familyt ad, azt kepezd le a v2
  `sheet` objektumra;
- ha a snapshot tobb, egymastol eltero sheet tipust hordoz, az adapter adjon
  egyertelmu, determinisztikus hibat;
- a task report mondja ki, hogy ez egy **single-sheet-family v2 adapter preview**,
  nem a teljes multi-stock backend rollout.

### 6. Determinizmus legyen bizonyithato
A v2 input builder ugyanolyan snapshotbol bitstabil canonical JSON hash-et adjon.
Kulonosen figyelj:
- parts rendezesere;
- rotaciohalmaz rendezesere;
- sheet kivalasztasi szabalyra;
- nincs `now()`/random/DB sorrend fugges.

### 7. Legyen task-specifikus smoke
Keszits dedikalt smoke-ot, ami minimum ezt bizonyitja:
- sikeres snapshot -> v2 input mapping;
- `version == nesting_engine_v2`;
- 45 fokos step policy helyesen teljes explicit rotaciohalmazza bomlik;
- a v2 input hash ket futasnal azonos;
- `allow_free_rotation=true` kontrollalt hibaval megall;
- tobb, eltero sheet tipus kontrollalt hibaval megall;
- hianyzo derivative geometry / hianyzo ring / ures parts hibat ad.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.yaml`
- `codex/prompts/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter/run.md`
- `worker/engine_adapter_input.py`
- `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py`
- `codex/codex_checklist/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`
- `codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`

## DoD
- letezik explicit snapshot -> `nesting_engine_v2` input builder;
- a v2 builder nem tori el a meglevo v1 build utat;
- a v2 input a `docs/nesting_engine/io_contract_v2.md` minimum input contractjaval kompatibilis;
- a rotation policy a v2 builderben mar nem a v1 0/90/180/270 korlatot koveti;
- a multi-sheet / nem reprezentalhato snapshot vilag fail-fast hibaval all meg;
- a v2 input canonical hash determinisztikus;
- a task-specifikus smoke zold;
- a standard verify wrapper lefut, report + log frissul.

## Kockazat + rollback
- Kockazat:
  - a task tul sokat vallal es atcsuszik backend switch scope-ba;
  - a sheet mapping csendesen veszteseges lesz;
  - a rotation policy nincs egyertelmuen lezarva.
- Mitigacio:
  - ebben a taskban ne nyulj a worker process futtato agahoz;
  - a sheet mappingnel fail-fast legyen a default, ne veszteseges fallback;
  - a smoke explicit bizonyitsa a sikeres es hibas agak viselkedeset.
- Rollback:
  - a builder + smoke + checklist/report diff egy task-commitban visszavonhato;
  - mivel nincs backend switch, a rollback kockazata alacsony.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/engine_adapter_input.py scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py`
  - `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py`

## Kapcsolodasok
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `worker/engine_adapter_input.py`
- `worker/main.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/validate_nesting_solution.py`
- `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
- `scripts/smoke_platform_determinism_rotation.sh`
