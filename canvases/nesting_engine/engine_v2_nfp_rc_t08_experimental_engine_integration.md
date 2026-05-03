# Engine v2 NFP RC — T08 Experimental Engine Integration

## Cél
Az új RC NFP-kernelt választható experimental módként bekötni az Engine v2-be.
A meglévő `ConcaveDefault` kernel az alapértelmezett és érintetlen marad.
A `ReducedConvolutionV1` kernel explicit opt-in, `quality_reduced_convolution_experimental`
quality profileon keresztül. Silent BLF fallback tilos.

## Miért szükséges
Anélkül, hogy az RC kernel bekerül a placer-be, nem lehet valós nesting futtatni rajta.
Az integration task biztosítja, hogy az új kernel production-safe módon legyen elérhető:
explicit kérés szükséges, a meglévő pipeline nem változik, a fallback explicit.

## Érintett valós fájlok

### Módosítandó (backward compatible):
- `rust/nesting_engine/src/nfp/mod.rs` — `NfpKernelPolicy` enum hozzáadása
- `rust/nesting_engine/src/placement/nfp_placer.rs` — kernel policy paraméter és stats bővítés
- `vrs_nesting/config/nesting_quality_profiles.py` — `quality_reduced_convolution_experimental` profil
- `frontend/src/lib/types.ts` — `QualityProfileName` literal union bővítése
- `frontend/src/pages/NewRunPage.tsx` — experimental profil megjelenítése (disabled/experimental badge)

### Olvasandó (kontextus):
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` — T05 output
- `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` — T06 output
- `rust/nesting_engine/src/nfp/nfp_validation.rs` — T06 output
- `vrs_nesting/config/nesting_quality_profiles.py` — meglévő profilok (VALID_PLACERS, etc.)
- `frontend/src/lib/types.ts` — meglévő TypeScript típusok

## Nem célok / scope határok
- Tilos a `ConcaveDefault` kernel-t módosítani vagy törölni.
- Tilos a meglévő quality profilokat módosítani.
- Tilos silent BLF fallback az RC kernel sikertelenségénél.
- Nem kell a teljes SA search módot módosítani.
- Nem kell a cavity_prepack_v2-t módosítani.

## Részletes implementációs lépések

### 1. `NfpKernelPolicy` enum — `rust/nesting_engine/src/nfp/mod.rs`

```rust
/// NFP számítási kernel választó — explicit opt-in az RC kernelhez
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum NfpKernelPolicy {
    /// Meglévő concave.rs orbit-alapú algoritmus (default, érintetlen)
    #[default]
    ConcaveDefault,
    /// T05 reduced convolution prototype — EXPERIMENTAL
    ReducedConvolutionV1,
}

impl NfpKernelPolicy {
    pub fn as_str(&self) -> &'static str {
        match self {
            NfpKernelPolicy::ConcaveDefault => "concave_default",
            NfpKernelPolicy::ReducedConvolutionV1 => "reduced_convolution_v1",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "concave_default" => Some(NfpKernelPolicy::ConcaveDefault),
            "reduced_convolution_v1" => Some(NfpKernelPolicy::ReducedConvolutionV1),
            _ => None,
        }
    }
}
```

### 2. `NfpPlacerStatsV1` bővítés — `rust/nesting_engine/src/placement/nfp_placer.rs`

Hozzáadandó mezők (a meglévők MELLÉ, nem helyett):
```rust
/// Ténylegesen használt NFP kernel
pub actual_nfp_kernel: String,
/// Hány alkalommal volt az RC kernel nem támogatott (explicit unsupported)
pub nfp_kernel_unsupported_count: u64,
/// Hány alkalommal kellett visszaesni (de ez explicit fallback, nem silent)
pub nfp_kernel_explicit_fallback_count: u64,
```

A placer bővítése: ha `NfpKernelPolicy::ReducedConvolutionV1` van kérve, de az NFP
`RcNfpError::NotImplemented`-et ad:
- `nfp_kernel_unsupported_count++`
- A placement státusza `degraded`
- **Tilos** BLF-re silent módon visszaesni

### 3. Quality profil — `vrs_nesting/config/nesting_quality_profiles.py`

A meglévő `_QUALITY_PROFILE_REGISTRY` dict-be hozzáadandó:
```python
"quality_reduced_convolution_experimental": {
    "placer": "nfp",
    "search": "sa",
    "part_in_part": "prepack",
    "compaction": "slide",
    "nfp_kernel": "reduced_convolution_v1",  # új mező
    "experimental": True,  # explicit jelölés
    "description": "Experimental: Reduced Convolution NFP kernel (T05 prototype)",
},
```

A `normalize_quality_profile_name` függvény nem változik (backward compat).
Ha a `nfp_kernel` mező nem ismert: explicit `ValueError` (nem silent ignore).

### 4. TypeScript típus — `frontend/src/lib/types.ts`

A `QualityProfileName` literal unionba:
```typescript
| "quality_reduced_convolution_experimental"
```
(A pontos struktúra a meglévő típusok alapján — olvasd el a fájlt.)

### 5. Frontend megjelenítés — `frontend/src/pages/NewRunPage.tsx`

Az experimental profil megjelenítésekor:
- Badge: "EXPERIMENTAL" (piros vagy sárga)
- Tooltip: "RC NFP kernel — kísérleti, nem production"
- Disabled checkbox opció elfogadható (de ne töröljük ki a profilt)
A meglévő profilok UI-ja változatlan.

### 6. Silent fallback teszt

```bash
# Ellenőrizd, hogy ha RC kernel NotImplemented: a response degraded státuszt tartalmaz,
# nem silent BLF sikerességet
python3 -c "
# Szimulált teszt: quality_reduced_convolution_experimental profil betöltése
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
profile = _QUALITY_PROFILE_REGISTRY.get('quality_reduced_convolution_experimental')
assert profile is not None, 'Profil nem található'
assert profile.get('nfp_kernel') == 'reduced_convolution_v1', 'nfp_kernel mező hiányzik'
assert profile.get('experimental') == True, 'experimental jelölés hiányzik'
print('quality profile OK')
"
```

## Adatmodell / contract változások

### Rust:
- `NfpKernelPolicy` enum — új típus, additive
- `NfpPlacerStatsV1` — 3 új mező, additive

### Python:
- `_QUALITY_PROFILE_REGISTRY` — 1 új entry, additive
- `nfp_kernel` mező — új opcionális mező a profil dict-ben

### TypeScript:
- `QualityProfileName` — 1 új literal, additive

## Backward compatibility

**Rust:** `NfpKernelPolicy::default()` = `ConcaveDefault` — a meglévő kód nem változik.
A `NfpPlacerStatsV1` struct extension additív.

**Python:** A meglévő quality profilok érintetlenek. A `normalize_quality_profile_name`
nem változik.

**TypeScript:** Literal union extension backward compat (strict mode: új literal hozzáadása
nem törhet meglévő type guard-ot ha exhaustive check nincs).

## Hibakódok / diagnosztikák
- `nfp_kernel_unsupported_count > 0` — a placer stats-ban explicit jelzi az RC kernel problémát
- `nfp_kernel_explicit_fallback_count > 0` — explicit fallback (nem silent)
- `actual_nfp_kernel: "concave_default"` — akkor is ha RC volt kérve de fallback történt
- Python: `ValueError` ha ismeretlen `nfp_kernel` értéket kap

## Tesztelési terv
```bash
# 1. Rust compile
cargo check -p nesting_engine

# 2. TypeScript compile
cd frontend && npx tsc --noEmit

# 3. Python quality profile
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
assert 'quality_reduced_convolution_experimental' in _QUALITY_PROFILE_REGISTRY
p = _QUALITY_PROFILE_REGISTRY['quality_reduced_convolution_experimental']
assert p['placer'] == 'nfp'
assert p['nfp_kernel'] == 'reduced_convolution_v1'
assert p['experimental'] == True
print('quality profile OK')
"

# 4. Meglévő profilok érintetlenek
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
existing = ['quality_draft', 'quality_standard', 'quality_high']
for p in existing:
    if p in _QUALITY_PROFILE_REGISTRY:
        print(f'{p}: OK')
"

# 5. runtime_policy_for_quality_profile meghívható
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
p = _QUALITY_PROFILE_REGISTRY['quality_reduced_convolution_experimental']
print('Profile returned:', p)
"

# 6. Silent fallback nem történt (manuális ellenőrzés)
# cargo test -p nesting_engine -- nfp_kernel_policy
```

## Elfogadási feltételek
- [ ] `cargo check -p nesting_engine` hibátlan
- [ ] `cd frontend && npx tsc --noEmit` hibátlan
- [ ] `quality_reduced_convolution_experimental` profil a registry-ben, nfp_kernel mező megvan
- [ ] `NfpKernelPolicy::default() == ConcaveDefault` (meglévő pipeline nem változik)
- [ ] `NfpPlacerStatsV1` tartalmazza az új mezőket
- [ ] Silent BLF fallback tilos — `nfp_kernel_unsupported_count` jelzi, ha az RC kernel nem fut
- [ ] Meglévő quality profilok mind működnek

## Rollback / safety notes
Az összes változás additive. A meglévő `ConcaveDefault` kernel érintetlen.
Ha az RC kernel problémás: `NfpKernelPolicy::ConcaveDefault`-ra állítva visszaáll.
A Python profil törlése visszaállítja a production állapotot.

## Dependency
- T05: reduced_convolution.rs (a kernel maga)
- T06: minkowski_cleanup.rs (cleanup pipeline)
- T07: correctness_validator — ha FAIL_FALSE_POSITIVE: T08 NEM integrálhat production-ba
- T09: cache kulcs bővítése (NfpKernelId)
- T10: a teljes integration tesztelése
