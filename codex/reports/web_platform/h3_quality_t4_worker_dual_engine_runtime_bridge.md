PASS

## 1) Meta
- Task slug: `h3_quality_t4_worker_dual_engine_runtime_bridge`
- Kapcsolodo canvas: `canvases/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t4_worker_dual_engine_runtime_bridge.yaml`
- Futas datuma: `2026-03-30`
- Branch / commit: `main @ 510071a (dirty working tree)`
- Fokusz terulet: `Worker runtime bridge (dual engine, projection, raw artifacts)`

## 2) Scope

### 2.1 Cel
- A worker runtime kapjon explicit backend selector alapjan v1/v2 switch-et, `sparrow_v1` defaulttal.
- A backend valasszon megfelelo snapshot->input buildert, hash helpert es runner invocation-t.
- A canonical `solver_input` artifact es az `engine_meta.json` valos backend truthot tartalmazzon v2 runnal is.
- A raw artifact persist tartsa meg a `nesting_output.json` kimenetet.
- A result normalizer tudjon v2 `nesting_output.json`-bol is projectiont adni, mikozben a v1 ut erintetlen marad.
- Keszuljon dedikalt smoke, ami bizonyitja a v1 default utat, a v2 switch-et es az invalid backend fail-fastot.

### 2.2 Nem-cel (explicit)
- Viewer-data endpoint vagy UI oldali v2 artifact megjelenites.
- Benchmark UX / A-B diff workflow.
- Run-level DB-s backend selector bevezetese.
- H3-E4 remnant vagy inventory domain rollout.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/raw_output_artifacts.py`
- `worker/result_normalizer.py`
- `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`
- `codex/codex_checklist/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`
- `codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md`

### 3.2 Mi valtozott es miert
- `worker/main.py`: bejott a `WORKER_ENGINE_BACKEND` alapu runtime dispatch (`sparrow_v1` / `nesting_engine_v2`), backend-fuggo builder/hash valasztassal es runner invocationnel (`vrs_solver_runner` vs `nesting_engine_runner --run-root`).
- `worker/main.py`: az `engine_meta.json` most backend-aware, mar nem fix v1 metadata.
- `worker/engine_adapter_input.py`: uj `nesting_engine_runtime_params(...)` helper a v2 payload runtime parametereinek tipusos/parsolt kezelesere.
- `worker/raw_output_artifacts.py`: a nyers artifact policy most mar `nesting_output.json`-t is perszistal.
- `worker/result_normalizer.py`: uj explicit v2 normalizer ag kerult be (`nesting_output.json`), mikozben a v1 ag valtozatlanul megmaradt.
- `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`: dedikalt fake worker/subprocess smoke bizonyitja a runtime bridge-kovetelmenyeket.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md` -> PASS

### 4.2 Opcionális, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py worker/engine_adapter_input.py worker/raw_output_artifacts.py worker/result_normalizer.py scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` -> PASS
- `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` -> PASS
- `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Worker explicit backend selector `sparrow_v1` defaulttal es `nesting_engine_v2` alternativaval | PASS | `worker/main.py:60`; `worker/main.py:107`; `worker/main.py:159`; `worker/main.py:200` | A backend enum es parser explicit, invalid ertekre korai `WorkerSettingsError` keletkezik, default marad `sparrow_v1`. | `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` |
| #2 Backend alapjan builder/hash/runner valasztas | PASS | `worker/main.py:1123`; `worker/main.py:1262`; `worker/main.py:1313`; `worker/engine_adapter_input.py:384` | A worker v1/v2 agban kulon valasztja az input buildert, hash helpert, runtime param parse-t es runner modult. | `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` |
| #3 Canonical `solver_input` artifact + `engine_meta.json` helyes truth v2 runnal is | PASS | `worker/main.py:1285`; `worker/main.py:1298`; `worker/main.py:1321` | A canonical input artifact kozos marad, az engine meta backend/contract/runner/hash adatokat valosan irja. | `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` |
| #4 Raw artifact persist a `nesting_output.json`-t sem veszti el | PASS | `worker/raw_output_artifacts.py:30`; `worker/raw_output_artifacts.py:34`; `worker/raw_output_artifacts.py:91` | A raw artifact spec bovitve lett v2 outputtal, metadata `legacy_artifact_type` egyertelmuen `nesting_output`. | `python3 scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py` |
| #5 Van minimum v2 normalizer ut, ami `done` projectiont tud epiteni | PASS | `worker/result_normalizer.py:536`; `worker/result_normalizer.py:583`; `worker/result_normalizer.py:659`; `worker/result_normalizer.py:754` | A normalizer `nesting_output.json` esetben explicit v2 agat futtat, placements/unplaced/metrics/sheet sorokkal downstream kompatibilis strukturat ad. | `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` |
| #6 A v1 default worker ut nem torik el | PASS | `worker/main.py:1264`; `worker/main.py:1132`; `worker/result_normalizer.py:338`; `worker/result_normalizer.py:755` | A v1 ag megmaradt, wrapper csak kiterjesztve lett file-alapu v1/v2 dispatch-csel. | `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`; `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` |
| #7 Task-specifikus smoke zold | PASS | `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py:403`; `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py:431`; `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py:460`; `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py:503` | A smoke bizonyitja a v1 default runner utat, a v2 switch-et, engine_meta truthot, projection `done` utat es invalid backend hibakezelest. | `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` |
| #8 Standard verify wrapper lefut, report + log frissul | PASS | `codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.verify.log` | A verify wrapper lefutott, a `.verify.log` fajl letrejott, az AUTO_VERIFY blokk frissult. | `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md` |

## 6) Advisory notes
- A task tudatosan worker runtime bridge scope-ban maradt; viewer-data/UI oldali v2 artifact megjelenites nem resze ennek a kornek.
- A v2 normalizer a meglévő snapshot geometry truth-ra epul (part bbox + polygon area), downstream kompatibilis mezostrukturaval.
- A `worker/main.py`-ban mar korabban is letezo canonical `solver_input` artifact regisztracio miatt egy regi smoke (`smoke_h1_e5_t2...`) fake kliens implementacioja nem teljes; ez nem volt e task output-scope-ja.

## 7) Follow-ups
- H3 kovetkezo korben a viewer-data endpoint v2 artifact-szemantikajat erdemes explicit kiegesziteni (`nesting_output` tipusu raw evidence visszaadasa).
- Ha run-level backend valaszto kell, azt kulon run_config + DB migration taskban kell bevezetni.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-30T00:21:52+02:00 → 2026-03-30T00:25:25+02:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.verify.log`
- git: `main@510071a`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 worker/engine_adapter_input.py |   6 ++
 worker/main.py                 | 132 ++++++++++++++++++------
 worker/raw_output_artifacts.py |   1 +
 worker/result_normalizer.py    | 228 ++++++++++++++++++++++++++++++++++++++++-
 4 files changed, 332 insertions(+), 35 deletions(-)
```

**git status --porcelain (preview)**

```text
A  docs/nesting_quality/nesting_quality_konkret_feladatok.md
 M worker/engine_adapter_input.py
 M worker/main.py
 M worker/raw_output_artifacts.py
 M worker/result_normalizer.py
?? canvases/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md
?? codex/codex_checklist/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_quality_t4_worker_dual_engine_runtime_bridge.yaml
?? codex/prompts/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge/
?? codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md
?? codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.verify.log
?? scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py
```

<!-- AUTO_VERIFY_END -->
