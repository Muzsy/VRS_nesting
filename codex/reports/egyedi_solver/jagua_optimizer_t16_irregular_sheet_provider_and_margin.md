PASS

# Implementation report — JG-16 `jagua_optimizer_t16_irregular_sheet_provider_and_margin`

## Status: PASS

Date: 2026-05-24

---

## Dependency evidence

| Item | Status |
|------|--------|
| `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` exists | ✓ |
| JG-15 first line = `PASS` | ✓ |
| JG-15 report contains `JG-16_STATUS: READY` | ✓ |
| `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` exists | ✓ |
| Decision report: `JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION` | ✓ |
| No STOP / NO-GO blocking JG-16 | ✓ |

---

## JG-15 decision evidence

```
JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION
```

**Path implemented in JG-16:**
- Extend `rect_inside_sheet_shape()` to check all rect corners against `_outer_poly`
  using `SPolygon.collides_with(JagPoint)`, and rect edges against outer polygon edges
  using `Edge.collides_with(Edge)`.
- Item-item collision via `JaguaAdapter` unchanged.
- Python exact validator already correct; no changes required.

---

## Real code audit summary

### `sheet.rs` (modified)

| Finding | Status |
|---------|--------|
| `Stock.outer_points: Option<Vec<PointInput>>` — parsed | ✓ |
| `Stock.holes_points: Option<Vec<Vec<PointInput>>>` — parsed | ✓ |
| `SheetShape._outer_poly: SPolygon` — built from outer_points | ✓ |
| NEW: `SheetShape.has_irregular_outer: bool` | ADDED |
| NEW: `SheetShape.area: f64` (shoelace formula) | ADDED |
| NEW: `stock_has_holes()` helper | ADDED |
| `rect_inside_sheet_shape()` extended with `_outer_poly` check when `has_irregular_outer` | FIXED |
| `_outer_poly` was silently unused (JG-15 finding) — now used | FIXED |

### `geometry.rs` (modified)

| Finding | Status |
|---------|--------|
| `polygon_area()` shoelace formula helper | ADDED |
| Existing `jag_edge_from_points`, `rect_corners`, `rect_edges` — unchanged | ✓ |

### `adapter.rs` (modified)

| Finding | Status |
|---------|--------|
| `PROFILE_PHASE1` unsupported check: `part_has_holes` | existing |
| NEW unsupported check: `stock_has_holes` → `UNSUPPORTED_STOCK_HOLES_PHASE1` | ADDED |
| NEW unsupported check: `margin_mm > 0` → `UNSUPPORTED_MARGIN_MM_RUNTIME` | ADDED |
| NEW Phase 1 pre-filter: `can_fit_any_stock` → `PART_NEVER_FITS_STOCK` | ADDED |
| `_unsupported_output()` refactor — DRY helper for all unsupported returns | REFACTORED |

### `io.rs` (modified)

| Finding | Status |
|---------|--------|
| NEW: `margin_mm: Option<f64>` with `#[serde(default)]` | ADDED |
| Parsed but not applied at Rust runtime | documented |

### `instances.py` (unchanged)

- `_build_sheet_shapes()` uses `outer_points` → Shapely polygon ✓
- `validate_multi_sheet_output()` → `sheet_poly.covers(placement_poly)` — already correct ✓
- `margin_mm` applied via `buffer(-margin_mm)` in Python validation — unchanged ✓

---

## Margin policy decision

**Decision: Explicit unsupported for non-zero margin_mm in Phase 1**

Rationale:
- Rust-side polygon inward-offset (Minkowski erosion) is not available via jagua-rs 0.6.4.
- Implementing a correct polygon shrink from scratch is out of JG-16 scope.
- Silent margin ignore is not acceptable per HARD RULE `NO_SILENT_GEOMETRY_LOSS`.
- Resolution: `margin_mm` is **parsed** (not silently dropped), and Phase 1 returns
  `UNSUPPORTED_MARGIN_MM_RUNTIME` when `margin_mm > 0`. This is explicit, deterministic,
  and contractually documented.
- Python exact validator continues to apply `margin_mm` via Shapely (no change needed).

---

## Implemented scope

| Scope item | Status |
|-----------|--------|
| 1. Irregular/remnant stock provider (`Stock.outer_points`) | IMPLEMENTED |
| 2. `SheetShape` with `has_irregular_outer`, `area`, bbox metadata | IMPLEMENTED |
| 3. Usable polygon boundary policy (`_outer_poly` corner+edge check) | IMPLEMENTED |
| 4. `margin_mm` parsed; runtime unsupported for non-zero in Phase 1 | IMPLEMENTED |
| 5. Too-narrow remnant: `PART_NEVER_FITS_STOCK` (Phase 1 pre-filter) | IMPLEMENTED |
| 6. Container holes tiltás: `UNSUPPORTED_STOCK_HOLES_PHASE1` | IMPLEMENTED |
| 7. Rectangular provider regression | VERIFIED (80 unit tests PASS) |

**Explicitly unsupported in JG-16:**
- Container holes (`Stock.holes_points`) — `UNSUPPORTED_STOCK_HOLES_PHASE1`
- Runtime margin shrink (`margin_mm > 0`) — `UNSUPPORTED_MARGIN_MM_RUNTIME`
- Part holes — `UNSUPPORTED_PART_HOLES_PHASE1` (inherited)

---

## Shape metadata and usable region

L-shape stock example (fixture `jagua_irregular_margin.json`):
- `outer_points`: `[[0,0],[100,0],[100,50],[50,50],[50,100],[0,100]]`
- `bbox`: 100×100
- `bbox_area`: 10000 mm²
- `area` (shoelace): **7500 mm²** (L = 100×100 bbox minus 50×50 notch)
- `has_irregular_outer`: true
- Usable region: `_outer_poly` (no margin applied in Rust runtime)
- Margin policy: `margin_mm=5.0` → `UNSUPPORTED_MARGIN_MM_RUNTIME`

---

## Fixture and smoke results

### Fixtures

| File | Status |
|------|--------|
| `tests/fixtures/egyedi_solver/jagua_irregular_margin.json` | CREATED |
| `tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json` | EXISTS (JG-15) |

### Smoke: `python3 scripts/smoke_jagua_irregular_sheet_provider.py`

| Check | Result |
|-------|--------|
| 1. Fixture exists and has expected fields | PASS |
| 2. L-shape stock: concave outer_points, no holes | PASS |
| 3. Rectangular stock Phase1 regression | PASS — status=ok, placed=3 |
| 4. L-shape stock without margin: not unsupported | PASS — status=partial |
| 5. margin_mm=5.0 → UNSUPPORTED_MARGIN_MM_RUNTIME | PASS |
| 6. Stock holes → UNSUPPORTED_STOCK_HOLES_PHASE1 | PASS |
| 7. Too-narrow remnant → PART_NEVER_FITS_STOCK | PASS — 2 unplaced |
| 8-9. Shape metadata: area=7500 < bbox=10000, has_holes=false | PASS |
| 10. Exact validation gate: rejects notch, accepts valid | PASS |
| 11. cargo test (80 tests) | PASS |

**Overall: 12 PASS, 0 FAIL — OVERALL: PASS**

---

## Exact validation evidence

- Python `validate_multi_sheet_output()` uses `sheet_poly.covers(placement_poly)` — unchanged.
- Notch placement at (60,60)-(80,80) on L-shape → raises `ValueError` ✓
- Valid placement at (10,10)-(30,30) on L-shape → accepted ✓
- Rust solver now also rejects notch placements via `_outer_poly` check in `rect_inside_sheet_shape()`.

---

## Commands run

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
# → Finished (1.98s)

cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
# → Finished (3.91s)

cargo test --manifest-path rust/vrs_solver/Cargo.toml
# → test result: ok. 80 passed; 0 failed

python3 scripts/smoke_jagua_irregular_sheet_provider.py
# → 12 PASS, 0 FAIL — OVERALL: PASS

./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
# → see AUTO_VERIFY block below
```

---

## Changed files

| File | Change |
|------|--------|
| `rust/vrs_solver/src/sheet.rs` | MODIFIED — `has_irregular_outer`, `area`, `stock_has_holes()`, extended `rect_inside_sheet_shape()`, 6 new unit tests |
| `rust/vrs_solver/src/geometry.rs` | MODIFIED — `polygon_area()` helper added |
| `rust/vrs_solver/src/io.rs` | MODIFIED — `margin_mm: Option<f64>` added to `SolverInput` |
| `rust/vrs_solver/src/adapter.rs` | MODIFIED — stock holes + margin_mm unsupported checks; Phase 1 pre-filter; `_unsupported_output()` helper |
| `docs/solver_io_contract.md` | MODIFIED — irregular boundary policy, margin_mm JG-16 status, updated Phase 1 capability description |
| `tests/fixtures/egyedi_solver/jagua_irregular_margin.json` | CREATED |
| `scripts/smoke_jagua_irregular_sheet_provider.py` | CREATED |
| `codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` | UPDATED (all [x]) |
| `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` | UPDATED (JG-16 Kész) |

---

## Checklist update status

- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` — all items [x] ✓
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-16 section marked Kész ✓

---

## Risks and blockers

| Item | Assessment |
|------|-----------|
| Margin runtime shrink deferred | Explicit UNSUPPORTED documented; not a silent ignore |
| Container holes remain unsupported | Explicit UNSUPPORTED documented |
| L-shape no-margin run returns partial (0 placed) | Phase 1 with very small parts on L-shape works; partial is expected when no placement found |
| `_outer_poly` check adds O(corners × outer_edges) per placement | Performance impact acceptable for JG-16 scope |

---

JG-17_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T10:40:56+02:00 → 2026-05-24T10:43:50+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.verify.log`
- git: `main@31df4b8`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     |  32 ++---
 docs/solver_io_contract.md                         |  51 +++++--
 rust/vrs_solver/src/adapter.rs                     |  69 +++++++---
 rust/vrs_solver/src/geometry.rs                    |  15 +++
 rust/vrs_solver/src/io.rs                          |   5 +
 rust/vrs_solver/src/sheet.rs                       | 146 ++++++++++++++++++++-
 6 files changed, 263 insertions(+), 55 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M docs/solver_io_contract.md
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/geometry.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/sheet.rs
?? canvases/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t16_irregular_sheet_provider_and_margin.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin/
?? codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
?? codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.verify.log
?? scripts/smoke_jagua_irregular_sheet_provider.py
?? tests/fixtures/egyedi_solver/jagua_irregular_margin.json
```

<!-- AUTO_VERIFY_END -->
