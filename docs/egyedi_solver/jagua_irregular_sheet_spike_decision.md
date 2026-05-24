# JG-15 Irregular Sheet Capability Spike — Decision Report

Date: 2026-05-24

---

## Spike objective

Determine whether the current `jagua-rs` integration provides **native** irregular/concave
sheet boundary support, or whether a custom boundary validator is required alongside
the existing jagua item-item collision detection.

---

## Architecture audit

### Rust side (`sheet.rs`)

| Capability | Finding |
|---|---|
| `Stock.outer_points` supported | YES — struct field `Option<Vec<PointInput>>` |
| `stock_to_shape()` builds `_outer_poly: SPolygon` | YES |
| `_outer_poly` used in boundary check | **NO** — field name `_outer_poly` signals unused |
| `rect_inside_sheet_shape()` checks outer boundary | **NO** — bbox bounds only (`min_x/max_x/min_y/max_y`) |
| `rect_inside_sheet_shape()` checks holes | YES — via `SPolygon.collides_with(point)` and edge intersection |
| Native jagua container/bin boundary API | **NOT PRESENT** — jagua-rs 0.6.4 exposes only `SPolygon`, `Edge`, `CollidesWith` primitives |

**Critical finding:** `rect_inside_sheet_shape()` does **not** use `_outer_poly` for the outer boundary.
For an L-shaped sheet, an item placed in the notch will **pass** the bbox+hole check but is
geometrically **outside** the L-shape. The current Rust solver silently accepts it.

### Python side (`instances.py`)

| Capability | Finding |
|---|---|
| `_build_sheet_shapes()` uses `outer_points` | YES — calls `_as_polygon()` → Shapely polygon |
| `validate_multi_sheet_output()` uses `sheet_poly.covers(placement_poly)` | YES — full polygon coverage check |
| Python validator detects notch placement | **YES** — `sheet_poly.covers(notch_item)` returns False → raises ValueError |

**The Python exact validator correctly rejects notch placements.**

---

## Spike binary results

Binary: `rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs`

```
positive_control (10,10)→(30,30): bbox=true outer_poly=true
negative_control (60,60)→(80,80): bbox=true outer_poly=false

NATIVE_BOUNDARY_SUPPORT: NO
OWN_BOUNDARY_VALIDATOR_REQUIRED: YES
L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES
CURRENT_BBOX_ONLY_RISK_DETECTED: YES
POSITIVE_CONTROL_PASS: YES
DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION
```

---

## L-shape geometry (spike fixture)

```
(0,100)─────(50,100)
   │             │
   │     L       │
   │             │
(0,50)       (50,50)─────(100,50)
   │                          │
   │       bottom bar         │
   │                          │
(0,0)─────────────────────(100,0)
```

- Bbox: 100×100
- Notch: x∈[50,100], y∈[50,100] (top-right 50×50 corner absent)
- Positive control: item 20×20 at (10,10) → inside L ✓
- Negative control: item 20×20 at (60,60) → in notch, bbox passes, L-shape fails ✓

---

## Path forward: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION

The recommended path for JG-16 (irregular sheet provider):

1. **Outer boundary validator**: extend `rect_inside_sheet_shape()` to check all rect corners
   against `_outer_poly` using the existing `SPolygon.collides_with(point)` primitive,
   and check rect edges against outer polygon edges using `Edge.collides_with(Edge)`.
   The `_outer_poly` field is already built — it just needs to be used.

2. **Item-item collision**: already functional via `JaguaAdapter::check_polygon_collision()`.
   No change needed.

3. **Python exact validator**: already correct — `sheet_poly.covers(placement_poly)` handles
   arbitrary polygon shapes via Shapely.

The required code change is in `rect_inside_sheet_shape()` in `sheet.rs`:
replace bbox-only outer check with `_outer_poly`-aware corner + edge check.

---

## What is NOT required

- A new jagua-rs API or FFI wrapper.
- Replacement of the Rust solver.
- Modifications to the Python exact validator (it already works).
- New jagua-rs crate version.

---

JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION
