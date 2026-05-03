# Engine v2 NFP RC T08 — Experimental Engine Integration
TASK_SLUG: engine_v2_nfp_rc_t08_experimental_engine_integration

## Szerep
Senior full-stack agent vagy. Az RC kernelt integrálod az Engine v2-be választható
experimental módként. ConcaveDefault default marad. Silent BLF fallback tilos.

## Cél
NfpKernelPolicy enum, NfpPlacerStatsV1 bővítés, quality profil, TypeScript literal,
frontend badge. cargo check + tsc --noEmit hibátlanul. Meglévő profilok érintetlenek.

## Előfeltétel ellenőrzés
```bash
ls rust/nesting_engine/src/nfp/reduced_convolution.rs || echo "STOP: T05 szükséges"
ls rust/nesting_engine/src/nfp/minkowski_cleanup.rs || echo "STOP: T06 szükséges"
# T07 correctness verdict
ls rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs || echo "WARN: T07 szükséges"
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t08_experimental_engine_integration.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t08_experimental_engine_integration.yaml`
- `rust/nesting_engine/src/placement/nfp_placer.rs` (NfpPlacerStatsV1 JELENLEGI mezők)
- `vrs_nesting/config/nesting_quality_profiles.py` (MEGLÉVŐ profilok, VALID_PLACERS)
- `frontend/src/lib/types.ts` (QualityProfileName jelenlegi definíció)
- `frontend/src/pages/NewRunPage.tsx` (profil megjelenítési logika)

## Engedélyezett módosítás
- `rust/nesting_engine/src/nfp/mod.rs` (NfpKernelPolicy enum)
- `rust/nesting_engine/src/placement/nfp_placer.rs` (3 új mező)
- `vrs_nesting/config/nesting_quality_profiles.py` (1 új profil)
- `frontend/src/lib/types.ts` (1 új literal)
- `frontend/src/pages/NewRunPage.tsx` (experimental badge)

## Szigorú tiltások
- **Tilos ConcaveDefault kernel-t módosítani.**
- **Tilos meglévő quality profilokat módosítani.**
- **Tilos silent BLF fallback.**
- Tilos cavity_prepack_v2-t módosítani.

## Végrehajtandó lépések

### Step 1: Jelenlegi kód olvasása
```bash
# nfp_placer.rs jelenlegi NfpPlacerStatsV1 mezők
grep -n "pub struct NfpPlacerStatsV1\|pub nfp_cache\|pub nfp_compute\|pub cfr\|pub sheets" \
  rust/nesting_engine/src/placement/nfp_placer.rs | head -20

# Meglévő quality profilok
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
for k, v in _QUALITY_PROFILE_REGISTRY.items():
    print(f'{k}: placer={v.get(\"placer\")}')
"

# TypeScript QualityProfileName
grep -n "QualityProfileName\|quality_" frontend/src/lib/types.ts | head -10
```

### Step 2: NfpKernelPolicy enum — `rust/nesting_engine/src/nfp/mod.rs`
A canvas spec szerint (ConcaveDefault = default, ReducedConvolutionV1, as_str, from_str).

### Step 3: NfpPlacerStatsV1 bővítés — `nfp_placer.rs`
Hozzáadandó mezők a meglévők MELLÉ:
```rust
pub actual_nfp_kernel: String,
pub nfp_kernel_unsupported_count: u64,
pub nfp_kernel_explicit_fallback_count: u64,
```
Ha RC kernel NotImplemented: `nfp_kernel_unsupported_count++`, placement degraded.
**Tilos silent BLF fallback.**

### Step 4: Quality profil — `nesting_quality_profiles.py`
```python
"quality_reduced_convolution_experimental": {
    "placer": "nfp",
    "search": "sa",
    "part_in_part": "prepack",
    "compaction": "slide",
    "nfp_kernel": "reduced_convolution_v1",
    "experimental": True,
    "description": "Experimental: Reduced Convolution NFP kernel (T05 prototype)",
},
```

### Step 5: TypeScript types.ts bővítés
A QualityProfileName literal union-ba:
```typescript
| "quality_reduced_convolution_experimental"
```

### Step 6: NewRunPage.tsx experimental badge
Az experimental=true profilnál badge jelölés (részletek a canvas spec-ben).

### Step 7: Validálás
```bash
# Rust compile
cargo check -p nesting_engine 2>&1 | tail -5

# TypeScript compile
cd frontend && npx tsc --noEmit 2>&1 | tail -10 && cd ..

# Python profil
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
p = _QUALITY_PROFILE_REGISTRY['quality_reduced_convolution_experimental']
assert p['placer'] == 'nfp'
assert p['nfp_kernel'] == 'reduced_convolution_v1'
assert p['experimental'] == True
print('quality profile OK')
"

# Meglévő profilok érintetlenek
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY
# A meglévő profilok nfp_kernel mezője NEM változott (ha volt)
for k, v in _QUALITY_PROFILE_REGISTRY.items():
    if k != 'quality_reduced_convolution_experimental':
        assert v.get('nfp_kernel') is None or v.get('nfp_kernel') == 'concave_default', f'{k}: nfp_kernel módosítva!'
print('meglévő profilok OK')
"

# NfpKernelPolicy::default() == ConcaveDefault
grep -n "ConcaveDefault\|#\[default\]" rust/nesting_engine/src/nfp/mod.rs
```

### Step 8: Report és checklist

## Tesztparancsok
```bash
cargo check -p nesting_engine
cd frontend && npx tsc --noEmit && cd ..
python3 -c "from vrs_nesting.config.nesting_quality_profiles import _QUALITY_PROFILE_REGISTRY; assert 'quality_reduced_convolution_experimental' in _QUALITY_PROFILE_REGISTRY; print('OK')"
grep -n "NfpKernelPolicy\|ConcaveDefault\|ReducedConvolutionV1" rust/nesting_engine/src/nfp/mod.rs
```

## Ellenőrzési pontok
- [ ] cargo check hibátlan
- [ ] tsc --noEmit hibátlan
- [ ] quality_reduced_convolution_experimental profil megvan, nfp_kernel mező OK
- [ ] NfpKernelPolicy::default()==ConcaveDefault
- [ ] NfpPlacerStatsV1 tartalmazza az új mezőket
- [ ] silent fallback tilos — nfp_kernel_unsupported_count számolja
- [ ] meglévő quality profilok érintetlenek
