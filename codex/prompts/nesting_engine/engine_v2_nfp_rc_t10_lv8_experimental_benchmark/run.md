# Engine v2 NFP RC T10 — LV8 Experimental Benchmark
TASK_SLUG: engine_v2_nfp_rc_t10_lv8_experimental_benchmark

## Szerep
Senior benchmark agent vagy. A teljes RC kernel pipeline-t méred valós LV8 adatokon.
A benchmark 6 FAIL feltételt ellenőriz. Fallback=FAIL. Invalid NFP=FAIL. Prepack guard=FAIL.

## Cél
Implementáld `scripts/benchmark_reduced_convolution_lv8.py`-t.
`--dry-run` fut. JSON riport kimentve. Minden FAIL feltétel működik.

## Előfeltétel ellenőrzés
```bash
# T01–T09 mind szükséges
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json || echo "STOP: T01"
ls rust/nesting_engine/src/geometry/cleanup.rs || echo "STOP: T03"
ls rust/nesting_engine/src/bin/nfp_pair_benchmark.rs || echo "STOP: T04"
ls rust/nesting_engine/src/nfp/reduced_convolution.rs || echo "STOP: T05"
ls rust/nesting_engine/src/nfp/minkowski_cleanup.rs || echo "STOP: T06"
ls rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs || echo "STOP: T07"
python3 -c "from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY; assert 'quality_reduced_convolution_experimental' in _QUALITY_PROFILE_REGISTRY" || echo "STOP: T08"
ls rust/nesting_engine/src/geometry/hash.rs || echo "STOP: T09"
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t10_lv8_experimental_benchmark.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t10_lv8_experimental_benchmark.yaml`
- `scripts/benchmark_cavity_v2_lv8.py` (első 100 sor — struktúra reference)
- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` (struktúra — olvasd)

## Engedélyezett módosítás
- `scripts/benchmark_reduced_convolution_lv8.py` (create)
- `tmp/reports/engine_v2_nfp_rc_t10/README.md` (create)

## Szigorú tiltások
- **Tilos `benchmark_cavity_v2_lv8.py`-t módosítani.**
- Tilos a cavity_prepack_v2 guard-ot kikapcsolni.
- Tilos fallback eredményt sikerként jelölni.
- Tilos invalid NFP-t sikerként elfogadni.

## Végrehajtandó lépések

### Step 1: benchmark_cavity_v2_lv8.py struktúra megértése
```bash
head -100 scripts/benchmark_cavity_v2_lv8.py
```
Értsd meg: hogyan hívja a prepack-ot, hogyan futtatja az engine-t, milyen riportot generál.

### Step 2: LV8 fixture struktúra
```bash
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('tests/fixtures/nesting_engine/ne2_input_lv8jav.json').read_text())
print('top-level keys:', list(data.keys()))
parts = data.get('parts', [])
print('parts count:', len(parts))
"
```

### Step 3: `scripts/benchmark_reduced_convolution_lv8.py` megírása

Parancssori interfész (canvas spec szerint):
```
--fixture <path>
--output-dir <path>
--timeout-minutes <N>
--dry-run
```

Benchmark flow:
1. Preflight: cavity_prepack_v2 → top_level_holes=0 ellenőrzés
2. Engine: quality_reduced_convolution_experimental profillal
3. Metrikák gyűjtése (összes NfpPlacerStatsV1 mező)
4. Correctness check (nfp_correctness_benchmark bin hívása)
5. Baseline összehasonlítás (ha van tmp/reports/cavity_v2_lv8/ riport)
6. Riport mentés + stdout összefoglaló

Verdict logika (6 FAIL feltétel):
1. top_level_holes_after_prepack > 0 → FAIL: prepack_guard_violated
2. fallback_occurred == true → FAIL: silent_fallback_detected
3. nfp_invalid_count > 0 → FAIL: invalid_nfp_accepted
4. overlap_count > 0 → FAIL: placements_overlap
5. bounds_violation_count > 0 → FAIL: bounds_violated
6. actual_nfp_kernel_used != "reduced_convolution_v1" → FAIL: wrong_kernel_used

3 WARNING (nem FAIL):
- correctness_validator_status == "not_run" → WARN
- nfp_kernel_unsupported_count > 0 → WARN
- rc_vs_baseline_utilization_delta_pct < -5.0 → WARN

### Step 4: Output könyvtár
```bash
mkdir -p tmp/reports/engine_v2_nfp_rc_t10
```

### Step 5: Validálás
```bash
# Szintaxis
python3 -c "import ast; ast.parse(open('scripts/benchmark_reduced_convolution_lv8.py').read()); print('syntax OK')"

# Dry run
python3 scripts/benchmark_reduced_convolution_lv8.py --dry-run

# benchmark_cavity_v2_lv8.py érintetlen
git diff HEAD -- scripts/benchmark_cavity_v2_lv8.py
```

### Step 6: Ha az engine ténylegesen futtatható — teljes benchmark
```bash
# Csak ha T01–T09 mind kész és az engine fut
python3 scripts/benchmark_reduced_convolution_lv8.py \
  --fixture tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  --output-dir tmp/reports/engine_v2_nfp_rc_t10 \
  --timeout-minutes 30
```

```bash
# JSON validálás
python3 -c "
import json, glob
for f in sorted(glob.glob('tmp/reports/engine_v2_nfp_rc_t10/*.json')):
    d = json.loads(open(f).read())
    assert 'verdict' in d
    assert d['results']['top_level_holes_after_prepack'] == 0, 'prepack guard violated!'
    if d['results']['fallback_occurred']:
        assert d['verdict'] == 'FAIL', 'fallback must be FAIL!'
    print(f, 'verdict:', d['verdict'])
"
```

### Step 7: Report és checklist

## Tesztparancsok
```bash
python3 -c "import ast; ast.parse(open('scripts/benchmark_reduced_convolution_lv8.py').read()); print('syntax OK')"
python3 scripts/benchmark_reduced_convolution_lv8.py --dry-run
ls tmp/reports/engine_v2_nfp_rc_t10/
git diff HEAD -- scripts/benchmark_cavity_v2_lv8.py
```

## Ellenőrzési pontok
- [ ] benchmark_reduced_convolution_lv8.py szintaxis OK
- [ ] --dry-run hiba nélkül fut
- [ ] top_level_holes=0 ellenőrzés aktív
- [ ] fallback_occurred=true esetén verdict=FAIL
- [ ] nfp_invalid_count>0 esetén verdict=FAIL
- [ ] JSON riport kimentve tmp/reports/engine_v2_nfp_rc_t10/-ba
- [ ] Human-readable összefoglaló stdout-on
- [ ] benchmark_cavity_v2_lv8.py érintetlen
