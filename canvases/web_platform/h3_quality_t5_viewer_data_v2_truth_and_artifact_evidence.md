# H3-Quality-T5 Viewer-data v2 truth es artifact evidence

## Funkcio
Ez a task a H3 quality lane otodik lepese.
A T4 utan a worker mar kepes a `nesting_engine_v2` backend futtatasara, es a
run artifactok kozott megjelenik a canonical `solver_input.json`, az
`engine_meta.json`, valamint a raw `nesting_output.json` is.

A jelenlegi `GET /v1/projects/{project_id}/runs/{run_id}/viewer-data` endpoint
viszont tovabbra is alapvetoen v1-centrikus:
- csak a legacy `solver_output.json` formatumot tudja placement/unplaced oldalrol
  ertelmezni;
- a solver inputbol csak a v1 `parts[].width/height` es `stocks[]` vilagot ismeri;
- a T4-ben bevezetett `engine_meta.json` es `nesting_output.json` evidence-t nem
  hasznalja determinisztikus artifact-truth kivalsztashoz;
- emiatt a v2 runok viewer-data kepileg hamis vagy hianyos maradhat, hiaba ment
  vegig a worker mar `done` allapotig.

Ez a task ezt a gapet zarja le. A cel **nem** frontend/UI rollout, hanem az,
hogy az API viewer-data response mar valos, backend-helyes kepet adjon a v1 es
v2 runokrol is.

## Scope

### Benne van
- a `viewer-data` endpoint v1+v2 kompatibilis raw artifact olvasasa;
- backend-helyes input/output artifact kivalsztas determinisztikus szaballyal;
- a v2 `solver_input`/`nesting_engine_v2` input sheet- es part-meret parse-olasa;
- a v2 `nesting_output.json` placement/unplaced parse-olasa viewer response-ba;
- optional engine/artifact evidence mezok a response-ban, visszafele kompatibilis
  boviteskent;
- dedikalt task-smoke v1 legacy, v2 truth es fallback esetekre.

### Nincs benne
- frontend komponens, run detail oldal vagy vizualis UI atalakitasa;
- worker runtime vagy result normalizer tovabbi valtoztatasa;
- benchmark harness / trial tool A-B diff UX;
- run-level backend selector DB oldali kivezetese;
- quality scoring vagy placement tuning.

## Talalt relevans fajlok / jelenlegi kodhelyzet
- `api/routes/runs.py`
  - a `get_viewer_data(...)` endpoint a run artifact listat olvassa;
  - jelenleg `solver_output`/`solver_output.json` raw outputot es
    `solver_input`/`solver_input.json` inputot keres;
  - a fallback snapshot olvasas mar letezik `solver_input_snapshot.json`-ra;
  - a helper parse-ok (`_parse_solver_input_part_sizes`,
    `_parse_solver_input_sheet_sizes`, `_parse_solver_output`) jelenleg v1-re vannak
    kihegyezve.
- `worker/main.py`
  - T1 ota canonical input artifact truth van;
  - T4 ota `engine_meta.json` es `nesting_output.json` is keletkezhet.
- `worker/raw_output_artifacts.py`
  - T4 ota a `nesting_output.json` formal raw artifactkent perszistalodik.
- `docs/nesting_engine/io_contract_v2.md`
  - normativan rogzitett a `nesting_engine_v2` input/output schema.
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
  - jo minta a viewer-data fake Supabase smoke szerkezetere.

## Jelenlegi runtime / API gap
A worker oldalon mar van v2 bridge, de a viewer-data endpoint tovabbra is csak
reszben ismeri az uj truthot. Ennek kovetkezmenyei:
- v2 inputnal a sheet meretek nem feltetlenul jelennek meg, mert a parser a v1
  `stocks[]` mezot keresi, mikozben v2-ben `sheet.width_mm/height_mm` van;
- v2 outputnal a placement mezok mas neven jonnek (`sheet`, `x_mm`, `y_mm`,
  `instance`), amit a legacy parser nem olvas;
- ha ugyanabban a runban tobb raw output-szeru artifact is latszik, nincs explicit
  backend-aware valasztasi szabaly;
- az endpoint jelenleg nem ad vissza strukturalt engine/artifact evidence-t, pedig
  T1/T4 ota az API mar tudna ezt audit- es debug-celra kozolni.

## Konkret elvarasok

### 1. Vezess be determinisztikus engine/input/output artifact truth valasztast
A `viewer-data` endpoint ne csak filename vegzodes alapjan olvasson, hanem
hasznalja a run artifact metadata-t es ahol relevans, az `engine_meta.json`-t is.

Kotelezo minimum szabaly:
- input truth preferencia: formal `solver_input` artifact -> snapshot fallback;
- output truth preferencia: raw output artifact, amelyik backendhez/passzolo
  filename-hez tartozik (`solver_output.json` v1, `nesting_output.json` v2);
- ha van olvashato `engine_meta.json`, azt hasznald a backend/contract truth
  feloldasahoz;
- ha nincs `engine_meta.json`, a valasztas legyen tovabbra is determinisztikus,
  filename + artifact_type + stabil sorrend alapjan.

### 2. A solver input parse legyen v1+v2 kompatibilis
Bovitsd a helper parse-okat ugy, hogy:
- v1-ben a meglevo `parts[].width/height` es `stocks[]` logika valtozatlanul
  megmaradjon;
- v2-ben a `parts[].outer_points_mm` / `holes_points_mm` alapjan legyen
  bbox-meret szamitas a viewer kartya szamara;
- v2-ben a single-sheet `sheet.width_mm` / `sheet.height_mm` vilagbol is kepzodjon
  sheet meret;
- ha a v2 input valojaban ugyanannak a sheetnek tobb peldanyat jelenti, a parser
  dokumentalt, determinisztikus modon adjon viewer sheet mereteket (minimum a
  tenylegesen hasznalt sheet indexekig).

### 3. A raw output parse legyen v1+v2 kompatibilis
A placement/unplaced parse helper tudja mindket schema-t:
- v1: `solver_output.json` legacy mezok;
- v2: `nesting_output.json` (`part_id`, `instance`, `sheet`, `x_mm`, `y_mm`,
  `rotation_deg`, `reason`).

Kotelezo minimum:
- a response `placements[]` es `unplaced[]` struktura maradjon backward kompatibilis;
- v2-ben az `instance_id` determinisztikusan kepzodjon (ajanlott: `part_id:instance`);
- a placement `width_mm` / `height_mm` a parsed input geometry truthbol jojjon;
- a v1 parser ne torjon el.

### 4. A sheet metrics legyenek v2-ben is ertelmesek
A viewer `sheets[]` listaban a `width_mm`, `height_mm`, `placements_count` es
`utilization_pct` v2 runnal se essen vissza ures/null allapotba.

Elfogadhato minimum:
- a per-sheet meretek legyenek kitoltve, ha az input truth tartalmazza oket;
- a `placements_count` a parsed placements alapjan helyes legyen;
- a `utilization_pct` legalabb ugyanazzal a hasznos simple-area logikaval kepzodjon,
  mint a v1 legacy esetben;
- ha a v2 raw output objective-bol egyertelmu globalis utilization olvashato, azt
  csak kiegeszito evidencekent hasznald, ne torj fel az endpoint szemantikajat.

### 5. Adj vissza optional engine/artifact evidence mezoket
A `ViewerDataResponse` additive, backward kompatibilis boviteskent kapjon optional
mezoket az audit/debug celokra.

Javasolt minimum mezok:
- `engine_backend`
- `engine_contract_version`
- `engine_profile`
- `input_artifact_source` (`artifact` / `snapshot_fallback` / `unknown`)
- `output_artifact_filename`
- `output_artifact_kind`

Szabaly:
- ezek optional mezok legyenek, ne torjek a meglevo klienseket;
- a response a T1/T4 artifact truthot tegye atlathatova, ne UI-specifikus extra
  payloadot epitsen.

### 6. Keszits dedikalt task-specifikus smoke-ot
A smoke legalabb ezt bizonyitsa fake Supabase klienssel:
- legacy v1 runnal a viewer-data a regi `solver_output.json` + `solver_input.json`
  vilagban tovabbra is helyes marad;
- v2 runnal a viewer-data a `nesting_output.json`-t parse-olja, kitolti a placements,
  sheets, rotation es sheet mereteket;
- ha a formal `solver_input` artifact hianyzik, a snapshot fallback tovabbra is
  mukodik;
- ha van `engine_meta.json`, annak truthja visszajon a response optional evidence
  mezoiben;
- a viselkedes determinisztikus (ismetlendo hivas ugyanarra az inputra azonos
  eredmenyt ad).

A smoke ne kerjen valodi Supabase-ot es ne kerjen valodi solver binary-t.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.yaml`
- `codex/prompts/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence/run.md`
- `api/routes/runs.py`
- `scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py`
- `codex/codex_checklist/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`
- `codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`

## DoD
- a `viewer-data` endpoint v1 es v2 raw output truthot is helyesen tud olvasni;
- a solver input parse v2 inputnal is ad sheet- es part-meretet a viewer response-hoz;
- a response `placements[]` / `unplaced[]` strukturaja backward kompatibilis marad;
- a `ViewerDataResponse` optional engine/artifact evidence mezokkel bovul;
- a formal `solver_input` artifact -> snapshot fallback szabaly tovabbra is mukodik;
- a v1 legacy viewer viselkedes nem torik el;
- a task-specifikus smoke zold;
- a standard verify wrapper lefut, report + log frissul.

## Kockazat + rollback
- Kockazat:
  - a viewer-data endpoint túl sok backend-specific logikat kap;
  - a v2 parse kozben a legacy v1 viewer response regressziot szenved;
  - a sheet metric szamitas elorefut a kesobbi UI igenyekhez kepest.
- Mitigacio:
  - tartsd a scope-ot szigoruan az API truth/parsing retegre;
  - a response bovites additive legyen;
  - a smoke fedje a v1 legacy es v2 truth esetet is.
- Rollback:
  - a helper parse + response model + smoke diff egy task-commitban visszavonhato;
  - mivel a valtozas API-oldali es additive, a kockazat kontrollalhato.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/routes/runs.py scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py`
  - `python3 scripts/smoke_h3_quality_t5_viewer_data_v2_truth_and_artifact_evidence.py`
  - ajanlott regresszio: `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`

## Kapcsolodasok
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `api/routes/runs.py`
- `worker/main.py`
- `worker/raw_output_artifacts.py`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
