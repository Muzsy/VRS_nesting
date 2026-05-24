PASS

# Report — JG-17 `jagua_optimizer_t17_irregular_boundary_validation`

## Meta

- **Task slug:** `jagua_optimizer_t17_irregular_boundary_validation`
- **Task id:** JG-17
- **Kapcsolódó canvas:** `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- **Runner:** `codex/prompts/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation/run.md`
- **Fókusz terület:** Rust boundary validation facade / Python exact validation / Docs / Smoke

## Dependency preflight evidence

- `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` exists, first line `PASS`.
- JG-16 report contains `JG-17_STATUS: READY`.
- `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` exists, decision = `OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION` (JG-15).
- `docs/solver_io_contract.md` contains JG-16 irregular sheet boundary policy section.

## Implementation summary

### optimizer/boundary.rs (created)

New `rust/vrs_solver/src/optimizer/boundary.rs` is the single auditable boundary policy point.
All construction, repair, scoring, and adapter paths delegate through it.

```
pub fn rect_within_boundary(rect: Rect, sheet: &SheetShape) -> bool
pub fn sheet_index_valid(sheet_index: usize, sheets: &[SheetShape]) -> bool
pub fn is_placement_boundary_valid(rect: Rect, sheet_index: usize, sheets: &[SheetShape]) -> bool
```

### Wiring

- `optimizer/mod.rs`: added `pub mod boundary;`
- `optimizer/initializer.rs`: `rect_inside_sheet_shape` → `rect_within_boundary`
- `optimizer/repair.rs`: both `find_violations()` and reinsertion loop use `rect_within_boundary`
- `adapter.rs`: `JaguaAdapter::check_rect_in_sheet()` delegates to `rect_within_boundary`

### On-boundary point fix (discovered and fixed)

Root cause: jagua-rs `SPolygon.collides_with(JagPoint)` returns false for points exactly
on the polygon boundary (vertex or collinear edge). For an L-shape with vertex at (0,0),
`generate_candidates` emits the first candidate at (0.0, 0.0). Without the fix, all corners
of a rect at origin would fail the containment test → all items get `REPAIR_FAILED`.

Fix: `rect_inside_sheet_shape()` uses an inset rect (INSET = 1e-6 per axis, inward) for ALL
irregular-stock checks (both corner containment and edge-crossing). This correctly tests:
"is the interior of the rect inside the polygon?" — the geometrically correct predicate.

The inset is small enough to be irrelevant for any physical placement (1 nm in mm units) and
large enough to survive f64→f32 narrowing in `to_jag_point` (f32 epsilon ≈ 1.2e-7 at scale 1).

## Boundary-touch policy

**Rectangular stocks** (`has_irregular_outer = false`):
- Bbox-only check with EPS = 1e-9 tolerance.
- Edge exactly touching sheet boundary → **accepted**.

**Irregular stocks** (`has_irregular_outer = true`):
- Inset rect (INSET = 1e-6) used for all containment and edge-crossing checks.
- Rect corner exactly on polygon vertex → **accepted** (interior is inside).
- Rect edge collinear with polygon edge → **accepted** (inset edge doesn't overlap).
- Rect with any corner in a concave notch → **rejected** (inset corner is outside polygon).
- Rect straddling the boundary → **rejected** (inset corner is outside, or inset edge crosses).

## Proxy vs exact boundary

- **Proxy (Rust):** `rect_within_boundary()` — fast; used during all optimizer paths.
  Correct containment check via jagua SPolygon primitives with inset semantics.
- **Exact (Python):** `vrs_nesting.nesting.instances.validate_multi_sheet_output()` —
  uses Shapely `sheet_poly.covers(placement_poly)`. Authoritative validation gate.
  Python validator also applies `margin_mm` via `buffer(-margin_mm)` (Rust does not).

## Positive and negative control examples

### Positive control — rect at (10,10)→(30,30) on L-shape stock

L-shape: `outer_points [[0,0],[100,0],[100,50],[50,50],[50,100],[0,100]]`

```
rect_within_boundary(Rect{10,10,30,30}, l_shape_sheet) == true
```

Item placed in bottom-left of L. All inset corners well inside polygon. ✓

### Positive control (boundary touch) — rect at (0,0)→(20,15) on L-shape stock

```
rect_within_boundary(Rect{0,0,20,15}, l_shape_sheet) == true
```

Corner (0,0) is exactly on polygon vertex. Inset corners at (1e-6,1e-6), (19.999999,1e-6),
(19.999999,14.999999), (1e-6,14.999999) — all inside L. ✓

### Negative control — rect at (60,60)→(80,80) on L-shape stock (notch)

```
rect_within_boundary(Rect{60,60,80,80}, l_shape_sheet) == false
```

All corners in the top-right notch (x>50, y>50). Inset corners also in notch.
`SPolygon.collides_with` returns false for all → boundary check rejects. ✓

### Python exact validator

```python
# Shapely: notch rect rejected
sheet_poly.covers(notch_placement_poly)  # False → ValueError raised

# Shapely: inside-L rect accepted
sheet_poly.covers(inside_placement_poly)  # True → no error
```

## Executed commands and results

```
cargo test (89 tests)
RESULT: ok. 89 passed; 0 failed
```

```
python3 scripts/smoke_jagua_irregular_boundary_validation.py
RESULTS: 11 PASS, 0 FAIL
OVERALL: PASS
```

Key smoke checks:
- Check 3: Rectangular stock regression → status='ok', placed=3 ✓
- Check 4: L-shape fixture → status='ok', placed=3 (all on sheet 0 at x=0,20,40) ✓
- Check 5: Notch placement validator reject ✓
- Check 6: Inside-L placement validator accept ✓
- Check 8: margin_mm=5.0 → `UNSUPPORTED_MARGIN_MM_RUNTIME` ✓
- Check 9: cargo test 89/89 ✓

```
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
RESULT: PASS ✅ (exit code 0)
```

## Files created / modified

**Created:**
- `rust/vrs_solver/src/optimizer/boundary.rs` — boundary policy facade (3 public fns + 9 unit tests)
- `tests/fixtures/egyedi_solver/jagua_irregular_boundary_validation.json` — L-shape fixture with positive/negative control metadata
- `scripts/smoke_jagua_irregular_boundary_validation.py` — 11-check smoke script

**Modified:**
- `rust/vrs_solver/src/sheet.rs` — inset-rect fix for irregular outer boundary check; new `l_shape_origin_placement_accepted` test
- `rust/vrs_solver/src/adapter.rs` — `check_rect_in_sheet` delegates to `boundary::rect_within_boundary`
- `rust/vrs_solver/src/optimizer/mod.rs` — `pub mod boundary;` added
- `rust/vrs_solver/src/optimizer/initializer.rs` — uses `boundary::rect_within_boundary`
- `rust/vrs_solver/src/optimizer/repair.rs` — uses `boundary::rect_within_boundary`
- `docs/solver_io_contract.md` — JG-17 boundary validation policy section added
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md` — all [x]
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-17 Kész

## Deviations from plan

None. All checklist items completed as specified.

The on-boundary point bug (jagua `SPolygon.collides_with` returning false for vertex-exact points,
and `JagEdge.collides_with` triggering for collinear overlap) was discovered during implementation
and fixed in `rect_inside_sheet_shape` using an inset rect. This is consistent with the JG-17
"safe-side" policy mandate and is documented in both the boundary.rs module docs and
`docs/solver_io_contract.md`.

JG-18_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- exit kód: `0`
- futás: 2026-05-24
- parancs: `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`
- log: `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.verify.log`

<!-- AUTO_VERIFY_END -->
