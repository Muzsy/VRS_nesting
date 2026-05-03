# Engine v2 NFP RC T05 — Reduced Convolution NFP Prototype
TASK_SLUG: engine_v2_nfp_rc_t05_reduced_convolution_prototype

## Szerep
Senior Rust fejlesztő agent vagy. Az első kísérleti RC NFP implementációt készíted.
Ha a teljes algoritmus meghaladja a scope-ot: `RcNfpError::NotImplemented` explicit —
nem panic, nem silent fallback.

## Cél
Implementáld `reduced_convolution.rs` és `nfp_rc_prototype_benchmark.rs`.
**PASS feltétel:** legalább 1 LV8 páronn tényleges NFP polygon keletkezik (`verdict = SUCCESS`).
`NOT_IMPLEMENTED` verdict minden páronn = `INFRA_PASS_BUT_ALGORITHM_NOT_READY` — ez BLOKKOLJA T06/T07/T08/T10-et.
Döntési pont dokumentálva a reportban.

## Előfeltétel ellenőrzés
```bash
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json || echo "STOP: T01 szükséges"
ls rust/nesting_engine/src/geometry/cleanup.rs || echo "STOP: T03 szükséges"
# T04 baseline mérések megvannak
python3 -c "import json; bm=json.load(open('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json'))['baseline_metrics']; print('T04 baseline:', bm.get('verdict', 'MISSING'))"
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t05_reduced_convolution_prototype.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t05_reduced_convolution_prototype.yaml`
- `rust/nesting_engine/src/nfp/mod.rs` (NfpError enum minta)
- `rust/nesting_engine/src/geometry/cleanup.rs` (T03 output)
- `rust/nesting_engine/src/geometry/types.rs` (Point64, Polygon64)

## Engedélyezett módosítás
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` (create)
- `rust/nesting_engine/src/bin/nfp_rc_prototype_benchmark.rs` (create)
- `rust/nesting_engine/src/nfp/mod.rs` (add pub mod reduced_convolution)

## Szigorú tiltások
- **Tilos `concave.rs`-t módosítani.**
- Tilos silent BLF fallback.
- Tilos panic `NotImplemented` helyett.
- Tilos a nfp_placer.rs-t módosítani (az T08 feladata).

## Végrehajtandó lépések

### Step 1: Architektúra döntés
```bash
ls tools/nfp_cgal_probe/ 2>/dev/null && echo "CGAL probe létezik" || echo "CGAL probe nincs"
which cmake && cmake --version || echo "CMake nem elérhető"
pkg-config --exists cgal && echo "CGAL elérhető" || echo "CGAL nem elérhető"
```
A döntést rögzítsd a report ARCHITECTURE_DECISION szekciójában.

### Step 2: `rust/nesting_engine/src/nfp/reduced_convolution.rs` megírása

Implementáld a canvas spec alapján:
- `ReducedConvolutionOptions` struct (integer_scale, min_edge_length_units, max_output_vertices, auto_cleanup)
- `RcNfpError` enum (InputTooComplex, EmptyInput, **NotImplemented**, ComputationFailed, OutputExceedsCap, CleanupFailed)
- `RcNfpResult` struct (polygon: Option<Polygon64>, raw_vertex_count, computation_time_ms, error, kernel_version)
- `compute_rc_nfp(part_a: &Polygon64, part_b: &Polygon64, options: &ReducedConvolutionOptions) -> RcNfpResult`

Algoritmus lépések (amennyire implementálható):
1. Input cleanup (ha auto_cleanup = true): T03 run_cleanup_pipeline hívása
2. part_b reflection: minden Point64 {x,y} → {x: -x, y: -y}
3. Edge decomposition: éllisták felépítése
4. Convolution: éllista rotációs összegzése
5. Loop closing
6. Output assembly
Ha bármely lépés nem implementált: `RcNfpError::NotImplemented` explicit return.

### Step 3: `rust/nesting_engine/src/bin/nfp_rc_prototype_benchmark.rs` megírása
- `--fixture <path>`, `--timeout-ms <N>`, `--compare-baseline`, `--output-json`
- verdict: SUCCESS | NOT_IMPLEMENTED | ERROR | TIMEOUT
- comparison_to_baseline szekció

### Step 4: nfp/mod.rs frissítése
```rust
pub mod reduced_convolution;
```

### Step 5: Kompilálás és tesztelés
```bash
cargo check -p nesting_engine 2>&1 | tail -10

cargo run --bin nfp_rc_prototype_benchmark -- --help

# Minden fixture lefut, verdict rögzítve
for pair in lv8_pair_01 lv8_pair_02 lv8_pair_03; do
  cargo run --bin nfp_rc_prototype_benchmark -- \
    --fixture "tests/fixtures/nesting_engine/nfp_pairs/${pair}.json" \
    --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'rc_result' in d and 'verdict' in d
assert d.get('rc_result',{}).get('error') != 'panic', 'PANIC!'
print('${pair}: verdict=', d['verdict'])
"
done

# KRITIKUS: legalább 1 páronn SUCCESS és valódi polygon kell
python3 -c "
import json, subprocess, sys
results = []
for pair_id in ['lv8_pair_01','lv8_pair_02','lv8_pair_03']:
    r = subprocess.run(
        ['cargo','run','--bin','nfp_rc_prototype_benchmark','--',
         '--fixture',f'tests/fixtures/nesting_engine/nfp_pairs/{pair_id}.json','--output-json'],
        capture_output=True, text=True
    )
    d = json.loads(r.stdout)
    results.append((pair_id, d.get('verdict'), d.get('rc_result',{}).get('raw_vertex_count',0)))
print('Verdicts:', results)
success_count = sum(1 for _, v, vc in results if v == 'SUCCESS' and vc > 0)
if success_count == 0:
    print('CHAIN_BLOCKED: algorithm_not_ready — minden fixture NOT_IMPLEMENTED. T06/T07/T08/T10 NEM INDÍTHATÓ.')
    sys.exit(1)
print(f'T05 PASS: {success_count}/3 páronn valódi NFP output.')
"

# concave.rs érintetlen
git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs
```

### Step 6: Report

Tartalmazza:
- ARCHITECTURE_DECISION (Rust prototype vs CGAL sidecar, reason)
- T01 fixture-ök verdict-jei
- Ha van output: comparison_to_baseline (T04 baseline-nal)

## Tesztparancsok
```bash
cargo check -p nesting_engine
cargo run --bin nfp_rc_prototype_benchmark -- --help
grep -n "pub mod reduced_convolution" rust/nesting_engine/src/nfp/mod.rs
git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs
```

## Ellenőrzési pontok
- [ ] cargo check hibátlan
- [ ] nfp_rc_prototype_benchmark --help fut
- [ ] **Legalább 1 LV8 páronn `verdict = SUCCESS` és `raw_vertex_count > 0`** (HARD REQUIREMENT)
- [ ] `NOT_IMPLEMENTED` minden páronn = `CHAIN_BLOCKED`, exitcode 1, T06–T10 NEM INDÍTHATÓ
- [ ] NotImplemented nem panic — explicit return
- [ ] Döntési pont dokumentálva a reportban
- [ ] concave.rs érintetlen
- [ ] pub mod reduced_convolution megjelenik a mod.rs-ben

## Stop conditions
Ha a `NOT_IMPLEMENTED` verdict minden fixture-n megjelenik:
→ **STOP. Írd a reportba: `CHAIN_BLOCKED: algorithm_not_ready`.**
→ Ne folytasd T06-tal.
→ A fejlesztési lánc csak akkor folytatható, ha az algoritmus legalább 1 LV8 páronn valódi NFP outputot ad.
