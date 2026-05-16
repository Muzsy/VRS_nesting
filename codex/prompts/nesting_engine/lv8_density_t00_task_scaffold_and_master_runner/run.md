# LV8 Density T00 — Task scaffold és master runner előkészítés
TASK_SLUG: lv8_density_t00_task_scaffold_and_master_runner

## Szerep

Senior repo-orchestration és Codex workflow agent vagy. A feladatod nem algoritmikus implementáció, hanem a végleges LV8 packing density fejlesztési terv agent-delegálható task-láncának repo-konform scaffoldja.

## Cél

Hozd létre:

1. `canvases/nesting_engine/lv8_density_task_index.md`
2. `codex/prompts/nesting_engine/lv8_density_master_runner.md`
3. `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
4. `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

Ne implementálj engine funkciót. Ne hozz létre T01-T22 canvas/YAML/runner fájlokat. A T00 csak indexet és master-runnert készít.

## Kötelező olvasnivaló prioritási sorrendben

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
7. `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml`
8. Minta canvas/YAML/runner fájlok:
   - `canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md`
   - `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.yaml`
   - `codex/prompts/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation/run.md`
   - `codex/prompts/nesting_engine/engine_v2_nfp_rc_master_runner.md`

Ha bármelyik kötelező szabályfájl hiányzik, állj meg, és a reportban FAIL-ként rögzítsd.

## Előfeltétel ellenőrzés

```bash
ls AGENTS.md || echo "STOP: AGENTS.md missing"
ls docs/codex/overview.md || echo "STOP: codex overview missing"
ls docs/codex/yaml_schema.md || echo "STOP: yaml schema missing"
ls docs/codex/report_standard.md || echo "STOP: report standard missing"
ls docs/qa/testing_guidelines.md || echo "STOP: testing guidelines missing"
ls canvases/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md || echo "STOP: T00 canvas missing"
ls codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t00_task_scaffold_and_master_runner.yaml || echo "STOP: T00 YAML missing"
```

## Valós repo anchorok ellenőrzése

Futtasd és rögzítsd a reportban:

```bash
ls rust/nesting_engine/src/nfp/cache.rs
ls rust/nesting_engine/src/placement/nfp_placer.rs
ls rust/nesting_engine/src/multi_bin/greedy.rs
ls vrs_nesting/config/nesting_quality_profiles.py
ls rust/nesting_engine/src/nfp/concave.rs
ls scripts/experiments/lv8_2sheet_claude_search.py
ls scripts/experiments/lv8_2sheet_claude_validate.py
ls worker/cavity_validation.py
ls tests/fixtures/nesting_engine/ne2_input_lv8jav.json
ls poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
```

Megjegyzés: a végleges tervben szereplő LV8 179 tmp fixture nem biztos, hogy létezik ebben a snapshotban. Ne kezeld létezőként. T01 feladatban kell fixture inventory / helyreállítás.

## Engedélyezett módosítások

Csak ezek a fájlok hozhatók létre vagy módosíthatók:

- `canvases/nesting_engine/lv8_density_task_index.md`
- `codex/prompts/nesting_engine/lv8_density_master_runner.md`
- `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.verify.log`

A T00 saját canvas/YAML/runner fájljai csak olvasandók, hacsak explicit nincs más utasítás.

## Szigorú tiltások

- Tilos Rust engine kódot módosítani.
- Tilos Python production kódot módosítani.
- Tilos quality profile-t módosítani.
- Tilos T01-T22 canvas/YAML/runner fájlokat létrehozni.
- Tilos nem létező fixture-t létezőként szerepeltetni.
- Tilos a végleges fejlesztési terv döntéseit megváltoztatni.
- Tilos a `docs/codex/yaml_schema.md` sémájától eltérő YAML-t írni.

## Végrehajtandó lépések

### Step 1 — Szabályfájlok és minták beolvasása

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,220p' docs/codex/yaml_schema.md
sed -n '1,180p' docs/codex/report_standard.md
sed -n '1,120p' canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md
sed -n '1,120p' codex/prompts/nesting_engine/engine_v2_nfp_rc_master_runner.md
```

### Step 2 — Repo anchor audit

```bash
for p in \
  rust/nesting_engine/src/nfp/cache.rs \
  rust/nesting_engine/src/placement/nfp_placer.rs \
  rust/nesting_engine/src/multi_bin/greedy.rs \
  vrs_nesting/config/nesting_quality_profiles.py \
  rust/nesting_engine/src/nfp/concave.rs \
  scripts/experiments/lv8_2sheet_claude_search.py \
  scripts/experiments/lv8_2sheet_claude_validate.py \
  worker/cavity_validation.py \
  tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  poc/nesting_engine/f2_4_sa_quality_fixture_v2.json; do
    test -e "$p" && echo "OK $p" || echo "MISSING $p"
  done
```

A reportban rögzítsd az eredményt.

### Step 3 — Task index létrehozása

Hozd létre: `canvases/nesting_engine/lv8_density_task_index.md`.

Minimum tartalom:

- Source of truth
- Global invariants
- Real repo anchors
- Task list T00-T22
- Dependency graph
- Critical path
- Parallelization notes
- First package batch
- Stop conditions

A T00-T22 tasklistát a T00 canvasban megadott névvel és sorrenddel használd.

### Step 4 — Master runner létrehozása

Hozd létre: `codex/prompts/nesting_engine/lv8_density_master_runner.md`.

Minimum tartalom:

- Cél
- Kötelező olvasnivaló
- Baseline preflight
- Global hard rules
- Files and fixtures to verify before start
- Execution order
- Checkpoints
- Per-task runner references
- Phase gates
- Final benchmark matrix
- Rollback rules
- Reporting rules

A T01-T22 runner útvonalakat expected pathként add meg, például:

```text
T01 expected runner path: codex/prompts/nesting_engine/lv8_density_t01_phase0_fixture_inventory/run.md
Status: to be created by its own package task.
```

### Step 5 — Checklist és report létrehozása

Hozd létre:

- `codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`
- `codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md`

A report a `docs/codex/report_standard.md` struktúráját kövesse.

### Step 6 — Sanity check

```bash
python3 - <<'PY'
from pathlib import Path
idx = Path('canvases/nesting_engine/lv8_density_task_index.md').read_text()
runner = Path('codex/prompts/nesting_engine/lv8_density_master_runner.md').read_text()
for token in ['T00', 'T01', 'T22', 'Dependency graph', 'Critical path']:
    assert token in idx, f'missing in task index: {token}'
for token in ['Baseline preflight', 'Global hard rules', 'Execution order', 'Rollback rules']:
    assert token in runner, f'missing in master runner: {token}'
print('T00 content sanity PASS')
PY
```

### Step 7 — Production diff guard

```bash
if git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx' | grep -v '^codex/' | grep -v '^canvases/' ; then
  echo 'STOP: unexpected production code diff'
  exit 1
else
  echo 'PASS: no production code diff'
fi
```

### Step 8 — Repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
```

Ha a verify piros, ne adj PASS-t. A reportban pontosan írd le a hibát.

## Tesztparancsok összefoglalva

```bash
ls canvases/nesting_engine/lv8_density_task_index.md
ls codex/prompts/nesting_engine/lv8_density_master_runner.md
ls codex/codex_checklist/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
ls codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md

python3 - <<'PY'
from pathlib import Path
idx = Path('canvases/nesting_engine/lv8_density_task_index.md').read_text()
runner = Path('codex/prompts/nesting_engine/lv8_density_master_runner.md').read_text()
for token in ['T00', 'T01', 'T22', 'Dependency graph', 'Critical path']:
    assert token in idx
for token in ['Baseline preflight', 'Global hard rules', 'Execution order', 'Rollback rules']:
    assert token in runner
print('PASS')
PY

./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t00_task_scaffold_and_master_runner.md
```

## Záró elvárás

A végén add meg:

- létrehozott fájlok listája,
- lefuttatott ellenőrzések listája,
- PASS/FAIL státusz,
- ha FAIL: pontos blokkoló ok és következő javító lépés.
