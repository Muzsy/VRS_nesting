# Engine v2 NFP RC T07 — NFP Correctness Validator
TASK_SLUG: engine_v2_nfp_rc_t07_nfp_correctness_validator

## Szerep
Senior Rust tesztelési agent vagy. Implementálod a correctness validatort, amely
méri az NFP false positive és false negative arányát. FAIL_FALSE_POSITIVE esetén
az NFP production-ban tilos.

## Cél
Implementáld `nfp_correctness_benchmark.rs` bin-t. T01 fixture-ökön lefut.
Mock NFP mód: false_positive_rate=0.0 (referencia mérés).

## Előfeltétel ellenőrzés
```bash
ls rust/nesting_engine/src/nfp/nfp_validation.rs || echo "STOP: T06 szükséges"
ls rust/nesting_engine/src/nfp/reduced_convolution.rs || echo "STOP: T05 szükséges"
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json || echo "STOP: T01 szükséges"
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t07_nfp_correctness_validator.yaml`
- `rust/nesting_engine/src/nfp/nfp_validation.rs` (T06 output)
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` (T05 output)
- `rust/nesting_engine/src/geometry/types.rs` (Point64, Polygon64)

## Engedélyezett módosítás
- `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` (create)

## Szigorú tiltások
- Tilos nfp_placer.rs-t módosítani.
- Tilos FAIL_FALSE_POSITIVE-t sikerként elfogadni.
- Tilos a correctness algoritmus megkerülése (NOT_AVAILABLE verdict ha NFP nincs — nem PASS).

## Végrehajtandó lépések

### Step 1: Feasibility modulok ellenőrzése
```bash
ls rust/nesting_engine/src/feasibility/ 2>/dev/null || echo "feasibility modul nem létezik"
ls rust/nesting_engine/src/feasibility/aabb.rs 2>/dev/null && echo "aabb OK" || echo "aabb nem létezik"
ls rust/nesting_engine/src/feasibility/narrow.rs 2>/dev/null && echo "narrow OK" || echo "narrow nem létezik"
```

### Step 2: `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` megírása

Parancssori interfész:
```
--fixture <path>
--nfp-source <src>         reduced_convolution_v1 | mock_exact
--sample-inside <N>        (default: 1000)
--sample-outside <N>       (default: 1000)
--sample-boundary <N>      (default: 200)
--boundary-perturbation    mm (default: 0.01)
--output-json
```

Implementálandó funkciók:
1. `exact_collision_check(part_a, part_b, placement) -> bool`
   - AABB prefilter + polygon-polygon intersection
2. `sample_points_inside(poly, n, seed) -> Vec<Point64>`
3. `sample_points_outside(poly, n, seed) -> Vec<Point64>`
4. `sample_points_on_boundary(poly, n, seed) -> Vec<Point64>`

Correctness algoritmus:
- Inside: minden belső pont → exact_collision = True kell
  - Ha False: false_negative_count++
- Outside: minden külső pont → exact_collision = False kell
  - Ha True: false_positive_count++
- Boundary: perturbáció teszt (részletek a canvas spec-ben)

stdout JSON output (a canvas spec szerinti séma).

correctness_verdict logika:
- PASS: false_positive_rate=0.0 ÉS false_negative_rate<0.001
- MARGINAL: false_positive_rate=0.0 ÉS false_negative_rate<0.01
- FAIL_FALSE_POSITIVE: false_positive_rate>0.0
- FAIL_FALSE_NEGATIVE: false_negative_rate>0.01
- NOT_AVAILABLE: NFP output nem volt (T05 NotImplemented)

Mock NFP mód (`--nfp-source mock_exact`):
- Konvex dekompozícióval számított exact NFP mint referencia
- Ezen a mock NFP-n false_positive_rate = 0.0 KELL

### Step 3: Kompilálás és tesztelés
```bash
cargo check -p nesting_engine 2>&1 | tail -10

cargo run --bin nfp_correctness_benchmark -- --help

# T01 fixture (NotImplemented OK)
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source reduced_convolution_v1 \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'correctness_verdict' in d
assert 'false_positive_rate' in d
assert 'false_negative_rate' in d
v = d['correctness_verdict']
assert v in ('PASS', 'MARGINAL', 'FAIL_FALSE_POSITIVE', 'FAIL_FALSE_NEGATIVE', 'NOT_AVAILABLE')
print('verdict:', v)
"

# Mock NFP mód: false_positive_rate = 0.0
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source mock_exact \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['false_positive_rate'] == 0.0, 'mock_exact should have 0 false positives!'
print('mock_exact: false_positive_rate=0.0 PASS')
"
```

### Step 4: Report és checklist

## Tesztparancsok
```bash
cargo run --bin nfp_correctness_benchmark -- --help
ls rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs
cargo check -p nesting_engine
```

## Ellenőrzési pontok
- [ ] nfp_correctness_benchmark --help fut
- [ ] T01 fixture-n lefut (NOT_AVAILABLE OK ha T05 NotImplemented)
- [ ] false_positive_rate és false_negative_rate a JSON-ban
- [ ] FAIL_FALSE_POSITIVE ha false_positive_count>0
- [ ] mock_exact: false_positive_rate=0.0
- [ ] correctness_verdict értékkészlete dokumentált
