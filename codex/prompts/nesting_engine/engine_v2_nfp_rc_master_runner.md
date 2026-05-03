# Engine v2 NFP RC Master Runner — Reduced Convolution / Robust Minkowski NFP teljes fejlesztési lánc

## Cél

Ez a dokumentum leírja a T01–T10 fejlesztési lánc helyes futtatási sorrendjét, minden
task kötelező ellenőrzési lépéseit, a checkpoint feltételeket és a végső auditot.
Egy agent ezzel a dokumentummal önállóan végigviheti az egész `engine_v2_nfp_rc`
fejlesztési láncon.

---

## Előfeltételek a teljes lánc indítása előtt

### 1. Alapeszközök
```bash
python3 --version      # >= 3.8
cargo --version        # Rust toolchain megvan
python3 -c "import shapely; print('shapely OK')" 2>/dev/null || echo "WARN: shapely hiányzik"
```

### 2. Baseline tesztek (cavity_prepack_v2 pipeline érintetlen)
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```
Ha bármely meglévő teszt piros: **NE INDÍTSD EL A LÁNCOT** — előbb fixeld.

### 3. Rust baseline
```bash
cargo check -p nesting_engine
cargo test -p nesting_engine
```
Ha fordítási hiba van: **NE INDÍTSD EL A LÁNCOT**.

### 4. LV8 fixture megléte
```bash
ls tests/fixtures/nesting_engine/ne2_input_lv8jav.json || echo "STOP: LV8 fixture szükséges"
```

---

## Kritikus tiltások (az egész láncon érvényes)

1. **Tilos silent BLF fallback** — ha az RC kernel fail, explicit `unsupported`/`degraded` státusz
2. **Tilos validálatlan NFP elfogadása** — minden NFP output cleanup + correctness check után
3. **Tilos a meglévő ConcaveDefault kernelt módosítani** — csak additive extension
4. **Tilos destructive geometry simplification** — reflex vertex elvesztés = topológia változás
5. **Tilos a `benchmark_cavity_v2_lv8.py`-t módosítani** — csak olvasni
6. **Tilos a `boundary_clean.rs`-t törölni** — felhasználható, de érintetlen marad
7. **Tilos a meglévő quality profilokat módosítani** — csak új profil adható hozzá
8. **Tilos timeout-ot sikerként kezelni** — explicit TIMEOUT verdict kötelező
9. **Tilos a cavity_prepack_v2 hole-free guard-ot kikapcsolni**
10. **Tilos placeholder/synthetic fixture-t létrehozni** — minden fixture valódi LV8 geometrián alapul, vagy STOP
11. **SPARROW NEM ALTERNATÍVA EHHEZ A FEJLESZTÉSHEZ** — Sparrow strip-packing optimalizáló, nem alkalmas 1500×3000 mm fizikai táblaméretű sheet-native nestingre. Tilos Sparrow futtatás eredményét az Engine v2 RC NFP fejlesztés sikerének vagy alternatívájának tekinteni. A cél az Engine v2 NFP-képességének fejlesztése valós táblaméretű nestinghez.

---

## Futtatási sorrend és függőségek

```
T01 (pair extraction)  ──┬── T04 (baseline instrumentation) ─────────────────────────────┐
                         │                                                                  │
T02 (geometry contract)  ┤── T03 (cleanup pipeline) ────── T05 (RC prototype) ────────────┤
                         │                                       │                          │
                         │                                       ▼                          │
                         │                                  T06 (Minkowski cleanup) ─────── ┤
                         │                                       │                          │
                         │                                       ▼                          │
                         │                                  T07 (correctness validator) ─── ┤
                         │                                                                  │
                         └──────────────────────────────── T08 (engine integration) ────── ┤
                                                                 │                          │
                                                                 ▼                          │
                                                            T09 (cache hash) ─────────────  ┤
                                                                                            │
                                                                                            ▼
                                                                                       T10 (LV8 benchmark)
```

**Párhuzamosan futtatható:** T01 és T02 (egymástól független).
**T03** futtatható T01 és T02 után, párhuzamosan T04-gyel.
**Kötelező sorrend:** T05 → T06 → T07 → T08 → T09 → T10.
**T04** futtatható T01 után, párhuzamosan T03-mal.

---

## CHECKPOINT-0: Baseline verify

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py tests/worker/test_result_normalizer_cavity_plan.py
cargo check -p nesting_engine
cargo test -p nesting_engine
```
**Feltétel: 0 piros teszt, 0 fordítási hiba. Ha van piros: STOP.**

---

## T01 — LV8 problémás part-pair extraction

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t01_lv8_pair_extraction/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t01_lv8_pair_extraction.yaml`
**Canvas:** `canvases/nesting_engine/engine_v2_nfp_rc_t01_lv8_pair_extraction.md`

```bash
# Kötelező lépések
python3 scripts/experiments/extract_nfp_pair_fixtures_lv8.py
python3 -c "import ast; ast.parse(open('scripts/experiments/extract_nfp_pair_fixtures_lv8.py').read()); print('syntax OK')"
```

**CHECKPOINT-T01:**
```bash
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_03.json
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json
python3 -c "import json,pathlib; p=json.loads(pathlib.Path('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json').read_text()); assert p['fixture_version']=='nfp_pair_fixture_v1'; print('schema OK')"
git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'  # üresnek kell lennie
```
- [ ] 3 fixture JSON létezik
- [ ] lv8_pair_index.json létezik
- [ ] fixture_version=nfp_pair_fixture_v1
- [ ] part_a.points_mm nem üres
- [ ] Nincs production kód módosítás

---

## T02 — Geometry Profile Contract

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t02_geometry_profile_contract/run.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t02_geometry_profile_contract.yaml`

```bash
# Kötelező lépések
# Olvasd el: geometry/types.rs, scale.rs, float_policy.rs, nfp/mod.rs, boundary_clean.rs
```

**CHECKPOINT-T02:**
```bash
ls docs/nesting_engine/geometry_preparation_contract_v1.md
python3 -c "
content = open('docs/nesting_engine/geometry_preparation_contract_v1.md').read()
sections = ['Exact geometry', 'Canonical clean', 'Solver', 'Integer robust', 'GEOM_EPS_MM', 'Simplification safety', 'Final validation']
missing = [s for s in sections if s not in content]
print('MISSING:', missing) if missing else print('All 7 sections present')
"
git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'  # üresnek kell lennie
```
- [ ] geometry_preparation_contract_v1.md létezik
- [ ] Mind a 7 szekció megvan
- [ ] Nincs production kód módosítás

---

## T03 — Geometry Cleanup Pipeline

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t03_geometry_cleanup_pipeline/run.md`
**Blokkoló dependency:** T01, T02

**CHECKPOINT-T03:**
```bash
cargo check -p nesting_engine
cargo run --bin geometry_prepare_benchmark -- --help
ls rust/nesting_engine/src/geometry/cleanup.rs
ls rust/nesting_engine/src/geometry/simplify.rs
cargo run --bin geometry_prepare_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert d['part_a']['simplify']['topology_changed']==False, 'topology changed!'
assert d['part_a']['simplify']['area_delta_mm2']<0.5, 'area delta too large!'
print('PASS')
"
git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs  # üresnek kell lennie
```
- [ ] cargo check hibátlan
- [ ] cleanup.rs, simplify.rs léteznek
- [ ] geometry_prepare_benchmark fut T01 fixture-ökön
- [ ] topology_changed=false
- [ ] boundary_clean.rs érintetlen

---

## T04 — NFP Baseline Instrumentation

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t04_nfp_baseline_instrumentation/run.md`
**Blokkoló dependency:** T01

**CHECKPOINT-T04:**
```bash
cargo run --bin nfp_pair_benchmark -- --help
cargo run --bin nfp_pair_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --timeout-ms 5000 --output-json | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert 'verdict' in d
assert d['verdict'] in ('SUCCESS','TIMEOUT','ERROR','DECOMPOSITION_FAILED')
print('verdict:', d['verdict'])
"
python3 -c "
import json; from pathlib import Path
for pair_id in ['lv8_pair_01','lv8_pair_02','lv8_pair_03']:
    bm = json.loads(Path(f'tests/fixtures/nesting_engine/nfp_pairs/{pair_id}.json').read_text())['baseline_metrics']
    assert bm.get('fragment_count_a') is not None, f'{pair_id}: still null'
    print(f'{pair_id}: OK, verdict={bm.get(\"verdict\")}')
"
git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs  # üresnek kell lennie
```
- [ ] nfp_pair_benchmark fut
- [ ] fixture baseline_metrics kitöltve
- [ ] concave.rs érintetlen

---

## T05 — Reduced Convolution Prototype

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t05_reduced_convolution_prototype/run.md`
**Blokkoló dependency:** T01, T03, T04

**CHECKPOINT-T05:**
```bash
cargo check -p nesting_engine
cargo run --bin nfp_rc_prototype_benchmark -- --help

# KRITIKUS: legalább 1 páronn SUCCESS verdict kell
python3 -c "
import json, subprocess, sys
success_count = 0
for pair_id in ['lv8_pair_01','lv8_pair_02','lv8_pair_03']:
    r = subprocess.run(
        ['cargo','run','--bin','nfp_rc_prototype_benchmark','--',
         '--fixture',f'tests/fixtures/nesting_engine/nfp_pairs/{pair_id}.json','--output-json'],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f'{pair_id}: cargo error')
        continue
    d = json.loads(r.stdout)
    v = d.get('verdict')
    vc = d.get('rc_result',{}).get('raw_vertex_count',0)
    print(f'{pair_id}: verdict={v} raw_vc={vc}')
    if v == 'SUCCESS' and vc > 0:
        success_count += 1
if success_count == 0:
    print('CHAIN_BLOCKED: algorithm_not_ready. T06/T07/T08/T10 NEM INDÍTHATÓ.')
    sys.exit(1)
print(f'T05 PASS: {success_count}/3 páronn valódi NFP output.')
"

grep -n 'pub mod reduced_convolution' rust/nesting_engine/src/nfp/mod.rs
git diff HEAD -- rust/nesting_engine/src/nfp/concave.rs  # üresnek kell lennie
```
- [ ] cargo check hibátlan
- [ ] nfp_rc_prototype_benchmark fut
- [ ] **Legalább 1 páronn SUCCESS és raw_vertex_count > 0** — NOT_IMPLEMENTED minden páronn = CHAIN_BLOCKED
- [ ] NotImplemented explicit (nem panic)
- [ ] concave.rs érintetlen

**BLOKKOLÓ:** Ha minden fixture NOT_IMPLEMENTED: **T06/T07/T08/T10 NEM INDÍTHATÓ.** Fixáld az algoritmust.

---

## T06 — Robust Minkowski Cleanup

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t06_robust_minkowski_cleanup/run.md`
**Blokkoló dependency:** T03, T05

**CHECKPOINT-T06:**
```bash
cargo check -p nesting_engine
cargo test -p nesting_engine -- minkowski_cleanup 2>&1 | tail -5
cargo test -p nesting_engine -- nfp_validation 2>&1 | tail -5
grep -n "pub mod minkowski_cleanup\|pub mod nfp_validation" rust/nesting_engine/src/nfp/mod.rs
git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs  # üresnek kell lennie
```
- [ ] cargo check hibátlan
- [ ] Unit tesztek: is_valid=false → polygon=None
- [ ] boundary_clean.rs érintetlen

---

## T07 — NFP Correctness Validator

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator/run.md`
**Blokkoló dependency:** T01, T05, T06

**CHECKPOINT-T07 (kétszintű):**
```bash
cargo run --bin nfp_correctness_benchmark -- --help

# SZINT 1 — validator_infra_pass
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source mock_exact --output-json | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert d['false_positive_rate'] == 0.0, 'mock_exact FP > 0!'
print('validator_infra_pass: mock_exact FP=0.0 PASS')
"

# SZINT 2 — rc_correctness_pass (T08 indításának feltétele)
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source reduced_convolution_v1 --output-json | python3 -c "
import json,sys; d=json.load(sys.stdin)
v = d.get('correctness_verdict')
fp = d.get('false_positive_rate', 1.0)
print(f'RC verdict={v} false_positive_rate={fp}')
if v == 'NOT_AVAILABLE':
    print('rc_correctness_pass=false: T05 nem adott output-ot — T05 fixálandó, T08 BLOKKOLVA')
    sys.exit(1)
if fp > 0:
    print('rc_correctness_pass=false: FAIL_FALSE_POSITIVE — T08 BLOKKOLVA')
    sys.exit(1)
print('rc_correctness_pass=true: T08 INDÍTHATÓ')
"
```
- [ ] nfp_correctness_benchmark fut
- [ ] validator_infra_pass: mock_exact false_positive_rate=0.0
- [ ] **rc_correctness_pass: tényleges RC NFP-n fut, NOT_AVAILABLE = BLOKK**
- [ ] **FAIL_FALSE_POSITIVE = T08 BLOKKOLVA**

**BLOKKOLÓ:** Ha `rc_correctness_pass = false`: **T08 NEM INDÍTHATÓ.** Cause: NOT_AVAILABLE → T05 fixálandó. Cause: FAIL_FALSE_POSITIVE → T05/T06 fixálandó.

---

## T08 — Experimental Engine Integration

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t08_experimental_engine_integration/run.md`
**Blokkoló dependency:** T05, T06, T07

**CHECKPOINT-T08:**
```bash
cargo check -p nesting_engine
cd frontend && npx tsc --noEmit && cd ..
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
p = _QUALITY_PROFILE_REGISTRY['quality_reduced_convolution_experimental']
assert p['nfp_kernel'] == 'reduced_convolution_v1'
assert p['experimental'] == True
print('profile OK')
"
# --nfp-kernel CLI arg megvan a Rust main-ben
grep -n 'nfp.kernel\|nfp_kernel\|NfpKernelPolicy' rust/nesting_engine/src/main.rs || echo "WARN: nfp_kernel CLI arg hiányzik a main.rs-ből"
# nfp_kernel wiring a runner-ben
python3 -c "
import inspect
from vrs_nesting.runner import nesting_engine_runner
assert 'nfp_kernel' in inspect.getsource(nesting_engine_runner), 'nfp_kernel wiring hiányzik a runner-ből!'
print('runner nfp_kernel wiring OK')
"
# Meglévő tesztek érintetlenek
python3 -m pytest -q tests/worker/test_cavity_prepack.py
```
- [ ] cargo check hibátlan
- [ ] tsc --noEmit hibátlan
- [ ] RC profil megvan, experimental=True
- [ ] **rust/nesting_engine/src/main.rs fogadja a --nfp-kernel argumentet**
- [ ] **vrs_nesting/runner/nesting_engine_runner.py átadja a nfp_kernel-t CLI arg-ként**
- [ ] **worker/main.py nem nyeli el az nfp_kernel mezőt**
- [ ] Meglévő cavity tesztek zöldek

---

## T09 — NFP Cache Geometry Hash

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t09_nfp_cache_geometry_hash/run.md`
**Blokkoló dependency:** T08

**CHECKPOINT-T09:**
```bash
cargo test -p nesting_engine 2>&1 | tail -10
grep -rn "NfpCacheKey {" rust/nesting_engine/src/ && echo "WARN: struct literal found" || echo "OK"
ls rust/nesting_engine/src/geometry/hash.rs
```
- [ ] cargo test hibátlan
- [ ] Nincs NfpCacheKey struct literal
- [ ] hash.rs létezik
- [ ] Kernel separation teszt PASS

---

## T10 — LV8 Experimental Benchmark

**Runner:** `codex/prompts/nesting_engine/engine_v2_nfp_rc_t10_lv8_experimental_benchmark/run.md`
**Blokkoló dependency:** T01–T09 MIND

**CHECKPOINT-T10:**
```bash
python3 -c "import ast; ast.parse(open('scripts/benchmark_reduced_convolution_lv8.py').read()); print('syntax OK')"
python3 scripts/benchmark_reduced_convolution_lv8.py --dry-run
ls tmp/reports/engine_v2_nfp_rc_t10/
# Teljes benchmark (ha minden T01–T09 kész):
# python3 scripts/benchmark_reduced_convolution_lv8.py --fixture tests/fixtures/nesting_engine/ne2_input_lv8jav.json
git diff HEAD -- scripts/benchmark_cavity_v2_lv8.py  # üresnek kell lennie
```
- [ ] benchmark_reduced_convolution_lv8.py szintaxis OK
- [ ] --dry-run fut
- [ ] benchmark_cavity_v2_lv8.py érintetlen

**T10 FAIL feltételek — bármely FAIL = lánc nem teljesített:**
1. top_level_holes_after_prepack > 0
2. fallback_occurred = true
3. nfp_invalid_count > 0
4. overlap_count > 0
5. bounds_violation_count > 0
6. actual_nfp_kernel_used != "reduced_convolution_v1"

---

## Végső teljes lánc audit

```bash
echo "=== ENGINE V2 NFP RC FULL CHAIN AUDIT ==="

echo "--- T01: Fixtures ---"
python3 -c "
import json; from pathlib import Path
for p_id in ['lv8_pair_01','lv8_pair_02','lv8_pair_03']:
    p = json.loads(Path(f'tests/fixtures/nesting_engine/nfp_pairs/{p_id}.json').read_text())
    a_vc = len(p['part_a']['points_mm'])
    b_vc = len(p['part_b']['points_mm'])
    print(f'{p_id}: A_vc={a_vc} B_vc={b_vc} product={a_vc*b_vc}')
"

echo "--- T02: Contract doc ---"
ls docs/nesting_engine/geometry_preparation_contract_v1.md && echo "OK" || echo "MISSING"

echo "--- T03: Cleanup pipeline ---"
cargo check -p nesting_engine 2>&1 | grep "^error" | wc -l | xargs -I{} echo "Rust errors: {}"
ls rust/nesting_engine/src/geometry/cleanup.rs && echo "cleanup.rs OK" || echo "MISSING"
ls rust/nesting_engine/src/geometry/simplify.rs && echo "simplify.rs OK" || echo "MISSING"

echo "--- T04: Baseline ---"
python3 -c "
import json; from pathlib import Path
bm = json.loads(Path('tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json').read_text())['baseline_metrics']
print('T04 baseline: fragment_count_a=%s verdict=%s' % (bm.get('fragment_count_a'), bm.get('verdict')))
"

echo "--- T05: RC Prototype ---"
ls rust/nesting_engine/src/nfp/reduced_convolution.rs && echo "reduced_convolution.rs OK" || echo "MISSING"

echo "--- T06: Cleanup ---"
ls rust/nesting_engine/src/nfp/minkowski_cleanup.rs && echo "minkowski_cleanup.rs OK" || echo "MISSING"
ls rust/nesting_engine/src/nfp/nfp_validation.rs && echo "nfp_validation.rs OK" || echo "MISSING"

echo "--- T07: Correctness ---"
ls rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs && echo "nfp_correctness_benchmark.rs OK" || echo "MISSING"

echo "--- T08: Integration ---"
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
p = _QUALITY_PROFILE_REGISTRY.get('quality_reduced_convolution_experimental')
print('T08 profile:', 'OK' if p and p.get('nfp_kernel')=='reduced_convolution_v1' else 'MISSING')
"
grep -n 'nfp.kernel\|nfp_kernel' rust/nesting_engine/src/main.rs 2>/dev/null && echo "T08 main.rs CLI OK" || echo "WARN: --nfp-kernel CLI arg hiányzik main.rs-ből"
python3 -c "
import inspect
try:
    from vrs_nesting.runner import nesting_engine_runner
    src = inspect.getsource(nesting_engine_runner)
    print('T08 runner wiring:', 'OK' if 'nfp_kernel' in src else 'MISSING')
except Exception as e:
    print('T08 runner check error:', e)
"

echo "--- T09: Cache ---"
ls rust/nesting_engine/src/geometry/hash.rs && echo "hash.rs OK" || echo "MISSING"
grep -rn "NfpCacheKey {" rust/nesting_engine/src/ 2>/dev/null && echo "WARN: struct literal" || echo "OK: no struct literals"

echo "--- T10: Benchmark ---"
ls scripts/benchmark_reduced_convolution_lv8.py && echo "benchmark OK" || echo "MISSING"
ls tmp/reports/engine_v2_nfp_rc_t10/ 2>/dev/null && echo "reports dir OK" || echo "MISSING"

echo "--- BASELINE REGRESSION CHECK ---"
python3 -m pytest -q tests/worker/test_cavity_prepack.py 2>&1 | tail -3
cargo test -p nesting_engine 2>&1 | tail -3

echo "=== AUDIT COMPLETE ==="
```

---

## Gyors referencia táblázat

| Task | Fő output | Tesztparancs | Blokkoló dependency | Blokkolási feltétel |
|------|-----------|--------------|---------------------|---------------------|
| T01 | lv8_pair_01..03.json, extraction script | `ls tests/fixtures/.../lv8_pair_01.json` | — | LV8 fixture nem parse-olható → FAIL, ne hozz létre fixture-t |
| T02 | geometry_preparation_contract_v1.md | `ls docs/nesting_engine/geometry_preparation_contract_v1.md` | — | — |
| T03 | cleanup.rs, simplify.rs, geometry_prepare_benchmark | `cargo check -p nesting_engine` | T01, T02 | — |
| T04 | nfp_pair_benchmark, fixture baseline_metrics | `cargo run --bin nfp_pair_benchmark -- --help` | T01 | — |
| T05 | reduced_convolution.rs, nfp_rc_prototype_benchmark | SUCCESS verdict ≥1 páronn | T01, T03, T04 | NOT_IMPLEMENTED minden páronn = CHAIN_BLOCKED |
| T06 | minkowski_cleanup.rs, nfp_validation.rs | `cargo test -- minkowski_cleanup` | T03, T05 | T05 CHAIN_BLOCKED → T06 nem fut |
| T07 | nfp_correctness_benchmark (2 szint) | mock_exact FP=0.0 + rc_correctness_pass | T01, T05, T06 | rc_correctness_pass=false → T08 BLOKKOLVA |
| T08 | NfpKernelPolicy + main.rs + runner.py + worker.py + profil + TS | `cargo check && tsc --noEmit` + runner wiring | T05, T06, T07 | T07 rc_correctness_pass=false → BLOKKOLVA |
| T09 | bővített NfpCacheKey, hash.rs | `cargo test -p nesting_engine` | T08 | — |
| T10 | benchmark_reduced_convolution_lv8.py, riportok | `python3 ... --dry-run` | T01–T09 | fallback/invalid NFP/holes → FAIL |

---

## Hibaelhárítási útmutató

### "cargo check: unresolved import" T03 után
- Ellenőrizd: `geometry/mod.rs`-ben megvan-e `pub mod cleanup; pub mod simplify;`

### "NfpCacheKey: missing fields" T09-ben
- A struct extension breaking change — az összes hívóhelyet `concave_default()` constructor-ra kell cserélni
- `grep -rn "NfpCacheKey {" rust/nesting_engine/src/` megmutatja a maradékokat

### "quality_reduced_convolution_experimental not found" T08 után
- `python3 -c "from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY; print(list(_QUALITY_PROFILE_REGISTRY.keys()))"`
- Ha hiányzik: a nesting_quality_profiles.py módosítás nem lett elmentve

### "tsc --noEmit errors" T08 után
- Ha QualityProfileName exhaustive type guard van a kódbázisban: az új literal hozzáadása után
  frissíteni kell a type guard-ot is
- `grep -rn "quality_reduced_convolution_experimental\|QualityProfileName" frontend/src/`

### T10 FAIL: fallback_occurred = true
- Ellenőrizd: `actual_nfp_kernel_used` mező értéke a riportban
- Ha `"concave_default"`: az RC kernel nem lett bekapcsolva — T08 quality profil ellenőrzés
- Ha silent fallback: `nfp_kernel_explicit_fallback_count` > 0 — T08 fallback logika vizsgálata

### T10 FAIL: top_level_holes_after_prepack > 0
- A cavity_prepack_v2 hole-free guard hibás — T08 nem módosíthatja a prepack-ot
- Ellenőrizd: a prepack worker változatlan-e: `git diff HEAD -- worker/cavity_prepack.py`
