PASS

# Implementation report — JG-15 `jagua_optimizer_t15_irregular_sheet_capability_spike`

## Status: PASS

Date: 2026-05-24

---

## DISCOVERED_MISMATCH

```
old plan says: Task JG-15 — Multi-child cavity-prepack V2
current task breakdown says: JG-15 — jagua_optimizer_t15_irregular_sheet_capability_spike
resolution: follow current task breakdown/checklist/master-runner chain;
            do not implement cavity-prepack in JG-15
```

---

## Dependency evidence

| Item | Status |
|------|--------|
| `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` exists | ✓ |
| JG-14 first line = `PASS` | ✓ |
| JG-14 contains `PHASE1_GATE_DECISION: PASS` | ✓ |
| JG-14 contains `JG-15_STATUS: READY` | ✓ |
| `scripts/bench_jagua_optimizer_phase1_rectangular.py` exists | ✓ |
| `codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md` exists | ✓ |

---

## Summary

Capability spike completed. Key findings from real code audit + Rust spike binary:

1. `Stock.outer_points` is supported in the Rust struct and correctly parsed into `_outer_poly: SPolygon`.
2. `_outer_poly` is **never used** in `rect_inside_sheet_shape()` — only bbox bounds are checked for the outer boundary.
3. The current Rust solver **silently accepts** placements in the notch of an L-shape (bbox passes, L-shape boundary not checked).
4. The Python exact validator **correctly rejects** notch placements (`sheet_poly.covers()` via Shapely).
5. jagua-rs 0.6.4 has **no native container/bin irregular boundary API** — only `SPolygon`, `Edge`, and `CollidesWith` primitives.
6. A custom `_outer_poly`-based boundary check works and is implementable with existing jagua primitives.

Decision: **OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION**

---

## Files created

| File | Action |
|------|--------|
| `rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs` | CREATED |
| `tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json` | CREATED |
| `scripts/smoke_jagua_irregular_sheet_spike.py` | CREATED |
| `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` | CREATED |
| `codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` | UPDATED (all [x]) |
| `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` | UPDATED (JG-15 Kész) |

---

## Real code audit

### `sheet.rs`

- `Stock.outer_points: Option<Vec<PointInput>>` — supported.
- `stock_to_shape()` builds `_outer_poly: SPolygon` from outer_points.
- `_outer_poly` field has `_` prefix — Rust dead-code suppression convention; NOT used in placement.
- `rect_inside_sheet_shape(rect, sheet)`:
  - Checks bbox bounds (`sheet.min_x/max_x/min_y/max_y`) — outer boundary **ONLY bbox**.
  - Checks hole polygons via `SPolygon.collides_with(point)` and edge intersection.
  - **Does NOT check `_outer_poly`** — concave outer boundary silently ignored.

### `geometry.rs`

- `to_jag_point`, `jag_edge_from_points`, `rect_corners`, `rect_edges` — all present, confirmed usable in spike.

### `adapter.rs`

- `JaguaAdapter::check_polygon_collision` — item-item collision via jagua `SPolygon.collides_with(point)` + `Edge.collides_with(Edge)`.
- Same primitives proven to work for outer boundary validation in spike binary.

### `instances.py`

- `_build_sheet_shapes()` uses `outer_points` → builds full Shapely polygon via `_as_polygon()`.
- `validate_multi_sheet_output()` → `sheet_poly.covers(placement_poly)` — **full polygon check, correctly rejects L-shape violations**.

### `Cargo.toml`

- `jagua-rs = "0.6.4"` — no native container/bin boundary API; only geometric primitives.

---

## Spike binary output

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

## Test results

```
cargo build --bin jagua_irregular_sheet_spike    → PASS
cargo run --bin jagua_irregular_sheet_spike      → PASS (decision lines present, exit 0)
python3 scripts/smoke_jagua_irregular_sheet_spike.py → 13 PASS, 0 FAIL — OVERALL: PASS
python3 scripts/bench_jagua_optimizer_phase1_rectangular.py → PHASE1_GATE_DECISION: PASS
python3 scripts/smoke_jagua_exact_validation_bridge.py → 13 PASS, 0 FAIL — OVERALL: PASS
cargo test --manifest-path rust/vrs_solver/Cargo.toml → 74 passed; 0 failed
```

### Smoke check summary

| Check | Result |
|-------|--------|
| 1. Fixture exists and is valid JSON | PASS |
| 2. Fixture is hole-free | PASS |
| 3. Concave outer_points stock present | PASS |
| 4. Rust spike bin builds | PASS |
| 5. Spike bin runs without error | PASS |
| 6. NATIVE_BOUNDARY_SUPPORT: NO | PASS |
| 7. L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES | PASS |
| 8. CURRENT_BBOX_ONLY_RISK_DETECTED: YES | PASS |
| 9. DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION | PASS |
| 10. Decision report has JG-15_DECISION line | PASS |
| 11. Python validator rejects notch placement | PASS |
| 12. Item-item collision regression | PASS |

---

## Decision

```
JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION
```

**Path forward for JG-16:**
- Extend `rect_inside_sheet_shape()` to check rect corners against `_outer_poly` using
  `SPolygon.collides_with(point)` and rect edges against outer polygon edges using
  `Edge.collides_with(Edge)`. The `_outer_poly` field is already built; it only needs to be used.
- Item-item collision via `JaguaAdapter` remains unchanged.
- Python exact validator already correct; no changes required.

---

JG-16_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T09:59:44+02:00 → 2026-05-24T10:02:39+02:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.verify.log`
- git: `main@0219154`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     | 32 +++++++++++-----------
 ...gua_optimizer_phase1_rectangular_benchmark.json |  6 ++--
 2 files changed, 19 insertions(+), 19 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json
?? canvases/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t15_irregular_sheet_capability_spike.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike/
?? codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
?? codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.verify.log
?? docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
?? rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs
?? scripts/smoke_jagua_irregular_sheet_spike.py
?? tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json
```

<!-- AUTO_VERIFY_END -->
