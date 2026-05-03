# Engine v2 NFP RC T09 — NFP Cache Geometry Hash
TASK_SLUG: engine_v2_nfp_rc_t09_nfp_cache_geometry_hash

## Szerep
Senior Rust fejlesztő agent vagy. Az NFP cache-t bővíted kernel azonosítóval.
A struktúra extension migrációt gondosan kell elvégezni — minden struct literal hívást
constructor hívásra kell cserélni.

## Cél
NfpKernelId, bővített NfpCacheKey, constructor metódusok, CacheStats bővítés,
geometry/hash.rs, nfp_placer.rs migráció. cargo test -p nesting_engine hibátlan.

## Előfeltétel ellenőrzés
```bash
ls rust/nesting_engine/src/nfp/cache.rs || echo "STOP: cache.rs szükséges"
# T08 NfpKernelPolicy megvan
grep -n "NfpKernelPolicy" rust/nesting_engine/src/nfp/mod.rs || echo "STOP: T08 szükséges"
# Jelenlegi NfpCacheKey struct
grep -n "pub struct NfpCacheKey\|shape_id_a\|shape_id_b\|rotation_steps" rust/nesting_engine/src/nfp/cache.rs
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t09_nfp_cache_geometry_hash.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t09_nfp_cache_geometry_hash.yaml`
- `rust/nesting_engine/src/nfp/cache.rs` (TELJES fájl — NfpCacheKey, shape_id, MAX_ENTRIES)
- `rust/nesting_engine/src/placement/nfp_placer.rs` (NfpCacheKey konstruálások helye)

## Engedélyezett módosítás
- `rust/nesting_engine/src/nfp/cache.rs` (bővítés)
- `rust/nesting_engine/src/geometry/hash.rs` (create)
- `rust/nesting_engine/src/geometry/mod.rs` (pub mod hash sor)
- `rust/nesting_engine/src/placement/nfp_placer.rs` (struct literal migráció)

## Szigorú tiltások
- **Tilos `shape_id()` függvényt módosítani.**
- Tilos MAX_ENTRIES értékét megváltoztatni.
- Tilos eviction policy-t megváltoztatni.
- Tilos Python kódot módosítani.

## Végrehajtandó lépések

### Step 1: Meglévő NfpCacheKey és hívóhelyek felmérése
```bash
# NfpCacheKey jelenlegi definíció
grep -n -A 10 "pub struct NfpCacheKey" rust/nesting_engine/src/nfp/cache.rs

# shape_id() függvény
grep -n "pub fn shape_id\|fn shape_id" rust/nesting_engine/src/nfp/cache.rs

# Összes NfpCacheKey struct literal a kódbázisban
grep -rn "NfpCacheKey {" rust/nesting_engine/src/
```

### Step 2: `NfpKernelId` enum és bővített `NfpCacheKey` — `cache.rs`
A canvas spec szerint:
- NfpKernelId (ConcaveDefault=0, ReducedConvolutionV1=1)
- From<NfpKernelPolicy> for NfpKernelId
- NfpCacheKey bővítése: nfp_kernel, cleanup_profile, spacing_units mezők
- `concave_default(shape_id_a, shape_id_b, rotation_steps_b, spacing_units)` constructor
- `reduced_convolution_v1(shape_id_a, shape_id_b, rotation_steps_b, cleanup_profile, spacing_units)` constructor

### Step 3: CacheStats bővítése — `cache.rs`
```rust
pub evictions: u64,
pub hits_by_kernel: std::collections::HashMap<String, u64>,
```

### Step 4: `rust/nesting_engine/src/geometry/hash.rs` implementálása
- `solver_geometry_hash(poly: &Polygon64, cleanup_profile: u8) -> u64`
- Determinisztikus hash (FNV-1a vagy hasonló)
- cleanup_profile byte bekerül a hashbe

### Step 5: geometry/mod.rs frissítése
```rust
pub mod hash;
```

### Step 6: nfp_placer.rs struct literal migráció
Minden `NfpCacheKey { shape_id_a: ..., shape_id_b: ..., rotation_steps_b: ... }` cseréje:
```rust
NfpCacheKey::concave_default(shape_id_a, shape_id_b, rotation_steps_b, 0)
```
(spacing_units=0 ha az info nem elérhető)

### Step 7: Unit tesztek cache kernel separation-re
```rust
#[test]
fn test_cache_kernel_separation() {
    let key_a = NfpCacheKey::concave_default(1, 2, 0, 0);
    let key_b = NfpCacheKey::reduced_convolution_v1(1, 2, 0, 0, 0);
    assert_ne!(key_a, key_b, "Different kernels should have different cache keys");
}
```

### Step 8: Kompilálás és tesztelés
```bash
cargo check -p nesting_engine 2>&1 | tail -10

cargo test -p nesting_engine 2>&1 | tail -20

# Nincs struct literal
grep -rn "NfpCacheKey {" rust/nesting_engine/src/ && echo "WARN: struct literal found" || echo "OK: no struct literals"

# solver_geometry_hash determinisztikus
cargo test -p nesting_engine -- geometry::hash 2>&1 | tail -5

# shape_id() változatlan
git diff HEAD -- rust/nesting_engine/src/nfp/cache.rs | grep "^-.*fn shape_id\|^+.*fn shape_id"
```

### Step 9: Report és checklist

## Tesztparancsok
```bash
cargo check -p nesting_engine
cargo test -p nesting_engine
grep -rn "NfpCacheKey {" rust/nesting_engine/src/ && echo "WARN" || echo "OK"
ls rust/nesting_engine/src/geometry/hash.rs
```

## Ellenőrzési pontok
- [ ] cargo test -p nesting_engine hibátlan
- [ ] azonos pár + azonos kernel → cache hit
- [ ] különböző kernel → különböző cache key (miss)
- [ ] CacheStats evictions és hits_by_kernel megvannak
- [ ] solver_geometry_hash determinisztikus
- [ ] nincs NfpCacheKey struct literal (csak constructor hívások)
- [ ] shape_id() változatlan
