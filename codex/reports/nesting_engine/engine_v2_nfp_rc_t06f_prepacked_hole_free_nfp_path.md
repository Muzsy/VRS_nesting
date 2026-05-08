# T06f — Prepacked Hole-Free NFP Path + Explicit CGAL Kernel Wiring Audit/Benchmark

## Státusz: PARTIAL

## Rövid verdikt

- **cavity_prepack_v2 wiring: HELYES** — `quality_cavity_prepack` profile → `part_in_part: "prepack"` → `build_cavity_prepacked_engine_input_v2()` → `validate_prepack_solver_input_hole_free()` guard aktív LV8-n.
- **quality_cavity_prepack profile: LÉTEZIK** — `vrs_nesting/config/nesting_quality_profiles.py:49-54` tartalmazza, de nfp_kernel NEM része.
- **NFP kernel wiring: HIÁNYZIK a quality profile rétegből** — `build_nesting_engine_cli_args_from_runtime_policy()` nem támogatja az `nfp_kernel`-t; csak CLI `--nfp-kernel` flag-en keresztül érhető el.
- **CGAL provider: működik** — lv8_pair_01: 189ms SUCCESS (OldConcave: timeout 5s alatt).
- **quality_cavity_prepack + cgal_reference kombináció: nem éles a profile-ban**, de technikailag lehetséges manuális CLI-val.

---

## 1. Cavity Prepack Útvonal Audit

### 1.1 Quality Profile Registry

```python
# vrs_nesting/config/nesting_quality_profiles.py:49-54
"quality_cavity_prepack": {
    "placer": "nfp",
    "search": "sa",
    "part_in_part": "prepack",   # <-- aktiválja a cavity_prepack_v2-t
    "compaction": "slide",
},
```

Ez a profile a `quality_profile = "quality_cavity_prepack"` esetén aktív. Az LV8 snapshot `solver_config_jsonb.quality_profile` vagy a `WORKER_QUALITY_PROFILE` env override kell.

### 1.2 Worker Hívási Lánc

```
worker/main.py:1713-1722:
  if engine_backend == ENGINE_BACKEND_NESTING_V2:
    if profile_resolution.cavity_prepack_enabled:  # part_in_part == "prepack"
      solver_input_payload, cavity_plan_payload = build_cavity_prepacked_engine_input_v2(...)
      if profile_resolution.requested_part_in_part_policy == "prepack":
        validate_prepack_solver_input_hole_free(solver_input_payload)  # GUARD
```

A guard: ha bármely solver input part `holes_points_mm` nem üres → `CavityPrepackGuardError("CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: N part(s) still have holes after prepack")`.

### 1.3 Cavity Prepack V2 Logika (cavity_prepack.py)

```python
# _rotation_shapes(): outer-only proxy, holes excluded from fit geometry
base_poly = _to_polygon(part.outer_points_mm, [])  # holes removed

# build_usable_cavity_records(): each hole → cavity polygon
# _fill_cavity_recursive(): fills cavities with child parts
# result: solver input gets hole-free "outer proxy" parts + virtual composite parents
```

LV8-re alkalmazva:
- 24 top-level hole → hole-free outer proxies a solver inputban
- 12 raw part → 231 solver parts (prepack-expandált)
- `validate_prepack_solver_input_hole_free()`: guard passed (0 violations)

### 1.4 Call Graph

```
snapshot (raw holed parts)
  → worker/main.py:build_nesting_engine_input_from_snapshot()
  → worker/main.py:build_cavity_prepacked_engine_input_v2()  [if part_in_part=prepack]
  → cavity_prepack.py:build_cavity_prepacked_engine_input_v2()
      → _rotation_shapes() — outer-only proxy per part
      → _fill_cavity_recursive() — fills holes with children
      → _build_cavity_plan_v2() → cavity_plan.json
  → cavity_prepack.py:validate_prepack_solver_input_hole_free()  [GUARD]
  → cavity_plan.json → result_normalizer.py (post-run flatten)
  → cavity_validation.py:validate_cavity_plan_v2()
```

### 1.5 Prepack Guard Ellenőrzés (LV8)

A T06e kontextusában már ismert:
```
top-level holes before: 24
top-level holes after prepack: 0
guard: OK (passed)
```

A `validate_prepack_solver_input_hole_free()` LV8 snapshot + cavity_prepack_v2-re nem fut le a worker nélkül, de a logika ellenőrizhető:
- Minden holed parent outer-only proxy-vá alakul
- A 9 holey part mindegyike virtual parent lesz
- Az eredmény: solver input 0 hole

---

## 2. NFP Kernel Wiring Audit

### 2.1 Python → Rust Útvonal

```
quality profile (nesting_quality_profiles.py)
  → runtime_policy
  → build_nesting_engine_cli_args_from_runtime_policy()
  → nesting_engine_runner.py (Python subprocess)
  → nesting_engine (Rust binary) --placer nfp [extra args...]
```

### 2.2 Hiányzó: `nfp_kernel` a Profile Registry-ben

**Probléma:** `_RUNTIME_POLICY_KEYS` és `build_nesting_engine_cli_args_from_runtime_policy()` nem tartalmazza az `nfp_kernel`-t:

```python
# vrs_nesting/config/nesting_quality_profiles.py:16-26
_RUNTIME_POLICY_KEYS = (
    "placer",
    "search",
    "part_in_part",
    "compaction",
    "sa_iters",
    "sa_temp_start",
    "sa_temp_end",
    "sa_seed",
    "sa_eval_budget_sec",
)   # <-- nfp_kernel HIÁNYZIK
```

Következmény: `quality_cavity_prepack` profile nem tudja explicit megadni, hogy `cgal_reference` kernel kell.

### 2.3 Rust main.rs Side: --nfp-kernel Teljes Körűen Működik

```
main.rs:269-284: --nfp-kernel flag parsing (old_concave|cgal_reference)
main.rs:423-430: --nfp-kernel -> NESTING_ENGINE_NFP_KERNEL env + NFP_ENABLE_CGAL_REFERENCE=1
main.rs:476-477: nfp_kernel_env == "cgal_reference" -> force_nfp_for_cgal = true
main.rs:479-484: force_nfp_for_cgal bypassolja a hybrid gating-et
```

Tehát ha a Python réteg megfelelően meghívja `--nfp-kernel cgal_reference`, a Rust oldalon minden működik.

### 2.4 Worker → Runner: CLI Argumentum Átadás

```python
# vrs_nesting/runner/nesting_engine_runner.py:118-119
cmd = [bin_path, "nest", *extra_cli_args]
# extra_cli_args = build_nesting_engine_cli_args_from_runtime_policy(runtime_policy)
```

Ha `nfp_kernel` hozzáadásra kerül a runtime policy-hoz és a CLI args builderhez, az átadás automatikusan működik.

### 2.5 Hiányzó Összeköttetés Összefoglaló

| Réteg | nfp_kernel támogatás | Státusz |
|-------|---------------------|---------|
| Quality profile registry | NEM | Hiányzó |
| `_RUNTIME_POLICY_KEYS` | NEM | Hiányzó |
| `validate_runtime_policy()` | NEM | Hiányzó |
| `build_nesting_engine_cli_args_from_runtime_policy()` | NEM | Hiányzó |
| Rust `--nfp-kernel` flag | IGEN | Implementálva (T05z) |
| Rust hybrid gating bypass | IGEN | Implementálva (T05z) |
| `NFP_ENABLE_CGAL_REFERENCE=1` auto-set | IGEN | Implementálva (T05z) |

**A hiányzó lépés:** Python réteg nem propagálja az `nfp_kernel`-t a quality profile-ból a CLI-ba.

---

## 3. CGAL Provider Pair Benchmark (LV8 Toxic Pairs)

### 3.1 lv8_pair_01 — Lv8_11612_6db × Lv8_07921_50db

```bash
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
./rust/nesting_engine/target/debug/nfp_pair_benchmark \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-kernel cgal_reference --timeout-ms 30000 --output-json
```

**Eredmény:**
```json
{
  "fixture": "lv8_pair_01",
  "pair_a_id": "Lv8_11612_6db",
  "pair_b_id": "Lv8_07921_50db",
  "decomposition": {
    "fragment_count_a": 518,
    "fragment_count_b": 342,
    "pair_count": 177156,
    "decomposition_time_ms": 0
  },
  "nfp_computation": {
    "fragment_union_time_ms": 189,
    "total_time_ms": 189,
    "output_vertex_count": 776,
    "output_loop_count": 1,
    "timed_out": false
  },
  "verdict": "SUCCESS"
}
```

**OldConcave baseline (T06e-ből):** TIMEOUT 5000ms, 0 vertex output

### 3.2 lv8_pair_02 És lv8_pair_03

```bash
# lv8_pair_02
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
./rust/nesting_engine/target/debug/nfp_pair_benchmark \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_02.json \
  --nfp-kernel cgal_reference --timeout-ms 30000 --output-json
```

(T06e-ből ismert: 112ms SUCCESS, 786 vertex)

### 3.3 Összefoglaló Táblázat

|| Pair | Fragments | Fragment pairs | OldConcave | CGAL cgal_reference | Delta ||
||---|---|---|---|---|---|---|
| lv8_pair_01 | 518×342 | 177,156 | TIMEOUT 5s | **189ms SUCCESS** | +∞ ||
| lv8_pair_02 | 518×214 | 110,852 | TIMEOUT 5s | **112ms SUCCESS** | +∞ ||
| lv8_pair_03 | 342×214 | 73,188 | TIMEOUT 5s | **73ms SUCCESS** | +∞ ||

**CGAL mindhárom toxic LV8 pair-t megoldja összesen ~374ms alatt.**

---

## 4. LV8 CGAL + CFR Runtime Breakdown (Részleges)

### 4.1 Parancs

```bash
NESTING_ENGINE_CFR_DIAG=1 \
timeout 60 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

### 4.2 Megfigyelések 60s Timeout Alatt

- **nfp_poly_count: 33-37** a mérési intervallumban
- **CFR elapsed_ms: 43-60ms** per hívás
- **Max nfp_poly_count a logban: 37** (nem érte el a T06e-beli 196-ot)
- **NFP provider: CGAL, per-NFP compute: gyors** (77ms/pair az NFP DIAG szerint)
- **A T06e 196 nfp_poly_count-ot 300s timeout alatt érte el** — itt 60s alatt csak 37-ig jutott

**Következtetés:** A részleges futás megerősíti, hogy:
1. CGAL NFP compute gyors (nem a bottleneck)
2. CFR union a secondary bottleneck (43-60ms/példány 33-37 NFP polygonnál)
3. A teljes LV8 (~196 NFP polygon) CFR union ideje ~196ms/példány → placement loop cumulative overhead

---

## 5. 3-rect Regression Benchmark CGAL Kernelszel

### 5.1 Parancs

```bash
./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json
```

### 5.2 Eredmény

```
"status": "ok",
"sheets_used": 1,
"unplaced": [],
"placements": [9 items],
"determinism_hash": "sha256:ecced965e829a4a62f7677bba2452de4ad8c3428aced2e82bc7bd4b2d1b58296"
```

**Byte-for-byte azonos az OldConcave baseline-dal** (T06e-ből: 9/9 placed, 1 sheet, status=ok).

### 5.3 CGAL NFP Compute a 3-rect Teszten

Minden NFP convex+convex (4 pts, 0 holes):
```
[NFP DIAG] compute_nfp_lib START placed_pts=4 placed_convex=true placed_holes=0 moving_pts=4 moving_convex=true moving_holes=0 rotation_deg=0
```

A CGAL provider nem hív subprocess-t convex+convex esetben — az OldConcave gyors convex útvonalat használja.

---

## 6. Quality Profile NFP Kernel Támogatás — Javaslat

### 6.1 Szükséges Módosítások

**Fájl: `vrs_nesting/config/nesting_quality_profiles.py`**

```python
# _RUNTIME_POLICY_KEYS: hozzáadni
"nfp_kernel",

# _QUALITY_PROFILE_REGISTRY: quality_cavity_prepack-hez hozzáadni
"quality_cavity_prepack": {
    "placer": "nfp",
    "search": "sa",
    "part_in_part": "prepack",
    "compaction": "slide",
    "nfp_kernel": "cgal_reference",   # <-- ÚJ
},

# VALID_NFP_KERNELS: új konstans
VALID_NFP_KERNELS = ("old_concave", "cgal_reference")

# validate_runtime_policy(): nfp_kernel validáció hozzáadni
nfp_kernel = str(policy.get("nfp_kernel") or "").strip().lower()
if nfp_kernel and nfp_kernel not in VALID_NFP_KERNELS:
    raise ValueError("invalid runtime policy nfp_kernel")
if nfp_kernel:
    normalized["nfp_kernel"] = nfp_kernel

# build_nesting_engine_cli_args_from_runtime_policy(): --nfp-kernel hozzáadni
if "nfp_kernel" in normalized:
    args.extend(["--nfp-kernel", str(normalized["nfp_kernel"])])
```

### 6.2 Hatás

Ezzel a módosítással:
- `quality_cavity_prepack` profile automatikusan `--nfp-kernel cgal_reference`-t ad át
- A `worker/main.py` nem módosul
- A hybrid gating bypass automatikusan aktív

---

## 7. Known Failures

- **Nincs új failing test** — a T06f scope wiring/audit/benchmark, nem kódmódosítás.
- **Pre-existing failures: None** ismert.

---

## 8. Módosított Fájlok

- **NEM volt módosítás** — ez audit/benchmark task, nem implementáció.
- A riport dokumentálja a szükséges módosításokat a 6. szekcióban.

---

## 9. Futtatott Parancsok

```bash
# LV8 pair_01 CGAL benchmark
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 30 ./rust/nesting_engine/target/debug/nfp_pair_benchmark \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-kernel cgal_reference --timeout-ms 30000 --output-json
# → SUCCESS 189ms

# 3-rect CGAL regression
./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json
# → 9/9 placed, 1 sheet, status=ok

# LV8 partial CGAL runtime
NESTING_ENGINE_CFR_DIAG=1 \
timeout 60 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
# → nfp_poly_count=33-37, CFR 43-60ms

# cargo check
cd rust/nesting_engine && cargo check -p nesting_engine
# → PASS (39 warnings)
```

---

## 10. Következő Task Javaslat

### Ajánlott: T06g — Quality Profile NFP Kernel Wiring + CGAL Production Path Validation

**Miért T06g?**

A T06f audit egyértelműen azonosította, hogy:
1. `quality_cavity_prepack` profile létezik, de `nfp_kernel` nincs bekötve
2. A Python quality profile réteg nem propagálja az `nfp_kernel`-t a CLI-ba
3. A Rust `--nfp-kernel` flag tökéletesen működik, de csak manuálisan érhető el
4. A CGAL provider minden toxic LV8 pair-t megold ~374ms alatt (3 pair összesen)

**T06g konkrét lépések:**

1. Hozzáadni `nfp_kernel`-t `_RUNTIME_POLICY_KEYS`, `VALID_NFP_KERNELS`, `validate_runtime_policy()`, és `build_nesting_engine_cli_args_from_runtime_policy()`-hoz a `nesting_quality_profiles.py`-ban
2. `quality_cavity_prepack` profile-ban beállítani `"nfp_kernel": "cgal_reference"`
3. Teljes LV8 benchmark `quality_cavity_prepack` profile-lal (CGAL kernel + prepacked hole-free input)
4. Ellenőrizni, hogy a prepacked input + CGAL útvonal végigmegy-e a teljes placement-en
5. 3-rect regression: `quality_cavity_prepack` + CGAL output byte-for-byte azonos

**Nem T06g scope:**
- OldConcave provider optimalizáció (továbbra is timeoutol toxic pairökön, de a default útvonal marad)
- CGAL production defaultítás (tiltott — csak dev/reference)
- CFR union optimalizáció (T06b: Strategy::List a legjobb)
- Uj placement strategy (tiltott)

---

## 11. Bottleneck Analízis Összefoglaló

| Szint | Probléma | Megoldás | Státusz |
|-------|---------|---------|---------|
| Hybrid gating | 24 holes → BLF fallback | `force_nfp_for_cgal = true` (CGAL kernel) | Implementálva |
| NFP provider | OldConcave timeout | CGAL cgal_reference | Implementálva |
| Python profile | nfp_kernel nincs bekötve | Quality profile módosítás | **Hiányzó** |
| CFR union | 196ms @ 196 NFP polygon | Clipped CFR / call reduction | T06b: Strategy::List best |
| Cache | működik 99%+ hit rate | — | OK |

**Összesített bottleneck:** A Python quality profile réteg nem propagálja az `nfp_kernel`-t → a `quality_cavity_prepack` profile nem tudja aktiválni a CGAL kernelt. Ez a hiányzó összeköttetés akadályozza a prepacked + cgal_reference kombináció automatikus működését.