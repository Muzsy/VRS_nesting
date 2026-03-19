PASS_WITH_NOTES

## 1) Meta
- Task slug: `h1_e5_t1_engine_adapter_input_mapping_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.yaml`
- Futas datuma: `2026-03-19`
- Branch / commit: `main @ d67031c (dirty working tree)`
- Fokusz terulet: `Worker engine adapter input mapping + snapshot minimalis bovites + smoke`

## 2) Scope

### 2.1 Cel
- H1 minimum engine adapter input helper bevezetese snapshot-only mappinggel.
- A `solver_input.json` v1 payload determinisztikus eloallitasa canonical run snapshotbol.
- Explicit rotation policy mapping es nem mappelheto policyre kontrollalt hiba.
- Minimalis snapshot builder bovites, hogy a geometry truth (`polygon` + `bbox`) a snapshotban legyen.
- Task-specifikus smoke sikeres es hibas agakra.

### 2.2 Nem-cel (explicit)
- Solver process start orchestration redesign.
- Raw output mentes, result normalizer, projection vagy artifact pipeline bovitese.
- Queue lease/lifecycle mechanika ujranyitasa.
- Run status lifecycle teljes ujratervezese.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum/run.md`
- `worker/engine_adapter_input.py`
- `worker/main.py`
- `api/services/run_snapshot_builder.py`
- `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`
- `codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md`

### 3.2 Mit szallit le a task (H1 minimum adapter-input scope)
- Keszult explicit `worker/engine_adapter_input.py` helper, amely snapshotbol allit elo solver-input payloadot.
- A helper a `project_manifest_jsonb` / `parts_manifest_jsonb` / `sheets_manifest_jsonb` / `geometry_manifest_jsonb` / `solver_config_jsonb` mezoket hasznalja.
- A mapping shaped-mode szerint dolgozik: `polygon.outer_ring` -> `outer_points`, `polygon.hole_rings` -> `holes_points`, `bbox` -> `width/height`, requirement -> `quantity`.
- A worker legalabb H1 minimum szinten mar generalja es hash-eli a snapshotbol kepzett solver inputot, majd feltolti `runs/{run_id}/inputs/solver_input_snapshot.json` ala.
- A snapshot builder minimalisan bovult, hogy a geometry manifest mar explicit polygon+bbox payloadot tartalmazzon a selected `nesting_canonical` derivative alapjan.

### 3.3 Mit NEM szallit le meg
- Nem tortent solver process start redesign (a `dxf-run` legacy ag maradt).
- Nem kerult be raw output/result/artifact pipeline uj scope.
- Nem tortent run lifecycle policy redesign.

### 3.4 Rotation policy szemantika (H1-E5-T1)
- A helper expliciten tiltja `allow_free_rotation=true` policyt (`unsupported rotation policy` hiba).
- `rotation_step_deg` alapjan 0-tol determinisztikusan kepzi a periodikus halmazt.
- Csak akkor engedi tovabb, ha a keletkezo halmaz elemei a solver v1 altal engedett `{0,90,180,270}` halmazba esnek.
- Nem mappelheto step (pl. 45) eseten determinisztikus hibaval leall, csendes torzitas nelkul.

### 3.5 Snapshot-only allapot es builder bovites
- A helper tenylegesen snapshot-only: nem olvas elo project/part/sheet domain tablakat.
- A worker viszont a futtatas legacy agaban tovabbra is olvas `run_config` + file object adatokat a `dxf-run` bemenethez.
- Emiatt a task statusza `PASS_WITH_NOTES`: az adapter-input scope kesz, de a full process path snapshot-only atallasa kovetkezo taskban zarhato le.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile worker/engine_adapter_input.py worker/main.py api/services/run_snapshot_builder.py api/services/run_creation.py scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit engine adapter input helper/modul. | PASS | `worker/engine_adapter_input.py:9`; `worker/engine_adapter_input.py:146` | Kulon helper modul keszult explicit API-val es sajat hibatipussal. | `py_compile` |
| A helper canonical run snapshotbol epit bemenetet. | PASS | `worker/engine_adapter_input.py:147`; `worker/engine_adapter_input.py:148`; `worker/engine_adapter_input.py:149`; `worker/engine_adapter_input.py:150`; `worker/engine_adapter_input.py:151` | A helper kiz arlag a snapshot manifest mezokbol dolgozik. | Smoke + kodellenorzes |
| A kimenet `solver_input.json` v1 contract kompatibilis. | PASS | `worker/engine_adapter_input.py:229`; `worker/engine_adapter_input.py:230`; `worker/engine_adapter_input.py:234`; `worker/engine_adapter_input.py:235`; `docs/solver_io_contract.md:16` | A kotelezo top-level mezok (`contract_version`, `project_name`, `seed`, `time_limit_s`, `stocks`, `parts`) eloallnak. | Smoke successful branch |
| A part geometry selected `nesting_canonical` derivative truth-bol jon. | PASS | `api/services/run_snapshot_builder.py:368`; `api/services/run_snapshot_builder.py:376`; `api/services/run_snapshot_builder.py:404`; `api/services/run_snapshot_builder.py:408`; `worker/engine_adapter_input.py:130`; `worker/engine_adapter_input.py:188` | Builder csak `nesting_canonical` derivativet fogad es geometry payloadot tesz a snapshotba, helper ebbol mapel. | Smoke geometry assertions |
| A sheet/stocks input a snapshot `sheets_manifest_jsonb` vilagabol jon. | PASS | `worker/engine_adapter_input.py:149`; `worker/engine_adapter_input.py:196`; `worker/engine_adapter_input.py:213`; `worker/engine_adapter_input.py:221` | A stocks tomb kozvetlenul a snapshot sheets manifestbol epul. | Smoke stock mapping |
| A rotation policy mapping explicit es dokumentalt. | PASS | `worker/engine_adapter_input.py:91`; `worker/engine_adapter_input.py:94`; `worker/engine_adapter_input.py:96`; `worker/engine_adapter_input.py:112`; `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:129`; `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:136` | `allow_free_rotation=true` tiltott, nem kompatibilis step eseteben determinisztikus hiba. | Smoke negative branches |
| A mapping determinisztikus. | PASS | `worker/engine_adapter_input.py:161`; `worker/engine_adapter_input.py:197`; `worker/engine_adapter_input.py:239`; `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:123` | Reszek rendezettek es canonical JSON hash hasznalt. | Smoke hash equality |
| A task nem csuszik at solver process / raw output / normalizer scope-ba. | PASS | `worker/engine_adapter_input.py:1`; `worker/main.py:1052`; `worker/main.py:1114` | Az adapter helper nem indit processzt; a workerben csak input mapping+feltoltes kerult hozzaadasra a megl evo process path ele. | Diff ellenorzes |
| Keszul task-specifikus smoke sikeres es hibas agakra. | PASS | `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:86`; `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:129`; `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:143`; `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py:150` | A smoke lefedi a sikeres mappinget, hash stabilitast, rotation es geometry/bbox hibaagakat. | Smoke PASS |
| Checklist es report evidence-alapon kitoltve. | PASS | `codex/codex_checklist/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md:1`; `codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md:1` | A task checklist/report letrehozva es DoD->Evidence matrix kitoltve. | Dokumentacios ellenorzes |
| Kotelezo verify.sh futtatasa PASS. | PASS | `codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.verify.log` | A verify log letrejott es a check.sh gate PASS-ra futott. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A helper snapshot-only implementacioja kesz, de a worker teljes process input atallasa meg legacy `run_config`/file letoltes utvonalon fut.
- H1-E5-T2-ben erdemes a tenyleges solver futtatast is erre a snapshot solver_input artefaktra atkotni.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-19T20:48:03+01:00 → 2026-03-19T20:51:36+01:00 (213s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.verify.log`
- git: `main@d67031c`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 api/services/run_snapshot_builder.py | 92 +++++++++++++++++++++++++++++++++++-
 worker/main.py                       | 61 +++++++++++++++++++-----
 2 files changed, 141 insertions(+), 12 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/services/run_snapshot_builder.py
 M worker/main.py
?? canvases/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum/
?? codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md
?? codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.verify.log
?? scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py
?? worker/engine_adapter_input.py
```

<!-- AUTO_VERIFY_END -->
