# Engine v2 NFP RC — T09 NFP Cache Geometry Hash

## Cél
Az NFP cache kibővítése az új kernel azonosítóval és a geometry hash pontosítása
a solver geometry szinthez. A cache hit-ek kernel-specifikusak legyenek: a
ConcaveDefault és ReducedConvolutionV1 kernel által számított NFP-k ne kerüljenek
egymás cache entry-jeibe.

## Miért szükséges
A jelenlegi `NfpCacheKey { shape_id_a, shape_id_b, rotation_steps_b }` nem különbözteti
meg a kernel típust. Ha a cache kulcsba nem kerül be a kernel azonosító, előfordulhat,
hogy a ConcaveDefault NFP cache entry-t az RC kernel NFP lekérésre kapja vissza —
ez helytelen NFP-t adna a placer-nek. A geometry hash pontosítása a solver geometry
cleanup profile-jét is tartalmazza.

## Érintett valós fájlok

### Módosítandó:
- `rust/nesting_engine/src/nfp/cache.rs` — NfpCacheKey bővítése, constructor hozzáadása

### Létrehozandó:
- `rust/nesting_engine/src/geometry/hash.rs` — solver_geometry_hash

### Módosítandó (minimal):
- `rust/nesting_engine/src/geometry/mod.rs` — `pub mod hash;` hozzáadása
- `rust/nesting_engine/src/placement/nfp_placer.rs` — NfpCacheKey constructor call frissítése

### Olvasandó (kontextus):
- `rust/nesting_engine/src/nfp/cache.rs` — meglévő NfpCacheKey, shape_id(), MAX_ENTRIES=10_000
- `rust/nesting_engine/src/nfp/mod.rs` — NfpKernelPolicy (T08 output)
- `rust/nesting_engine/src/placement/nfp_placer.rs` — ahol NfpCacheKey-t konstruálják

## Nem célok / scope határok
- A meglévő `shape_id()` függvény nem változik (backward compat).
- A meglévő `MAX_ENTRIES = 10_000` nem változik.
- Nem kell az eviction policy-t megváltoztatni.
- Nem kell a Python kódot módosítani.

## Részletes implementációs lépések

### 1. `NfpKernelId` enum — `rust/nesting_engine/src/nfp/cache.rs`

```rust
/// NFP cache kulcs kernel azonosítója
/// Különböző kernelek által számított NFP-k külön cache entry-kbe kerülnek
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NfpKernelId {
    ConcaveDefault = 0,
    ReducedConvolutionV1 = 1,
}

impl From<NfpKernelPolicy> for NfpKernelId {
    fn from(policy: NfpKernelPolicy) -> Self {
        match policy {
            NfpKernelPolicy::ConcaveDefault => NfpKernelId::ConcaveDefault,
            NfpKernelPolicy::ReducedConvolutionV1 => NfpKernelId::ReducedConvolutionV1,
        }
    }
}
```

### 2. Bővített `NfpCacheKey` — `rust/nesting_engine/src/nfp/cache.rs`

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
    // ÚJ MEZŐK (T09):
    /// NFP kernel azonosító — különböző kernelek külön cache entry-k
    pub nfp_kernel: NfpKernelId,
    /// Cleanup profil azonosítója (0 = default)
    pub cleanup_profile: u8,
    /// Spacing internal unitokban — különböző spacing-ek külön cache entry-k
    pub spacing_units: i64,
}
```

**Constructor metódusok:**
```rust
impl NfpCacheKey {
    /// Backward compatible constructor a ConcaveDefault kernelhez
    /// Ez az összes meglévő hívás helyettesítője
    pub fn concave_default(
        shape_id_a: u64,
        shape_id_b: u64,
        rotation_steps_b: i16,
        spacing_units: i64,
    ) -> Self {
        Self {
            shape_id_a,
            shape_id_b,
            rotation_steps_b,
            nfp_kernel: NfpKernelId::ConcaveDefault,
            cleanup_profile: 0,
            spacing_units,
        }
    }

    /// Constructor az RC kernelhez
    pub fn reduced_convolution_v1(
        shape_id_a: u64,
        shape_id_b: u64,
        rotation_steps_b: i16,
        cleanup_profile: u8,
        spacing_units: i64,
    ) -> Self {
        Self {
            shape_id_a,
            shape_id_b,
            rotation_steps_b,
            nfp_kernel: NfpKernelId::ReducedConvolutionV1,
            cleanup_profile,
            spacing_units,
        }
    }
}
```

**Fontos:** A struct literal `NfpCacheKey { ... }` közvetlenül való használata
fordítási hibát ad (új mezők). A `nfp_placer.rs`-ben az összes struct literal konstruálást
a `NfpCacheKey::concave_default(...)` constructor hívásra kell cserélni.

### 3. `CacheStats` bővítés — `rust/nesting_engine/src/nfp/cache.rs`

```rust
#[derive(Debug, Clone, Default)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
    /// Hányszor volt clear_all() (eviction round)
    pub evictions: u64,
    /// Kernel-bontású hit count
    pub hits_by_kernel: std::collections::HashMap<String, u64>,
}
```

### 4. `rust/nesting_engine/src/geometry/hash.rs` implementálása

```rust
/// Solver geometry hash — a cleanup profile is belekerül a hashbe
/// Ez tudatosabb hash mint shape_id(), mert cleanup-specifikus
pub fn solver_geometry_hash(poly: &Polygon64, cleanup_profile: u8) -> u64

/// A meglévő shape_id() változatlan marad (backward compat)
/// Ezért ez egy KÜLÖNBÖZŐ függvény, nem shape_id() replacement
```

Implementáció: FNV-1a vagy más determinisztikus hash.
- poly outer ring koordinátái (összes Point64.x, Point64.y)
- cleanup_profile byte
- Determinisztikus — azonos geometria + azonos cleanup_profile = azonos hash

### 5. `nfp_placer.rs` frissítése

Minden `NfpCacheKey { shape_id_a: ..., shape_id_b: ..., rotation_steps_b: ... }` struct literal
cseréje:
```rust
NfpCacheKey::concave_default(shape_id_a, shape_id_b, rotation_steps_b, spacing_units)
```

Ha az `NfpPlacerConfig` nem tartalmaz spacing_units mezőt, 0-t kell használni mint default.

### 6. Validálás

```bash
# Compile (az összes meglévő NfpCacheKey struct literal cserélve)
cargo check -p nesting_engine

# Cache unit tesztek
cargo test -p nesting_engine -- cache

# Cache hit teszt: azonos pár → hit
cargo test -p nesting_engine -- cache_hit_same_pair
```

## Adatmodell / contract változások

### NfpCacheKey (breaking struct literal change → constructor-ra migrálva):
- Régi: `NfpCacheKey { shape_id_a, shape_id_b, rotation_steps_b }`
- Új: `NfpCacheKey::concave_default(shape_id_a, shape_id_b, rotation_steps_b, spacing_units)`

### Invariáns:
- Azonos kernel, azonos geometry, azonos rotation → azonos cache key → hit
- Különböző kernel, egyébként azonos → különböző cache key → miss (helyes viselkedés)

## Backward compatibility
`NfpKernelId::ConcaveDefault = 0` biztosítja, hogy a meglévő `concave_default()`
constructor által generált kulcsok a régi viselkedést követik.
A `shape_id()` függvény változatlan.

## Hibakódok / diagnosztikák
- `CacheStats.evictions > 0` — cache clear_all() volt (várható nagy job esetén)
- `hits_by_kernel["concave_default"] > 0` — ConcaveDefault hit
- `hits_by_kernel["reduced_convolution_v1"] > 0` — RC hit

## Tesztelési terv
```bash
# 1. Compile
cargo check -p nesting_engine

# 2. Unit tesztek
cargo test -p nesting_engine -- nfp::cache

# 3. Backward compat: ConcaveDefault hit
cargo test -p nesting_engine -- cache_concave_default_hit

# 4. Kernel separation: RC key ≠ ConcaveDefault key
cargo test -p nesting_engine -- cache_kernel_separation

# 5. solver_geometry_hash determinisztikus
cargo test -p nesting_engine -- geometry::hash

# 6. Nincs struct literal NfpCacheKey konstruálás (csak constructor hívások)
grep -rn "NfpCacheKey {" rust/nesting_engine/src/ && echo "WARN: struct literal found" || echo "OK: no struct literals"
```

## Elfogadási feltételek
- [ ] `cargo test -p nesting_engine` hibátlan (beleértve cache teszteket)
- [ ] `cargo check -p nesting_engine` hibátlan
- [ ] Azonos pár + azonos kernel → cache hit
- [ ] Különböző kernel (ConcaveDefault vs RC) → különböző cache key (miss)
- [ ] `CacheStats` tartalmazza `evictions` és `hits_by_kernel` mezőket
- [ ] `solver_geometry_hash` determinisztikus (azonos input = azonos output)
- [ ] Nincs `NfpCacheKey { ... }` struct literal (csak constructor hívások)
- [ ] A meglévő `shape_id()` változatlan

## Rollback / safety notes
A `NfpCacheKey` struct extension törhetne meglévő kódot (struct literal),
de a `nfp_placer.rs`-ben az összes hívás constructor-ra van cserélve.
Ha probléma van: a new mezőkkel együtt a `nfp_placer.rs` patch visszavonható.

## Dependency
- T08: NfpKernelPolicy (az enum-ból jön az NfpKernelId)
- T05: ReducedConvolutionV1 enum értéke
- T10: cache hit rate mérése a benchmark-ban
