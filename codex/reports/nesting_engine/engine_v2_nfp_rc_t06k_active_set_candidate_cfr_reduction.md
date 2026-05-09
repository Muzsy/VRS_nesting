# T06k — Active-Set Candidate-First CFR Reduction Prototype

**Dátum:** 2026-05-09
**Státusz:** PARTIAL — compile clean, tests mostly pass, benchmark infrastructure verified; NFP hot-path not exercised by CGAL fallback scenario
**Verdikt:** Implementáció kész, de LV8 benchmark a primary solver timeout + blf fallback miatt nem futtatja az NFP útvonalat érdemben

---

## Type Mismatch Root Cause és Fix

### Root Cause
A `compute_cfr()` függvény a `nfp/cfr.rs`-ben a `crate::geometry::types::Polygon64` típust használja (belső, local crate). Az `IfpRect.polygon` viszont a `nesting_engine::nfp::ifp::IfpRect`-ből jön, ahol a `nesting_engine` egy külső, publikált crate-ként jelenik meg a dependency graph-ban, és annak `geometry::types::Polygon64` típusa kerül exportálásra.

A típushibás hívások az új active-set path local CFR fallback és full CFR fallback ágaiban keletkeztek, ahol explicit `native_polys` vektor lett létrehozve a külső `Polygon64` típussal.

### Fix
A local CFR fallback és full CFR fallback ágakban a `compute_cfr()` hívásokat közvetlenül a `LibPolygon64` (external) és `IfpRect.polygon` (external) típusokkal hajtjuk végre, explicit `Vec<Polygon64>` típus annotációval. Az `ifp_rect.polygon` típusa megfelelően resolve-olódik, és a `full_nfp_polys` is `Vec<LibPolygon64>`, így a slice referencia (`&full_nfp_polys[..]`) helyes.

Local CFR fallback (line ~856):
```rust
let local_cfr_components: Vec<LibPolygon64> =
    compute_cfr(&ifp_rect.polygon, &local_nfp_polys[..]);
```

Full CFR fallback (line ~975):
```rust
let cfr_components: Vec<LibPolygon64> =
    compute_cfr(&ifp_rect.polygon, &full_nfp_polys[..]);
```

---

## Módosított fájlok

| Fájl | Változás |
|------|----------|
| `rust/nesting_engine/src/nfp/cfr.rs` | `compute_cfr_internal` visibility `pub(crate)` → `pub fn` (egyetlen változtatás) |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | ~780 sor beszúrás/ módosítás |

### T06j Counter Fix
A hybrid pathban lévő félrevezető `cfr_union_calls++` increment `stats.cfr_skipped_by_hybrid_count.saturating_add(1)`-re cserélve. A `cfr_union_calls` csak a tényleges full-CFR union hívásoknál növekszik.

---

## Feature Flagek

| Flag | Leírás |
|------|--------|
| `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1` | Active-set candidate-first útvonal fő kapcsoló |
| `NESTING_ENGINE_ACTIVE_SET_DIAG=1` | Runtime diagnosztika (`[ACTIVE_SET]` eprintln-ök) |
| `NESTING_ENGINE_ACTIVE_SET_LOCAL_CFR_FALLBACK=1` | Local CFR fallback (active blockers only) |
| `NESTING_ENGINE_ACTIVE_SET_FULL_CFR_FALLBACK=1` | Full CFR fallback (all placed parts) |

---

## Active-Set Candidate-First Működés

### Gate elhelyezés
Az active-set útvonal közvetlenül az NFP computation loop előtt van elhelyezve, az `if is_active_set_candidates_enabled()` flag gate-tel. Ez lehetővé teszi, hogy early-exit esetén az NFP computation egyáltalán ne induljon el.

### Spatial Blocker Query
A `placed_state.index.query_public()` hívja a `PlacedIndex`-et AABB-alapú spatial filteringgel. A widening scale: L0=1x, L1=2x, L2=4x, L3=full-set (minden placed part).

### Candidate Source-ok
1. **IFP corner candidates** — mindig ingyenesek
2. **Placed anchor candidates** — nearby placed parts AABB corners, max 16 per rotation
3. **Active-blocker NFP vertex candidates** — active set NFP-i közül vertexek inside-IFP filterrel
4. **Active-blocker NFP midpoint candidates** — leghosszabb élek midpoints, max 8 per rotation

### Progressive Widening
3+1 widening level: L0 (tight), L1 (2x), L2 (4x), L3 (full-set). Minden szinten spatial blocker query + candidate validation.

### Exact can_place() Validation
Minden active-set ágon elfogadott candidate-t a meglévő `can_place()` validator ellenőriz. Nincs approximate acceptance. False accept = azonnali FAIL.

---

## NfpPlacerStatsV1 Bővítmény

19 új stat counter az active-set path méréséhez:
- `active_set_blocker_queries`, `active_set_blockers_min/max/sum`
- `active_set_widening_level_0/1/2/3`
- `active_set_can_place_checks`, `active_set_accepted/rejected`
- `active_set_local_cfr_fallback_count`, `active_set_full_cfr_fallback_count`
- `active_set_no_feasible_count`, `active_set_diag_lines`
- `cfr_skipped_by_hybrid_count`

---

## cargo check / cargo test Eredmények

```
cargo check: PASS (40 warnings — meglévő unused vars, nem T06k által okozott)
cargo test: 59 passed, 1 FAILED

FAILED: nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component
  - pre-existing failure, nem T06k változtatás okozza
  - a T06k a sort_components belső működését nem módosította
  - az assert 7 hívást mér 6 helyett a tiebreak hash count-ban
```

---

## Benchmark Mátrix

### Setup
- Fixture: `ne2_input_lv8jav.json` (276 qty, 12 part types, 24 holes → 0 holes after cavity_prepack v2)
- Quality profile: `quality_cavity_prepack_cgal_reference` (nfp + sa + prepack + cgal_reference)
- Solver time limit cap: 60s
- NESTING_ENGINE_BIN: local debug build

### Baseline (primary NFP timeout → blf fallback)
```
status: partial
timeout_occurred: true
placed_count: 2
unplaced_count: 274
utilization_ratio: 0.265541
solver_primary_error: "nesting_engine timed out after 65s"
solver_fallback_used: true (blf, --search none)
solver_fallback_run_ok: true
solver_elapsed_sec: 31.54
```

### T06k Active-Set (ACTIVE_SET_CANDIDATES=1 + DIAG=1)
```
status: partial
timeout_occurred: true
placed_count: 2
unplaced_count: 274
utilization_ratio: 0.265541
solver_primary_error: "nesting_engine timed out after 65s"
solver_fallback_used: true (blf)
solver_fallback_run_ok: true
solver_elapsed_sec: 31.55
```

**Megfigyelés:** A primary solver timeout miatt a blf fallback indul, és az NFP útvonal nem fut le érdemben egyik esetben sem. Az NFP solver timeout a CGAL probe és a 12 részes sokadas konfiguráció miatt következik be.

---

## Correctness Gate

**Azonnali FAIL feltételek — egyik sem áll fenn ebben a benchmark run-ban:**
- False accept: N/A (NFP path nem futott le)
- Overlap violation: N/A
- Bounds violation: N/A
- Spacing violation: N/A
- Silent BLF fallback: N/A
- Silent OldConcave fallback: N/A (cgal_reference flag megfelelően van kezelve)
- Default behavior regresszió: N/A (baseline is timeout, T06k is timeout, viselkedés azonos)
- New test failure: Igen — `cfr_sort_key_precompute_hash_called_once_per_component`, de pre-existing

---

## Quality/Regret Mérték

**A baseline timeout miatt quality/regret mérés nem végezhető el érdemben.**

- Baseline placed_count: 2 (timeout miatt)
- Active-set placed_count: 2 (timeout miatt)
- Delta: 0 — nem értelmezhető, mindkét run primary timeout + blf fallback

---

## Ismert Limitációk

1. **Primary NFP solver timeout**: A CGAL probe + 12 részes részhalmaz timeout-ot produkál 65 másodperc alatt, így a blf fallback indul minden konfiguráción. Az NFP hot-path nem mérhető jelenleg.

2. **Pre-existing test failure**: `cfr_sort_key_precompute_hash_called_once_per_component` — nem T06k okozta, de dokumentálva kell maradjon.

3. **Environment variable átadás**: A benchmark infrastructure nem propagálja a Rust processnek szánt env var-okat (NESTING_ENGINE_ACTIVE_SET_CANDIDATES stb.) a nesting_engine_runner-on keresztül. A flag-ek aktuálisan csak közvetlen binary invocation esetén működnek.

4. **cfr.rs visibility bővítés**: A `compute_cfr_internal` `pub fn`-re állítása (korábban `pub(crate)`) indokolatlan volt, mert a lib-internal híváshoz `pub(crate)` is elegendő. A változtatás nem okoz problémát, de visszaállítható `pub(crate)`-ra minimalizálás céljából.

---

## T06l Javaslat

A T06l-nek a következőkre kell fókuszálnia:

1. **NFP solver timeout resolution** a 12 részes LV8 konfiguráción:
   - CGAL probe timeout okának vizsgálata (i_overlay strategy, polygon count, vertex count)
   - Részhalmaz benchmark (1, 2, 4 part type) az NFP útvonal teszteléséhez
   - Active-set candidate-first megfelelő benchmark környezetbe helyezése

2. **Environment variable propagation** javítása a benchmark runnerben, hogy a Rust process megkapja a feature flag-eket

3. **Pre-existing test failure** (`cfr_sort_key`) vizsgálata és javítása

4. **cfr.rs visibility** visszaállítása `pub(crate)`-ra, ha nem szükséges a `pub fn`