# Engine v2 NFP RC — T06 Robust Minkowski Cleanup

## Cél
A reduced convolution nyers outputját nestingre alkalmas NFP-vé tisztítani.
A cleanup kötelező minden RC NFP output után — validálatlan NFP nem fogadható el.
A `minkowski_cleanup.rs` és `nfp_validation.rs` modulok biztosítják, hogy az NFP
output ténylegesen helyes NFP legyen, nem csak egy polygon.

## Miért szükséges
A reduced convolution / Minkowski összeg nyers outputja tipikusan tartalmaz:
- Nulla területű hurkokat (degenerate edges)
- Belső éleket (az összefonódott konvolúciós hurkok maradékai)
- Sliver-eket (vékony, elhanyagolható területű részeket)
- Önmetsző szakaszokat (floating point imprecision)
Ezek tisztítása nélkül az NFP nem használható elhelyezési döntésre.

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `rust/nesting_engine/src/nfp/boundary_clean.rs` — clean_polygon_boundary, ring_has_self_intersection (minta)
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` — T05 output (RcNfpResult)
- `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64
- `rust/nesting_engine/src/geometry/cleanup.rs` — T03 cleanup (felhasználható)
- `docs/nesting_engine/geometry_preparation_contract_v1.md` — T02 contract

### Létrehozandó:
- `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` — cleanup modul
- `rust/nesting_engine/src/nfp/nfp_validation.rs` — validátor modul

### Módosítandó:
- `rust/nesting_engine/src/nfp/mod.rs` — `pub mod minkowski_cleanup; pub mod nfp_validation;` hozzáadása

## Nem célok / scope határok
- Tilos a `boundary_clean.rs` meglévő funkcionalitását törölni.
- Tilos az NFP-t a placer-be integrálni (az T08 feladata).
- Tilos invalid NFP-t sikerként elfogadni.
- Nem kell Python kódot módosítani.

## Részletes implementációs lépések

### 1. `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` implementálása

**CleanupOptions struct:**
```rust
#[derive(Debug, Clone)]
pub struct CleanupOptions {
    /// Minimum él hossza egységben — kisebb élek eldobandók
    pub min_edge_length_units: i64,
    /// Minimum poligon terület egységben² — kisebb területű hurkok eldobandók
    pub min_area_units2: i64,
    /// Collinear merge szög threshold fokokban
    pub collinear_angle_deg_threshold: f64,
    /// Sliver detection: ha egy hurok aspect ratio (bbox_h/bbox_w) < threshold → sliver
    pub sliver_aspect_ratio_threshold: f64,
}

impl Default for CleanupOptions {
    fn default() -> Self {
        Self {
            min_edge_length_units: 100,
            min_area_units2: 1000,
            collinear_angle_deg_threshold: 0.5,
            sliver_aspect_ratio_threshold: 0.01,
        }
    }
}
```

**CleanupError enum:**
```rust
#[derive(Debug, Clone)]
pub enum CleanupError {
    /// Cleanup után is invalid a polygon — explicit hiba, NEM silent fallback
    InvalidAfterCleanup(String),
    EmptyInput,
    AllLoopsRemoved,
}
```

**CleanupResult struct:**
```rust
#[derive(Debug, Clone)]
pub struct CleanupResult {
    /// None ha CleanupError keletkezett
    pub polygon: Option<Polygon64>,
    pub loops_removed_zero_area: usize,
    pub internal_edges_removed: usize,
    pub micro_edges_removed: usize,
    pub collinear_merged: usize,
    pub slivers_detected: usize,
    pub self_intersections_detected: usize,
    /// true ha a végeredmény valid NFP
    pub is_valid: bool,
    pub error: Option<CleanupError>,
}
```

**Publikus API:**
```rust
pub fn run_minkowski_cleanup(
    raw_nfp: &Polygon64,
    options: &CleanupOptions,
) -> CleanupResult
```

**Kötelező cleanup lépések sorrendben:**

1. **duplicate_vertex_removal** — egymást követő azonos pontok eltávolítása
2. **null_edge_removal** — nulla hosszú élek eltávolítása
3. **micro_edge_removal** — `min_edge_length_units` alatti élek eltávolítása
4. **loop_classification** — minden hurok: outer (CCW, area > 0) vs hole (CW, area < 0)
5. **zero_area_loop_removal** — nulla területű hurkok eltávolítása (counter: `loops_removed_zero_area`)
6. **internal_edge_removal** — belső élek eltávolítása (az outer-en belüli élek)
7. **collinear_merge** — `collinear_angle_deg_threshold` alatti szögű collinear vertexek összevonása
8. **sliver_detection** — vékony hurkok detektálása (counter: `slivers_detected`)
9. **polygon_validity_check** — ha invalid: `CleanupError::InvalidAfterCleanup(reason)`

**Szigorú szabály:** Ha a 9. lépés invalid-ot jelez:
- `is_valid = false`
- `error = Some(CleanupError::InvalidAfterCleanup(...))`
- `polygon = None`
- **Tilos** `is_valid = false` + `polygon = Some(...)` kombinációt visszaadni

### 2. `rust/nesting_engine/src/nfp/nfp_validation.rs` implementálása

**Publikus API:**
```rust
/// Polygon orientáció, area > 0, no self-intersection ellenőrzése
/// Visszatér true ha valid NFP-nek fogadható el
pub fn polygon_is_valid(poly: &Polygon64) -> bool

/// Részletes validáció hibaüzenettel
pub fn polygon_validation_report(poly: &Polygon64) -> ValidationReport

#[derive(Debug, Clone)]
pub struct ValidationReport {
    pub is_valid: bool,
    pub outer_ring_vertex_count: usize,
    pub outer_ring_ccw: bool,
    pub outer_ring_area_mm2: f64,
    pub self_intersection_detected: bool,
    pub holes_count: usize,
    pub degenerate_edges_count: usize,
    pub reason_if_invalid: Option<String>,
}
```

**Validáció szabályai:**
1. outer_ring_vertex_count ≥ 3
2. outer_ring_ccw = true (counter-clockwise orientáció)
3. outer_ring_area_mm2 > 0.0
4. self_intersection_detected = false (ring_has_self_intersection-t használja)
5. Ha lyuk: hole_ring_cw = true, hole_area > 0

### 3. nfp/mod.rs módosítás

```rust
pub mod minkowski_cleanup;
pub mod nfp_validation;
```

### 4. Integráció a T05 outputtal

Ha T05-ben `RcNfpResult::polygon = Some(...)`:
```rust
let rc_result = compute_rc_nfp(&part_a, &part_b, &options);
if let Some(raw_nfp) = rc_result.polygon {
    let cleanup_result = run_minkowski_cleanup(&raw_nfp, &CleanupOptions::default());
    if !cleanup_result.is_valid {
        // Explicit hiba — tilos silent fallback BLF-re
        return Err(NfpError::NotSimpleOutput);
    }
    // cleanup_result.polygon.unwrap() a valid NFP
}
```

### 5. Validálás és tesztelés

```bash
# Compile
cargo check -p nesting_engine

# Szimulált invalid input cleanup próba
cargo test -p nesting_engine -- minkowski_cleanup
cargo test -p nesting_engine -- nfp_validation
```

## Adatmodell / contract változások
Két új Rust modul (`minkowski_cleanup.rs`, `nfp_validation.rs`).
`nfp/mod.rs` minimális módosítás (pub mod sorok).

## Backward compatibility
A `boundary_clean.rs` érintetlen. `ring_has_self_intersection` felhasználható
a `nfp_validation.rs`-ből.

## Hibakódok / diagnosztikák
- `CleanupError::InvalidAfterCleanup(String)` — cleanup után is invalid, string tartalmaz okot
- `CleanupError::EmptyInput` — üres input polygon
- `CleanupError::AllLoopsRemoved` — minden hurok eldobásra került

**Kritikus invariáns:** `is_valid = false` esetén `polygon = None` MINDIG.

## Tesztelési terv
```bash
# 1. Compile check
cargo check -p nesting_engine 2>&1 | tail -5

# 2. Unit tesztek futnak
cargo test -p nesting_engine minkowski_cleanup 2>&1 | tail -10
cargo test -p nesting_engine nfp_validation 2>&1 | tail -10

# 3. polygon_is_valid false esetén polygon = None invariáns
# (Unit tesztben ellenőrizve, lásd a test modul-ban)

# 4. Ha T05 adott outputot: cleanup lefut
# (integration test a T05 bin-nel)
```

## Elfogadási feltételek
- [ ] `cargo check -p nesting_engine` hibátlan
- [ ] `run_minkowski_cleanup` publikus API megvalósítva mind a 9 lépéssel
- [ ] `polygon_is_valid` és `polygon_validation_report` megvalósítva
- [ ] `CleanupError::InvalidAfterCleanup` esetén `polygon = None` (nem silent continue)
- [ ] `is_valid = false` esetén soha nem kerülhet a polygon a placer inputjába
- [ ] A `boundary_clean.rs` érintetlen
- [ ] `ring_has_self_intersection` felhasználható a nfp_validation.rs-ből

## Rollback / safety notes
Additive modulok. A `boundary_clean.rs` érintetlen.
A meglévő NFP pipeline nem változik (az T08 integrálja).

## Dependency
- T03: cleanup.rs (duplicate_vertex_removal, null_edge_removal felhasználható)
- T05: reduced_convolution.rs RcNfpResult (cleanup input)
- T07: nfp_correctness_validator uses nfp_validation.rs
- T08: minkowski_cleanup.rs integrálva a placer-be
