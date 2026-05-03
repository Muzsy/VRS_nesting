# Engine v2 NFP RC T06 — Robust Minkowski Cleanup
TASK_SLUG: engine_v2_nfp_rc_t06_robust_minkowski_cleanup

## Szerep
Senior Rust fejlesztő agent vagy. Implementálod a Minkowski NFP cleanup pipeline-t
és a polygon validity validatort. is_valid=false esetén polygon=None MINDIG.

## Cél
Implementáld `minkowski_cleanup.rs` és `nfp_validation.rs`. A cleanup pipeline
9 lépéses, sorrendben futtatandó. CleanupError::InvalidAfterCleanup explicit hiba.

## Előfeltétel ellenőrzés
```bash
ls rust/nesting_engine/src/nfp/reduced_convolution.rs || echo "STOP: T05 szükséges"
ls rust/nesting_engine/src/geometry/cleanup.rs || echo "STOP: T03 szükséges"
grep -n "^pub fn" rust/nesting_engine/src/nfp/boundary_clean.rs
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t06_robust_minkowski_cleanup.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t06_robust_minkowski_cleanup.yaml`
- `rust/nesting_engine/src/nfp/boundary_clean.rs` (ring_has_self_intersection — felhasználható)
- `rust/nesting_engine/src/nfp/reduced_convolution.rs` (T05: RcNfpResult)
- `rust/nesting_engine/src/geometry/cleanup.rs` (T03: meglévő cleanup funkciók)

## Engedélyezett módosítás
- `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` (create)
- `rust/nesting_engine/src/nfp/nfp_validation.rs` (create)
- `rust/nesting_engine/src/nfp/mod.rs` (add pub mod sorok)

## Szigorú tiltások
- **Tilos `boundary_clean.rs`-t módosítani.**
- Tilos `is_valid=false` + `polygon=Some(...)` kombinációt visszaadni.
- Tilos invalid NFP-t sikerként elfogadni.
- Tilos a nfp_placer.rs-t módosítani.

## Végrehajtandó lépések

### Step 1: boundary_clean.rs és T03 cleanup megértése
```bash
# Mi van már implementálva?
grep -n "^pub fn\|^pub struct\|^pub enum" rust/nesting_engine/src/nfp/boundary_clean.rs
grep -n "^pub fn\|^pub struct\|^pub enum" rust/nesting_engine/src/geometry/cleanup.rs 2>/dev/null | head -20
```

### Step 2: `rust/nesting_engine/src/nfp/minkowski_cleanup.rs` megírása

A canvas spec szerinti struktúrák:
- `CleanupOptions` (min_edge_length_units, min_area_units2, collinear_angle_deg_threshold, sliver_aspect_ratio_threshold)
- `CleanupError` (InvalidAfterCleanup(String), EmptyInput, AllLoopsRemoved)
- `CleanupResult` (polygon: Option<Polygon64>, loops_removed_zero_area, internal_edges_removed, micro_edges_removed, collinear_merged, slivers_detected, self_intersections_detected, is_valid: bool, error: Option<CleanupError>)
- `run_minkowski_cleanup(raw_nfp: &Polygon64, options: &CleanupOptions) -> CleanupResult`

9 kötelező lépés sorrendben (RÉSZLETES a canvas spec-ben).

**Kritikus invariáns implementálása:**
```rust
// A polygon_validity_check (9. lépés) után:
if !polygon_is_valid(&assembled_polygon) {
    return CleanupResult {
        polygon: None,  // TILOS Some(...) ha invalid
        is_valid: false,
        error: Some(CleanupError::InvalidAfterCleanup("reason".to_string())),
        // ... counter mezők
    };
}
```

### Step 3: `rust/nesting_engine/src/nfp/nfp_validation.rs` megírása

- `polygon_is_valid(poly: &Polygon64) -> bool`
- `polygon_validation_report(poly: &Polygon64) -> ValidationReport`
- `ValidationReport` struct (is_valid, outer_ring_vertex_count, outer_ring_ccw, outer_ring_area_mm2, self_intersection_detected, holes_count, degenerate_edges_count, reason_if_invalid)

`ring_has_self_intersection` a boundary_clean.rs-ből felhasználható.

### Step 4: nfp/mod.rs frissítése
```rust
pub mod minkowski_cleanup;
pub mod nfp_validation;
```

### Step 5: Unit tesztek írása (inline #[cfg(test)])
Minimum tesztek `minkowski_cleanup.rs`-ben:
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_invalid_after_cleanup_polygon_is_none() {
        // Ha cleanup után invalid: polygon=None, is_valid=false
        // ...
    }
    
    #[test]
    fn test_empty_input_returns_error() {
        // Üres polygon: CleanupError::EmptyInput
        // ...
    }
}
```

### Step 6: Kompilálás és tesztelés
```bash
cargo check -p nesting_engine 2>&1 | tail -10

cargo test -p nesting_engine -- minkowski_cleanup 2>&1 | tail -10
cargo test -p nesting_engine -- nfp_validation 2>&1 | tail -10

# boundary_clean.rs érintetlen
git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs
```

### Step 7: Report és checklist

## Tesztparancsok
```bash
cargo check -p nesting_engine
cargo test -p nesting_engine -- minkowski_cleanup
cargo test -p nesting_engine -- nfp_validation
grep -n "pub mod minkowski_cleanup\|pub mod nfp_validation" rust/nesting_engine/src/nfp/mod.rs
git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs
```

## Ellenőrzési pontok
- [ ] cargo check hibátlan
- [ ] run_minkowski_cleanup mind a 9 lépéssel implementálva
- [ ] polygon_is_valid és polygon_validation_report implementálva
- [ ] is_valid=false esetén polygon=None (unit teszttel bizonyítva)
- [ ] CleanupError::InvalidAfterCleanup explicit hiba
- [ ] boundary_clean.rs érintetlen
- [ ] pub mod sorok a mod.rs-ben
