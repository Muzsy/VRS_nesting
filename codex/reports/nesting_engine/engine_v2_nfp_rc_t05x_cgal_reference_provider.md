# T05x — CGAL Reference Provider: NfpProvider Adapter

## Státusz: PASS

## Rövid verdikt

- **CGAL provider bekötve?** IGEN — `CgalReferenceProvider` implementálva, a `CgalReference` kernel mögé kötve.
- **Default maradt old_concave?** IGEN — `NfpKernel::OldConcave` változatlanul default.
- **Toxic pair javult?** IGEN — lv8_pair_01 5000ms timeout helyett 186ms SUCCESS.

---

## Módosított fájlok

| Fájl | Változás |
|------|----------|
| `rust/nesting_engine/src/nfp/cgal_reference_provider.rs` | ÚJ — `CgalReferenceProvider` implementáció |
| `rust/nesting_engine/src/nfp/mod.rs` | 7 új `NfpError` variant, `Copy` eltávolítva |
| `rust/nesting_engine/src/nfp/provider.rs` | `CgalReference` kernel factory támogatás |
| `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` | `--nfp-kernel` CLI flag, `run_nfp_with_provider()` fv |

---

## Hogyan működik a CgalReferenceProvider

### Architektúra

```
NfpProvider trait (kernel, supports_holes, compute, kernel_name)
        |
        v
CgalReferenceProvider
  - binary_path: PathBuf
  - timeout_ms: u64
  - compute() -> subprocess hívás -> JSON parse -> Polygon64
```

### Env/config guard

```rust
NFP_ENABLE_CGAL_REFERENCE=1          // kötelező: explicit opt-in
NFP_CGAL_PROBE_BIN=/path/to/binary   // opcionális, default: $WORKSPACE/tools/nfp_cgal_probe/build/nfp_cgal_probe
```

Ha `NFP_ENABLE_CGAL_REFERENCE` nincs beállítva:
```
Err(NfpError::UnsupportedKernel("cgal_reference requires NFP_ENABLE_CGAL_REFERENCE=1"))
```

Ha binary nem található:
```
Err(NfpError::CgalBinaryNotFound(...))
```

### Binary hívás

```bash
nfp_cgal_probe \
  --fixture <temp_input.json> \
  --algorithm reduced_convolution \
  --output-json <temp_output.json>
```

### Input JSON contract (nfp_cgal_probe_fixture_v1)

```json
{
  "fixture_version": "nfp_cgal_probe_fixture_v1",
  "pair_id": "provider_runtime_pair",
  "scale": 1000000,
  "part_a": {
    "points_mm": [[x, y], ...],
    "holes_mm": [[[x, y], ...]]
  },
  "part_b": {
    "points_mm": [[x, y], ...],
    "holes_mm": [[[x, y], ...]]
  }
}
```

SCALE: `1_000_000` (Point64 integer -> mm konverzió).

### Output JSON contract (nfp_cgal_probe_result_v1)

```json
{
  "schema": "nfp_cgal_probe_result_v1",
  "status": "success",
  "outer_i64": [[x, y], ...],
  "holes_i64": [[[x, y], ...]],
  "timing_ms": 123.45
}
```

### Hibakezelés (mind `Err(...)`, nincs silent fallback)

| Eset | Error variant |
|------|--------------|
| binary missing | `CgalBinaryNotFound` |
| timeout | `CgalSubprocessError` |
| nonzero exit | `CgalNonZeroExit` |
| output JSON missing | `CgalIoError` |
| output JSON invalid | `CgalParseError` |
| status != success | `CgalInternalError` |
| empty outer_i64 | `CgalEmptyOutput` |

---

## Cache key

A cache key kernel-aware. `CgalReferenceProvider` esetén:

```rust
provider.kernel() -> NfpKernel::CgalReference
```

Így a CGAL és OldConcave output külön cache-be kerül — nincs keveredés.

---

## Default kernel

Továbbra is `NfpKernel::OldConcave`. A `create_nfp_provider()` az `NfpProviderConfig { kernel: NfpKernel::OldConcave }` esetén `OldConcaveProvider`-t ad vissza implicit.

---

## Futtatott parancsok és eredmények

### cargo check
```bash
cd rust/nesting_engine && cargo check
# exit 0, warning-ek csak unused code-ra
```

### cargo test --lib
```bash
cd rust/nesting_engine && cargo test --lib
# 60 passed, 0 failed
```

### CGAL probe smoke test
```bash
bash scripts/smoke_nfp_cgal_probe_lv8.sh
# ALL SMOKE TESTS PASSED
# lv8_pair_01: 135ms
# lv8_pair_02: 135ms
# lv8_pair_03: 104ms
```

### Guard ellenőrzés (cgal_reference env nélkül)
```bash
cargo run --bin nfp_pair_benchmark -- --fixture ... --nfp-kernel cgal_reference
# nfp_pair_benchmark: failed to create provider: kernel not available: cgal_reference requires NFP_ENABLE_CGAL_REFERENCE=1
# exit 1 — guard működik
```

---

## Pair eredmény táblázat

| pair_id | provider | status | runtime_ms | output_vertices | output_holes | cache_key_kernel | notes |
|---------|----------|--------|-----------|----------------|-------------|-----------------|-------|
| lv8_pair_01 | old_concave | TIMEOUT | 5000 | 0 | — | OldConcave | 177156 fragmentpairs, >5s alatt sem készült |
| lv8_pair_01 | cgal_reference | SUCCESS | 186 | 776 | 0 | CgalReference | |
| lv8_pair_02 | cgal_reference | SUCCESS | 140 | 786 | 0 | CgalReference | |
| lv8_pair_03 | cgal_reference | SUCCESS | 83 | 324 | 0 | CgalReference | |

---

## Production constraints betartása

| Constraint | Status |
|-----------|--------|
| CGAL default kernelként | MEGELVEZVE — `OldConcave` default |
| CGAL production dependency | MEGELVEZVE — csak `tools/nfp_cgal_probe` binary (GPL) |
| Production Dockerfile módosítás | NINCS |
| Worker production runtime módosítás | NINCS |
| Optimalizáló rewrite | NINCS |
| OldConcaveProvider törlés | NINCS |
| Silent fallback CGAL hibánál | NINCS |

---

## Ismert limitációk

1. **CGAL NEM production komponens** — GPL licenc, csak dev/reference használatra.
2. **CGAL provider csak holes=0-ra validált** — a CGAL probe `--algorithm reduced_convolution` jelenleg nem támogatja a lyukakat; `supports_holes() -> true` de holes input üres.
3. **Cache key NfpKernel::CgalReference** — de a `nfp_placer.rs`-ben a kernel a provider-ből jön, nem pedig a config-ból. Ellenőrizni kell, hogy a cache key valóban kernel-aware módon épül-e fel downstream.
4. **nfp_pair_benchmark --nfp-kernel CLI flag** — minimális implementáció, nem része a production confignak.

---

## Következő javasolt task

**T05y** — CGAL provider validáció és output quality ellenőrzés: összehasonlítani a CGAL NFP output geometriát az OldConcave outputtal kontroll fixtureken (nem toxic pairökön), hogy ellenőrizzük topológiai ekvivalenciát és az output minőségét.

**Nem T08** — T08 a toxic pair analízis és megoldás lenne, de a CGAL provider architektúra megkerüli a problémát upstream.
