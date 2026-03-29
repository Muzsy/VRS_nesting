PASS_WITH_NOTES

## 1) Meta
- Task slug: `h3_quality_t1_engine_observability_and_artifact_truth`
- Kapcsolodo canvas: `canvases/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml`
- Futas datuma: `2026-03-29`
- Branch / commit: `main @ e7b9bd8 (dirty working tree)`
- Fokusz terulet: `Worker artifact truth + viewer fallback + trial tool observability`

## 2) Scope

### 2.1 Cel
- A solver input artifact source of truth egyertelmusitese a worker-ben.
- Engine meta (backend, contract_version, profile) visszakeresheto rogzitese a run evidence-ben.
- A viewer-data endpoint determinisztikus fallback logikaja canonical vs snapshot input eseten.
- A trial tool summary bovitese quality-debug minimum mezokkel.
- Task-specifikus smoke az artifact truth es viewer fallback igazolasara.

### 2.2 Nem-cel (explicit)
- nesting_engine_v2 input adapter
- worker backend valtas / dual-engine switch
- v2 result normalizer
- frontend layout redesign
- remnant/inventory domain
- DXF preflight/normalize modul

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `worker/main.py`
- `api/routes/runs.py`
- `scripts/trial_run_tool_core.py`
- `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py`
- `codex/codex_checklist/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`
- `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md`

### 3.2 Mi valtozott es miert
- Korabbi artifact truth zavar: a worker feltoltotte a `solver_input_snapshot.json` payloadot storage-ba, de ez nem volt formalis `solver_input` artifactkent regisztralva, igy a viewer csak esetenkent talalt inputot.
- Task utani canonical input/source of truth: a worker explicit `solver_input` artifactkent regisztralja a `runs/{run_id}/inputs/solver_input_snapshot.json` objektumot, igy a run_artifacts API-bol determinisztikusan felderitheto.
- Viewer canonical vs fallback: a viewer-data endpoint eloszor a canonical `solver_input` artifactot olvassa, es csak ha nincs, akkor fallbackel a snapshot kulcsra (`runs/{run_id}/inputs/solver_input_snapshot.json`).
- Engine meta visszakereshetoseg: explicit `engine_meta.json` artifact kerul run evidence-be, benne backend, contract version, profile es runner module adatokkal.
- Trial summary quality-debug: uj `Engine & Artifact Evidence` szekcio jelzi backend/contract/allapot mezoket es az artifact completeness erteket.
- Miert fontos v2/dual-engine elott: a kovetkezo adapter/backend taskok csak akkor debugolhatok megbizhatoan, ha a canonical input es a tenyleges engine meta egyertelmuen visszaolvashato run-szinten.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md` -> PASS

### 4.2 Opcionalis, feladatfuggo ellenorzes
- `python3 -m py_compile worker/main.py api/routes/runs.py scripts/trial_run_tool_core.py` -> PASS
- `python3 -m py_compile scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` -> PASS
- `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Run input artifact source of truth egyertelmu | PASS | `worker/main.py:1230`; `worker/main.py:1235`; `worker/main.py:1239` | A canonical solver input snapshot explicit `solver_input` artifactkent regisztralodik a run artifact tablaba. | `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` |
| #2 Viewer input fallback helyes sheet-size/utilization | PASS | `api/routes/runs.py:845`; `api/routes/runs.py:861`; `api/routes/runs.py:866`; `api/routes/runs.py:881`; `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py:110` | Viewer eloszor canonical inputot olvas, hiany eseten determinisztikus snapshot fallbackot hasznal, majd ebbol szamolja a sheet mereteket/utilizationt. | `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` |
| #3 Trial tool summary kimondja backend/contract/artifact teljesseget | PASS | `scripts/trial_run_tool_core.py:857`; `scripts/trial_run_tool_core.py:861`; `scripts/trial_run_tool_core.py:870`; `scripts/trial_run_tool_core.py:1570`; `scripts/trial_run_tool_core.py:1585` | A summary uj evidenceszekcioja explicit backend/contract/profile es artifact jelenlet/completeness mezoket ad. | `python3 scripts/smoke_trial_run_tool_cli_core.py`; `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` |
| #4 Dedikalt smoke zold | PASS | `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py:55`; `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py:110`; `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py:221`; `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py:231` | A smoke ellenorzi a worker canonical truth markeret, viewer canonical/fallback viselkedest es a trial summary quality-mezoket. | `python3 scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` |
| #5 Standard verify wrapper lefut, report + log frissul | PASS | `codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.verify.log` | A kotelezo wrapper futott, es automatikusan frissitette az AUTO_VERIFY blokkot. | `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md` |

## 6) Advisory notes
- A trial summary quality mezok validalasara a dedikalt smoke a mar letezo `smoke_trial_run_tool_cli_core.py` scriptet is futtatja.
- A munkafa tartalmaz taskon kivuli modositasokat is; ezek a jelen task DoD teljesuleset nem blokkoljak.

## 7) Follow-ups
- H3 quality lane kovetkezo lepeseiben (`v2 adapter`, `dual-engine`) az `engine_meta.json` mezokre lehet epiteni egy osszehasonlito/A-B reportot.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-29T22:38:33+02:00 → 2026-03-29T22:42:05+02:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.verify.log`
- git: `main@e7b9bd8`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 api/routes/runs.py                       | 20 ++++++++++++
 scripts/smoke_trial_run_tool_cli_core.py | 21 ++++++++++++
 scripts/trial_run_tool_core.py           | 55 ++++++++++++++++++++++++++++++++
 worker/main.py                           | 55 ++++++++++++++++++++++++++++++++
 4 files changed, 151 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/routes/runs.py
 M scripts/smoke_trial_run_tool_cli_core.py
 M scripts/trial_run_tool_core.py
 M worker/main.py
?? canvases/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md
?? codex/codex_checklist/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_quality_t1_engine_observability_and_artifact_truth.yaml
?? codex/prompts/web_platform/h3_quality_t1_engine_observability_and_artifact_truth/
?? codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md
?? codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.verify.log
?? docs/nesting_quality/
?? scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py
```

<!-- AUTO_VERIFY_END -->
