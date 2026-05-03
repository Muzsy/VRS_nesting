# Engine v2 NFP RC — T04 NFP Baseline Instrumentation

## Cél
A jelenlegi `concave.rs` algoritmust pontosan mérni a T01 fixture-ökön, meghatározni
pontosan hol és miért hal meg. A mért adatok képezik a T05–T10 összehasonlítási
baseline-ját. A T01 fixture-ök `baseline_metrics` mezőit ki kell tölteni.

## Miért szükséges
Bizonyítékalapú fejlesztés követelmény: az új kernel csak akkor lehet jobb, ha tudjuk,
miben és mennyivel rosszabb a jelenlegi. Konkrétan: fragment count, pair count,
timeout threshold, és az NfpError variant meghatározza, hogy melyik irányba kell
fejleszteni (orbit algoritmus vs. dekompozíció vs. convolution).

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `rust/nesting_engine/src/nfp/concave.rs` — ConcaveNfpMode, ConcaveNfpOptions, compute_concave_nfp_default
- `rust/nesting_engine/src/nfp/convex.rs` — convex NFP (az orbit algoritmus alapja)
- `rust/nesting_engine/src/nfp/mod.rs` — NfpError enum teljes lista
- `rust/nesting_engine/src/bin/nfp_fixture.rs` — meglévő bin (stdin/stdout JSON alapú) — minta
- `rust/nesting_engine/src/nfp/cache.rs` — NfpCache, shape_id()
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` — T01 fixture
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` — T01 fixture
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` — T01 fixture

### Létrehozandó:
- `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` — mérő bin

### Módosítandó (fixture frissítés):
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` — baseline_metrics kitöltése
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` — baseline_metrics kitöltése
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` — baseline_metrics kitöltése

## Nem célok / scope határok
- Tilos a `concave.rs`-t módosítani (csak mérni).
- Tilos a `convex.rs`-t módosítani.
- Tilos a `nfp/mod.rs` NfpError enum-ot módosítani.
- A timeout-ot nem szabad sikerként kezelni.
- Nem kell új NFP algoritmust implementálni.

## Részletes implementációs lépések

### 1. Meglévő nfp_fixture.rs megértése

Olvasd el a `rust/nesting_engine/src/bin/nfp_fixture.rs`-t:
- Milyen JSON formátumot vár stdin-en?
- Milyen JSON-t ad stdout-on?
- Hogyan hívja a concave NFP API-t?
Ez lesz a minta a `nfp_pair_benchmark.rs`-hez.

### 2. `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` implementálása

**Parancssori interfész:**
```
--fixture <path>     NFP pair fixture JSON fájl
--timeout-ms <N>     Timeout milliszekundumban (default: 5000)
--part-a-only        Csak a part_a geometriát teszteli (diagnosztikai mód)
--part-b-only        Csak a part_b geometriát teszteli
--output-json        JSON riport stdout-ra (default: human-readable)
```

**Mért JSON output:**
```json
{
  "benchmark_version": "nfp_pair_benchmark_v1",
  "fixture": "lv8_pair_01",
  "pair_a_id": "Lv8_11612",
  "pair_b_id": "Lv8_07921",
  "timestamp_utc": "...",
  "decomposition": {
    "fragment_count_a": 42,
    "fragment_count_b": 67,
    "pair_count": 2814,
    "decomposition_time_ms": 120,
    "error": null
  },
  "nfp_computation": {
    "fragment_union_time_ms": 8500,
    "cleanup_time_ms": 45,
    "total_time_ms": 8765,
    "output_vertex_count": 0,
    "output_loop_count": 0,
    "timed_out": true,
    "error": "timeout after 5000ms",
    "nfp_error_kind": null
  },
  "verdict": "TIMEOUT"
}
```

**verdict értékek:**
- `SUCCESS` — NFP sikeresen kiszámítva, valid output
- `TIMEOUT` — timeout_ms elérve, explicit
- `ERROR` — NfpError variant keletkezett (nfp_error_kind mezőben rögzítve)
- `DECOMPOSITION_FAILED` — konvex dekompozíció sikertelen

**timeout implementáció:**
A Rust standard library `std::sync::mpsc` vagy `std::thread::spawn` + `join` kombináció
timeout-tal. Ha a timeout lejár: `timed_out = true`, a szál leállítása best-effort.

**NfpError variant mapping:**
```rust
match err {
    NfpError::EmptyPolygon => "EmptyPolygon",
    NfpError::NotConvex => "NotConvex",
    NfpError::NotSimpleOutput => "NotSimpleOutput",
    NfpError::OrbitLoopDetected => "OrbitLoopDetected",
    NfpError::OrbitDeadEnd => "OrbitDeadEnd",
    NfpError::OrbitMaxStepsReached => "OrbitMaxStepsReached",
    NfpError::OrbitNotClosed => "OrbitNotClosed",
    NfpError::DecompositionFailed => "DecompositionFailed",
}
```

### 3. Baseline mérések futtatása

```bash
for pair in lv8_pair_01 lv8_pair_02 lv8_pair_03; do
  echo "=== ${pair} ==="
  cargo run --release --bin nfp_pair_benchmark -- \
    --fixture tests/fixtures/nesting_engine/nfp_pairs/${pair}.json \
    --timeout-ms 5000 \
    --output-json
done
```

### 4. Fixture baseline_metrics kitöltése

A mért értékek alapján frissítsd minden fixture JSON `baseline_metrics` mezőjét:
```json
"baseline_metrics": {
  "fragment_count_a": 42,
  "fragment_count_b": 67,
  "expected_pair_count": 2814,
  "current_nfp_timeout_reproduced": true,
  "decomposition_time_ms": 120,
  "total_nfp_time_ms_if_not_timeout": null,
  "nfp_error_kind_if_errored": null,
  "verdict": "TIMEOUT",
  "notes": "T04 mérés alapján kitöltve — pair_count>1000, timeout 5000ms-nál"
}
```

### 5. Diagnosztikai összefoglaló

Stdout-ra egy összefoglaló táblázat:
```
Pair ID          | A_frags | B_frags | Pairs  | Verdict  | Time(ms)
lv8_pair_01      |     42  |     67  |  2814  | TIMEOUT  |    5000+
lv8_pair_02      |     ...
lv8_pair_03      |     ...
```

## Adatmodell / contract változások
- Új Rust bin: `nfp_pair_benchmark.rs`
- Fixture JSON `baseline_metrics` mezők feltöltve (nem structural change, csak null → érték)

## Backward compatibility
A `concave.rs` érintetlen. Meglévő NfpError enum érintetlen. A fixture JSON séma
kompatibilis marad (baseline_metrics mezők null → value kitöltés).

## Hibakódok / diagnosztikák
- `verdict: TIMEOUT` — explicit timeout, nem hiba
- `verdict: ERROR` — NfpError keletkezett, nfp_error_kind rögzítve
- `verdict: DECOMPOSITION_FAILED` — konvex dekompozíció sikertelen
- Ha timeout reprodukált: `current_nfp_timeout_reproduced: true` a fixture-ben

## Tesztelési terv
```bash
# 1. Bin futtatható
cargo run --bin nfp_pair_benchmark -- --help

# 2. T01 fixture-ökön lefut (akár timeout-tal is)
cargo run --bin nfp_pair_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --timeout-ms 5000 \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'decomposition' in d
assert 'fragment_count_a' in d['decomposition']
assert 'verdict' in d
assert d['verdict'] in ('SUCCESS', 'TIMEOUT', 'ERROR', 'DECOMPOSITION_FAILED')
print('PASS: output schema valid, verdict:', d['verdict'])
"

# 3. Fixture baseline_metrics frissítve
python3 -c "
import json
from pathlib import Path
for pair_id in ['lv8_pair_01', 'lv8_pair_02', 'lv8_pair_03']:
    p = json.loads(Path(f'tests/fixtures/nesting_engine/nfp_pairs/{pair_id}.json').read_text())
    bm = p['baseline_metrics']
    assert bm.get('fragment_count_a') is not None, f'{pair_id}: fragment_count_a still null'
    print(f'{pair_id}: fragment_count_a={bm[\"fragment_count_a\"]} verdict={bm[\"verdict\"]}')
"

# 4. Nincs concave.rs módosítás
git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs
```

## Elfogadási feltételek
- [ ] `cargo run --bin nfp_pair_benchmark -- --help` fut
- [ ] T01 összes fixture-n lefut (akár timeout-tal is)
- [ ] Minden mért metrika a JSON output-ban megjelenik (fragment_count_a, fragment_count_b, pair_count, verdict, timed_out)
- [ ] Fixture JSON baseline_metrics mezők ki vannak töltve (nem null)
- [ ] `current_nfp_timeout_reproduced` helyes értéket tartalmaz
- [ ] verdict soha nem hiányzik a JSON-ból
- [ ] A `concave.rs` érintetlen

## Rollback / safety notes
Új bin, fixture update (null → érték). A `concave.rs` érintetlen.
Ha a benchmark bin törölhető, nincs production hatás.

## Dependency
- T01: lv8_pair_01–03 fixture-ök szükségesek
- T05: a baseline mérések referencia értékei
- T10: benchmark összehasonlítja az új kerneelt a T04 baseline-nal
