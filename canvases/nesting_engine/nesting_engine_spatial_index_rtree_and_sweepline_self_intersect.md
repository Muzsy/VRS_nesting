# canvases/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md`
> **TASK_SLUG:** `nesting_engine_spatial_index_rtree_and_sweepline_self_intersect`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — Teljesítmény: R-tree broad-phase + sweep-line self-intersect

## 🎯 Funkció

A baseline placer és az inflate pipeline jelenleg két teljesítmény-kockázatot hordoz nagy pontszámú (spline/arc polygonizált) inputnál:

1) **Broad-phase ütközésvizsgálat lineáris listán:**  
   A feasibility ellenőrzés `placed: &[PlacedPart]` listát szűr AABB alapján (`aabb_overlaps`), ami sok alkatrész esetén O(N) jelöltet gyárt minden candidate-hez.

2) **Önmetszés-vizsgálat brute-force O(N²):**  
   A `rust/nesting_engine/src/geometry/pipeline.rs` `polygon_self_intersects()` dupla ciklusos szegmens-ellenőrzést futtat, ami ezer pontnál milliós nagyságrendű művelet.

A task célja:
- **R-tree (rstar) spatial index** bevezetése a baseline placerben, hogy a jelöltek lekérdezése O(log N) legyen, és csak a releváns részek kerüljenek narrow-phase i_overlay vizsgálatra.
- **Sweep-line (geo)** alapú self-intersect detektálás bevezetése a pipeline-ban a brute-force helyett.

**Nem cél:**
- NFP motor (Fázis 2) implementálása
- i_overlay narrow-phase logika cseréje
- AABB (aabb.rs) módosítása: megtartandó

---

## 🧠 Fejlesztési részletek

### Releváns meglévő pontok a kódban (valós fájlok)

- `rust/nesting_engine/src/placement/blf.rs`
  - `placed_state: Vec<PlacedPart>` gyűjti a letett alkatrészeket
  - `can_place(&candidate, bin_polygon, &placed_state)` hívás a belső ciklusban

- `rust/nesting_engine/src/feasibility/narrow.rs`
  - `pub fn can_place(candidate, bin, placed: &[PlacedPart]) -> bool`
  - A broad-phase jelöltek: `placed.iter().filter(|p| aabb_overlaps(...))` → lineáris
  - Determinizmus: a jelölteket AABB alapján rendezi narrow-phase előtt (ezt meg kell tartani)

- `rust/nesting_engine/src/feasibility/aabb.rs`
  - Kész, jó AABB, `aabb_overlaps` stb. (megtartandó)

- `rust/nesting_engine/src/geometry/pipeline.rs`
  - `polygon_self_intersects()` jelenleg brute-force + `segments_intersect()` (O(N²))

- `rust/nesting_engine/Cargo.toml`
  - `rstar = "=0.12.2"` már bent van, de nincs használat
  - `geo` még nincs bent → hozzá kell adni

### 1) Spatial index (R-tree) – célállapot

A baseline placer tartson fenn egy:
- `Vec<PlacedPart>` (tényleges geometria + AABB)
- `rstar::RTree<PlacedPartRef>` (AABB envelope + index a Vec-be mutatva)

**Kulcspontok:**
- RTree query: “mely placed elemek AABB-je metszi a candidate AABB-t”
- A query eredményeinek sorrendje NEM garantált → a narrow-phase előtt **továbbra is determinisztikus sort** kell:
  - a régi kulcs: `min_x`, majd `min_y`

**Döntés (API):**
- A `can_place` signature-t érdemes úgy refaktorálni, hogy ne slice-on iteráljon, hanem egy “index” objektumtól kérje le a jelölteket (AABB query).  
  Mivel a `can_place` csak a `blf.rs`-ből van hívva, ez biztonságosan megtehető.

Javasolt minimál-invazív struktúra:
- `feasibility/narrow.rs`-ben:
  - `pub struct PlacedIndex { parts: Vec<PlacedPart>, rtree: RTree<PlacedPartEnvelope> }`
  - `impl PlacedIndex { fn new(); fn insert(PlacedPart); fn query_overlaps(aabb)->Vec<usize>; fn get(idx)->&PlacedPart }`
  - `pub fn can_place(candidate, bin, placed_index: &PlacedIndex) -> bool`
  - `can_place` broad-phase outputját explicit rendezni kell (`min_x`, `min_y`) narrow-phase előtt.

A blf-ben pedig:
- `let mut placed_index = PlacedIndex::new();`
- sikeres lerakáskor: `placed_index.insert(PlacedPart{...})`

### 2) Sweep-line self-intersect – célállapot

A `polygon_self_intersects(points: &[Point64]) -> bool` implementációt cseréljük `geo`-ra:
- `geo = "0.28.0"` dependency bevezetése (a repo pinning stílusához igazítva)
- `geo::sweep::Intersections` sweep-line iterator használata
- A szomszédos polygon-élek metszését (közös csúcs) explicit ki kell szűrni, hogy a valid egyszerű polygon ne legyen tévesen self-intersect.
- A pontok `Point64 {x,y}` µm i64 koordináták. A geo típusnak:
  - első körben f64 koordinátákkal adjuk át (a 2^53 korlát miatt a tipikus mérettartományban ez egzakt), és a detektálás determinisztikus.
  - A cél nem “javítás”, csak detect+reject.

**Invariáns:**
- Az invalid kontúrt továbbra is `STATUS_SELF_INTERSECT`-tel el kell utasítani (a jelenlegi pipeline logikát meg kell tartani).

### Tesztelés / mérhetőség

- Self-intersect: hozzunk be egy olyan tesztet (pipeline.rs tests), ami sok ponttal is gyorsan fut (nem “időre” mér, csak legyen nagyobb input és fusson).
- R-tree: adjunk tesztet a feasibility modulhoz vagy blf tesztekhez:
  - ugyanaz az input, ugyanaz az output (determinism megmarad)
  - a `can_place` behavior nem változik funkcionálisan (csak gyorsul)

---

## 🧪 Tesztállapot

### DoD
- `rust/nesting_engine/src/geometry/pipeline.rs` nem tartalmaz brute-force `polygon_self_intersects` dupla ciklusos szegmens-ellenőrzést; helyette `geo` sweep-line.
- `rust/nesting_engine/src/feasibility/narrow.rs` broad-phase jelöltgyűjtése RTree query-vel történik (nincs lineáris filter a teljes placed listán).
- A narrow-phase determinisztikus sorrend megmarad (AABB sort).
- A meglévő unit tesztek (blf + pipeline) zöldek, és új tesztek lefedik:
  - self-intersect reject
  - determinism megmaradása a placerben
- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spatial_index_rtree_and_sweepline_self_intersect.md` zöld.

---

## 🌍 Lokalizáció

Nincs UI. Log/diagnosztika angol maradhat, stabil státuszkódokkal.

---

## 📎 Kapcsolódások

- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/feasibility/narrow.rs`
- `rust/nesting_engine/src/feasibility/aabb.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/Cargo.toml`
