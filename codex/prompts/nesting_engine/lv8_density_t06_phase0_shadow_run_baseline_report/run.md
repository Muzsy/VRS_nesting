# Runner — lv8_density_t06_phase0_shadow_run_baseline_report

## Feladat

Végrehajtandó task: **T06 — Phase 0 shadow run baseline report**.

A cél a Phase 0 lezáró shadow baseline riport elkészítése a T02–T05 outputok alapján. Ez mérési/audit task: nem fejleszt új algoritmust.

## Kötelező források

Olvasd el először:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/nesting_engine/lv8_density_task_index.md
codex/prompts/nesting_engine/lv8_density_master_runner.md
codex/reports/nesting_engine/development_plan_packing_density_20260515.md
canvases/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t06_phase0_shadow_run_baseline_report.yaml
```

Ellenőrizd, hogy ezek PASS vagy PASS_WITH_NOTES státuszúak:

```text
codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md
codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md
codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md
codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md
```

Ha bármelyik hiányzik vagy FAIL/BLOCKED, állj meg, és írj T06 `FAIL/BLOCKED` reportot. Ne indíts hosszú benchmarkot.

## Scope

Engedélyezett módosítások:

```text
scripts/experiments/lv8_phase0_shadow_run_matrix.py
tests/test_lv8_phase0_shadow_run_matrix.py
codex/codex_checklist/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.verify.log
tmp/lv8_density_phase0_shadow_runs/**
```

Tilos módosítani:

```text
rust/nesting_engine/src/**
scripts/experiments/lv8_polygon_validator.py
scripts/experiments/lv8_2sheet_claude_search.py
vrs_nesting/config/nesting_quality_profiles.py
worker/cavity_validation.py
```

Ha ezek módosítása szükségesnek látszik, állj meg, és dokumentáld `FAIL/BLOCKED` reportban.

## Végrehajtási lépések

### 1) Előfeltétel-ellenőrzés

Ellenőrizd:

```bash
python3 - <<'PY'
from pathlib import Path
reports = [
    'codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md',
    'codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md',
    'codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md',
    'codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md',
    'codex/reports/nesting_engine/lv8_density_t05_phase0_polygon_validation_gate.md',
]
for r in reports:
    p = Path(r)
    print(r, 'OK' if p.is_file() else 'MISSING')
PY
```

A T06 reportban rögzítsd az előfeltételeket.

### 2) Profile-párok ellenőrzése

Futtasd:

```bash
python3 - <<'PY'
from vrs_nesting.config.nesting_quality_profiles import get_phase0_shadow_profile_pairs, get_quality_profile_policy
pairs = get_phase0_shadow_profile_pairs()
print(pairs)
for old, new in pairs.items():
    print(old, get_quality_profile_policy(old))
    print(new, get_quality_profile_policy(new))
PY
```

Elvárt:

```text
quality_default -> quality_default_no_sa_shadow
quality_aggressive -> quality_aggressive_no_sa_shadow
```

### 3) Fixture availability ellenőrzés

Ellenőrizd:

```bash
ls tests/fixtures/nesting_engine/ne2_input_lv8jav.json
ls poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
ls scripts/smoke_svg_export.py
ls samples/dxf_demo/stock_rect_1000x2000.dxf
ls samples/dxf_demo/part_arc_spline_chaining_ok.dxf
```

LV8 179 esetén:

```bash
if [ -f tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json ]; then
  echo "LV8_179_PRESENT"
else
  echo "LV8_179_MISSING"
fi
```

Ha LV8 179 hiányzik, ne hozz létre placeholdert. A matrixban szerepeljen `fixture_missing`, és `hard_cut_decision = DEFER_HARD_CUT` vagy `BLOCKED`.

### 4) Shadow matrix script

Hozd létre:

```text
scripts/experiments/lv8_phase0_shadow_run_matrix.py
```

Minimum funkciók:

- CLI:

```bash
python3 scripts/experiments/lv8_phase0_shadow_run_matrix.py \
  --out-root tmp/lv8_density_phase0_shadow_runs \
  --time-limit-sec 600 \
  --seed 42 \
  --include-lv8-179 auto \
  --run-contract-freeze-smoke 1
```

- Engine fixture run:
  - subprocessként hívja `scripts/experiments/lv8_2sheet_claude_search.py`-t,
  - profile-párok: `quality_default` vs `quality_default_no_sa_shadow`, `quality_aggressive` vs `quality_aggressive_no_sa_shadow`,
  - külön out_dir minden fixture/profile kombinációhoz.
- Contract-freeze:
  - futtassa: `python3 scripts/smoke_svg_export.py`,
  - írjon regression row-t.
- Aggregáció:
  - `runs.jsonl`,
  - `phase0_shadow_matrix.json`,
  - `phase0_shadow_matrix.md`,
  - `hard_cut_decision.json`.

### 5) Tesztek

Hozd létre:

```text
tests/test_lv8_phase0_shadow_run_matrix.py
```

Minimum tesztek:

1. profile-pár mapping importálható,
2. missing fixture -> `fixture_missing` + `DEFER_HARD_CUT`,
3. no-SA jobb/equal -> `pair_pass=True`,
4. polygon gate false -> pair nem passolhat,
5. contract-freeze `not_applicable` row nem kap hamis util/placed összehasonlítást.

### 6) Célzott ellenőrzések

Futtasd:

```bash
python3 -m py_compile scripts/experiments/lv8_phase0_shadow_run_matrix.py
python3 -m pytest tests/test_lv8_phase0_shadow_run_matrix.py -q
python3 -m py_compile scripts/experiments/lv8_2sheet_claude_search.py
python3 -m py_compile scripts/experiments/lv8_polygon_validator.py
```

### 7) Shadow run futtatás

Ha nincs release binary:

```bash
cargo build --release -p nesting_engine
```

Majd:

```bash
python3 scripts/experiments/lv8_phase0_shadow_run_matrix.py \
  --out-root tmp/lv8_density_phase0_shadow_runs \
  --time-limit-sec 600 \
  --seed 42 \
  --include-lv8-179 auto \
  --run-contract-freeze-smoke 1
```

Ha időlimit vagy gépi környezet miatt a teljes LV8 matrix nem futtatható, dokumentáld. Ne írj hamis PASS-t. A hard-cut decision legyen `DEFER_HARD_CUT` vagy `BLOCKED`.

## Report és checkpoint alias

Hozd létre:

```text
codex/codex_checklist/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
```

A task report kötelezően tartalmazza:

- státusz: PASS / PASS_WITH_NOTES / FAIL / BLOCKED,
- T01–T05 előfeltétel státuszok,
- fixture availability matrix,
- profile-pair matrix,
- per-run summary táblázat,
- polygon gate eredmények,
- engine_stats elérhetőség,
- contract-freeze regression row,
- hard-cut decision és indok,
- DoD → Evidence Matrix,
- AUTO_VERIFY blokk,
- legfeljebb 5 advisory note,
- T07 indulási feltétel.

A `codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md` checkpoint alias report legalább ezt tartalmazza:

- T06 task report link,
- hard-cut decision,
- Phase 0 pass/defer/block státusz,
- T07 indulhat-e.

## Kötelező repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
```

## STOP feltételek

Állj meg és írj `FAIL/BLOCKED` reportot, ha:

- T01–T05 valamelyike hiányzik vagy FAIL/BLOCKED,
- a profile-párok hiányoznak,
- `lv8_2sheet_claude_search.py` vagy `lv8_polygon_validator.py` nem importálható,
- a shadow matrix script csak AABB validitásra támaszkodna,
- Rust engine kódot kellene módosítani,
- a report nem tudja bizonyítani, hogy a polygon-aware gate binding.

## Fontos

A T06 report státusza és a hard-cut decision két külön dolog. Lehet `PASS_WITH_NOTES` úgy, hogy a `hard_cut_decision` = `DEFER_HARD_CUT`, ha a futtatási infrastruktúra helyes, de a teljes 1-hetes / teljes fixture evidence nem teljes. `APPROVE_NO_SA_HARD_CUT` csak teljes és kedvező evidence mellett engedélyezett.
