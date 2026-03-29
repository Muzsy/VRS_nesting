# H3-Quality-T1 Engine observability es artifact truth

## Funkcio
Ez a task egy kulon **quality lane** elso lepese a H3-E4 elott.
A cel nem uj remnant/inventory domain, hanem az, hogy a web_platform futasokrol
vegul stabil, auditálható es quality-debugra alkalmas truth keletkezzen.

A jelenlegi repoban mar latszik egy torz allapot:
- a worker eloallit egy v1 solver input payloadot es feltolti input snapshotkent;
- a runtime futas kulon `solver_input.json` fajllal dolgozik;
- a viewer a `solver_input` artifact vilagabol probal sheet meretet es part meretet
  visszaolvasni;
- a trial tool jelenleg foleg orchestration evidence-t ment, de backend / contract /
  artifact completeness nezopontban meg nem eleg eros.

Ez a task **nem** nesting_engine_v2 adapter task, **nem** dual-engine switch,
**nem** result normalizer v2 task es **nem** H3-E4 remnant task.
A cel itt az, hogy a kesobbi engine-integracios lepesekhez ne vakon debugoljunk.

## Scope
- Benne van:
  - hivatalos solver input artifact truth rendberakasa;
  - engine backend / contract version / profile meta egyertelmu rogzitese;
  - viewer oldali input artifact fallback logika tisztazasa;
  - trial tool summary bovitese quality-debugra alkalmas metaadatokkal;
  - task-specifikus smoke, ami bizonyitja az artifact truthot es a viewer input fallbackot.
- Nincs benne:
  - nesting_engine_v2 input adapter;
  - worker backend valtas;
  - v2 result normalizer;
  - frontend layout redesign;
  - remnant/inventory domain;
  - DXF preflight/normalize modul implementacio.

## Talalt relevans fajlok (pontos kodhelyzet)
- `worker/main.py`
  - L1209: `build_solver_input_from_snapshot(snapshot_row)` — itt epul a solver input payload.
  - L1217-1221: `solver_input_snapshot_v1.json` lokalis fajl a temp/input konyvtarba.
  - L1222-1226: `runs/{run_id}/inputs/solver_input_snapshot.json` feltoltes storage-be (de NEM regisztralva artifact-kent!).
  - L1227: `set_run_input_snapshot_hash` — hash mentese a run-re.
  - L1229-1230: `solver_input.json` runtime fajl letrehozasa a solver szamara (ez egy kulon fajl az input_dir-ben).
  - L1231-1237: a `vrs_solver_runner` innen kapja a `--input` parameterben a runtime solver_input.json-t.
  - L960-980: `_artifact_type_for_path` — `solver_input.json` nevet `"solver_input"` artifact_type-ra mappeli.
  - Nincs explicit `engine_meta` (backend/contract/profile) artifact regisztracio.
- `worker/engine_adapter_input.py`
  - L146-236: `build_solver_input_from_snapshot` — snapshot -> solver_input v1 mapper.
  - L229: kimeneti payload `contract_version: "v1"` — ez az egyetlen engine_contract hely.
  - L239-241: `solver_input_sha256` — determinisztikus hash szamitas.
- `api/routes/runs.py`
  - L800-802: `solver_payload`, `solver_input_payload` init ures dict-kent.
  - L845-859: `solver_input` artifact keresese (`artifact_type == "solver_input"` VAGY `filename.endswith("solver_input.json")`).
  - L861-862: `_parse_solver_input_part_sizes` / `_parse_solver_input_sheet_sizes` a part/sheet meret olvasashoz.
  - L916-923: sheet meretek fallback: CSAK ha `solver_input_payload` tartalmazza a stocks-t.
  - Ha a `solver_input` artifact nem letezik, `solver_input_payload = {}` marad es a sheet meretekre `None` jon.
- `scripts/trial_run_tool_core.py`
  - L810-877: `_build_summary_markdown` — status, run_dir, project_id, run_id, counts, technology_setup, token.
  - Hianyzo mezok: engine_backend, contract_version, input/output artifact jelenlet,
    run.log/runner_meta/stderr jelenlet, artifact completeness.
- `scripts/smoke_trial_run_tool_cli_core.py`
  - jo minta a tool oldali smoke feladathoz.
- `scripts/smoke_h1_real_solver_artifact_chain_closure.py`
  - referencia a solver artifact truth closure gondolkodashoz.

## Jelenlegi artifact truth zavar (felderites eredmenye)
A worker ket kulonbozo helyre menti a solver inputot:
1. **Storage upload**: `runs/{run_id}/inputs/solver_input_snapshot.json` — ez a storage-ba feltoltott teljes
   payload, de NINCS `run_artifacts` tablabol elintezheto artifact regisztracio hozza.
2. **Runtime fajl**: `solver_input.json` az `input_dir`-ben — ezt kapja a solver runner `--input`-kent,
   de ez is eltunik a temp dir takaritassal.
3. **Run-dir artifacts**: a `vrs_solver_runner` a run_dir-be maskent irhatja ki — ha kiirja, az
   `_upload_run_artifacts` felismeri (`solver_input.json` -> `solver_input` artifact_type).

A viewer (L845-859) az `solver_input` artifact_type-ot keresi a `run_artifacts` tablabol.
Ha ez nincs (mert pl. a runner nem masolta ki a run_dir-be), a sheet meretek `None` lesznek,
es a viewer csendes, fals kepet ad. Nincs fallback a snapshot upload-ra.

## Konkret elvarasok

### 1. Egyertelmu input artifact truth legyen
A worker jelenleg ne csak belso futasi fajlt irjon, hanem egyertelmuen kezelje,
hogy melyik a hivatalos input artifact. A task eredmenyeben:
- legyen vilagos, melyik artifact tekintendő hivatalos solver inputnak;
- a storage oldalon ne legyen ketertelmu a `solver_input` vs `snapshot` szerep;
- a report / summary tudja megmondani, melyik input fajl a source of truth.

### 2. Engine meta ne logokbol kelljen kitalalni
A run artifact vilagban minimum visszaolvashato legyen:
- `engine_backend`
- `engine_contract_version`
- `engine_profile` vagy egyertelmu `default`
- ha van, `solver_runner_module`

Ezt ne csak stderr logban vagy implicit fajlnevben lehessen megtalalni.

### 3. Viewer fallback legyen robusztus
A `viewer-data` endpoint jelenleg az input artifact alapjan allitja elo a part- es sheet-mereteket.
A task utan:
- ha a canonical `solver_input` artifact elerheto, azt olvassa;
- ha csak snapshot jellegu input van, legyen determinisztikus fallback;
- ne adjon csendes, fals sheet-size kepet csak azert, mert az input artifact elnevezese elcsuszott.

### 4. Trial tool summary mondja ki a quality-debug minimumot
A `scripts/trial_run_tool_core.py` summary/resolved config vilagaban latszodjon legalabb:
- melyik backend futott;
- milyen contract verzio futott;
- elerheto-e a solver input artifact;
- elerheto-e a solver output artifact;
- elerheto-e a run.log / runner_meta / stderr;
- artifact completeness jelzo.

Ez a task meg nem A/B diff task, de mar tegye atlathatova, hogy mennyire teljes a run evidence.

### 5. Legyen dedikalt smoke
Keszits task-specifikus smoke-ot, ami minimum ezt bizonyitja:
- a worker oldali artifact truth egyertelmu;
- a canonical input artifactbol a viewer vissza tudja olvasni a sheet mereteket;
- fallback eseten is determinisztikus viselkedes van;
- a trial tool summary tartalmazza a backend / contract / artifact completeness adatokat.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`
- `codex/prompts/web_platform/h3_quality_t1_engine_observability_and_artifact_truth/run.md`
- `worker/main.py`
- `api/routes/runs.py`
- `scripts/trial_run_tool_core.py`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `codex/codex_checklist/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`

## DoD
- a run input artifact source of truth egyertelmu es dokumentalt;
- a viewer input artifact fallbackkal egyutt helyes sheet-size es utilization kepet ad;
- a trial tool summary kifejezetten kimondja a backend/contract/artifact teljestseget;
- a dedikalt smoke zold;
- a standard verify wrapper lefut, report + log frissul.
