# SGH-Q00 — Sparrow/jagua-rs Quality-Feature Parity Audit

## Purpose

Kódszintű bizonyíték alapján megállapítja, milyen nesting-minőségjavító funkciókat tartalmaz az eredeti `jagua-rs` / `Sparrow`, ezekből mit vett át a VRS, mit butított le, és mit kell teljesen vagy VRS-kompatibilisen portolni ahhoz, hogy legalább az eredeti minőségi szintet célozzuk.

Ez **audit/report task**: production kód nem változott, külső forrás nem volt vendorálva.

---

## Audit scope és dependency gate

**Dependency:** `sgh_05_transfer_swap_reinsert_move_operators.md` → első sor `PASS`, tartalmazza `SGH-06_STATUS: READY`. ✓

---

## Külső forrás inventory

| Repo | URL | Commit hash | Licenc | Státusz |
|---|---|---|---|---|
| JeroenGar/jagua-rs | https://github.com/JeroenGar/jagua-rs | `43e81373` | MPL-2.0 | CLONED |
| JeroenGar/sparrow | https://github.com/JeroenGar/sparrow | `a4bfbbe0` | MIT | CLONED |
| coroush/sparrow | https://github.com/coroush/sparrow | `5df9ce15` | MIT (fork) | REFERENCED (prior SGH-00 audit) |
| coroush/sparrow-grasshopper | https://github.com/coroush/sparrow-grasshopper | `0c9a1362` | — | CLONED (C# GH wrapper only) |

---

## jagua-rs auditált fájlok

- `jagua-rs/src/geometry/geo_enums.rs` → `RotationRange`
- `jagua-rs/src/geometry/d_transformation.rs` → `DTransformation`
- `jagua-rs/src/geometry/transformation.rs` → `Transformation` (3×3 matrix)
- `jagua-rs/src/geometry/original_shape.rs` → `OriginalShape` (preprocessing pipeline)
- `jagua-rs/src/collision_detection/cd_engine.rs` → `CDEngine`, `CDEConfig`
- `jagua-rs/src/entities/item.rs` → `Item` (shape_orig, shape_cd, allowed_rotation)

## Sparrow auditált fájlok

- `src/config.rs` → `SparrowConfig`, `ExplorationConfig`, `CompressionConfig`
- `src/quantify/overlap_proxy.rs` → `overlap_area_proxy` (Algorithm 3)
- `src/quantify/tracker.rs` → `CollisionTracker` (Algorithm 8)
- `src/sample/search.rs` → `search_placement` (Algorithm 6)
- `src/optimizer/separator.rs` → `Separator` (Algorithm 9, 10)
- `src/optimizer/worker.rs` → `SeparatorWorker` (Algorithm 5)
- `src/optimizer/explore.rs` → `exploration_phase` (Algorithm 12)
- `src/optimizer/compress.rs` → `compression_phase` (Algorithm 13)

## VRS auditált fájlok

- `rust/vrs_solver/src/optimizer/separator.rs` → `VrsCollisionTracker`, `VrsSeparator`
- `rust/vrs_solver/src/optimizer/score.rs` → `ScoreModel`, `ScoreWeights`, `ObjectiveBreakdown`
- `rust/vrs_solver/src/optimizer/working.rs` → `WorkingLayout`, commit gate
- `rust/vrs_solver/src/optimizer/moves.rs` → `MoveExecutor`, move operators (SGH-05)
- `rust/vrs_solver/src/item.rs` → `Part`, `normalize_allowed_rotations`
- `rust/vrs_solver/src/sheet.rs` → `Stock`, `SheetShape`, `cost_per_use`

---

## Feature-by-feature audit

### 1. RotationRange / continuous vs. discrete rotation

**jagua-rs forrás:**
```rust
// jagua-rs/src/geometry/geo_enums.rs
pub enum RotationRange {
    None,
    Continuous,
    Discrete(Vec<f32>),
}
```
Az `Item` tárolja: `allowed_rotation: RotationRange`. A `DTransformation.rotation` `f32` radián — kontinuus.

**Sparrow forrás:**
```rust
// src/sample/search.rs
let wiggle = item.allowed_rotation == RotationRange::Continuous;
```
Kontinuus rotáció esetén a `coord_descent` refine lépéseiben rotációs perturbáció is aktív (`wiggle=true`).

**VRS jelenlegi:**
```rust
// rust/vrs_solver/src/item.rs
pub allowed_rotations_deg: Vec<i64>,
// normalize_allowed_rotations: csak 0, 90, 180, 270 megengedett
```
`rotation_deg: i64` — csak 4 értéket vesz fel.

**Parity: MISSING** — kontinuus rotáció és a `RotationRange::Continuous` ág nincs. A VRS kizárólag 4 fix szög közül választ.

**Quality risk:** Kontinuus rotáció nagy minőségjavulást ad szabálytalan alakzatoknál (Paper: 5-15% density gain). Rectangular items esetén negligibilis, de a VRS Phase 2 irregular-nál kritikus lesz.

**Szükséges migráció:** `RotationPolicy` trait bevezetése; `DiscreteRotationPolicy` (jelenlegi VRS) és `ContinuousRotationPolicy` (jagua-rs RotationRange::Continuous) implementáció.

---

### 2. Continuous sampling + local rotation wiggle/refinement

**jagua-rs / Sparrow forrás:**
```rust
// src/sample/search.rs — Algorithm 6
// 1. Focussed uniform samples around current placement (BBox sampler)
// 2. Container-wide uniform samples
// 3. Pre-refine coord descent (n_coord_descents best samples)
// 4. Final coord descent (finest refinement)
// CDConfig: t_step_init, t_step_limit, r_step_init, r_step_limit
// wiggle = allowed_rotation == Continuous → rotation coordinate descent
```
`UniformBBoxSampler` mintáz kontinuus (x, y, r) térben. A két lépéses refine fokozatosan finomít.

**VRS jelenlegi:**
`generate_candidates_with_sheets` (candidates.rs) LBF-alapú diskrét pozíció-set. Nincs stochasztikus mintavétel, nincs coord descent, nincs rotation wiggle.

**Parity: MISSING** — stochasztikus mintavétel, focussed sampling és coord descent nincs. VRS determinisztikus LBF kandidátokat használ.

**Quality risk:** A Sparrow minőségének nagy részét a stochasztikus mintavétel és a helyi refine adja (Paper Algorithm 6). A VRS csak determinisztikus LBF grid-et néz.

---

### 3. Transformation model

**jagua-rs forrás:**
```rust
// transformation.rs
// Transformation: 3×3 matrix form
// compose/decompose, rotate, translate, rotate_translate, inverse
// DTransformation: (rotation: f32 radians, translation: (f32, f32))
```
Teljes merev test transzformáció, invertálható, chainelhető.

**VRS jelenlegi:**
`Placement { x: f64, y: f64, rotation_deg: i64, sheet_index: usize }` — nem 3×3 mátrix, nincs inverse, nincs chain. Rotáció diskrét integer.

**Parity: PROXY** — a VRS egyszerűsített anchor+rotation modell, ami elegendő 4 fixált szög esetén, de incompatibilis a jagua-rs `DTransformation` kontinuus modellel. Irregular Phase 2-höz full transformation model kell.

---

### 4. jagua-rs CDE / exact shape collision usage

**jagua-rs forrás:**
```rust
// cd_engine.rs
// CDEngine: quadtree-based (configurable depth) + hazard registry
// detect_poly_collision: edge intersection + containment check
// collect_poly_collisions: reports all colliding hazards
// detect_surrogate_collision: fast-fail via poles + piers
// CDEConfig: { quadtree_depth: u8, cd_threshold: u8, item_surrogate_config: SPSurrogateConfig }
```
Pontos poligon–poligon ütközésvizsgálat, quadtree-vel gyorsítva. Az `SPSurrogate` (poles + piers) fast-fail: hamis pozitívot nem ad.

**VRS jelenlegi:**
```rust
// separator.rs
fn bbox_overlap_area(a: &PlacedBbox, b: &PlacedBbox) -> f64 {
    let dx = (a.x2.min(b.x2) - a.x1.max(b.x1)).max(0.0);
    // axis-aligned bounding box only
}
```
Kizárólag AABB overlap. Nincs quadtree, nincs poligon, nincs surrogate.

**Parity: PROXY** — AABB proxy rectangular items esetén elfogadható (AABB = exact), de irregular alakzatoknál minőségvesztés. Boundary check: `rect_within_boundary` szintén AABB.

**Quality risk:** Rectangular packing esetén PROXY elegendő. Irregular Phase 2-höz CDEngine port szükséges. Jelenlegi PROXY nincs jelölve quality-risk flaggel a kódban.

---

### 5. Collision severity / penetration / smooth loss

**Sparrow forrás:**
```rust
// quantify/overlap_proxy.rs — Algorithm 3
pub fn overlap_area_proxy(sp1: &SPSurrogate, sp2: &SPSurrogate, epsilon: f32) -> f32 {
    let pd = (p1.radius + p2.radius) - p1.center.distance_to(&p2.center);
    let pd_decay = match pd >= epsilon {
        true => pd,
        false => epsilon.powi(2) / (-pd + 2.0 * epsilon),  // smooth transition
    };
    total_overlap += pd_decay * f32::min(p1.radius, p2.radius);
}
```
Pole–pole penetration depth, sima átmenet az ε küszöb körül. A `CollisionTracker` per-pair és per-container `loss` + `weight` pár.

**VRS jelenlegi:**
```rust
// separator.rs
fn bbox_overlap_area(a: &PlacedBbox, b: &PlacedBbox) -> f64 {
    dx * dy  // area-based, no penetration depth decay
}
pub fn boundary_loss(&self, i: usize) -> f64 {
    if self.boundary_valid[i] { 0.0 } else { BOUNDARY_LOSS_PROXY }  // binary, not smooth
}
```
Nincs penetration depth, nincs smooth loss formula, nincs ε-alapú sima átmenet. Boundary loss bináris (0/1), nem graduális.

**Parity: PROXY** — Rectangular AABB area overlap közelít, de a sima Sparrow loss függvényt nem valósítja meg. Boundary loss bináris → rossz gradient a GLS-nek.

**Quality risk:** Smooth loss gradient nélkül a GLS kevésbé hatékonyan irányítja az itemeket.

---

### 6. Shape-based penalty

**Sparrow forrás:**
A kollízió kvantifikáció pole-alapú (SPSurrogate): a penalties poligon alakján alapulnak (konvex burokhoz közelítve). `min_item_separation` configurable offset-tel kiterjeszthető.

**VRS jelenlegi:**
`ScoreModel` (score.rs): `overlap_penalty_per_pair` és `boundary_penalty_per_item` — flat penalty per violation count. Nincs shape-based súlyozás, nincs area-arányos penalty-fokozás a separator GLS-ében.

**Parity: MISSING** — shape-based (area- vagy volume-proportional) penalty modell nincs. A `BOUNDARY_LOSS_PROXY = 1.0` constant, shape-független.

---

### 7. GLS dynamic weights

**Sparrow forrás:**
```rust
// quantify/tracker.rs — Algorithm 8
pub fn update_weights(&mut self) {
    let max_loss = ...;  // max across all pairs
    for e in pair_collisions + container_collisions {
        let multiplier = match e.loss == 0.0 {
            true  => GLS_WEIGHT_DECAY,  // decay back to 1.0
            false => GLS_WEIGHT_MIN_INC_RATIO + (MAX - MIN) * (e.loss / max_loss),
        };
        e.weight = (e.weight * multiplier).max(1.0);
    }
}
```
Collision pair szintű, loss-arányos növelés, max_loss normalizáció, decay ha nincs collision.

**VRS jelenlegi:**
```rust
// separator.rs
pub fn update_weights(&mut self, decay: f64, weight_max: f64) {
    for each pair with loss > 0:
        *w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max);
    // no max_loss normalization, additive (not multiplicative)
}
```
GLS weights megvannak, de:
- Additive increment (nem multiplicative mint Sparrowban)
- Nincs max_loss normalizáció
- Nincs külön min/max ratio interpoláció
- Decay: weight alaptól nem függ explicit módon

**Parity: PARTIAL** — GLS struktúra jelen van, de a konkrét weight update formula eltér a Sparrow Algorithm 8-tól.

---

### 8. Separator incumbent / restore / strike / best-state

**Sparrow forrás:**
```rust
// optimizer/separator.rs — Algorithm 9
let mut min_loss_sol = (self.prob.save(), self.ct.save());
// strikes: counter per failed 'outer' attempt (< 98% improvement threshold)
self.rollback(&min_loss_sol.0, Some(&min_loss_sol.1));
// rollback with tracker snapshot (restore_but_keep_weights)
```
`CTSnapshot` megőrzi a loss értékeket, de megtartja a súlyokat (`restore_but_keep_weights`). Incumbent = legjobb loss state.

**VRS jelenlegi:**
```rust
// separator.rs
let mut best_layout = current.snapshot();
// strikes: simple counter
// rollback: best_layout visszaállítása (munkaterület visszagörgetés)
// Nincs CT snapshot / separate weight preservation
```
Rollback van, strikes van, de nincs külön `restore_but_keep_weights` — VRS fullrestet hoz létre CT-t rollback nélkül.

**Parity: PARTIAL** — Incumbent tracking és rollback jelen van, de a weight-preserving CT restore MISSING. Ez azt jelenti, hogy minden rollback elveszíti a tanult GLS súlyokat.

---

### 9. move_items_multi / multi-worker / multi-order logic

**Sparrow forrás:**
```rust
// optimizer/separator.rs — Algorithm 10
fn move_items_multi(&mut self) -> SepStats {
    self.workers.par_iter_mut().map(|worker| {
        worker.load(&master_sol, &self.ct);
        worker.move_items()  // each with shuffled item order
    }).sum();
    // pick best by weighted_loss
    // discard all others
}
// n_workers configurable: default 3
```
Párhuzamos munkások, minden worker más véletlenszerű sorrendben mozgatja az itemeket, a legjobb összeredményt tartja meg.

**VRS jelenlegi:**
```rust
// separator.rs — VrsSeparator
// Single-threaded, deterministic
// No workers, no random ordering
// Selects worst collider by weighted loss (deterministic max)
```
Egyetlen munkás, determinisztikus sorrend (max weighted loss kiválasztás), nincs rayon párhuzamosság.

**Parity: MISSING** — multi-worker párhuzamos keresés nincs. Ez jelentős quality gap: a Sparrow minden iterációban 3 független véletlenszerű sorrend legjobb eredményét veszi.

---

### 10. BLF/LBF role

**Sparrow forrás:**
`search_placement` `UniformBBoxSampler` mintáz egy bbox-on belül. LBF-et a Sparrow a söprésvonal (SPP) szélesség-csökkentéssel implementálja: az exploration phase shrink_step értéke a söprésvonal határ. Az ütközés-mentesség a CDE-en keresztül ellenőrződik, nem LBF-lista alapján.

**VRS jelenlegi:**
`generate_candidates_with_sheets` (candidates.rs): valós LBF kandidátlista (y növekvő, x növekvő, used-sheet-first). Az `lbf_clear_on_sheet` (moves.rs) ezt használja. Ez VRS-natív, nem port.

**Parity: PROXY** — A VRS LBF determinisztikus és jó construction baseline-hoz, de a Sparrow stochasztikus mintavételét nem helyettesíti quality szempontból.

---

### 11. Exploration / compression phases

**Sparrow forrás:**
- **Exploration** (Algorithm 12): iteratív strip-shrink (shrink_step arány), separator hívás, feasible sol megőrzés, infeasible pool kezelés, disruption
- **Compression** (Algorithm 13): legjobb feasible sol-tól indul, csökkenő shrink step (time-based vagy failure-based), random split position
- **Phase split**: külön `ExplorationConfig` és `CompressionConfig` időkorlátokkal

**VRS jelenlegi:**
Nincs exploration/compression phase orchestration. `sheet_elimination.rs` (SGH-04) tartalmaz egy egyszerű elimináció próbát, de nincs iteratív strip-shrink, nincs phase split, nincs separate time budget per phase.

**Parity: MISSING** — A kétfázisú optmizáció (exploration + compression) hiányzik. Az SGH task chain ezt SGH-06+ felé tervezi.

---

### 12. Infeasible solution pool

**Sparrow forrás:**
```rust
// explore.rs
let mut infeas_sol_pool: Vec<(SPSolution, f32)> = vec![];
// stored sorted by loss (ascending)
// selected by Normal(0, stddev) → bias toward better solutions
// cleared when feasible solution found
```

**VRS jelenlegi:**
Nincs infeasible solution pool. `VrsSeparator` csak az aktuális legjobb (incumbent) állapotot tartja.

**Parity: MISSING** — Solution pool teljesen hiányzik.

---

### 13. Perturbation / disruption / large-item swap

**Sparrow forrás:**
```rust
// explore.rs — disrupt_solution
// Step 1: define 'large' items by CH area percentile (large_item_ch_area_cutoff_percentile)
// Step 2: choose two large items randomly, swap their positions
// Step 3: cascade contained items (POI containment check) to new empty space
// Conversion: convert_sample_to_closest_feasible for rotation feasibility
```

**VRS jelenlegi:**
`MoveExecutor.try_swap()` (moves.rs, SGH-05): rollback-safe swap, de nincs large-item szelekcó, nincs cascade, nincs perturbation loop. A swap operátor API-szintű, nem solver-loop szintű.

**Parity: PARTIAL** — Swap primitív megvan (SGH-05), de a disruption logika (large-item selection, cascade, pool-from restore) nincs.

---

### 14. Time budget / phase split

**Sparrow forrás:**
```rust
// config.rs
pub struct ExplorationConfig { pub time_limit: Duration, ... }
pub struct CompressionConfig { pub time_limit: Duration, ... }
// Default: exploration=9min, compression=60s
```

**VRS jelenlegi:**
Nincs kétfázisú time budget. A `stopping.rs` tartalmaz `StoppingCondition` struktúrát, de fázisokhoz rendelt külön időkorlát nincs.

**Parity: MISSING** — Fázis-split time budget nem implementált.

---

### 15. Seed determinism

**Sparrow forrás:**
```rust
// config.rs
pub rng_seed: Option<usize>,
// Workers: Xoshiro256PlusPlus::seed_from_u64(rng.random())
```
Determinisztikus futás seedelhető.

**VRS jelenlegi:**
`VrsSeparator`: nincs RNG, determinisztikus (max weighted loss tiebreaking index szerint). `MoveExecutor`: szintén nincs RNG. A VRS separator inherensen determinisztikus — de nem amiatt, hogy seed van, hanem mert nincs stochasztikus lépés.

**Parity: FULL (restricted)** — VRS teljesen determinisztikus (nincs RNG), de ez azért van, mert a stochasztikus keresés MISSING. Ha a stochasztikus mintavétel bekerül, seedelhetőségre is szükség lesz.

---

### 16. BPP / bin reduction logic in forks

**coroush/sparrow forrás** (prior SGH-00 audit, commit `5df9ce15`):
A coroush fork a JeroenGar/sparrow-t kiterjesztette BPP (Bin Packing Problem) módba: a `bp_moves.rs` tartalmaz sheet-to-sheet transfer, swap és reinsert operátorokat; a `bp_explore.rs` sheet eliminációt.

**coroush/sparrow-grasshopper** (`0c9a1362`):
C# Grasshopper wrapper — nem tartalmaz Rust BPP logikát, csak GH plugin glue.

**VRS jelenlegi:**
`sheet_elimination.rs` (SGH-04): sheet eliminálás kísérlet, a `bp_moves.rs` operátorait VRS-natívan reimplementálta a SGH-04/05.

**Parity: PARTIAL** — A coroush `bp_moves.rs` operátorait SGH-05 VRS-natívan megvalósítja. A coroush BPP exploration loop (bp_explore.rs) VRS-en MISSING.

---

### 17. Geometry caching / preprocessing / simplification

**jagua-rs forrás:**
```rust
// original_shape.rs
// Pipeline: center → offset → simplify_shape → close_narrow_concavities → simplify again
// Config: offset, simplify_tolerance, narrow_concavity_cutoff
// Result: Arc<SPolygon> (shared immutable) — cached
// SPSurrogate: pre-generated poles + piers for fast-fail
```
Az `OriginalShape` tárol minden preprocessing lépést. Az `Item` két shape-t tárol: `shape_orig` (eredeti) és `shape_cd` (collision detection, simplifiedsugate-tel).

**VRS jelenlegi:**
`Part` (item.rs): `width`, `height`, `outer_points`, `holes_points` (JsonValue, nem feldolgozott). Nincs polygon preprocessing pipeline, nincs surrogate, nincs quadtree. Csak AABB-alapú geometria.

**Parity: MISSING** — Geometry preprocessing pipeline, surrogate generation, shape caching teljes egészében hiányzik.

---

### 18. Irregular container / remnant support

**jagua-rs forrás:**
`SPProblem` (strip packing): a container egy csík (`strip_width`), belső boundary pontos poligon lehet. A `CDEngine` bármilyen `SPolygon` boundary-t kezel (hazard-based). `Item.min_quality: Option<usize>` — quality zónák.

**VRS jelenlegi:**
`SheetShape` (sheet.rs): `width`, `height`, `outer_points`, `holes_points` (JsonValue). A `rect_within_boundary` függvény csak AABB-t ellenőriz. Az `outer_points` és `holes_points` mezők `Option<JsonValue>` — beolvasva, de nem feldolgozva.

**Parity: PROXY** — A mezők léteznek (IO contract megvan), de az irregular boundary-t a jelenlegi kód nem kezeli pontosan; csak AABB boundary-check van.

---

## Összefoglalás: parity státuszok

| Feature | Status |
|---|---|
| RotationRange / continuous rotation | MISSING |
| Continuous sampling + wiggle/refinement | MISSING |
| Transformation model | PROXY |
| CDE / exact shape collision | PROXY |
| Collision severity / smooth loss | PROXY |
| Shape-based penalty | MISSING |
| GLS dynamic weights | PARTIAL |
| Separator incumbent / restore / strike | PARTIAL |
| move_items_multi / multi-worker | MISSING |
| BLF/LBF role | PROXY |
| Exploration / compression phases | MISSING |
| Infeasible solution pool | MISSING |
| Perturbation / disruption / large-item swap | PARTIAL |
| Time budget / phase split | MISSING |
| Seed determinism | FULL (restricted) |
| BPP / bin reduction (coroush) | PARTIAL |
| Geometry caching / preprocessing | MISSING |
| Irregular container / remnant support | PROXY |

A részletes evidence + migration strategy: `sgh_q00_quality_feature_gap_matrix.md`.  
Moduláris architektúra elvek: `sgh_q00_modular_architecture_principles.md`.
