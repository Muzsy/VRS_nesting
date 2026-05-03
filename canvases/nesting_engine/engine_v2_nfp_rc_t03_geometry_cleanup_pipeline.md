# Engine v2 NFP RC — T03 Geometry Cleanup Pipeline

## Cél
Megmérni, mennyire csökkenthető biztonságosan a vertexszám az LV8 problémás partokon,
és implementálni a cleanup + simplification infrastruktúrát mérési képességgel.
A task bizonyítja, hogy a T01 fixture-ök vertex countja biztonságosan redukálható
topológia-veszteség nélkül, ami a T05 reduced convolution prototype előfeltétele.

## Miért szükséges
A jelenlegi concave NFP 342 × 518 = 177 156 pár-NFP-t számít fragment explosion módban.
Ha a solver geometry vertex count akár 50%-kal csökkenthető topológia-veszteség nélkül,
az önmagában 4× gyorsítást adhat a pair count csökkentésén keresztül. A cleanup pipeline
egységes interfészt biztosít T05–T08 számára.

## Érintett valós fájlok

### Olvasandó (read-only kontextus):
- `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64, PartGeometry
- `rust/nesting_engine/src/geometry/pipeline.rs` — run_inflate_pipeline (meglévő minta)
- `rust/nesting_engine/src/nfp/boundary_clean.rs` — clean_polygon_boundary, ring_has_self_intersection (NEM módosítandó)
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json` — T01 output fixture
- `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_index.json` — fixture index
- `docs/nesting_engine/geometry_preparation_contract_v1.md` — T02 output contract

### Létrehozandó Rust kód:
- `rust/nesting_engine/src/geometry/cleanup.rs` — cleanup pipeline modul
- `rust/nesting_engine/src/geometry/simplify.rs` — simplification modul
- `rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs` — mérő bin

### Módosítandó (minimálisan):
- `rust/nesting_engine/src/geometry/mod.rs` — `pub mod cleanup; pub mod simplify;` hozzáadása

## Nem célok / scope határok
- Nem kell NFP-t számítani.
- Nem kell a `boundary_clean.rs` funkcionalitását törölni vagy refaktorálni.
- Nem kell destructive simplification (hole elhagyás, reflex vertex elvesztése).
- Nem kell a meglévő `run_inflate_pipeline`-t módosítani.
- Nem kell Python kódot módosítani.

## Részletes implementációs lépések

### 1. T01 és T02 output olvasása

Ellenőrizd, hogy a T01 fixture-ök léteznek:
```bash
python3 -c "
import json
from pathlib import Path
for pair_id in ['lv8_pair_01', 'lv8_pair_02', 'lv8_pair_03']:
    p = json.loads(Path(f'tests/fixtures/nesting_engine/nfp_pairs/{pair_id}.json').read_text())
    print(f'{pair_id}: A_vc={len(p[\"part_a\"][\"points_mm\"])} B_vc={len(p[\"part_b\"][\"points_mm\"])}')
"
```

### 2. `rust/nesting_engine/src/geometry/cleanup.rs` implementálása

**CleanupError enum:**
```rust
#[derive(Debug, Clone)]
pub enum CleanupError {
    EmptyPolygon,
    InvalidOrientationAfterCleanup(String),
    InsufficientVertices { count: usize },
}
```

**CleanupResult struct:**
```rust
#[derive(Debug, Clone)]
pub struct CleanupResult {
    pub polygon: Polygon64,
    pub vertex_count_before: usize,
    pub vertex_count_after: usize,
    pub null_edges_removed: usize,
    pub duplicate_vertices_removed: usize,
    pub collinear_merged: usize,
    pub orientation_fixed: bool,
}
```

**Publikus API:**
```rust
/// Duplicate vertex removal: eltávolítja az egymást követő azonos pontokat
pub fn remove_duplicate_vertices(poly: &Polygon64) -> Result<CleanupResult, CleanupError>

/// Null edge removal: eltávolítja a nulla hosszú éleket
pub fn remove_null_edges(poly: &Polygon64) -> Result<CleanupResult, CleanupError>

/// Collinear merge: összevonja az egyvonalban lévő vertexeket (angle_threshold_deg: f64)
/// TILOS ha a szög meghaladja az angle_threshold_deg-t
pub fn merge_collinear_vertices(poly: &Polygon64, angle_threshold_deg: f64) -> Result<CleanupResult, CleanupError>

/// Orientation normalize: outer CCW, holes CW (signed area alapján)
pub fn normalize_orientation(poly: &Polygon64) -> Result<CleanupResult, CleanupError>

/// Full cleanup pipeline: a fenti lépések sorrendben
pub fn run_cleanup_pipeline(poly: &Polygon64, angle_threshold_deg: f64) -> Result<CleanupResult, CleanupError>
```

**Invariánsok (minden függvényre érvényes):**
- A visszaadott polygon legalább 3 vertexet tartalmaz (outer ring)
- Holes count nem csökken
- area(result) ≈ area(input) (floating point precision szinten)

### 3. `rust/nesting_engine/src/geometry/simplify.rs` implementálása

**SimplifyResult struct:**
```rust
#[derive(Debug, Clone)]
pub struct SimplifyResult {
    pub polygon: Polygon64,
    pub vertex_count_before: usize,
    pub vertex_count_after: usize,
    pub reflex_vertex_count_before: usize,
    pub reflex_vertex_count_after: usize,
    pub area_delta_mm2: f64,
    pub bbox_delta_mm: f64,
    pub max_deviation_mm: f64,
    pub topology_changed: bool,
    pub simplification_ratio: f64,  // vertex_after / vertex_before
}

#[derive(Debug, Clone)]
pub enum SimplifyError {
    EpsilonTooLarge { epsilon_mm: f64, area_delta_mm2: f64 },
    TopologyChanged { reflex_before: usize, reflex_after: usize },
    EmptyResult,
}
```

**Publikus API:**
```rust
/// Topology-preserving Ramer-Douglas-Peucker simplification
/// epsilon_mm: max eltérés mm-ben (pl. 0.1 mm)
/// Ha topology_changed = true: SimplifyError::TopologyChanged
pub fn topology_preserving_rdp(poly: &Polygon64, epsilon_mm: f64) -> Result<SimplifyResult, SimplifyError>

/// Reflex vertex count számítása (mérési segédfüggvény)
pub fn count_reflex_vertices(ring: &[Point64]) -> usize
```

**Kötelező ellenőrzések topology_preserving_rdp-ben:**
1. Reflex vertex count mérése ELŐTT és UTÁN
2. Ha reflex count csökkent: `topology_changed = true`, `SimplifyError::TopologyChanged`
3. Max deviation mérése: minden elhagyott vertex távolsága az egyenestől
4. Area delta mérése: |area(result) - area(input)| mm²-ben
5. Ha area_delta_mm2 > epsilon_mm × perimeter: visszautasítás

### 4. `rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs` implementálása

**Parancssori interfész:**
```
--fixture <path>          NFP pair fixture JSON fájl (default: tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json)
--rdp-epsilon <mm>        RDP epsilon mm-ben (default: 0.1)
--collinear-threshold <°> Collinear merge szög threshold (default: 0.5)
--output-json             JSON riport stdout-ra
```

**stdout JSON output:**
```json
{
  "input_fixture": "lv8_pair_01",
  "rdp_epsilon_mm": 0.1,
  "collinear_threshold_deg": 0.5,
  "part_a": {
    "part_id": "...",
    "cleanup": {
      "vertex_count_before": 342,
      "vertex_count_after": 310,
      "null_edges_removed": 5,
      "duplicate_vertices_removed": 0,
      "collinear_merged": 27,
      "orientation_fixed": false
    },
    "simplify": {
      "vertex_count_before": 310,
      "vertex_count_after": 89,
      "reflex_vertex_count_before": 45,
      "reflex_vertex_count_after": 43,
      "area_delta_mm2": 0.12,
      "bbox_delta_mm": 0.02,
      "max_deviation_mm": 0.08,
      "topology_changed": false,
      "simplification_ratio": 0.287
    }
  },
  "part_b": {
    "..."
  },
  "pair_fragment_count_estimate": {
    "before_cleanup": 177156,
    "after_cleanup": null,
    "after_simplify": null,
    "reduction_ratio": null
  }
}
```

A `pair_fragment_count_estimate` = vertex_count_a × vertex_count_b (approximáció, nem tényleges NFP).

### 5. geometry/mod.rs módosítás

```rust
pub mod cleanup;
pub mod simplify;
```
Hozzáadása a meglévő `pub mod` sorok mellé.

### 6. Validálás

```bash
# Compile check
cargo check -p nesting_engine 2>&1 | tail -5

# Bin help fut
cargo run --bin geometry_prepare_benchmark -- --help

# T01 összes fixture-ön lefut
for pair in lv8_pair_01 lv8_pair_02 lv8_pair_03; do
  cargo run --bin geometry_prepare_benchmark -- \
    --fixture tests/fixtures/nesting_engine/nfp_pairs/${pair}.json \
    --output-json 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print('${pair}:', 'topology_changed:', d['part_a']['simplify']['topology_changed'])"
done
```

## Adatmodell / contract változások
Új Rust modulok (`cleanup.rs`, `simplify.rs`) és egy új bin (`geometry_prepare_benchmark.rs`).
A `geometry/mod.rs`-ben két `pub mod` sor keletkezik. Nincs API breaking change.

## Backward compatibility
A meglévő `boundary_clean.rs` érintetlen. A meglévő `run_inflate_pipeline` érintetlen.
Új modulok additive extension-ök.

## Hibakódok / diagnosztikák
- `CleanupError::EmptyPolygon` — üres input polygon
- `CleanupError::InsufficientVertices` — 3-nál kevesebb vertex marad cleanup után
- `SimplifyError::TopologyChanged` — reflex count csökkent → tilos elfogadni
- `SimplifyError::EpsilonTooLarge` — az epsilon túl nagy, area delta meghaladja a limitet

## Tesztelési terv
```bash
# 1. Compile
cargo check -p nesting_engine

# 2. Bin futtatható
cargo run --bin geometry_prepare_benchmark -- --help

# 3. Nincs panic T01 fixture-ökön
cargo run --bin geometry_prepare_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json

# 4. topology_changed = false ellenőrzés
cargo run --bin geometry_prepare_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['part_a']['simplify']['topology_changed'] == False, 'topology changed!'
assert d['part_a']['simplify']['area_delta_mm2'] < 0.5, 'area delta too large!'
print('PASS: topology_changed=False, area_delta OK')
"

# 5. Nincs dead_code warning publikus API-kon
cargo check -p nesting_engine 2>&1 | grep "dead_code" | grep -v "#\[allow"
```

## Elfogadási feltételek
- [ ] `rust/nesting_engine/src/geometry/cleanup.rs` létezik és kompilál
- [ ] `rust/nesting_engine/src/geometry/simplify.rs` létezik és kompilál
- [ ] `rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs` létezik és futtatható
- [ ] `cargo check -p nesting_engine` hibátlan
- [ ] T01 összes fixture-n lefut, nincs panic
- [ ] `topology_changed = false` a T01 fixture-ökön (0.1 mm epsilon-nal)
- [ ] `area_delta_mm2 < 0.5` a T01 fixture-ökön
- [ ] SimplifyResult tartalmazza az összes kötelező mezőt
- [ ] Nincs `#[allow(dead_code)]` a publikus API-kon
- [ ] A meglévő `boundary_clean.rs` érintetlen

## Rollback / safety notes
Új fájlok additive jellegűek. A `geometry/mod.rs` minimális módosítása visszavonható.
A meglévő `boundary_clean.rs` érintetlen — a meglévő NFP pipeline nem változik.

## Dependency
- T01: lv8_pair_01.json fixture szükséges input
- T02: geometry_preparation_contract_v1.md — a simplification safety szabályok referenciája
- T05 (reduced_convolution_prototype) uses cleanup.rs és simplify.rs
