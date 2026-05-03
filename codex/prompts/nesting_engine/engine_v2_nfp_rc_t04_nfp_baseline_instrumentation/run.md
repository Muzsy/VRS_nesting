# Engine v2 NFP RC T04 — NFP Baseline Instrumentation
TASK_SLUG: engine_v2_nfp_rc_t04_nfp_baseline_instrumentation

## Szerep
Senior Rust mérési agent vagy. A jelenlegi concave NFP algoritmust méred a T01
fixture-ökön. Csak mérő bin-t írsz — a `concave.rs` érintetlen marad.

## Cél
Implementáld `nfp_pair_benchmark.rs` bin-t. Futtasd T01 fixture-ökön.
Töltsd ki a fixture `baseline_metrics` mezőit a mért értékekkel.

## Előfeltétel ellenőrzés
```bash
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json || echo "STOP: T01 szükséges"
ls rust/nesting_engine/src/bin/nfp_fixture.rs || echo "WARN: nfp_fixture.rs nem található"
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t04_nfp_baseline_instrumentation.yaml`
- `rust/nesting_engine/src/bin/nfp_fixture.rs` (JSON interfész minta)
- `rust/nesting_engine/src/nfp/concave.rs` (első 80 sor — ConcaveNfpOptions)
- `rust/nesting_engine/src/nfp/mod.rs` (NfpError enum teljes lista)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` (struktúra)

## Engedélyezett módosítás
- `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` (create)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` (modify: baseline_metrics)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json` (modify: baseline_metrics)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json` (modify: baseline_metrics)

## Szigorú tiltások
- **Tilos `concave.rs`-t módosítani.**
- Tilos timeout-ot sikerként kezelni.
- Tilos NfpError variant-ot elnyelni silent módon.
- Tilos új NFP algoritmust implementálni.

## Végrehajtandó lépések

### Step 1: nfp_fixture.rs interfész megértése
```bash
cat rust/nesting_engine/src/bin/nfp_fixture.rs | head -100
grep -n "NfpError\|pub enum\|fragment\|decomp" rust/nesting_engine/src/nfp/mod.rs | head -20
grep -n "pub fn compute_concave\|ConcaveNfpOptions\|ConcaveNfpMode" rust/nesting_engine/src/nfp/concave.rs | head -10
```

### Step 2: `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` megírása

Parancssori interfész:
- `--fixture <path>` — NFP pair fixture JSON
- `--timeout-ms <N>` — timeout (default: 5000)
- `--part-a-only` — csak part_a tesztelése
- `--output-json` — JSON output

JSON output séma:
```json
{
  "benchmark_version": "nfp_pair_benchmark_v1",
  "fixture": "lv8_pair_01",
  "pair_a_id": "...",
  "pair_b_id": "...",
  "timestamp_utc": "...",
  "decomposition": {
    "fragment_count_a": N,
    "fragment_count_b": N,
    "pair_count": N,
    "decomposition_time_ms": N,
    "error": null
  },
  "nfp_computation": {
    "fragment_union_time_ms": N,
    "cleanup_time_ms": N,
    "total_time_ms": N,
    "output_vertex_count": N,
    "output_loop_count": N,
    "timed_out": bool,
    "error": null,
    "nfp_error_kind": null
  },
  "verdict": "SUCCESS|TIMEOUT|ERROR|DECOMPOSITION_FAILED"
}
```

Timeout implementáció: `std::sync::mpsc` + `std::thread::spawn` + recv_timeout.
NfpError mapping: minden variant string-be konvertálva nfp_error_kind mezőbe.

### Step 3: Baseline mérések futtatása
```bash
cargo run --release --bin nfp_pair_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --timeout-ms 5000 \
  --output-json

cargo run --release --bin nfp_pair_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json \
  --timeout-ms 5000 \
  --output-json

cargo run --release --bin nfp_pair_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json \
  --timeout-ms 5000 \
  --output-json
```

### Step 4: Fixture baseline_metrics frissítése
A mért értékek alapján frissítsd minden fixture JSON-t:
```json
"baseline_metrics": {
  "fragment_count_a": <mért érték>,
  "fragment_count_b": <mért érték>,
  "expected_pair_count": <mért érték>,
  "current_nfp_timeout_reproduced": <true/false>,
  "decomposition_time_ms": <mért érték>,
  "total_nfp_time_ms_if_not_timeout": <mért vagy null>,
  "nfp_error_kind_if_errored": <mért vagy null>,
  "verdict": "<TIMEOUT/SUCCESS/ERROR>",
  "notes": "T04 mérés alapján kitöltve"
}
```

### Step 5: Validálás
```bash
# Bin help fut
cargo run --bin nfp_pair_benchmark -- --help

# Schema ellenőrzés
cargo run --bin nfp_pair_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'decomposition' in d
assert 'fragment_count_a' in d['decomposition']
assert 'verdict' in d
assert d['verdict'] in ('SUCCESS', 'TIMEOUT', 'ERROR', 'DECOMPOSITION_FAILED')
print('PASS: schema valid, verdict:', d['verdict'])
"

# Fixture baseline_metrics kitöltve
python3 -c "
import json
from pathlib import Path
for pair_id in ['lv8_pair_01', 'lv8_pair_02', 'lv8_pair_03']:
    p = json.loads(Path(f'tests/fixtures/nesting_engine/nfp_pairs/{pair_id}.json').read_text())
    bm = p['baseline_metrics']
    assert bm.get('fragment_count_a') is not None, f'{pair_id}: fragment_count_a still null'
    print(f'{pair_id}: fragment_count_a={bm[\"fragment_count_a\"]} verdict={bm.get(\"verdict\")}')
"

# concave.rs érintetlen
git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs
```

### Step 6: Report és checklist

## Tesztparancsok
```bash
cargo run --bin nfp_pair_benchmark -- --help
ls rust/nesting_engine/src/bin/nfp_pair_benchmark.rs
python3 -c "import json; bm=json.load(open('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json'))['baseline_metrics']; print('verdict:', bm.get('verdict'), 'frag_a:', bm.get('fragment_count_a'))"
```

## Ellenőrzési pontok
- [ ] nfp_pair_benchmark --help fut
- [ ] T01 összes fixture-n lefut (akár timeout-tal)
- [ ] fragment_count_a, fragment_count_b, pair_count, verdict a JSON-ban
- [ ] fixture baseline_metrics ki vannak töltve (nem null)
- [ ] TIMEOUT verdict ha timed_out=true
- [ ] concave.rs érintetlen
