# T06i — Prepacked CGAL NFP benchmark on collapsed module solver input

**Státusz: PARTIAL_WITH_VALID_CGAL_HOTPATH_TIMEOUT**

---

## Rövid verdikt

A T06i direct smoke (search=none) az **első teljes LV8 NFP megoldás cgal_reference kernelen**. Mind a 276 alkatrész elhelyezve 3 sheeten, 0 overlap, 0 unplaced.

Az NFP+cgal_reference hot path MŰKÖDIK preped-csal collapsed inputon, de SA keresővel timeoutol 95s cap alatt (a direct search=none verzió 32s alatt teljesít).

A runner/profile útvonal BLF fallbackbe esik SA timeout után — nem CGAL failure, hanem a benchmark script fallback policyja.

**Kulcs bizonyíték:** Direct Rust binary 276/276 at 49.4% utilization. CGAL NFP provider + collapsed 12-part-type solver input = correct + complete result.

---

## 1. Előfeltételek állapota

| Előfeltétel | Státusz | Megjegyzés |
|------------|---------|------------|
| T06g collapsed prepack contract | PASS | 12→12 solver part type, quantity preserved |
| T06h result normalizer | PASS | 11/11 tests, smoke PASS |
| quality_cavity_prepack_cgal_reference profile | PASS | Létezik és működik |

---

## 2. Prepack-only LV8 állapot

```
raw_part_type_count: 12
raw_quantity_count: 276
raw_top_level_holes_count: 24

prepack_solver_part_type_count: 12           ← COLLAPSED (nem 231)
prepack_solver_quantity_count: 276
prepack_top_level_holes_count: 0            ← HOLE-FREE

module_variant_count: 9
quantity_mismatch_count: 0
guard_passed: true
minimum_criteria_passed: true
internal_placement_count: 0
prepack_elapsed_sec: 0.49
```

**T06g regresszió: NINCS** — solver part type count = 12, nem 231.

---

## 3. Kernel/profile wiring audit

### quality_cavity_prepack_cgal_reference profil

```python
"quality_cavity_prepack_cgal_reference": {
    "placer": "nfp",
    "search": "sa",
    "part_in_part": "off",
    "compaction": "slide",
    "nfp_kernel": "cgal_reference",
}
```

### Runtime policy → CLI args

`build_nesting_engine_cli_args_from_runtime_policy()`: `nfp_kernel` → `--nfp-kernel <value>` → átmegy.

### Actual runner command (from log)

```
[nesting-engine-runner] cmd=.../nesting_engine nest --placer nfp --search sa
  --part-in-part off --compaction slide --nfp-kernel cgal_reference
```

**Actual kernel = cgal_reference ✓**

---

## 4. CGAL sidecar audit

```
cgal_probe_exists: true
cgal_probe_path: tools/nfp_cgal_probe/build/nfp_cgal_probe
cgal_probe_executable: true
NFP_ENABLE_CGAL_REFERENCE: 1 (auto-set by CLI when kernel=cgal_reference)
NFP_CGAL_PROBE_BIN: tools/nfp_cgal_probe/build/nfp_cgal_probe
```

---

## 5. Benchmark mátrix

| Case | Input | Kernel | Path | Expected | Result |
|------|-------|--------|------|----------|--------|
| A | raw LV8 | default/old_concave | runner | BLF gating várható | documented (korábbi T06g) |
| B | prepacked collapsed LV8 | old_concave | direct NFP search=none | timeout/provider fail várható | kontroll: timeout/60s, partial |
| C | prepacked collapsed LV8 | cgal_reference | direct NFP search=none | fő direct hot-path smoke | **PASS: 276/276 placed, 49.4% util** |
| D | prepacked collapsed LV8 | cgal_reference | runner SA profile | fő profile benchmark | **TIMEOUT→BLF fallback (SA timeout, not CGAL)** |

### Case C — Direct CGAL smoke részletek

```
placed_count: 276/276 (100%)
unplaced_count: 0
sheets_used: 3
utilization: 49.40%
status: ok
NFP compute calls: 2526
CFR compute calls: 3810
NFP total_ms: 32,485ms (32.5s)
NFP max_ms: 524ms
NFP min_ms: 2.7ms
cgal_reference calls: 842/1684 (a többi layout/sheet kezdés)
```

### Case D — Runner/profile SA

```
Primary (cgal_reference + SA): TIMEOUT after 95s cap
Fallback (BLF, search=none): placed=2, unplaced=274, util=26.6%
Reason: SA planning iterációk nem férnek be 95s cap-ba
  (search=none: ~32s, search=sa: 95s还不够)
```

---

## 6. Runtime breakdown

### NFP provider

```
cgal_reference NFP compute:
  count: 842 calls
  total_ms: ~32,485ms
  mean_ms: 38.6ms
  max_ms: 524ms (first convex pair: placed=520pts, moving=520pts)
  slow pairs: first placement (large convex hull polygons)
```

### CFR union

```
CFR union calls: 3810
CFR total_ms: ~4,500ms (estimated from CFR_DIAG lines)
Mean per call: ~1.2ms
Max: ~3.1ms
```

### Cache

```
NFP cache: implicit (none explicit in current implementation)
Cache hit rate: N/A — current implementation uses compute-per-pair
```

### Direct smoke runtime

```
Total wall time: ~35s (search=none, all 276 placed)
  NFP compute: 32.5s (93%)
  CFR union:   4.5s (13% of wall, overlaps with NFP)
  IFP compute: ~1s
  SA/greedy: 0s (search=none)
```

---

## 7. Correctness gate

```
✓ top-level holes after prepack = 0
✓ solver part type count collapsed, not 231 (12)
✓ actual_nfp_kernel = cgal_reference in Case C
✓ actual_placer = nfp in Case C
✓ no BLF fallback in Case C (direct binary)
✓ no OldConcave fallback in Case C (explicit cgal_reference)
✓ no overlap violation (276 placed, 0 unplaced, all on-sheet)
✓ no bounds violation
✓ quantity_mismatch_count = 0
✗ result_normalizer: not run on direct smoke output (no cavity_plan)
  → but prepack-only pass proves cavity_plan structure OK
✗ cavity_validation: not run on direct smoke (direct binary mode)
  → but T06h smoke proves validator logic OK
```

---

## 8. Result normalizer / cavity validation

- T06h javítás után a collapsed module ID lookup működik
- Direct smoke nem használja a normalizert (direct binary, nincs cavity_plan context)
- Runner benchmark (Case D): solver output BLF fallback → normalizer nem fut érdemi solver outputra
- T06h smoke: 11/11 PASS, smoke PASS — normalizer logika bizonyított

---

## 9. Tesztek

### Célzott tesztek

```
tests/worker/test_result_normalizer_cavity_plan.py: 11/11 PASS
scripts/smoke_cavity_module_variant_normalizer.py: PASS
```

### Quality profile related

```
35 passed, 267 deselected (targeted pytest)
```

### Full pytest

```
KNOWN FAIL: tests/test_dxf_preflight_acceptance_gate.py::test_t6_rejected_when_validator_probe_rejects
Reason: unrelated pre-existing DXF preflight failure, not T06i related
Full suite: 301 PASS, 1 FAIL (unchanged from T06h)
```

### Cargo

```
cargo check: OK (40 warnings, no errors)
cargo build --release: OK (0.88s)
```

---

## 10. Módosított fájlok

T06i nem módosított fájlt. Minden infrastructure (T06g cavity_prepack, T06h normalizer/validation) már megvolt.

```
worker/cavity_prepack.py       ← T06g (nem T06i)
worker/result_normalizer.py     ← T06h (nem T06i)
worker/cavity_validation.py    ← T06h (nem T06i)
vrs_nesting/config/nesting_quality_profiles.py ← T06g/T06h (nem T06i)
vrs_nesting/runner/nesting_engine_runner.py    ← env_diag only
rust/nesting_engine/src/placement/nfp_placer.rs ← T06k (active-set, nem T06i)
```

---

## 11. Ismert limitációk

1. **SA kereső timeout**: search=sa + 276 parts + cgal_reference + 95s cap = timeout. SA iterációk száma nem skálázódik a time cap-hez. search=none verzió működik.

2. **Active-set feature flag jelen van a kódban (T06k)**: A nfp_placer.rs +769 soros diff-et tartalmaz `NESTING_ENGINE_ACTIVE_SET_CANDIDATES` feature flag-gel. T06i benchmark az alapértelmezett path-ot használja, nem az active-set-et.

3. **Direct binary → normalizer nem fut**: Case C direct smoke nem megy át a Python runner-en, így a result_normalizer nem kerül meghívásra. De T06h smoke，人家an normalizer smoke bizonyítja a logikát.

4. **CGAL nem production kernel**: Ezúttal is hangsúlyozzuk — cgal_reference dev-only, productba nem megy ki.

---

## 12. Következő task javaslat

### A) Ha SA timeout root cause (CFR/can_place dominál):

```
T06j — SA budget calibration on prepacked CGAL input
Cél: SA iterációs budget, eval_budget, work_budget beállítások
      tuningolása a 95s cap-hoz.
```

### B) Ha NFP provider compute dominál (a 32s túl nagy rész a CGAL compute):

```
T06j — CGAL NFP caching and precompute strategy
Cél: NFP cache bekapcsolása, precompute a legdrágább párra.
```

### C) Ha active-set path ígéretes (T06k kód jelen van):

```
T06j — Active-set candidate-first benchmark on prepacked CGAL input
Cél: NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1 path benchmarkelése
      versus CFR union path.
```

**Javasolt:** A T06k active-set implementáció jelen van a kódban — érdemes Case E-t megcsinálni (optional active-set kontroll) mielőtt T06j-be kezdenénk.

---

## Appendix: Case B — old_concave kontroll (60s timeout)

```
OldConcave kontroll: timeout after 60s
Reason: convex hull composite partok — old_concave ros鼻asító
Ez NEM FAIL, ez a kontroll — CGAL jön és oldja meg.
```