# T05w — NFP Provider Selection + Cache Key Safety Pilot

## Státusz: PASS

## Összefoglaló

T05w sikeresen lezárult. A provider selection modell explicit, a cache key kernel-aware, és a jövőbeli CGAL/RC provider-ek nem keverhetők az `old_concave` cache-sel. Az optimalizáló lánc (greedy + SA + multi-sheet) érintetlen maradt.

---

## Módosított fájlok

| Fájl | Változás |
|------|----------|
| `rust/nesting_engine/src/nfp/provider.rs` | Teljes átírás: `NfpKernel` bővítve 3 variantára, `NfpProviderConfig`, `create_nfp_provider` factory, `OldConcaveProvider` |
| `rust/nesting_engine/src/nfp/mod.rs` | `NfpError::UnsupportedKernel(&'static str)` variant hozzáadva |
| `rust/nesting_engine/src/nfp/cache.rs` | `NfpCacheKey.nfp_kernel: NfpKernel` mező hozzáadva, tesztek frissítve |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | `NfpKernel` import, cache key konstrukciók frissítve `nfp_kernel: NfpKernel::OldConcave`-val |
| `rust/nesting_engine/src/bin/nfp_pair_benchmark.rs` | `NfpError::UnsupportedKernel(name)` match ág hozzáadva |

---

## Provider Selection Modell

### NfpKernel Enum (3 variant)

```rust
pub enum NfpKernel {
    OldConcave,                          // ✓ implementálva
    ReducedConvolutionExperimental,       // ✗ unsupported — explicit error
    CgalReference,                        // ✗ unsupported — explicit error
}
```

### NfpProviderConfig

```rust
pub struct NfpProviderConfig {
    pub kernel: NfpKernel,
}
impl Default for NfpProviderConfig {
    fn default() -> Self {
        Self { kernel: NfpKernel::OldConcave }
    }
}
```

### create_nfp_provider Factory

```rust
pub fn create_nfp_provider(config: &NfpProviderConfig) -> Result<Box<dyn NfpProvider>, NfpError>
```

| Config kernel | Eredmény |
|---|---|
| `OldConcave` | `Ok(Box::new(OldConcaveProvider::new()))` |
| `ReducedConvolutionExperimental` | `Err(NfpError::UnsupportedKernel("reduced_convolution_experimental is not wired in T05w"))` |
| `CgalReference` | `Err(NfpError::UnsupportedKernel("cgal_reference is not wired in T05w"))` |

---

## Cache Key Változás

### Előtte

```rust
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
}
```

### Utána

```rust
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
    /// T05w: mindig NfpKernel::OldConcave.
    /// Jövőbeli provider-ek a saját kernel variant-jukat használják.
    pub nfp_kernel: NfpKernel,
}
```

### Miért fontos

Ha később egy CGAL vagy RC provider ugyanarra a polygon párra számol NFP-t, a cache key különbözni fog (`NfpKernel::CgalReference` vs `NfpKernel::OldConcave`), így a két kernel cache bejegyzései nem alias-olnak. Ez a T05w pipeline szeparáció előfeltétele.

---

## Default Kernel

Továbbra is `NfpKernel::OldConcave`. A `NfpProviderConfig::default()` mindent `OldConcave`-ra állít.

---

## Optimalizáló Változás

Nincs. A greedy / SA / multi-sheet / slide compaction stratégia nem módosult.

---

## Futtatott parancsok és eredmények

```
cargo check        → PASS  (0 error, 28 pre-existing warning)
cargo test --lib   → 59/60 PASS, 1 FAIL (pre-existing CFR: cfr_sort_key_precompute_hash_called_once_per_component)
benchmark lv8_pair_01 --timeout-ms 5000 --output-json → TIMEOUT (várt, toxic concave, old_concave kernel)
```

---

## Ismert Limitációk

1. **Pre-existing CFR tesztfail** — `cfr.rs:650`: 8 hívást talál, 6-ot vár. Nem T05w regresszió.
2. **Cache key backward compatibility** — A `nfp_kernel` mező hozzáadása után a meglévő cache entries (régi 3-mezős key) nem kompatibilisek. Ez nem probléma T05w scope-ban (T05v tesztek is új cache-t használnak).
3. **Nincs CLI/profile wiring** — A `NfpProviderConfig` létezik, de a CLI `--nfp-kernel` flag nincs bekötve. A teljes profile wiring külön task (T05w2/T05x előfeltétel).
4. **Factory nem publikus a lib API-ban** — A `create_nfp_provider` a `provider.rs`-ban van, nem a `mod.rs`-ban exportálva. Ez szándékos: a jelenlegi binary call graph-ot nem kell módosítani.

---

## Következő ajánlott task

**T06** vagy **T07** (külön jóváhagyással):
- T06: Toxic concave NFP timeout kezelése bounded timeout + fallback-gal
- T07: CGAL reference NFP probe bekötése `NfpProvider` trait-en keresztül
- T05w2: CLI `--nfp-kernel` flag és profile config wiring

**Nem indulok T08-ba külön jóváhagyás nélkül.**
