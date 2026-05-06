# T05f — Hole Boundary Sampling Implementation + Real Output-Hole Regression

**Státusz: PASS**

## Rövid összefoglaló

A T07 `nfp_correctness_benchmark` hole boundary mintavételezéssel bővült. A `sample_points_on_boundary` már mintavételezi mind az outer, mind a hole ringeket, és az output JSON külön riportolja az outer/hole boundary metrikákat. Minden regressziós teszt PASS, nincs regresszió az outer-only esetekben.

## Módosított fájlok

| Fájl | Módosítás |
|------|-----------|
| `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` | BoundarySample: `is_hole` mező; BenchmarkOutput: 7 új mező; `sample_ring_boundary`: ring-szintű mintavételezés hole-aware outward normal logikával; `sample_polygon_boundary`: outer+hole 50/50 allokáció; boundary perturbation szétválasztás outer/hole metrikákra |

## Implementáció részletek

### BoundarySample bővítés
- `is_hole: bool` mező hozzáadva — jelzi, hogy a minta outer vagy hole ringből származik

### BenchmarkOutput új mezők
```rust
boundary_holes_supported: bool           // true ha az NFP-nek van hole ringje
outer_boundary_samples: usize            // outer ringből vett minták száma
hole_boundary_samples: usize             // hole ringekből vett minták száma
outer_boundary_penetration_max_mm: f64  // outer boundary max penetráció
hole_boundary_penetration_max_mm: f64   // hole boundary max penetráció
hole_boundary_collision_count: usize     // hole boundary minták: collider
hole_boundary_non_collision_count: usize // hole boundary minták: nem collider
```

### Ring sampling logika
- `sample_ring_boundary`: egyetlen ring mintavételezése tetszőleges outward-normal irányítással
- Outer ring (CCW): outward normal = bal kéz-szabály (dy, -dx)
- Hole ring (CW): outward normal = jobb kéz-szabály (-dy, dx) — a "kifelé" a lyuk belseje felé mutat
- `sample_polygon_boundary`: 50% outer + 50% hole allokáció, hole-ok közt egyenletesen elosztva

### Boundary perturbation
- Külső pont: `base + outward * units` — az NFP határán kívül
- Belső pont: `base - outward * units` — az NFP határán belül
- Ha belső nem-collider VAGY külső collider → penetráció
- Hole boundary esetén: hole_boundary_collision_count / non_collision_count külön számlálás

## Regressziós eredmények

### A) real_work_dxf_holes_pair_02 (output-hole-os)

```bash
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_02.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/real_work_dxf_holes_pair_02.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 400 --output-json
```

| Mező | Érték |
|------|-------|
| correctness_verdict | **PASS** |
| boundary_holes_supported | **true** |
| outer_boundary_samples | **398** |
| hole_boundary_samples | **2** |
| outer_boundary_penetration_max_mm | 0.0 |
| hole_boundary_penetration_max_mm | 0.01 |
| hole_boundary_collision_count | 2 |
| hole_boundary_non_collision_count | 0 |
| false_positive_count | 0 |
| false_negative_count | 0 |
| notes | "HOLES_AWARE: 1 hole(s) parsed from holes_i64, hole-aware containment active" |

### B) lv8_pair_01 (outer-only regresszió)

```bash
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/lv8_pair_01.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 --output-json
```

| Mező | Érték |
|------|-------|
| correctness_verdict | **PASS** |
| boundary_holes_supported | **false** |
| outer_boundary_samples | **200** |
| hole_boundary_samples | **0** |
| outer_boundary_penetration_max_mm | 0.0 |
| hole_boundary_penetration_max_mm | 0.0 |
| false_positive_count | 0 |
| false_negative_count | 0 |

### C) lv8_pair_holes_smoke (synthetic holes smoke)

```bash
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_holes_smoke.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/lv8_pair_holes_smoke.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 --output-json
```

| Mező | Érték |
|------|-------|
| correctness_verdict | **PASS** |
| boundary_holes_supported | **true** |
| outer_boundary_samples | **197** |
| hole_boundary_samples | **3** |
| outer_boundary_penetration_max_mm | 0.0 |
| hole_boundary_penetration_max_mm | 0.01 |
| hole_boundary_collision_count | 3 |
| hole_boundary_non_collision_count | 0 |

## Összefoglaló táblázat

| fixture_id | output_holes | outer_boundary_samples | hole_boundary_samples | T07 verdict | FP | FN | boundary_penetration_max_mm | notes |
|------------|-------------|----------------------|---------------------|-------------|----|----|---------------------------|-------|
| real_work_dxf_holes_pair_02 | 1 | 398 | 2 | PASS | 0 | 0 | 0.01 | HOLES_AWARE active, hole boundary collision=2 |
| lv8_pair_01 | 0 | 200 | 0 | PASS | 0 | 0 | 0.0 | outer-only, no regression |
| lv8_pair_holes_smoke | 1 | 197 | 3 | PASS | 0 | 0 | 0.01 | HOLES_AWARE active, hole boundary collision=3 |

## Ismert limitációk

1. **Hole boundary = boundary contact state**: A hole boundary ponton a mozgó alkatrész referenciapontja az NFP határán van — ez mindig "érintkezés" állapot. A `hole_boundary_collision_count` azt méri, hogy a külső perturbált pont collider-e, ami nem azonos a "contact distance" validációval. Ez egy binary collide/nem-collide mérés, nem távolság-alapú.

2. **Boundary penetration threshold**: A `boundary_perturbation_mm` fix érték (default 0.01mm). Ha a penetráció ennél kisebb, nem számítódik — nem egy valódi távolság-mérés.

3. **CGAL = prototípus**: A CGAL probeGPL miatt továbbra sem production komponens. T08 integráció TILOS.

## Blockerek

Nincs.

## Futtatott parancsok

```bash
# Build
cd rust/nesting_engine && cargo fmt && cargo build --release --bin nfp_correctness_benchmark

# Regresszió A: real_work_dxf_holes_pair_02
cargo run --release --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_02.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/real_work_dxf_holes_pair_02.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 400 --output-json

# Regresszió B: lv8_pair_01 (outer-only)
cargo run --release --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/lv8_pair_01.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 --output-json

# Regresszió C: lv8_pair_holes_smoke
cargo run --release --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_holes_smoke.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/lv8_pair_holes_smoke.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 200 --output-json
```

## Következő javasolt lépés

T05g: Hole boundary penetration distance mérés — a jelenlegi binary collision check kiegészítése valódi contact-distance metrikával (ha a perturbált pont az NFP boundary-ján van, mérjük a távolságot a valódi határig).

**NEM T08. NEM production integráció.**
