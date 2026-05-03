# Engine v2 NFP RC T03 — Geometry Cleanup Pipeline
TASK_SLUG: engine_v2_nfp_rc_t03_geometry_cleanup_pipeline

## Szerep
Senior Rust fejlesztő agent vagy. Implementálod a geometry cleanup és simplification
infrastruktúrát mérési képességgel. A T03 modulokat T05–T08 fogja felhasználni.

## Cél
Implementáld: `cleanup.rs`, `simplify.rs`, `geometry_prepare_benchmark.rs` bin.
A bin futtatható T01 fixture-ökön, topology_changed=false, area_delta<0.5 mm².

## Előfeltétel ellenőrzés
```bash
# T01 fixture-ök megvannak
ls tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json || echo "STOP: T01 szükséges"

# T02 contract doc megvan
ls docs/nesting_engine/geometry_preparation_contract_v1.md || echo "WARN: T02 contract hiányzik"

# Meglévő geometry mod.rs tartalom
cat rust/nesting_engine/src/geometry/mod.rs
```

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/engine_v2_nfp_rc_t03_geometry_cleanup_pipeline.md` (teljes spec)
- `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t03_geometry_cleanup_pipeline.yaml`
- `rust/nesting_engine/src/geometry/types.rs` (Point64, Polygon64)
- `rust/nesting_engine/src/geometry/pipeline.rs` (meglévő pipeline minta)
- `rust/nesting_engine/src/nfp/boundary_clean.rs` (clean_polygon_boundary — NEM módosítandó)
- `rust/nesting_engine/src/geometry/mod.rs` (meglévő pub mod sorok)

## Engedélyezett módosítás
- `rust/nesting_engine/src/geometry/cleanup.rs` (create)
- `rust/nesting_engine/src/geometry/simplify.rs` (create)
- `rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs` (create)
- `rust/nesting_engine/src/geometry/mod.rs` (minimális módosítás: pub mod sorok)

## Szigorú tiltások
- **Tilos `boundary_clean.rs`-t módosítani.**
- Tilos destructive simplification (hole elvesztés, reflex vertex elvesztés).
- Tilos `#[allow(dead_code)]` a publikus API-kon.
- Tilos NFP-t számítani.

## Végrehajtandó lépések

### Step 1: Meglévő kód megértése
```bash
# geometry/types.rs Point64, Polygon64 definíciók
grep -n "pub struct\|pub fn\|pub type" rust/nesting_engine/src/geometry/types.rs | head -30

# boundary_clean.rs publikus API
grep -n "^pub fn" rust/nesting_engine/src/nfp/boundary_clean.rs

# Meglévő geometry mod.rs
cat rust/nesting_engine/src/geometry/mod.rs
```

### Step 2: `rust/nesting_engine/src/geometry/cleanup.rs` megírása
A canvas spec alapján implementáld:
- `CleanupError` enum (EmptyPolygon, InvalidOrientationAfterCleanup, InsufficientVertices)
- `CleanupResult` struct (vertex_count_before/after, null_edges_removed, duplicate_vertices_removed, collinear_merged, orientation_fixed)
- `remove_duplicate_vertices(poly: &Polygon64) -> Result<CleanupResult, CleanupError>`
- `remove_null_edges(poly: &Polygon64) -> Result<CleanupResult, CleanupError>`
- `merge_collinear_vertices(poly: &Polygon64, angle_threshold_deg: f64) -> Result<CleanupResult, CleanupError>`
- `normalize_orientation(poly: &Polygon64) -> Result<CleanupResult, CleanupError>`
- `run_cleanup_pipeline(poly: &Polygon64, angle_threshold_deg: f64) -> Result<CleanupResult, CleanupError>`

### Step 3: `rust/nesting_engine/src/geometry/simplify.rs` megírása
A canvas spec alapján:
- `SimplifyResult` struct (vertex_count_before/after, reflex_vertex_count_before/after, area_delta_mm2, bbox_delta_mm, max_deviation_mm, topology_changed, simplification_ratio)
- `SimplifyError` enum (EpsilonTooLarge, TopologyChanged, EmptyResult)
- `topology_preserving_rdp(poly: &Polygon64, epsilon_mm: f64) -> Result<SimplifyResult, SimplifyError>`
- `count_reflex_vertices(ring: &[Point64]) -> usize`

Kötelező: ha reflex count csökkent → `SimplifyError::TopologyChanged`.

### Step 4: `rust/nesting_engine/src/bin/geometry_prepare_benchmark.rs` megírása
- `--fixture <path>`, `--rdp-epsilon <mm>`, `--collinear-threshold <°>`, `--output-json`
- Olvassa a fixture JSON-t, futtatja cleanup + simplify pipeline-t
- stdout JSON: part_a és part_b cleanup/simplify metrikák + pair_fragment_count_estimate

### Step 5: geometry/mod.rs frissítése
```rust
// Meglévő sorok mellé add hozzá:
pub mod cleanup;
pub mod simplify;
```

### Step 6: Kompilálás és tesztelés
```bash
cargo check -p nesting_engine 2>&1 | tail -10

cargo run --bin geometry_prepare_benchmark -- --help

cargo run --bin geometry_prepare_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --output-json 2>&1 | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['part_a']['simplify']['topology_changed'] == False, 'topology changed!'
assert d['part_a']['simplify']['area_delta_mm2'] < 0.5, 'area delta too large!'
print('PASS: topology_changed=False, area_delta OK')
"

# Összes T01 fixture-n
for pair in lv8_pair_01 lv8_pair_02 lv8_pair_03; do
  cargo run --bin geometry_prepare_benchmark -- \
    --fixture tests/fixtures/nesting_engine/nfp_pairs/${pair}.json \
    --output-json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('${pair}: A_before=${d[\"part_a\"][\"cleanup\"][\"vertex_count_before\"]} A_after_simplify=${d[\"part_a\"][\"simplify\"][\"vertex_count_after\"]} topo_changed=${d[\"part_a\"][\"simplify\"][\"topology_changed\"]}')
" 2>/dev/null || echo "${pair}: check failed"
done
```

### Step 7: dead_code ellenőrzés
```bash
cargo check -p nesting_engine 2>&1 | grep "dead_code" | grep -v "#\[allow"
```

### Step 8: Report és checklist
Töltsd ki a checklistet és a reportot.

## Tesztparancsok
```bash
cargo check -p nesting_engine
cargo run --bin geometry_prepare_benchmark -- --help
ls rust/nesting_engine/src/geometry/cleanup.rs
ls rust/nesting_engine/src/geometry/simplify.rs
grep -n "pub mod cleanup" rust/nesting_engine/src/geometry/mod.rs
git diff HEAD -- rust/nesting_engine/src/nfp/boundary_clean.rs
```

## Ellenőrzési pontok
- [ ] cargo check -p nesting_engine hibátlan
- [ ] cleanup.rs, simplify.rs léteznek
- [ ] geometry_prepare_benchmark --help fut
- [ ] T01 összes fixture-n lefut, nincs panic
- [ ] topology_changed=false (0.1 mm epsilon)
- [ ] area_delta_mm2 < 0.5
- [ ] SimplifyResult összes kötelező mező megvan
- [ ] boundary_clean.rs érintetlen
- [ ] Nincs #[allow(dead_code)] a publikus API-kon
