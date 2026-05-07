# T05u — Engine v2 NFP Provider Audit & Integration Plan

**Státusz: AUDIT_COMPLETE**

**Feladat:** Feltérképezni a meglévő Engine v2 NFP kernel csere lehetőségét — anélkül, hogy új optimalizálót írnánk, vagy CGAL-t production dependencyvé tennénk.

---

## Rövid összefoglaló

**A valódi hibapont a `concave.rs`-beli `union_nfp_fragments` függvény**, nem az optimalizáló logika. A meglévő Engine v2 optimizer lánc (greedy + SA + multi-sheet + slide compaction) jól működik és nem kell újraírni. A megoldás: a régi concave NFP kernel cseréje egy plug-in NFP providerre.

| | |
|---|---|
| **Új optimalizáló kell?** | NEM |
| **NFP provider csere kell?** | IGEN |
| **Legkritikusabb fájl** | `rust/nesting_engine/src/nfp/concave.rs:1057` (`union_nfp_fragments`) |
| **CGAL productionban?** | NEM — csak reference provider lehet |

---

## 1. NFP Call Graph

### 1.1 Belépési pontok

```
main.rs:run_nest()
  └─> greedy_multi_sheet()         [multi_bin/greedy.rs]
        └─> nfp_place()             [placement/nfp_placer.rs]
              └─> compute_nfp_lib() [nfp_placer.rs:489]  ← KULCS BELÉPÉSI PONT

  VAGY (SA search módban)
        └─> run_sa_search_over_specs() [search/sa.rs]
              └─> (belsőleg szintén nfp_place / compute_nfp_lib)
```

### 1.2 NFP kernel dispatch (`compute_nfp_lib`, nfp_placer.rs:489–496)

```rust
fn compute_nfp_lib(placed_polygon: &Polygon64, moving_polygon: &Polygon64) -> Option<LibPolygon64> {
    let placed_lib = to_lib_polygon(placed_polygon);
    let moving_lib = to_lib_polygon(moving_polygon);
    if is_convex(&placed_polygon.outer) && is_convex(&moving_polygon.outer) {
        compute_convex_nfp(&placed_lib, &moving_lib).ok()   // convex.rs
    } else {
        compute_concave_nfp_default(&placed_lib, &moving_lib).ok()  // concave.rs ← CSAK EZ AZ AGGÁLYOS
    }
}
```

**Konvex/concave választás:** Minden alkalommal `compute_nfp_lib`-ben történik, a `placed_polygon.outer` és `moving_polygon.outer` `is_convex()` tesztje alapján.

### 1.3 Convex NFP (OK — nem a bottleneck)

```
convex.rs:compute_convex_nfp() (line 6)
  └─> O(n+m) edge-vector merge
  └─> NEM használ i_overlay-t
  └─> NEM decompose-ol
  └─> Bizalmas, gyors
```

### 1.4 Concave NFP (A BOTTLENECK — `compute_stable_concave_nfp`, concave.rs:261)

```
compute_stable_concave_nfp(a, b)     [concave.rs:261]
  │
  ├─ decompose_to_convex_parts(&a.outer)  [concave.rs:911]
  │     ear_clip_triangulate() → O(n) triangles
  │     Lv8_07921_50db (344pts) → 342 triangles
  │     Lv8_11612_6db (520pts) → 518 triangles
  │
  ├─ decompose_to_convex_parts(&b.outer)
  │
  ├─ 342 × 518 = 177,156 NFP pár
  │     compute_convex_nfp() minden párra → ~6s összesen (partial NFP loop)
  │
  └─ union_nfp_fragments(&partial_nfpc)    [concave.rs:1057]  ← GLOBÁLIS BOTTLENECK
        Overlay::with_shapes_options(
          &subject_shapes,          // 177,156 IntShape
          &empty_shapes,
          IntOverlayOptions::keep_all_points(),
          Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE),
        )
        overlay.overlay(OverlayRule::Union, FillRule::NonZero)  ← NEMÁLL VISSZA
```

**Diagnosztikai output** (T05 Phase 8 instrumentáció, concave.rs:274–316):
```
[CONCAVE NFP DIAG] decompose_done convex_a=342 convex_b=518 estimated_nfp_pairs=177156
[CONCAVE NFP DIAG] partial_nfp_done [...]  → ~6s után kész
[CONCAVE NFP DIAG] union_done              → SOHA NEM JELENIK MEG
```
A `union_done` sosem íródik ki → az `i_overlay` union SOSEM tér vissza.

### 1.5 Hole kezelés

**Fontos:** A jelenlegi `compute_stable_concave_nfp` explicit módon elutasítja a holed inputot (concave.rs:265–266):
```rust
if !a.holes.is_empty() || !b.holes.is_empty() {
    return Err(NfpError::DecompositionFailed);
}
```
Ez a gyakorlatban azért működik, mert a `cavity_prepack` előtte hole-collapsed geometriát szolgáltat (az összes lyuk kitöltődik). A `has_nominal_holes` check a main.rs:439 aztán BLF-re风水 át ha lyuk van.

### 1.6 Orbit Exact Mode (`compute_orbit_exact_nfp`, concave.rs:320)

Két mód van (`ConcaveNfpMode` enum, concave.rs:26):
- `StableDefault` (default): a fenti decompose+union path
- `ExactOrbit`: event-based orbit tracing — jelenleg NEM aktív defaultban

---

## 2. Meglévő Optimizer Call Graph

### 2.1 Greedy Multi-Sheet (`greedy.rs`)

```
main.rs:run_nest()
  └─> greedy_multi_sheet() [greedy.rs]
        ├─ Part rendezés: ByArea (default) vagy ByInputOrder
        ├─ Iteráció: minkét part × instance
        │     ├─ HA placer == Nfp → nfp_place()
        │     └─ HA placer == Blf → blf_place()
        ├─ HA PartInPart == Auto → rekurzív nesting (cavity-fill)
        ├─ Új sheet nyitás: ha nem fér el
        └─ Slide Compaction: sheet compaction minden sheet után
```

**Score/scoring** (greedy.rs:268–309):
- `SCORE_PPM_SCALE = 1_000_000`
- `REMNANT_AREA_WEIGHT_PPM = 500_000` — legnagyobb súly
- `REMNANT_COMPACTNESS_WEIGHT_PPM = 300_000`
- `REMNANT_MIN_WIDTH_WEIGHT_PPM = 200_000`
- Score = legjobb sheet kiválasztása remnant value alapján

### 2.2 NFP Placer (`nfp_placer.rs`)

```
nfp_place() [nfp_placer.rs]
  ├─ Per-rotation loop (rotation_rank, rotation_deg)
  │     ├─ rotate_polygon() → normalize_polygon_min_xy()
  │     ├─ compute_ifp_rect() → IFP téglalap korlát
  │     └─ NFP loop: placed vs. minden korábban elhelyezett
  │           ├─ cache.get(key) → HIT/MISS
  │           ├─ HA MISS → compute_nfp_lib()
  │           │     ├─ convex A + convex B → compute_convex_nfp()
  │           │     └─ egyéb → compute_concave_nfp_default()
  │           └─ cache.insert(key, poly_rel)
  ├─ CFR computation: compute_cfr_with_stats()
  │     (i_overlay Union + Difference, de itt kevés fragment van)
  ├─ Candidate generation: vertex enumeration + nudge
  └─ Collision check: can_place() → AABB + narrow phase
```

### 2.3 Slide Compaction (`greedy.rs`, a greedy_multi_sheet-ből hívva)

- Minden sheet után: `CompactionEvidence` számítás
- `CompactionMode::Slide`: part-ok eltolása a "legjobb remnant" irányába
- Csak az adott sheet belső állapotát módosítja

### 2.4 SA Search (`sa.rs`)

```
run_sa_search_over_specs() [sa.rs]
  └─> SA mag: random swap + rotation perturbation
        └─> evaluate(): greedy_single_sheet() hívás minden iterációnál
```

**Cost encoding** (sa.rs:53–57):
- `unplaced_weight`, `sheets_weight`, `remnant_axis`
- Evaluálás: `greedy_multi_sheet()` hívása minden SA iterációban (drága)

---

## 3. Bottleneck Pontos Azonosítása

### 3.1 Proof — T05 Phase 8 instrumentáció

Forrás: `concave.rs:274–316` + T05 Phase 8 report.

**LV8 legtoxikusabb pár (Lv8_07921_50db + Lv8_11612_6db):**
- convex_a = 342 triangles
- convex_b = 518 triangles
- NFP pairs = 342 × 518 = **177,156**
- Partial NFP loop: ~6s (minden pár kiszámítva)
- `union_nfp_fragments`: **NEM TÉR VISSZA** — `i_overlay Strategy::List` O(n²) vagy rosszabb 177K polygonon
- OS SIGTERM (35s) → Python runner "timeout"-nak érzékeli

**LV8 nem-toxikus pár (LV8_02049_50db + Lv8_11612_6db):**
- convex_a = 1 (LV8_02049 már konvex)
- NFP pairs = 1 × 518 = 518
- Union: 931ms
- Eredmény: PASS

### 3.2 Miért NEM az optimizer az elsődleges probléma

1. **Greedy + SA + slide compaction jól működik** — a meglévő logic helyes
2. **Cavity_prepack v2: 24 lyuk → 0, guard=true, ~0.03s** — ez már készen van
3. **Az NFP timeout/fallback nem az optimalizáló, hanem az NFP kernel hibája** — a fallback BLF-re mutat, de a BLF kevésbé hatékony placement-et ad
4. **CGAL T05b–T05e bizonyította**: a `minkowski_sum_by_reduced_convolution_2` kezeli a holed geometry-t, nincs triangle explosion, 118–200ms/pair

### 3.3 Kritikus cserepont

| Fájl | Funkció | Probléma | Teendő |
|---|---|---|---|
| `concave.rs:489` (`compute_nfp_lib`) | Convex/concave dispatch | Hardcoded | Absztrakt interface |
| `concave.rs:261` (`compute_stable_concave_nfp`) | Decompose + union | i_overlay Strategy::List O(n²) | Provider csere |
| `concave.rs:1057` (`union_nfp_fragments`) | Polygon union | **GLOBAL BOTTLENECK** | CGAL/reduced convolution |

---

## 4. Meglévő Optimizer Újrahasznosítási Terv

**A teljes optimizer lánc érintetlen marad.** Csak a `compute_nfp_lib` belső implementációja cserélendő.

```
┌─────────────────────────────────────────────────────────┐
│  greedy.rs / sa.rs — NEM MODOSUL                         │
│  (part ordering, score, multi-sheet, slide compaction)   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  nfp_placer.rs — compute_nfp_lib() implementáció cseréje │
│  (cache.get / cache.insert interface marad)              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  NfpProvider trait (ÚJ)                                  │
│  ├─ OldConcave (default, jelenlegi)                    │
│  ├─ ReducedConvolutionExperimental (Rust, beégetett)    │
│  └─ CgalProbeReference (external binary, GPL, dev only) │
└──────────────────────────────────────────────────────────┘
```

**Minden más marad:** `greedy.rs`, `sa.rs`, `blf.rs`, `cfr.rs`, `minkowski_cleanup.rs`, `nfp_validation.rs`, `boundary_clean.rs`.

---

## 5. NFP Provider Interface Javaslat

### 5.1 Core Trait

```rust
// rust/nesting_engine/src/nfp/provider.rs (ÚJ fájl)

use crate::geometry::types::{Point64, Polygon64};
use crate::nfp::NfpError;

/// NFP computation result from any kernel.
#[derive(Debug, Clone)]
pub struct NfpProviderResult {
    /// The computed NFP outer boundary.
    pub outer: Polygon64,
    /// Inner holes of the NFP (if any).
    pub holes: Vec<Vec<Point64>>,
    /// Time spent computing in milliseconds.
    pub compute_time_ms: u64,
    /// Which kernel produced this result.
    pub kernel: NfpKernel,
    /// Validation status (if checked).
    pub validation_status: Option<NfpValidationStatus>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NfpKernel {
    /// Original convex-decomposition + i_overlay union (default, production-safe)
    OldConcave,
    /// Rust reduced-convolution prototype (experimental, MIT)
    ReducedConvolutionExperimental,
    /// CGAL reference via external binary (GPL, dev/reference only)
    CgalProbeReference,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NfpValidationStatus {
    Valid,
    InvalidSelfIntersection,
    InvalidEmptyOutput,
    // ... etc
}

/// NFP provider trait — pluggable kernel interface.
pub trait NfpProvider: Send + Sync {
    /// Human-readable kernel name.
    fn kernel_name(&self) -> &'static str;

    /// Compute NFP for two polygons.
    /// Returns Err on kernel failure (NO silent fallback).
    fn compute(
        &self,
        part_a: &Polygon64,
        part_b: &Polygon64,
    ) -> Result<NfpProviderResult, NfpError>;

    /// Whether this kernel can handle holed polygons natively.
    fn supports_holes(&self) -> bool { false }
}
```

### 5.2 Jelenlegi cache integráció

A meglévő `NfpCache` és `NfpCacheKey` (cache.rs:18) marad:
```rust
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
}
```

**Nem változik:** a cache a `compute_nfp_lib` szintjén működik, az új provider csak a `compute()` implementációt cseréli.

### 5.3 Provider regisztráció

```rust
// nfp_placer.rs — compute_nfp_lib helyett
fn compute_nfp_lib(
    placed_polygon: &Polygon64,
    moving_polygon: &Polygon64,
    provider: &dyn NfpProvider,  // új paraméter
) -> Option<LibPolygon64> {
    let placed_lib = to_lib_polygon(placed_polygon);
    let moving_lib = to_lib_polygon(moving_polygon);
    provider.compute(&placed_lib, &moving_lib)
        .map(|r| to_lib_polygon(&r.outer))
        .ok()
}
```

---

## 6. Cache Terv

### 6.1 Bővített cache kulcs

A jelenlegi `NfpCacheKey` (cache.rs:18) kibővítése:

```rust
pub struct NfpCacheKeyV2 {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
    pub nfp_kernel: NfpKernel,       // ÚJ: melyik kernel
    pub cleanup_profile: String,    // ÚJ: minkowski_cleanup paraméterek
    // geometry_profile: implicit a shape_id-ban (canonical geometry hash)
}
```

**shape_id tartalmazza:** outer + holes canonical form (cache.rs:92–107), tehát a `geometry_profile` implicit része a kulcsnak.

### 6.2 Cache lekérdezés helye

`nfp_placer.rs:208` — **MARAD**, a `cache.get(&key)` hívás a `compute_nfp_lib` előtt változatlan.

### 6.3 Cache feltöltés helye

`nfp_placer.rs:247` — **MARAD**, `cache.insert(key, poly_rel.clone())` változatlan.

### 6.4 Failure/timeout cache kezelés

**Kulcs elv: NE legyen silent fallback.**

```rust
// nfp_placer.rs — compute_nfp_lib wrapper
fn compute_nfp_with_cache(
    placed: &Polygon64,
    moving: &Polygon64,
    cache: &mut NfpCache,
    provider: &dyn NfpProvider,
) -> Option<Polygon64> {
    let key = NfpCacheKey {
        shape_id_a: shape_id(placed),
        shape_id_b: shape_id(moving),
        rotation_steps_b: ...,
        nfp_kernel: provider.kernel_name(),
        // ...
    };

    if let Some(cached) = cache.get(&key) {
        return Some(cached.clone());
    }

    match provider.compute(placed, moving) {
        Ok(result) => {
            // Nem failure → cache-be
            cache.insert(key, result.outer.clone());
            Some(result.outer)
        }
        Err(NfpError::...) => {
            // Kernel failure → NEM cache-eljük
            // → BLF fallback a placer szintjén (nfp_placer.goes_to_blf...)
            None
        }
    }
}
```

**Failure cache tiltás:** ha `compute()` hibát ad, a kulcsot nem írjuk cache-be. A `cache.insert`-et csak `Ok` ágon hívjuk.

### 6.5 Hit/miss statisztika

A jelenlegi `NfpCache.stats()` (cache.rs:70) már működik:
```rust
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
}
```

Kibővítés: `CacheStatsV2 { hits, misses, entries, failures: u64, by_kernel: HashMap<NfpKernel, KernelStats> }`.

---

## 7. CGAL Reference Provider Terv

### 7.1 GPL korlátozások

- CGAL `minkowski_sum_by_reduced_convolution_2` → GPL
- **Soha nem lehet production Docker image dependency**
- **Soha nem lehet production runtime hívás**
- CI: opcionális, feature flag mögött
- Binary: `tools/nfp_cgal_probe/build/nfp_cgal_probe` (létezik, v0.2.0)

### 7.2 Hívási mechanizmus

```rust
// rust/nesting_engine/src/nfp/cgal_reference_provider.rs (ÚJ)

use std::process::Command;

pub struct CgalReferenceProvider {
    binary_path: String,
}

impl NfpProvider for CgalReferenceProvider {
    fn kernel_name(&self) -> &'static str { "cgal_reference" }

    fn supports_holes(&self) -> bool { true }

    fn compute(&self, part_a: &Polygon64, part_b: &Polygon64) -> Result<NfpProviderResult, NfpError> {
        let input = build_cgal_fixture_json(part_a, part_b)?;
        let output = Command::new(&self.binary_path)
            .args(["--fixture", &input, "--algorithm", "reduced_convolution", "--output-json"])
            .output()
            .map_err(|e| NfpError::ComputationFailed(format!("CGAL probe failed: {e}")))?;

        if !output.status.success() {
            return Err(NfpError::ComputationFailed(
                String::from_utf8_lossy(&output.stderr).to_string()
            ));
        }

        parse_cgal_output_json(&output.stdout)
    }
}
```

### 7.3 JSON contract

**Input** (a probe felé):
```json
{
  "version": "nfp_pair_fixture_v1",
  "part_a": { "outer_mm": [[x,y],...], "holes_mm": [[[x,y],...],...] },
  "part_b": { "outer_mm": [[x,y],...], "holes_mm": [[[x,y],...],...] },
  "spacing_mm": 0.0
}
```

**Output** (a probe-tól):
```json
{
  "version": "nfp_cgal_probe_result_v1",
  "outer_i64": [[x,y],...],
  "holes_i64": [[[x,y],...],...],
  "status": "success",
  "compute_time_ms": 127,
  "hole_aware": true
}
```

### 7.4 T07 validáció

A `nfp_validation.rs:polygon_validation_report()` már létezik. A CGAL probe output-ot közvetlenül erre kell vezetni:
```rust
let report = polygon_validation_report(&result.outer);
if !report.is_valid {
    return Err(NfpError::NotSimpleOutput);
}
```

### 7.5 Silent fallback tiltás

```rust
// nfp_placer.rs — CGAL kernel hívás
match cgal_provider.compute(...) {
    Ok(r) => { ... }
    Err(e) => {
        // NEM: return fallback to convex
        // IGEN: return Err → placer decides BLF
        return Err(e);
    }
}
```

**TILOS:** `Err(_) => compute_convex_nfp_fallback()` típusú silent fallback.

---

## 8. Rust Reduced Convolution Experimental Provider Terv

### 8.1 Jelenlegi állapot

`reduced_convolution.rs` (line 95–98):
```rust
// Prototype path: full reduced-convolution loop assembly is not implemented yet.
// We compute a deterministic convex-hull envelope of Minkowski vertex sums.
// This gives a bounded, non-panicking baseline for T05 experimentation.
let reflected_b = reflect_polygon(&cleaned_b);
let hull = convex_hull(&summed_points);  // ← CSAK KONVEX HULL, NEM VALÓDI NFP
```

Ez jelenleg **nem valódi reduced convolution** — csak a pontok konvex burka. A `compute_rc_nfp()` a `ReducedConvolutionOptions`-szal már a provider interface felé halad.

### 8.2 Providerré alakítás

```rust
// rust/nesting_engine/src/nfp/rc_provider.rs

pub struct RcNfpProvider {
    options: ReducedConvolutionOptions,
}

impl NfpProvider for RcNfpProvider {
    fn kernel_name(&self) -> &'static str { "reduced_convolution_experimental" }

    fn supports_holes(&self) -> bool { false }  // jelenleg nem kezeli a lyukakat

    fn compute(&self, part_a: &Polygon64, part_b: &Polygon64) -> Result<NfpProviderResult, NfpError> {
        let result = compute_rc_nfp(part_a, part_b, &self.options);
        match result {
            RcNfpResult { polygon: Some(poly), computation_time_ms, .. } => {
                Ok(NfpProviderResult {
                    outer: poly,
                    holes: Vec::new(),
                    compute_time_ms: computation_time_ms,
                    kernel: NfpKernel::ReducedConvolutionExperimental,
                    validation_status: None,
                })
            }
            RcNfpResult { error: Some(err), computation_time_ms, .. } => {
                Err(err_to_nfp_error(err))
            }
            // ...
        }
    }
}
```

### 8.3 T06 cleanup integráció

A `minkowski_cleanup.rs` már létezik és működik:
```rust
// A provider compute() után
let cleaned = run_minkowski_cleanup(&raw_output, &CleanupOptions::default());
if !cleaned.is_valid {
    return Err(NfpError::NotSimpleOutput);
}
```

### 8.4 T07 validátor integráció

```rust
let report = polygon_validation_report(&result.outer);
if !report.is_valid {
    return Err(NfpError::NotSimpleOutput);
}
```

### 8.5 Productionba lépés feltétele

- **Egyedi LV8 holed LV8 párosításokra kell átmennie** a T05b–T05e T07 validációján (FP=0, FN=0)
- **CGAL vs. RC összehasonlító benchmark** kell, hogy az RC nem rosszabb a CGAL-nál
- **Timeouts/slow cases kezelése** explicit error kell, nem silent fallback

---

## 9. Szükséges fájlmódosítások (következő task)

### Új fájlok

| Fájl | Leírás |
|---|---|
| `rust/nesting_engine/src/nfp/provider.rs` | `NfpProvider` trait + `NfpProviderResult` |
| `rust/nesting_engine/src/nfp/cgal_reference_provider.rs` | External binary wrapper (GPL) |
| `rust/nesting_engine/src/nfp/rc_provider.rs` | `ReducedConvolutionProvider` wrapper |

### Módosított fájlok

| Fájl | Módosítás |
|---|---|
| `rust/nesting_engine/src/nfp/mod.rs` | Provider modul export |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | `compute_nfp_lib` → provider paraméter + kernel dispatch |
| `rust/nesting_engine/src/nfp/cache.rs` | `NfpCacheKey` bővítése kernel+cleanup_profile mezőkkel |

### NEM módosul (tiltás)

- `greedy.rs` — optimizer marad
- `sa.rs` — optimizer marad
- `blf.rs` — fallback placer marad
- `cfr.rs` — CFR marad
- `boundary_clean.rs` — cleanup marad
- `minkowski_cleanup.rs` — cleanup marad
- `nfp_validation.rs` — validátor marad
- `concave.rs` — CSAK provider-tárolóként, nem töröljük (tiltás)
- `convex.rs` — nem módosul

---

## 10. Kockázatok

| Kockázat | Súlyosság | Kezelés |
|---|---|---|
| CGAL binary path nem található | Medium | Graceful error, NEM silent fallback |
| RC provider output invalid geometry | Medium | T07 validátor minden output-ra |
| Cache poison (failure-t cache-elés) | High | Failure esetén NEM cache-elem |
| CGAL output vs. RC output nem kompatibilis | Low | T07 FP/FN mérés külön |
| Provider trait API instabilitás | Low | Migrations megengedette |
| Memory blow a CGAL probe-ban | Medium | Timeout a subprocess-en |

---

## 11. Következő Ajánlott Task

### T05v — NFP Provider Interface Pilot

**Cél:** A legegyszerűbb provider váltás implementálása — a `compute_nfp_lib` függvényt paraméterezhetővé tenni, és a jelenlegi `compute_concave_nfp_default`-et egy `OldConcaveProvider`-be csomagolni.

**Szükséges lépések:**
1. `rust/nesting_engine/src/nfp/provider.rs` létrehozása (`NfpProvider` trait)
2. `rust/nesting_engine/src/nfp/mod.rs` bővítése
3. `nfp_placer.rs:489` (`compute_nfp_lib`) módosítása: `impl NfpProvider` fogadása
4. `OldConcaveProvider` implementáció (wrap `compute_concave_nfp_default`)
5. `NfpCacheKey` bővítése kernel mezővel
6. **NEM törlünk** `concave.rs`-t, csak elfedjük

**Becsült idő:** 1 session

**Nem része a T05v-nek:**
- CGAL provider implementáció
- RC provider implementáció
- Új optimizer írása
- Dockerfile módosítás
