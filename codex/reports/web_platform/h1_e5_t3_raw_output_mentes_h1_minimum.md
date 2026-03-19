PASS_WITH_NOTES

## 1) Meta
- Task slug: `h1_e5_t3_raw_output_mentes_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t3_raw_output_mentes_h1_minimum.yaml`
- Futas datuma: `2026-03-19`
- Branch / commit: `main @ 673b6eb (dirty working tree)`
- Fokusz terulet: `Worker raw output artifact persistence (H1 minimum)`

## 2) Scope

### 2.1 Cel
- Explicit worker-oldali helper boundary bevezetese a raw output artifact persistence-re.
- A raw artifact storage path canonical H0 policyra allitasa (`projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`) a `run-artifacts` bucketben.
- Idempotens `app.run_artifacts` regisztracio biztositas retry/re-run esetekre.
- A raw evidence visszakereshetosegenek megtartasa success/failure/timeout/cancel/lease-lost eletciklusban, ahol a fajl tenylegesen rendelkezesre all.
- Task-specifikus smoke fake upload/register boundaryval a canonical path, mapping es hash/path determinisztika bizonyitasara.

### 2.2 Nem-cel (explicit)
- Result normalizer vagy projection pipeline.
- Viewer SVG/DXF/export artifact generalas.
- Worker queue lease mechanika ujratervezese.
- `app.run_artifacts` schema/enums tovabbi migracios modositasai.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t3_raw_output_mentes_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum/run.md`
- `worker/raw_output_artifacts.py`
- `worker/main.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`
- `codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`

### 3.2 Mi valtozott es miert
- `worker/raw_output_artifacts.py`: kulon helper modulba kerult a raw artifact lista, canonical path kepzes, hash-alapu tarolasi kulcs, metadata es register boundary.
- `worker/main.py`: a queue processing canonical futasi agaban a run snapshot `project_id` alapjan fut a raw artifact persistence, plusz idempotens `register_run_artifact_raw` SQL path kerult be (`ON CONFLICT`).
- `vrs_nesting/runner/vrs_solver_runner.py`: a `run.log` most timeout/non-zero/missing-output/success agban is keletkezik, igy stabil raw evidence uploadolhato.
- `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py`: fake gateway boundaryval bizonyitja a canonical path prefixet, artifact-kind mappinget, determinisztikus hash/path kepzest, illetve failure/timeout evidence retentiont.

### 3.3 Canonical raw artifact path kepzes
- A storage path a `worker/raw_output_artifacts.py` helperben kepzodik:
  - `projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_sha256}.{ext}`
  - forras: `worker/raw_output_artifacts.py:60-74`, `worker/raw_output_artifacts.py:96-104`.

### 3.4 H1 minimum raw evidence fajlok es branch-garanciak
- Success branch (runner output teljes): `solver_stdout.log`, `solver_stderr.log`, `solver_output.json`, `runner_meta.json`, `run.log`.
- Non-zero / timeout / missing-output branch: `solver_stdout.log` + `solver_stderr.log` + `runner_meta.json` + `run.log`; `solver_output.json` csak ha tenylegesen letrejott.
- Cancel / lease-lost branch: a worker a run_dir-ben mar meglevo raw fajlokat tartja meg es menti; nem gyart szintetikus fajlokat.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py worker/raw_output_artifacts.py worker/queue_lease.py worker/engine_adapter_input.py vrs_nesting/runner/vrs_solver_runner.py scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit worker-oldali raw artifact persistence helper/boundary. | PASS | `worker/raw_output_artifacts.py:10-141` | Kulon modul tartalmazza a raw artifact specifikaciot, canonical path kepzest, feltoltest es regisztraciot. | `py_compile` |
| A raw output mentes H0 canonical `run-artifacts` bucket + path policy szerint tortenik. | PASS | `worker/main.py:184`; `worker/raw_output_artifacts.py:60-74`; `worker/raw_output_artifacts.py:98-104`; `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py:52-55` | Default bucket `run-artifacts`, path policy canonical project-prefixes mintaval. | Smoke PASS |
| A `solver_stdout.log` / `solver_stderr.log` / `solver_output.json` / `runner_meta.json` / `run.log` raw evidence visszakereshetoen tarolhato. | PASS | `worker/raw_output_artifacts.py:30-36`; `worker/main.py:1289-1304`; `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py:136-151` | A helper explicit kezeli ezt az ot fajlt, a worker run_dir-bol persistalja es a smoke ellenorzi. | Smoke PASS |
| Az `app.run_artifacts` regisztracio idempotens es retry-biztos. | PASS | `worker/main.py:489-520`; `worker/raw_output_artifacts.py:95-104`; `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py:124-135` | Hash-alapu path + `ON CONFLICT (run_id, storage_path) DO UPDATE` stabil, retry-biztos regisztraciot ad. | Smoke idempotency assert |
| Hibas futasoknal is megmarad a lenyegi raw evidence a reportban tisztazott szabaly szerint. | PASS | `vrs_nesting/runner/vrs_solver_runner.py:202-220`; `vrs_nesting/runner/vrs_solver_runner.py:234-235`; `worker/main.py:1289-1312`; `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py:160-186` | Timeout/non-zero/missing-output agban is ir meta+run.log, worker persistalja a tenylegesen letrejott raw fajlokat. | Smoke failure+timeout PASS |
| A task nem csuszik at result normalizer / projection / viewer artifact scope-ba. | PASS | `worker/raw_output_artifacts.py:30-36`; `worker/main.py:1291-1298`; `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t3_raw_output_mentes_h1_minimum.yaml:18-25` | Csak raw output artifact perszisztencia valtozott; nincs normalizer/projection/viewer pipeline modositas. | Diff review |
| Keszul task-specifikus smoke a canonical raw-output mentes fo agakra. | PASS | `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py:20-42`; `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py:116-186` | Fake upload/register boundary es success/failure/timeout branch ellenorzesek keszultek. | Smoke PASS |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md:1`; `codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md:1` | A checklist pontok es a DoD->Evidence matrix kitoltve. | Dokumentacios ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.verify.log` | A standard repo gate wrapperrel futtatva. | verify.sh |

## 6) Advisory notes
- A `worker/main.py`-ben letezo legacy artifact helper kodreszek maradnak a fajlban, de a H1-E5-T3 canonical raw path mar az uj helperen fut.
- Cancel/lease-lost esetben a garancia "best-effort existing raw files", mert ezekben az agokban a subprocess leallitasa idozitesfuggo.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-19T22:06:30+01:00 → 2026-03-19T22:10:03+01:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.verify.log`
- git: `main@673b6eb`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 vrs_nesting/runner/vrs_solver_runner.py | 16 ++++++
 worker/main.py                          | 88 +++++++++++++++++++++++----------
 2 files changed, 78 insertions(+), 26 deletions(-)
```

**git status --porcelain (preview)**

```text
 M vrs_nesting/runner/vrs_solver_runner.py
 M worker/main.py
?? canvases/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e5_t3_raw_output_mentes_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum/
?? codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md
?? codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.verify.log
?? scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py
?? worker/raw_output_artifacts.py
```

<!-- AUTO_VERIFY_END -->
