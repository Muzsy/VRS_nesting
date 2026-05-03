# Engine v2 NFP RC — T10 LV8 Experimental Benchmark

## Cél
Mérni az új reduced convolution + cleanup kernel hatását teljes LV8 csomagon.
Ez nem csak runtime teszt — minden metrikát mérni kell: correctness, cache efficiency,
utilization, fallback count, invalid NFP count. A benchmark eredmény meghatározza,
hogy az RC kernel alkalmas-e a production-ba való előléptetésre.

## Miért szükséges
T01–T09 elszigetelt tesztek. T10 a teljes pipeline end-to-end tesztje valós LV8
adatokon. Az összehasonlítás a T04 baseline-nal (concave NFP) mutatja meg,
hogy az RC kernel: (a) egyáltalán fut-e végig LV8 adatokon, (b) jobb-e a runtime,
(c) megőrzi-e a kihasználtságot, (d) nincs-e invalid NFP, (e) nincs-e fallback.

## Érintett valós fájlok

### Olvasandó (kontextus):
- `scripts/benchmark_cavity_v2_lv8.py` — LV8 benchmark minta (struktúra reference)
- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` — LV8 solver input
- `worker/cavity_prepack.py` — build_cavity_prepacked_engine_input_v2

### Létrehozandó:
- `scripts/benchmark_reduced_convolution_lv8.py` — RC kernel LV8 benchmark script
- `tmp/reports/engine_v2_nfp_rc_t10/` — output riport könyvtár (mkdir -p)

## Nem célok / scope határok
- Tilos a `benchmark_cavity_v2_lv8.py`-t módosítani (csak olvasni).
- Tilos a cavity_prepack_v2 guard-ot kikapcsolni.
- Tilos a `top_level_holes_after_prepack > 0` esetet sikerként kezelni.
- Tilos fallback eredményt sikerként jelölni.
- Tilos invalid NFP-t sikerként elfogadni.
- **TILOS Sparrow-ra kapcsolni vagy Sparrow eredményt összehasonlítási sikernek tekinteni.**
  Sparrow strip-packing optimalizáló, nem alkalmas valós 1500×3000 mm fizikai táblaméretű sheet-native nestingre.
  A T10 célja az Engine v2 RC NFP kernel teljesítményének mérése — Sparrow más problémaosztályt old meg.

## Részletes implementációs lépések

### 1. `scripts/benchmark_reduced_convolution_lv8.py` implementálása

**Parancssori interfész:**
```
--fixture <path>      LV8 solver input (default: tests/fixtures/nesting_engine/ne2_input_lv8jav.json)
--output-dir <path>   Riport könyvtár (default: tmp/reports/engine_v2_nfp_rc_t10)
--timeout-minutes <N> Teljes timeout percekben (default: 30)
--dry-run             Csak a preflight ellenőrzések futnak le
```

**Benchmark flow:**

1. **Preflight:** cavity_prepack_v2 futtatása → top_level_holes_after_prepack = 0 ellenőrzés
2. **Engine futtatás:** `quality_reduced_convolution_experimental` profillal
3. **Metrikák gyűjtése:** minden NfpPlacerStatsV1 mező rögzítése
4. **Correctness check:** nfp_correctness_benchmark futtatása a result NFP-in
5. **Összehasonlítás:** baseline (benchmark_cavity_v2_lv8 utolsó futás) vs RC result
6. **Riport mentése:** JSON + human-readable összefoglaló

**Kötelező stdout JSON output:**
```json
{
  "benchmark_version": "engine_v2_nfp_rc_lv8_v1",
  "timestamp": "2026-05-03T...",
  "nfp_kernel": "reduced_convolution_v1",
  "quality_profile": "quality_reduced_convolution_experimental",
  "fixture": "ne2_input_lv8jav.json",
  "preflight": {
    "top_level_holes_after_prepack": 0,
    "preflight_passed": true
  },
  "results": {
    "top_level_holes_after_prepack": 0,
    "nfp_total_pairs": 0,
    "nfp_cache_hit_rate": 0.0,
    "nfp_timeout_count": 0,
    "nfp_invalid_count": 0,
    "placed_parts": 0,
    "unplaced_parts": 0,
    "overlap_count": 0,
    "bounds_violation_count": 0,
    "utilization_pct": 0.0,
    "sheet_count": 0,
    "fallback_occurred": false,
    "fallback_count": 0,
    "nfp_kernel_unsupported_count": 0,
    "correctness_validator_status": "not_run",
    "actual_nfp_kernel_used": "reduced_convolution_v1",
    "total_runtime_seconds": 0.0
  },
  "comparison_to_baseline": {
    "baseline_source": "benchmark_cavity_v2_lv8",
    "baseline_utilization_pct": null,
    "baseline_nfp_time_seconds": null,
    "baseline_placed_parts": null,
    "rc_vs_baseline_utilization_delta_pct": null,
    "rc_vs_baseline_nfp_time_ratio": null,
    "comparison_verdict": "NO_BASELINE"
  },
  "verdict": "PASS",
  "verdict_reasons": []
}
```

**Verdict logika — FAIL feltételek (bármely FAIL-t okoz):**
1. `top_level_holes_after_prepack > 0` → `FAIL: prepack_guard_violated`
2. `fallback_occurred == true` → `FAIL: silent_fallback_detected`
3. `nfp_invalid_count > 0` → `FAIL: invalid_nfp_accepted`
4. `overlap_count > 0` → `FAIL: placements_overlap`
5. `bounds_violation_count > 0` → `FAIL: bounds_violated`
6. `actual_nfp_kernel_used != "reduced_convolution_v1"` → `FAIL: wrong_kernel_used`

**WARNING feltételek (nem FAIL, de jelölni kell):**
- `correctness_validator_status == "not_run"` → `WARN: correctness_not_validated`
- `nfp_kernel_unsupported_count > 0` → `WARN: some_pairs_unsupported`
- `rc_vs_baseline_utilization_delta_pct < -5.0` → `WARN: utilization_regression`

### 2. Output könyvtár és fájlok

```bash
mkdir -p tmp/reports/engine_v2_nfp_rc_t10
```

Mentendő fájlok:
- `tmp/reports/engine_v2_nfp_rc_t10/benchmark_result_TIMESTAMP.json` — teljes JSON riport
- `tmp/reports/engine_v2_nfp_rc_t10/benchmark_summary_TIMESTAMP.txt` — human-readable összefoglaló
- `tmp/reports/engine_v2_nfp_rc_t10/README.md` — mi van ebben a könyvtárban

### 3. Baseline összehasonlítás

Ha a `benchmark_cavity_v2_lv8.py` korábban futott és van riport:
```bash
# Utolsó baseline eredmény keresése
ls tmp/reports/cavity_v2_lv8/ 2>/dev/null | sort | tail -1
```
Ha nincs baseline: `comparison_verdict: "NO_BASELINE"` — nem FAIL.

### 4. Correctness validator integráció

A benchmark lefutása után:
```bash
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source reduced_convolution_v1 \
  --output-json
```
Az eredmény `correctness_validator_status`-ba kerül:
- `"pass"`, `"marginal"`, `"fail_false_positive"`, `"fail_false_negative"`, `"not_available"`

Ha `"fail_false_positive"`: a benchmark verdict FAIL.

### 5. Human-readable összefoglaló formátuma

```
============================================
Engine v2 NFP RC — LV8 Experimental Benchmark
============================================
Timestamp   : 2026-05-03T...
Kernel      : reduced_convolution_v1
Profile     : quality_reduced_convolution_experimental
Fixture     : ne2_input_lv8jav.json

PREFLIGHT   : PASS (0 top-level holes)

RESULTS
  Placed parts           : N / M
  Utilization            : X.X%
  Sheet count            : S
  NFP pairs              : P
  NFP cache hit rate     : H.H%
  NFP timeout count      : T
  NFP invalid count      : I
  Fallback count         : F
  Overlap count          : O
  Bounds violations      : B

CORRECTNESS : PASS / MARGINAL / FAIL_FALSE_POSITIVE / NOT_AVAILABLE

COMPARISON  : (vs baseline_cavity_v2_lv8)
  Utilization delta      : +/-X.X%
  NFP time ratio         : X.Xx

VERDICT     : PASS / FAIL
Fail reasons: (lista ha FAIL)
============================================
```

## Adatmodell / contract változások
Új Python script (`scripts/benchmark_reduced_convolution_lv8.py`).
Új output könyvtár (`tmp/reports/engine_v2_nfp_rc_t10/`).

## Backward compatibility
A `benchmark_cavity_v2_lv8.py` érintetlen. A cavity_prepack_v2 guard érintetlen.
Nincs production kód változás.

## Hibakódok / diagnosztikák
- `FAIL: prepack_guard_violated` — cavity_prepack_v2 hole-free guard megsértve
- `FAIL: silent_fallback_detected` — fallback_occurred=true
- `FAIL: invalid_nfp_accepted` — nfp_invalid_count > 0
- `FAIL: wrong_kernel_used` — nem az RC kernel futott ténylegesen
- `WARN: correctness_not_validated` — nfp_correctness_benchmark nem futott

## Tesztelési terv
```bash
# 1. Script szintaxis
python3 -c "import ast; ast.parse(open('scripts/benchmark_reduced_convolution_lv8.py').read()); print('syntax OK')"

# 2. Dry run
python3 scripts/benchmark_reduced_convolution_lv8.py --dry-run

# 3. Teljes benchmark futtatás (hosszú — csak ha minden T01–T09 kész)
python3 scripts/benchmark_reduced_convolution_lv8.py \
  --fixture tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  --output-dir tmp/reports/engine_v2_nfp_rc_t10 \
  --timeout-minutes 30

# 4. Riport létezik
ls tmp/reports/engine_v2_nfp_rc_t10/*.json

# 5. JSON validálás
python3 -c "
import json, glob
for f in glob.glob('tmp/reports/engine_v2_nfp_rc_t10/*.json'):
    d = json.loads(open(f).read())
    assert 'verdict' in d
    assert 'results' in d
    assert d['results']['top_level_holes_after_prepack'] == 0, 'prepack guard violated!'
    print(f, 'verdict:', d['verdict'])
"

# 6. FAIL ha fallback
python3 -c "
import json, glob
for f in glob.glob('tmp/reports/engine_v2_nfp_rc_t10/*.json'):
    d = json.loads(open(f).read())
    if d['results']['fallback_occurred']:
        assert d['verdict'] == 'FAIL', f'fallback_occurred but verdict is not FAIL in {f}'
        print(f, 'PASS: fallback correctly triggers FAIL')
"
```

## Elfogadási feltételek
- [ ] `scripts/benchmark_reduced_convolution_lv8.py` létezik és szintaxis OK
- [ ] `--dry-run` lefut hiba nélkül
- [ ] Teljes benchmark fut (akár hosszú ideig)
- [ ] `top_level_holes_after_prepack = 0` (prepack guard aktív)
- [ ] `fallback_occurred = true` esetén verdict = FAIL
- [ ] `nfp_invalid_count > 0` esetén verdict = FAIL
- [ ] JSON riport kimentve `tmp/reports/engine_v2_nfp_rc_t10/`-ba
- [ ] Human-readable összefoglaló megjelenik stdout-on
- [ ] Nincs production kód módosítás (csak új script és tmp riport)

## Rollback / safety notes
Kizárólag új Python script és `tmp/` riportok. Nincs production kód változás.
A `tmp/reports/engine_v2_nfp_rc_t10/` könyvtár törölhető.

## Dependency
Minden korábbi task:
- T01: LV8 fixture pair-ek
- T03: cleanup pipeline (az engine használja)
- T04: baseline mérések (comparison_to_baseline)
- T05: RC kernel (actual_nfp_kernel)
- T06: cleanup pipeline (nfp_invalid_count = 0 szükséges)
- T07: correctness validator (correctness_validator_status)
- T08: engine integration (quality_reduced_convolution_experimental profil)
- T09: cache (nfp_cache_hit_rate mérése)
