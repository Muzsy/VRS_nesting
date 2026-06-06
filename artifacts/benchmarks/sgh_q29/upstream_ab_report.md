# SGH-Q29 Phase A: Upstream Sparrow A/B Report

**Status: PASS**

- Upstream commit: `c95454e390276231b278c879d25b39708398b7d3`
- Upstream binary: `.cache/sparrow/target/release/sparrow`
- Build command: `cargo build --release --manifest-path .cache/sparrow/Cargo.toml`
- Local binary: `rust/vrs_solver/target/release/vrs_solver`

## Case: micro

Input: jakobs1.json from .cache/sparrow/data/input/

Geometry notes: Same polygon geometry. Upstream: SPP strip packing (minimize width, strip_h=40.004). Local: FSPP fixed sheet (120×40). Objectives differ; search behavior / runtime comparable.

| Metric | Upstream | Local |
|--------|----------|-------|
| Status | ok | ok |
| Runtime ms | 12483.5 | 2384.6 |
| Placed count | 25 | 25 |
| Iterations | — | 1 |
| Search calls | — | 0 |
| Final pairs | — | 0 |
| Strip width / density | 11.0 / 0.9 | — (fixed sheet) |

## Case: medium

Input: jakobs2.json from .cache/sparrow/data/input/

Geometry notes: Same polygon geometry. Upstream: SPP strip packing (minimize width, strip_h=70.007). Local: FSPP fixed sheet (210×70). Objectives differ; search behavior / runtime comparable.

| Metric | Upstream | Local |
|--------|----------|-------|
| Status | ok | ok |
| Runtime ms | 20252.5 | 2485.0 |
| Placed count | 25 | 25 |
| Iterations | — | 1 |
| Search calls | — | 0 |
| Final pairs | — | 0 |
| Strip width / density | 24.4 / 0.8 | — (fixed sheet) |

## Case: lv8_subset

Input: Dense-191 LV8 fixture, first 3 part types (67 instances)

Geometry notes: Same LV8 polygon geometry (outer_points → SPP simple_polygon). Upstream: SPP strip_h=3000. Local: fixed sheet 1500×3000. Objectives differ; geometry identical.

| Metric | Upstream | Local |
|--------|----------|-------|
| Status | ok | ok |
| Runtime ms | 31304.4 | 15872.1 |
| Placed count | 67 | 67 |
| Iterations | — | 1 |
| Search calls | — | 11 |
| Final pairs | — | 0 |
| Strip width / density | 108.1 / 0.8 | — (fixed sheet) |

