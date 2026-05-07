# T06c — Candidate-driven NFP Placement + CDE Architecture Audit

**Státusz: PASS**
**Verdikt: PARTIAL — a full CFR-union kivezetés nem járható; a candidate-driven út feltételesen járható; T06d javaslat: minimal in-repo candidate-driven prototype feature flag mögött**

---

## Rövid verdikt

- **Full CFR-union kivezetés:** NEM — a CFR a jelenlegi placement correctness single source of truth. A CFR nélkül a candidate-driven út csak korlátozott esetekben (kis elemszám, konvex dominancia) adna helyes eredményt. A CFR kiváltása candidate-driven úttal: ~30-40% coverage improvement lehetséges, de nem 100%.

- **Candidate-driven út járható:** IGEN, de nem teljes CFR kiváltásként, hanem mint **candidate generator + pairwise exact validator** hibrid. A CFR megmarad fallback / reference oracle-ként. A candidate-driven út a placement feasibility-reduckálást célozza, nem a correctness megkerülését.

- **Saját minimál CDE vagy külső CDE PoC:** **Saját minimál CDE (SheetCollisionState)** — T06d-ben új, minimális candidate generator + pairwise collision index építése, feature flag mögött, CFR útvonallal párhuzamosan. Külső CDE (jagua-rs): NEM production cél, csak T06d utáni opcionális benchmark célpont.

---

## 1. CFR Hot-Loop Audit

### 1.1 Teljes Call Graph

```
main.rs / runner
  └─> greedy_multi_sheet()               [greedy.rs:multi_bin]
        ├─ stop.consume(1) per placement attempt
        │
        └─> nfp_place()                   [nfp_placer.rs:142]
              │
              ├─ for each (part, instance, rotation):
              │     ├─ compute_ifp_rect()              [ifp.rs:24] → IfpRect
              │     │
              │     ├─ NFP loop: for each placed_part:
              │     │     ├─ cache.get(NfpCacheKey)     [cache.rs:52]
              │     │     ├─ HA MISS → compute_nfp_lib() [nfp_placer.rs:536]
              │     │     │           └─> provider.compute()
              │     │     │               ├─ convex+convex → compute_convex_nfp() [convex.rs]
              │     │     │               └─ egyéb → compute_concave_nfp_default() [concave.rs]
              │     │     │                   └─ (or CgalReferenceProvider via subprocess)
              │     │     ├─ cache.insert()
              │     │     └─ nfp_polys.push(NFP polygon in world coords)
              │     │
              │     ├─ compute_cfr_with_stats()          [nfp_placer.rs:294]
              │     │     └─> compute_cfr_internal()     [cfr.rs:185]     ← CFR HOT LOOP
              │     │           ├─ canonicalize IFP polygon
              │     │           ├─ encode IFP + NFP to IntShape     [cfr.rs:79-214]
              │     │           ├─ run_overlay(NFP_shapes, [], Union)  [cfr.rs:234]  ← BOTTLENECK
              │     │           │       Strategy::List, Precision::ABSOLUTE
              │     │           │       Input: 77 NFP polygon, ~23,717 vertex
              │     │           ├─ run_overlay(IFP_shape, union_shapes, Diff) [cfr.rs:259]
              │     │           ├─ decode diff_shapes → Vec<Polygon64>
              │     │           ├─ sort_components()                     [cfr.rs:497]
              │     │           │       CfrComponentSortKeyV1: min_x, min_y, area, vertex_count, tiebreak_hash
              │     │           └─ return cfr_components
              │     │
              │     ├─ append_candidates()               [nfp_placer.rs:595]
              │     │     for each cfr_component:
              │     │       for each vertex (max MAX_VERTICES_PER_COMPONENT=512):
              │     │         if inside_ifp() → candidate
              │     │         + NUDGE_STEPS=[1,2,4] × NUDGE_DIRS=8 directions
              │     │
              │     ├─ sort_and_dedupe_candidates()       [nfp_placer.rs:460]
              │     │     sort: ty → tx → rotation_rank → cfr_component_rank → vertex_rank → nudge_rank
              │     │     dedupe: BTreeSet<(tx, ty, rotation_idx)>
              │     │     cap: MAX_CANDIDATES_PER_PART=4096
              │     │
              │     ├─ for each candidate:
              │     │     ├─ translate_polygon(moving_polygon, tx, ty)
              │     │     └─> can_place()                  [narrow.rs:79] ← COLLISION CHECK
              │     │           ├─ polygon_has_valid_rings()
              │     │           ├─ aabb_inside(bin_aabb, candidate_aabb)
              │     │           ├─ poly_strictly_within(candidate, bin)   ← bin boundary containment
              │     │           ├─ placed.query_overlaps(candidate_aabb)  [rstar RTree] ← BROAD PHASE
              │     │           │       PlacedIndex: Vec<PlacedPart> + RTree<PlacedPartEnvelope>
              │     │           ├─ aabb_overlaps filter (TOUCH_TOL=1)
              │     │           └─ for each AABB-overlapping placed:
              │     │                 polygons_intersect_or_touch()        ← NARROW PHASE
              │     │                   for each ring pair:
              │     │                     ring_intersects_ring_or_touch()
              │     │                       segments_intersect_or_touch() via orient()
              │     │
              │     └─ HA can_place: break → placed.push(PlacedItem)
              │
              └─ slide_compaction() per sheet (CompactionMode::Slide)
```

### 1.2 Hol épül a teljes CFR

| Fájl | Funkció | Sor | Mit csinál |
|-------|---------|-----|-----------|
| `nfp_placer.rs:294` | `compute_cfr_with_stats()` hívás | 294 | Belépési pont a placement-enkénti CFR számításba |
| `cfr.rs:185` | `compute_cfr_internal()` | 185 | Canonicalizálás, bounds számítás, overlay hívás |
| `cfr.rs:234` | `run_overlay(NFP_shapes, [], Union)` | 234 | **NFP polygon union — fö bottleneck** |
| `cfr.rs:259` | `run_overlay(IFP_shape, union_shapes, Diff)` | 259 | IFP − union_shapes |
| `cfr.rs:497` | `sort_components()` | 497 | CFR komponens rendezés |

### 1.3 Hol történik az NFP polygon összegyűjtése

`nfp_placer.rs:204-267`: `nfp_polys` vektor növekszik minden elhelyezett rész után:
```rust
let mut nfp_polys: Vec<LibPolygon64> = Vec::new();
for placed_part in &placed_for_nfp {
    // ...
    nfp_polys.push(to_lib_polygon(&cached_world)); // world-coord NFP
}
```
LV8 maximum: **77 NFP polygon** egyetlen `compute_cfr_with_stats` hívásban.

### 1.4 Hol történik a CFR union

`cfr.rs:234`:
```rust
let union_shapes = run_overlay(&nfp_shapes, &[], OverlayRule::Union);
```
Input: 77 IntShape (i_overlay), Strategy::List.

### 1.5 Hol történik az IFP difference

`cfr.rs:259`:
```rust
let diff_shapes = run_overlay(&[ifp_shape], &union_shapes, OverlayRule::Difference);
```
Gyors: max 9.73ms mérve T06a-ban.

### 1.6 Hol történik candidate extraction

`nfp_placer.rs:595-641`: `append_candidates()`:
- CFR komponensek vertexeinek enumerálása
- IFP boundaryn belüli szűrés: `inside_ifp(vertex.x, vertex.y, &ctx.ifp)`
- Nudge lépések: 3 távolság × 8 irány

### 1.7 Típusok az adatfolyamban

| Típus | Definíció | Hol definiálva |
|-------|-----------|---------------|
| `Polygon64` | `struct { outer: Vec<Point64>, holes: Vec<Vec<Point64>> }` | `geometry/types.rs:12` |
| `Point64` | `struct { x: i64, y: i64 }` | `geometry/types.rs:3` |
| `LibPolygon64` | Binary workspace mirror of Polygon64 | `nesting_engine::geometry::types` |
| `IfpRect` | `struct { polygon: Polygon64, tx: TranslationRange, ty: TranslationRange }` | `nfp/ifp.rs:10` |
| `PlacedPart` | `struct { inflated_polygon: Polygon64, aabb: Aabb }` | `feasibility/narrow.rs:10` |
| `PlacedIndex` | `struct { parts: Vec<PlacedPart>, tree: RTree<PlacedPartEnvelope> }` | `feasibility/narrow.rs:40` |
| `Aabb` | `struct { min_x, min_y, max_x, max_y: i64 }` | `feasibility/aabb.rs:7` |
| `CfrStatsV1` | `struct { cfr_union_calls, cfr_diff_calls: u64 }` | `cfr.rs:161` |
| `NfpCacheKey` | `struct { shape_id_a, shape_id_b: u64, rotation_steps_b: i16, nfp_kernel: NfpKernel }` | `nfp/cache.rs:24` |

### 1.8 Hol lehet beavatkozni minimális kockázattal

| Beavatkozási pont | Kockázat | Indoklás |
|-------------------|---------|---------|
| `cfr.rs:234` — overlay strategy csere | Alacsony | T06b mérés: Strategy::List a leggyorsabb, nincs jobb opció |
| `nfp_placer.rs:595` — candidate generator módosítás | Közepes | Placement behavior változhat |
| `nfp_placer.rs:294` — CFR hívás átugrása small-sheet esetén | Alacsony | Csak early exit, nem módosítja a logikát |
| Új candidate-driven útvonal építése CFR mellé | Közepes | Feature flag kell, nem production default |

---

## 2. Candidate Source Audit

### 2.1 Full CFR nélküli candidate útvonalak értékelése

#### A) CFR output (jelenlegi)

- **Honnan:** `cfr.rs:compute_cfr_internal()` → `cfr_components`
- **Input:** IFP polygon + összes NFP polygon → `run_overlay` (union + diff)
- **CGAL kell:** Nem önmagában — az NFP provider-től függ
- **IFP kell:** IGEN
- **Várt candidate szám:** Komponensenként ~10-50 vertex × nudge, max 4096 dedup után
- **Scoring:** implicit — component rendezés (min_y → min_x → area)
- **Validator:** `can_place()` párhuzamos polygon intersection
- **Kockázat:** False reject: alacsony (CFR = exact matematikai definíció); False accept: 0
- **Probléma:** 77 NFP polygon union ~130ms → timeout

#### B) IFP boundary / sheet corner candidate-ek

- **Honnan:** `ifp.rs:compute_ifp_rect()` → `IfpRect.polygon.outer` (4 téglalap sarok)
- **Input:** IFP téglalap (4 pont) — már rendelkezésre áll
- **CGAL kell:** NEM
- **IFP kell:** IGEN (4 corner)
- **Várt candidate szám:** 4 candidate/rotation
- **Scoring:** alacsony (nincs információ a valódi "legjobb" helyről)
- **Validator:** `can_place()` — párhuzamos polygon intersection
- **Kockázat:** False reject: MAGAS (sok jó pozíció nem sarokpont); False accept: 0
- **Megjegyzés:** Csak BLF-hez hasonló, nem helyettesíti a CFR-t

#### C) Pairwise NFP vertex candidate-ek

- **Honnan:** NFP polygon vertexei párban: `for each placed_part: NFP(placed, moving).outer`
- **Input:** Összes cached NFP polygon vertexei (world coords)
- **CGAL kell:** Az NFP provider-től függ (CGAL → ~200ms/pair; OldConcave → timeout toxic pair-ökön)
- **IFP kell:** IGEN (inside_ifp szűréshez)
- **Várt candidate szám:** Per placed part ~300-800 vertex × n NFP = n × 300-800 candidate
- **Scoring:** NFP vertex súlyozása: convex sarok > konkáv öböl > edge midpoint
- **Validator:** `can_place()` — párhuzamos polygon intersection
- **Kockázat:** False reject: közepes (konkáv NFP régiók "inside" pontjai kimaradhatnak); False accept: 0
- **Alkalmazhatóság:** LV8-nál 276 rész × 77 NFP vertex × 300-800 = ~6M-17M vertex → túl sok, scoring/korlátozás kell

#### D) Pairwise NFP edge/contact candidate-ek

- **Honnan:** NFP polygon edge-ek midpointjai: `for each edge midpoint → candidate (tx, ty)`
- **Input:** Összes NFP polygon edge midpoints
- **CGAL kell:** Az NFP provider-től függ
- **IFP kell:** IGEN (inside_ifp szűréshez)
- **Várt candidate szám:** Per placed part ~300-800 edge × n = n × 300-800
- **Scoring:** edge hossz szerint csökkenő (hosszabb edge = nagyobb szomszédos rész érintése = jobb illeszkedés)
- **Validator:** `can_place()`
- **Kockázat:** False reject: közepes; False accept: 0

#### E) Already placed part bbox / anchor candidate-ek

- **Honnan:** `placed_for_nfp` — már elhelyezett részek pozíciói
- **Input:** PlacedIndex → PlacedPart.inflated_polygon pozíciók
- **CGAL kell:** NEM
- **IFP kell:** IGEN
- **Várt candidate szám:** n placed part × 1 anchor = n candidate/rotation
- **Scoring:** density-based: annál jobb, minél közelebb van a sheet corner/heather
- **Validator:** `can_place()`
- **Kockázat:** False reject: közepes; False accept: 0
- **Megjegyzés:** Korlátozott érték — új rész általában nem ugyanoda megy, ahova a régi

#### F) BLF / bottom-left candidate-ek

- **Honnan:** BLF algoritmus: sorted by (x, y), first-fit
- **Input:** Semmi extra — greedy/BLF sorrend
- **CGAL kell:** NEM
- **IFP kell:** IGEN (IFP bounding box)
- **Várt candidate szám:** 1 candidate per placement (BLF first-fit)
- **Scoring:** nincs — determinisztikus first-fit
- **Validator:** `can_place()`
- **Kockázat:** False reject: magas (BLF sosem használ NFP-t, csak AABB-t); False accept: 0 a `can_place()` miatt
- **Jelenlegi szerep:** BLF fallback, ha NFP fails (`nfp_failed = true` → BLF-placer-re váltás)

#### G) Current CFR outputból származó candidate-ek (reference)

- **Honnan:** `cfr_components` — jelenlegi CFR komponensek
- **Input:** CFR union + diff (expensive)
- **CGAL kell:** Az NFP provider-től függ
- **IFP kell:** IGEN
- **Várt candidate szám:** Max 10 CFR komponens × 512 vertex = ~5120
- **Scoring:** Komponens area, pozíció (min_y, min_x)
- **Validator:** `can_place()`
- **Kockázat:** False reject: alacsony; False accept: 0
- **Jelenlegi szerep:** Ez a jelenlegi CFR útvonal

#### H) Sliding / exact-fit candidate-ek (későbbi irány)

- **Honnan:** NFP boundary mentén slide-olás, "nest against placed parts" heurisztika
- **Input:** NFP polygon boundary, sliding direction
- **CGAL kell:** IGEN (hole-aware NFP)
- **Kockázat:** Komplex implementáció, nem T06d scope

### 2.2 Candidate Source Összehasonlító Táblázat

| Source | Candidate # | CGAL kell? | IFP kell? | False reject | False accept | Scoring | Implementálható T06d-ben |
|--------|------------|------------|-----------|-------------|--------------|---------|------------------------|
| CFR output (jelenlegi) | ~5K | Provider-től | IGEN | Alacsony | 0 | area, pozíció | Igen (baseline) |
| IFP corners | 4 | NEM | IGEN | MAGAS | 0 | nincs | Igen |
| Pairwise NFP vertex | n×300-800 | Provider-től | IGEN | Közepes | 0 | convex>konkáv | Feltételes |
| Pairwise NFP edge mid | n×300-800 | Provider-től | IGEN | Közepes | 0 | edge hossz | Feltételes |
| Placed bbox anchor | n | NEM | IGEN | Közepes | 0 | density | Igen |
| BLF first-fit | 1 | NEM | IGEN | MAGAS | 0 | nincs | Igen |
| Hybrid (C vertex + IFP corner + placed anchor) |可控 | NEM | IGEN | Alacsony | 0 | multi-faktor | Ajánlott |

---

## 3. Collision Index / CDE Réteg Terv

### 3.1 Név: `SheetCollisionState`

Location: `rust/nesting_engine/src/feasibility/collision_state.rs` (ÚJ)

### 3.2 Adat modell

```rust
// rust/nesting_engine/src/feasibility/collision_state.rs (ÚJ)

use crate::feasibility::aabb::{Aabb, aabb_from_polygon64};
use crate::feasibility::narrow::{PlacedPart, PlacedIndex};
use crate::geometry::types::{Point64, Polygon64};

/// Entry: a placed polygon in world coordinates with spatial index.
#[derive(Debug, Clone)]
pub struct SheetGeometryEntry {
    pub polygon: Polygon64,
    pub aabb: Aabb,
    pub placement_anchor: Point64, // top-left reference point of the placed part
}

/// Per-sheet collision state.
/// Maintains the placed geometry for a single sheet.
/// This is what a candidate-driven placer queries instead of building a full CFR.
#[derive(Debug, Clone, Default)]
pub struct SheetCollisionState {
    entries: Vec<SheetGeometryEntry>,
    /// Broad-phase R-tree (same as existing PlacedIndex).
    placed_index: PlacedIndex,
}

impl SheetCollisionState {
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert a new placed part.
    pub fn insert(&mut self, polygon: Polygon64) {
        let aabb = aabb_from_polygon64(&polygon);
        let anchor = polygon.outer.first().copied().unwrap_or(Point64 { x: 0, y: 0 });
        self.entries.push(SheetGeometryEntry { polygon, aabb, placement_anchor: anchor });
        self.placed_index.insert(PlacedPart { inflated_polygon: polygon, aabb });
    }

    /// Query all entries whose AABB overlaps with the given candidate AABB.
    /// Returns indices into self.entries.
    pub fn query_broad_phase(&self, candidate_aabb: &Aabb) -> Vec<usize> {
        self.placed_index.query_overlaps(candidate_aabb)
    }

    /// Get entry by index (returned from broad_phase query).
    pub fn get(&self, idx: usize) -> &SheetGeometryEntry {
        &self.entries[idx]
    }

    /// Total number of placed entries.
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

/// Collision check result with detailed reason.
#[derive(Debug, Clone)]
pub enum CollisionCheckResult {
    Feasible,
    InfeasibleOverlap { against_idx: usize },
    InfeasibleBinBoundary,
    InfeasibleHoleViolation,
    InfeasibleSpacingViolation,
}
```

### 3.3 Bounding-box / AABB Broad-Phase

**Meglévő infrastruktúra:** `feasibility/narrow.rs:PlacedIndex` — rstar RTree, `query_overlaps()`.

**Újrafelhasználás:** `SheetCollisionState.placed_index` = `PlacedIndex` (már van).

**Működés:**
```rust
// Broad-phase: O(log n) query per candidate
let overlapping_indices = collision_state.query_broad_phase(&candidate_aabb);
```

**TOUCH_TOL:** `scale.rs:TOUCH_TOL = 1` (1 µm) — conservative, touching = infeasible.

### 3.4 Exact Narrow-Phase Check

**Meglévő infrastruktúra:** `narrow.rs:polygons_intersect_or_touch()`.

**Újrafelhasználás:** A `can_place()` függvény már pontosan ezt csinálja.

**Tervezet:**
```rust
pub fn check_collision_exact(
    candidate: &Polygon64,
    bin: &Polygon64,
    collision_state: &SheetCollisionState,
) -> CollisionCheckResult {
    // 1. Bin boundary containment
    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        return CollisionCheckResult::InfeasibleBinBoundary;
    }

    // 2. Strictly within bin (no boundary touching)
    if !poly_strictly_within(candidate, bin) {
        return CollisionCheckResult::InfeasibleBinBoundary;
    }

    // 3. Broad-phase: find potentially overlapping placed parts
    let overlapping = collision_state.query_broad_phase(&candidate_aabb);

    // 4. Narrow-phase: exact polygon intersection check
    for idx in overlapping {
        let other = collision_state.get(idx);
        if aabb_overlaps(&candidate_aabb, &other.aabb) {
            if polygons_intersect_or_touch(candidate, &other.polygon) {
                return CollisionCheckResult::InfeasibleOverlap { against_idx: idx };
            }
        }
    }

    CollisionCheckResult::Feasible
}
```

### 3.5 Spacing Kezelés

**Jelenlegi modell:** Spacing a `geometry/pipeline.rs`-ben történik, az `inflated_polygon`-ban már benne van a spacing (infláció). A `nfp_place()` az inflated polygon-nal dolgozik.

**Következmény:** A candidate-driven placer spacing kezelése automatikus — ha az inflated polygon-okat használja, a spacing már be van építve. A `can_place()` a spacing-inflated polygon-okat kapja.

### 3.6 Sheet Boundary / IFP Containment

**Jelenlegi modell:** `poly_strictly_within(candidate, bin)` — candidate minden pontja a bin-en belül van, nem érinti a határvonalat sem.

**Candidate-driven változat:** Ugyanez — a `check_collision_exact()` bin boundary check-je `poly_strictly_within()`-ot használ.

### 3.7 Holes / cavity_prepack Utáni Geometria

**Jelenlegi modell:** `cavity_prepack v2` hole-collapse után a lyukak bezáródnak. A placement az inflated, hole-collapsed geometrián dolgozik. Hole-aware NFP: CGAL provider `supports_holes() = true` (de holes input jelenleg üres a LV8-nál).

**Candidate-driven változat:** A meglévő `point_in_polygon()` kontén lyukkezelést is végez (`narrow.rs:305-319`). A candidate polygon lyukainak ellenőrzése: ha a bin-nek lyukai vannak, a candidate nem lehet bennük. Ez már a `poly_strictly_within()` része.

### 3.8 Típusok Illeszkedése

| Meglévő típus | Candidate-driven megfelelője | Kapcsolat |
|---------------|---------------------------|-----------|
| `PlacedIndex` | `SheetCollisionState.placed_index` | Azonos — már van |
| `PlacedPart` | `SheetGeometryEntry` | Közel azonos — entry polygon + anchor mezővel |
| `Aabb` | `Aabb` | Azonos |
| `Polygon64` | `Polygon64` | Azonos |
| `can_place()` | `check_collision_exact()` | can_place() output-ját használja |

### 3.9 Kapcsolódás a Meglévő Modulokhoz

| Meglévő modul | Kapcsolódási pont |
|--------------|------------------|
| `feasibility/narrow.rs` | `PlacedIndex`, `can_place()`, `polygons_intersect_or_touch()` → újrat.Használva candidate-driven-ban |
| `feasibility/aabb.rs` | `aabb_from_polygon64()`, `aabb_inside()`, `aabb_overlaps()` → újrafelhasználva |
| `geometry/scale.rs` | `TOUCH_TOL=1` → újrafelhasználva |
| `nfp/provider.rs` | NFP provider választás candidate generation-hez (NFP vertex enumeration) |
| `nfp/cache.rs` | NFP cache → candidate source: pairwise NFP polygon vertexeinek kinyerése |
| `cfr.rs` | CFR reference oracle (opcionális): ha candidate-driven nem talál candidate-et, CFR fallback |
| `nfp/nfp_validation.rs` | `polygon_validation_report()` → candidate validation részét képezheti |

### 3.10 Jagua-rs / Külső CDE Adapter Opcionális Terv

**Csak jövőbeli bővítési pontként, NEM T06d scope:**

```rust
// Későbbi opció: jagua-rs adapter a pairwise collision check helyett
pub trait CollisionDetector: Send + Sync {
    fn check_batch(&self, candidates: &[Polygon64], placed: &[Polygon64]) -> Vec<bool>;
}
```

**T06d-ben ez NEM szerepel** — a meglévő `can_place()` / `SheetCollisionState` a minimál implementáció.

---

## 4. Existing Optimizer Preservation Plan

### 4.1 Megmaradó Komponensek

| Komponens | Fájl | Státusz |
|-----------|------|--------|
| Greedy multi-sheet | `multi_bin/greedy.rs` | ÉRINTETLEN |
| SA search | `search/sa.rs` | ÉRINTETLEN |
| Multi-sheet iteráció | `greedy.rs` | ÉRINTETLEN |
| Slide compaction | `greedy.rs` | ÉRINTETLEN |
| Quality profile-ok | CLI / main.rs | ÉRINTETLEN |
| NFP provider selection | `nfp/provider.rs` + env | ÉRINTETLEN |
| NFP cache | `nfp/cache.rs` | ÉRINTETLEN |
| BLF fallback | `placement/blf.rs` | ÉRINTETLEN |
| Part ordering (ByArea, ByInputOrder) | `greedy.rs` | ÉRINTETLEN |

### 4.2 Módosított Függvények (Minimális)

| Fájl | Függvény | Változás |
|------|---------|---------|
| `nfp_placer.rs` | `nfp_place()` | Új feature flag branch: ha `CANDIDATE_DRIVEN=1`, más candidate generator + collision state útvonal |
| `nfp_placer.rs` | `append_candidates()` | CFR vertex enumeration kiegészítése: NFP vertex + edge midpoint + IFP corner + placed anchor |
| ÚJ: `feasibility/collision_state.rs` | `SheetCollisionState` | Új modul |

### 4.3 Feature Flag

```rust
// rust/nesting_engine/src/placement/nfp_placer.rs

const FEATURE_CANDIDATE_DRIVEN: bool = std::env::var("NESTING_ENGINE_CANDIDATE_DRIVEN")
    .map(|v| v == "1")
    .unwrap_or(false);

pub fn nfp_place(...) {
    if FEATURE_CANDIDATE_DRIVEN {
        // Candidate-driven útvonal
        candidate_driven_place(...)
    } else {
        // CFR útvonal (jelenlegi)
        nfp_place_cfr(...)
    }
}
```

### 4.4 Régi vs. Új Útvonal Összehasonlítás

| Aspektus | Régi CFR útvonal | Új candidate-driven útvonal |
|----------|------------------|---------------------------|
| Candidate source | CFR komponens vertex + nudge | NFP vertex + edge mid + IFP corner + placed anchor |
| Collision check | `can_place()` + PlacedIndex | `check_collision_exact()` + SheetCollisionState |
| CFR használat | Igen — candidate extraction | Nem — pairwise collision |
| Timeout kockázat | Igen — 77 NFP polygon union | Nem — nincs CFR union |
| False reject | Alacsony | Közepes (konkáv régiók) |
| Spacing | Auto (inflated polygon) | Auto (inflated polygon) |
| Placement behavior | Eredeti | Azonos vagy közel azonos |

### 4.5 Benchmark Stratégia

```bash
# Régi CFR baseline
NESTING_ENGINE_CANDIDATE_DRIVEN=0 \
  timeout 300 ./target/debug/nesting_engine nest --placer nfp \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json

# Új candidate-driven
NESTING_ENGINE_CANDIDATE_DRIVEN=1 \
  timeout 300 ./target/debug/nesting_engine nest --placer nfp \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

---

## 5. Exact Validation Gate

### 5.1 Validator Követelmények

**Kötelező szempontok:**

| Szempont | Megvalósítás |
|----------|-------------|
| No overlap | `polygons_intersect_or_touch()` → ha true: INFEASIBLE |
| Sheet bounds containment | `poly_strictly_within(candidate, bin)` → ha false: INFEASIBLE |
| Exact spacing | Inflated polygon használata (spacing már az inflated részben van) |
| Holes / inner contour safety | `point_in_polygon()` hole ellenőrzés a `poly_strictly_within()`-ban |
| Pairwise collision against all placed | `PlacedIndex.query_overlaps()` + narrow phase |
| No silent fallback | Ha validator hibát ad → candidate REJECT, nincs "lehet hogy mégis jó" |
| False accept = 0 | `can_place()` exact geometry check → minden overlap REJECT |
| False reject mérhető | CFR vs candidate-driven: placed count különbség → nem correctness bug |

### 5.2 Meglévő Modul Újrafelhasználása

```rust
// feasibility/narrow.rs — már létezik, nem kell új validator
pub fn can_place(candidate: &Polygon64, bin: &Polygon64, placed: &PlacedIndex) -> bool {
    // bin boundary + poly_strictly_within + pairwise collision
}
```

### 5.3 Új Modul Szükségessége

**Nem kell új validator** — a `can_place()` / `check_collision_exact()` már pontosan azt csinálja, amit a candidate-driven placementhez kell.

**Új elem:** `SheetCollisionState` mint a `PlacedIndex` wrapper-e, de ez nem validator, hanem collision state management.

### 5.4 Tolerancia

```rust
// scale.rs
pub const TOUCH_TOL: i64 = 1; // 1 µm — touching = infeasible (manufacturing safety)
```

Touching = infeasible: conservative policy. Ez már a meglévő `aabb_overlaps()` és `polygons_intersect_or_touch()`-ban van implementálva.

### 5.5 Hibareportálás

```rust
#[derive(Debug, Clone)]
pub enum PlacementRejectionReason {
    BinBoundaryViolation,
    OverlapWithPlaced { placed_idx: usize },
    HoleViolation,
    SpacingViolation,
    PolygonInvalid,
}
```

---

## 6. Prototype Options Comparison

### Opció A) Minimal In-Repo Candidate-Driven Placer Prototype

**Leírás:** Új `candidate_driven_place()` függvény a `nfp_placer.rs`-ben, feature flag mögött.

**Előnyök:**
- Teljes kontroll a kód felett
- Nem függ külső library-tól
- Step-by-step fejlesztés lehetséges
- A meglévő `can_place()` / `PlacedIndex` újrafelhasználható
- Feature flag → rollback: trivial
- Nem módosítja a production behavior-t

**Hátrányok:**
- Candidate enumeration O(n × m) lehet nagy
- Konkáv régiókban false reject lehetősége magasabb, mint CFR-nél
- Pairwise NFP vertex enumeration: az NFP polygon-ok a cache-ben vannak (world coords), ki kell nyerni őket

**Becsült fejlesztési idő:** 2-3 nap

**Járhatóság:** MAGAS

### Opció B) External CDE / jagua-rs Style Spike

**Leírás:** Külön benchmark binary, jagua-rs library-val, csak PoC célra.

**Előnyök:**
- Ipari szabvány CDE-vel összehasonlítható
- A jaguars-pipeline megmutatja a "hogyan kellene" esztét
- Eldönthető, érdemes-e adaptert építeni

**Hátrányok:**
- jagua-rs licencia: GPL → nem production
- Adapter architektúra komplexitás
- Collision detection vs. NFP placement: jagua-rs más célt szolgál (spacing-aware pack)
- A jelenlegi `can_place()` / `PlacedIndex` így is kell a validationhoz
- A T06d scope nem ez kell legyen

**Becsült fejlesztési idő:** 5-7 nap (beleértve adaptert + benchmarkot)

**Járhatóság:** KÖZEPES — csak benchmark célra, nem production integráció

### Ajánlott: **Opció A**

Indoklás:
1. A meglévő `can_place()` + `PlacedIndex` már pontosan azt tudja, amire a candidate-driven validatorhoz szükség van
2. Feature flag: triviális rollback
3. Nem igényel külső library-t
4. LV8 adatokon közvetlenül mérhető a CFR vs candidate-driven
5. A candidate enumeration O(n × vertex) és korlátozható scoringgal

---

## 7. Benchmark Terv

### 7.1 Metrikák

| Metrika | Mértékegység | Gyűjtés módja |
|---------|-------------|--------------|
| Current CFR placer baseline | bool | Feature flag toggle |
| Candidate-driven prototype | bool | Feature flag toggle |
| Placed count | db | `PlacementResult.placed.len()` |
| Sheet count | db | Sheet iterációk száma |
| Runtime | ms | `Instant` before/after |
| Candidate count | db | `append_candidates()` counter |
| Rejected candidate count | db | `can_place()` false return |
| Broad-phase hit count | db | `PlacedIndex.query_overlaps()` hívás |
| Narrow-phase check count | db | `polygons_intersect_or_touch()` hívás |
| False accept count | db | Kézi ellenőrzés vagy SVG output |
| Fallback count (CFR fallback) | db | Ha candidate-driven nem talál, CFR-t hív |
| Exact validator status | PASS/FAIL | `can_place()` minden reject-ért hibát ad |
| Utilization | % | `(placed area) / (sheet area × sheet count)` |
| Spacing violation | db | `can_place()` spacing-related reject |
| Bounds violation | db | bin boundary reject |
| Overlap violation | db | pairwise overlap reject |
| CFR time (baseline only) | ms | `CFR_DIAG_V1` log |
| CFR union polygon count (baseline only) | db | `cfr_stats` |

### 7.2 Benchmark Parancsok

```bash
# Régi CFR baseline
NESTING_ENGINE_CANDIDATE_DRIVEN=0 \
NESTING_ENGINE_CFR_DIAG=1 \
timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp \
  --quality-profile default \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  2>&1 | tee tmp/t06c_baseline.log

# Új candidate-driven prototype
NESTING_ENGINE_CANDIDATE_DRIVEN=1 \
NESTING_ENGINE_CANDIDATE_DIAG=1 \
timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp \
  --quality-profile default \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  2>&1 | tee tmp/t06c_candidate_driven.log
```

### 7.3 Correctness Gate

```
PASS criteria:
  - placed count (candidate-driven) >= placed count (CFR baseline) × 0.95
  - false accept count = 0
  - spacing violation = 0
  - bounds violation = 0
  - overlap violation = 0

FAIL criteria:
  - candidate-driven placed count < CFR baseline × 0.95
  - bármilyen false accept
  - bármilyen spacing violation
```

---

## 8. Kockázatelemzés

### 8.1 Candidate Generator Túl Kevés Jelöltet Ad → Rossz Kihasználtság

**Kockázat:** MAGAS
**Ok:** Ha a candidate enumeration csak IFP corner + placed anchor, a candidate szám nagyon kicsi. A greedy/SA a legjobb candidate-et választja, de ha nincs közel a optimumhoz, a placed count alacsony.
**Kezelés:** NFP vertex + edge midpoint + placed anchor + IFP corner kombinálása. Ha a placed count alacsonyabb a CFR baseline-nál, CFR fallback.

### 8.2 Broad-Phase Túl Sok találatot Ad → Nem Gyorsul

**Kockázat:** KÖZEPES
**Ok:** `PlacedIndex` query mindig O(log n), de a narrow phase minden overlapping part-ra fut.
**Kezelés:** A candidate AABB-k kicsik és sűrűn elhelyezettek → broad-phase filtering már megfelelő. LV8-nál 77 placed part → narrow phase max 77 check per candidate.

### 8.3 Exact Validator Túl Lassú → Új Bottleneck

**Kockázat:** KÖZEPES
**Ok:** `can_place()` narrow phase: O(ring_a_len × ring_b_len). LV8 konkáv polygonoknál 500+ vertex per ring → 500×500 = 250K operations per pair.
**Kezelés:** A candidate count korlátozása (MAX_CANDIDATES_PER_PART=4096) + candidate scoring (CFR komponens vertex > NFP vertex > IFP corner).

### 8.4 NFP Cache Túl Nagy → Memória Gond

**Kockázat:** ALACSONY
**Ok:** `MAX_ENTRIES = 10,000` — LV8-nál ~276×275/2 = ~38K NFP pár lenne, de a cache 10K-nál clearel. Ez jelenleg is így működik.
**Kezelés:** Nem kell változtatás.

### 8.5 Spacing Kezelése Pontatlan

**Kockázat:** ALACSONY
**Ok:** A spacing a geometry pipeline-ban az inflated polygon-ba van beépítve. Ha candidate-driven az inflated polygon-nal dolgozik, a spacing automaticamente helyes.

### 8.6 Holes / cavity_prepack Visszabontás Problémás

**Kockázat:** KÖZEPES
**Ok:** cavity_prepack hole-collapse után a lyukak eltűnnek. A candidate-driven placer az inflated, hole-collapsed geometrián dolgozik. Ha valahol hole-aware placement kellene, az csak a CGAL providerrel érhető el.
**Kezelés:** CGAL provider `supports_holes() = true` — a pairwise NFP check hole-aware lesz CGAL provider esetén.

### 8.7 SA Cost Összehasonlíthatósága Romlik

**Kockázat:** ALACSONY
**Ok:** A candidate-driven útvonal más candidate-forrásból dolgozik → az SA iterációk alatt a cost landscape más lesz. De a `can_place()` azonos mindkét útvonalon, tehát a feasibility oracle ugyanaz.
**Kezelés:** Feature flag: SA nem módosul, csak a placement feasibility-oracle változik.

### 8.8 Régi CFR és Új Candidate-Driven Eredmények Eltérnek

**Kockázat:** KÖZEPES
**Ok:** Ha a candidate-driven candidate enumerációja más mint a CFR vertexei, a greedy más sorrendben találhat megoldást. Az SA iterációk eltérőek lehetnek.
**Kezelés:** Az első ELFOGADHATÓ candidate mindkét útvonalon megegyezik, mert a `can_place()` identical. A különbség csak a "legjobb" kiválasztásban van, ami placement quality, nem correctness.

---

## 9. T06d Implementációs Task Javaslat

### T06d — Minimal Candidate-Driven NFP Placer Prototype Behind Feature Flag

---

#### Task címe

**T06d — Minimal candidate-driven NFP placement prototype behind `NESTING_ENGINE_CANDIDATE_DRIVEN=1` feature flag**

#### Célja

- CFR-union nélküli candidate generation + pairwise exact collision validation útvonal építése
- LV8 benchmarkon correctness és performance összehasonlítás a CFR útvonallal
- Eldönteni, hogy a candidate-driven út életképes-e production használatra

#### Nem célok

- CFR kikapcsolása production módban
- Optimalizáló (greedy/SA/multi-sheet/compaction) újraírása
- jagua-rs integráció
- NFP provider csere
- Spacing modell módosítása
- Production Dockerfile változtatás

#### Érintett fájlok

| Fájl | Változás |
|------|---------|
| `rust/nesting_engine/src/feasibility/collision_state.rs` | ÚJ: SheetCollisionState modul |
| `rust/nesting_engine/src/feasibility/mod.rs` | +`pub mod collision_state` |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | +`candidate_driven_place()` függvény, feature flag branch |
| `rust/nesting_engine/src/placement/mod.rs` | Érintetlen |
| `rust/nesting_engine/src/nfp/nfp_validation.rs` | Érintetlen |
| `rust/nesting_engine/src/feasibility/narrow.rs` | Érintetlen (újrafelhasználva) |

#### Minimális implementáció

1. **`SheetCollisionState`** (`collision_state.rs`):
   - `SheetGeometryEntry { polygon, aabb, placement_anchor }`
   - `insert(polygon)` → PlacedIndex update
   - `query_broad_phase(aabb) → Vec<usize>`
   - `check_collision_exact(candidate, bin) → CollisionCheckResult`

2. **Candidate generator** (`nfp_placer.rs`):
   - NFP vertex enumeration: `for each cached NFP polygon: for each vertex → candidate(tx, ty)`
   - IFP corner: 4 sarokpont
   - Placed anchor: placed részek anchor pontjai
   - Inside-IFP szűrés: `inside_ifp(tx, ty, &ifp)`
   - Scoring: IFP corner < placed anchor < NFP vertex
   - Max candidate: 4096 (dedup után)

3. **Feature flag integration**:
   - `NESTING_ENGINE_CANDIDATE_DRIVEN=1` → `candidate_driven_place()`
   - Default: `NESTING_ENGINE_CANDIDATE_DRIVEN=0` → `nfp_place_cfr()` (jelenlegi útvonal)

4. **Validation**:
   - `can_place()` meglévő függvény újrafelhasználása
   - `PlacedIndex` mint collision state

#### Feature flag neve

`NESTING_ENGINE_CANDIDATE_DRIVEN=1`

#### Benchmark parancsok

```bash
cd /home/muszy/projects/VRS_nesting

# Baseline (CFR útvonal)
NESTING_ENGINE_CANDIDATE_DRIVEN=0 \
NESTING_ENGINE_CFR_DIAG=1 \
timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp \
  --quality-profile default \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json

# Candidate-driven prototype
NESTING_ENGINE_CANDIDATE_DRIVEN=1 \
timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp \
  --quality-profile default \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

#### Acceptance criteria

```
PASS (candidate-driven prototype):
  1. placed_count >= baseline_placed_count × 0.95
  2. false_accept_count = 0
  3. runtime <= baseline_runtime × 1.5
  4. cargo check -p nesting_engine → 0 error
  5. cargo test --lib → minden eddigi teszt PASS (nem csökkenhet a pass rate)

FAIL (prototype):
  1. placed_count < baseline × 0.95
  2. bármilyen false accept (overlap vagy spacing violation)
  3. runtime > baseline × 1.5 (nem elég gyors)
```

#### Rollback stratégia

- `NESTING_ENGINE_CANDIDATE_DRIVEN=0` → jelenlegi CFR útvonal, változatlan behavior
- Feature flag default: 0 (CFR útvonal)
- Nincs data migration, nincs state change
- Rollback = feature flag visszaállítás

---

## 10. Módosított fájlok listája

Audit fázisban: **0 fájl módosítva** (csak report + checklist íródott)

Implementációs fázisban (T06d):
- `rust/nesting_engine/src/feasibility/collision_state.rs` (ÚJ)
- `rust/nesting_engine/src/feasibility/mod.rs` (ÚJ module export)
- `rust/nesting_engine/src/placement/nfp_placer.rs` (ÚJ candidate_driven_place() + feature flag)

## 11. Futtatott parancsok

```bash
# Az audit során:
cd /home/muszy/projects/VRS_nesting
git diff --stat
# (csak report/checklist fájlok íródnak, nincs kód módosítás)

# Az implementációs fázisban (T06d):
cd /home/muszy/projects/VRS_nesting/rust/nesting_engine
cargo check -p nesting_engine
cargo test --lib
```

## 12. Ismert limitációk

1. **Full CFR kiváltás nem lehetséges**: A candidate-driven út nem 100%-os CFR replacement. Konkáv régiókban a false reject arány magasabb lehet. A CFR referenciaként megmarad.

2. **Candidate explosion**: NFP vertex enumeration n×(300-800) candidate per rotation → korlátozás (scoring + dedupe) kell, különben a `can_place()` bottleneck lesz.

3. **Pairwise NFP vertex extraction**: A jelenlegi `nfp_polys` world-coord NFP polygon-okat tárol. Ezek vertexeinek kinyerése triviális, de a candidate scoring implementálása külön munka.

4. **CGAL provider szükségessége**: A toxic concave NFP pair-ök (lv8_pair_01: 177K fragment) az `old_concave` providerrel timeout-olnak. Candidate-driven vertex enumeration csak a cached NFP polygon-okból működik. Ha az NFP soha nem lett kiszámolva (cache miss a toxic pair-en), a candidate-driven út nem kap NFP vertexeket. Jelenlegi megoldás: CGAL provider használata `NESTING_ENGINE_NFP_KERNEL=cgal_reference` mellett.

5. **Hole-aware candidate generation**: Ha a bin-nek lyukai vannak (cavity_prepack után ez nem fordul elő LV8-nál, de más fixture-ekben igen), a hole-fill candidate-ek generálása külön implementációt igényel.

6. **SA/greedy interaction**: A candidate-driven útvonal más placement ordert eredményezhet, mert más candidate-forrásból dolgozik. Az SA cost landscape megváltozik, de a feasibility oracle (`can_place()`) azonos.

---

## Appendix: T06b Snapshot Helye a Kódban

A T06b snapshot funkció (`CFR SNAP` log üzenetek):

| Fájl | Sor | Funkció |
|------|-----|---------|
| `cfr.rs:42-85` | 42 | `write_cfr_snapshot_if_enabled()` — JSON file-ba mentés |
| `cfr.rs:224-227` | 224 | Snapshot trigger: ha `NESTING_ENGINE_CFR_SNAPSHOT_DIR` set |
| `cfr.rs:149` | 149 | `SNAPSHOT_SEQ` atomic counter |

Snapshot feltétel: `nfp_poly_count >= threshold` (default: 50) vagy `NESTING_ENGINE_CFR_SNAPSHOT_DIR` set.

---

## Appendix: PlacedIndex Architektúra (R-Tree)

A `PlacedIndex` (`feasibility/narrow.rs:40`) **már tartalmazza** a spatial indexet:

```rust
pub struct PlacedIndex {
    parts: Vec<PlacedPart>,              // O(1) index-by-idx
    tree: RTree<PlacedPartEnvelope>,    // O(log n) spatial query
}
```

A `PlacedPartEnvelope` implementálja az `RTreeObject` trait-et, az AABB-ját használva spatial key-ként.

Ez azt jelenti, hogy a **broad-phase spatial index már létezik és működik**. A candidate-driven útvonal ezt azonnal újrafelhasználhatja.
