PASS

# Report — JG-18 `jagua_optimizer_t18_irregular_candidate_generation`

## Meta

- **Task slug:** `jagua_optimizer_t18_irregular_candidate_generation`
- **Task id:** JG-18
- **Kapcsolódó canvas:** `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- **Runner:** `codex/prompts/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation/run.md`
- **Fókusz terület:** Irregular-aware candidate generation / `candidates.rs` API / `sheet.rs` metadata / Integration / Docs / Smoke

## Dependency preflight evidence

- `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md` exists, first line `PASS`.
- JG-17 report contains `JG-18_STATUS: READY`.
- `rust/vrs_solver/src/optimizer/boundary.rs` exists — the single auditable boundary façade created in JG-17.
- `docs/solver_io_contract.md` contains JG-17 boundary policy section (irregular inset semantics).

## Implementation summary

### sheet.rs — outer_vertices field (JG-18 new)

Added `pub outer_vertices: Vec<Point>` to `SheetShape`. Populated in `stock_to_shape()`:

```rust
let outer_vertices = if has_irregular_outer { outer.clone() } else { Vec::new() };
```

Non-empty only for irregular stocks (`has_irregular_outer = true`). Used by `generate_candidates_with_sheets` for vertex-near, edge-near, and interior grid candidates.

### candidates.rs — irregular-aware API (JG-18 new)

New types added:

```rust
pub enum CandidateSource { Origin, PlacedNeighbor, VertexNear, EdgeNear, InteriorSample }

pub struct CandidateGenerationStats {
    pub total: usize,
    pub from_origin: usize,
    pub from_neighbor: usize,
    pub from_vertex: usize,
    pub from_edge: usize,
    pub from_interior: usize,
}
```

New function:

```rust
pub fn generate_candidates_with_sheets(
    sheets: &[SheetShape],
    placed: &[PlacedBbox],
) -> (Vec<CandidatePoint>, CandidateGenerationStats)
```

Candidate sources per sheet:
- **Origin (legacy):** one `(0.0, 0.0)` per sheet.
- **PlacedNeighbor (legacy):** right/top/top-right of each placed bbox.
- **VertexNear (irregular only):** each `outer_vertices` polygon vertex.
- **EdgeNear (irregular only):** midpoint of each outer polygon edge.
- **InteriorSample (irregular only):** deterministic grid, step = `bbox / INTERIOR_GRID_STEPS` (5), min step 1.0; up to 4×4 = 16 interior points per sheet.

For rectangular stocks: identical output to legacy `generate_candidates()`.

Legacy `generate_candidates(sheet_count, placed)` is preserved unchanged (backward compat).

Constants: `INTERIOR_GRID_STEPS = 5`, `MIN_STEP = 1.0`.

Sort/dedup policy: `(sheet_index ASC, y ASC, x ASC)`, EPS-proximity dedup on same sheet.

### initializer.rs — candidate stats in ConstructionDiagnostics (JG-18)

Added fields to `ConstructionDiagnostics`:

```rust
pub total_candidates_generated: usize,
pub candidates_from_vertex: usize,
pub candidates_from_edge: usize,
pub candidates_from_interior: usize,
```

Updated `build_initial_layout()` to use `generate_candidates_with_sheets` and accumulate:

```rust
let (candidates, cgen) = generate_candidates_with_sheets(sheets, &placed_bboxes);
diag.total_candidates_generated += cgen.total;
diag.candidates_from_vertex += cgen.from_vertex;
diag.candidates_from_edge += cgen.from_edge;
diag.candidates_from_interior += cgen.from_interior;
```

### repair.rs — irregular-aware candidates (JG-18)

Changed reinsertion loop to use `generate_candidates_with_sheets(sheets, &placed_bboxes)`.

### sheet_elimination.rs — candidate API + boundary bug fix (JG-18)

Two changes:
1. Candidate call updated to `generate_candidates_with_sheets`.
2. **Bug fix:** was calling `rect_inside_sheet_shape(rect, sheet)` directly, bypassing the
   `boundary::rect_within_boundary` façade. Fixed to use the façade (JG-17 inset semantics).

## Candidate source breakdown example

L-shape stock (100×100 bbox, 6 vertices, 6 edges):
- `from_origin = 1` (one per sheet)
- `from_vertex = 6` (6 polygon vertices)
- `from_edge = 6` (6 edge midpoints)
- `from_interior ≤ 16` (4×4 grid, step 20mm; after dedup with vertex/edge points)

This produces more candidates than legacy (origin only + placed neighbors) → better coverage
of the irregular interior without uniform raster sampling.

## Irregular placement example

Fixture `tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json`:
- L-shape stock: `outer_points` 6-point, `qty=1`
- Part `small_part`: 20×15, qty=3, rotations [0, 90]

Solver run (seed=42, time_limit=5s, profile=jagua_optimizer_phase1_outer_only):

```
status: ok
placed_count: 3
```

All 3 items placed in the bottom-left valid region of the L-shape. The vertex-near and
interior candidates enable the BLF-first search to find valid positions in the L-interior.

## Determinism evidence

Two solver runs on identical input (same fixture, seed=42) produce identical placements:

```
run 1: 3 placements [identical keys]
run 2: 3 placements [identical keys]
determinism: PASS
```

Candidate generation is deterministic for identical `(sheets, placed)` input —
no random sampling, sort/dedup is stable.

## Rectangular regression evidence

Rectangular stock regression (200×200, Phase1, seed=42):

```
status: ok
placed_count: 3 (2×50×50 + 1×80×30)
```

For rectangular stocks, `generate_candidates_with_sheets` produces zero vertex/edge/interior
candidates (guarded by `has_irregular_outer` check) — identical to legacy behavior.

## Tests

`cargo test` result: **93 passed, 0 failed** (4 new JG-18 tests + 89 prior):

New JG-18 tests in `candidates.rs`:
- `irregular_candidates_include_vertex_edge_interior`
- `irregular_candidates_more_than_legacy`
- `rectangular_sheets_no_irregular_sources`
- `irregular_candidates_deterministic`

## Smoke

```
python3 scripts/smoke_jagua_irregular_candidate_generation.py
=== RESULTS: 10 PASS, 0 FAIL ===
OVERALL: PASS
```

JG-17 regression smoke also PASS.

## Deviation from plan

**Neighbor-near** as a distinct new candidate source was not implemented as a separate class.
The existing `PlacedNeighbor` behavior (right/top/top-right of placed bboxes) is the
neighbor-near source. This is correct per the task spec ("neighbor-near implementálva vagy
dokumentált fallbackkel jelölve") — the source already existed and is now documented as such.

No other deviations.

## Files changed

- `rust/vrs_solver/src/sheet.rs` — `outer_vertices` field added
- `rust/vrs_solver/src/optimizer/candidates.rs` — `CandidateSource`, `CandidateGenerationStats`, `generate_candidates_with_sheets`, 4 new tests
- `rust/vrs_solver/src/optimizer/initializer.rs` — `generate_candidates_with_sheets`, expanded `ConstructionDiagnostics`
- `rust/vrs_solver/src/optimizer/repair.rs` — `generate_candidates_with_sheets`
- `rust/vrs_solver/src/optimizer/sheet_elimination.rs` — `generate_candidates_with_sheets` + `rect_within_boundary` bug fix
- `tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json` — new fixture
- `scripts/smoke_jagua_irregular_candidate_generation.py` — new smoke script (10 checks)
- `docs/solver_io_contract.md` — JG-18 candidate generation contract section
- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md` — all [x]
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` — JG-18 Kész

JG-19_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-24T17:55:31+02:00 → 2026-05-24T17:58:26+02:00 (175s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.verify.log`
- git: `main@de4d6cd`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 .codegraphcontext/db/falkordb.settings             |   2 +-
 .../jagua_optimizer_task_progress_checklist.md     |  36 ++--
 docs/solver_io_contract.md                         |  61 ++++++
 rust/vrs_solver/src/optimizer/candidates.rs        | 226 +++++++++++++++++++++
 rust/vrs_solver/src/optimizer/initializer.rs       |  22 +-
 rust/vrs_solver/src/optimizer/repair.rs            |   4 +-
 rust/vrs_solver/src/optimizer/sheet_elimination.rs |   9 +-
 rust/vrs_solver/src/sheet.rs                       |   8 +-
 8 files changed, 339 insertions(+), 29 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .codegraphcontext/db/falkordb.settings
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M docs/solver_io_contract.md
 M rust/vrs_solver/src/optimizer/candidates.rs
 M rust/vrs_solver/src/optimizer/initializer.rs
 M rust/vrs_solver/src/optimizer/repair.rs
 M rust/vrs_solver/src/optimizer/sheet_elimination.rs
 M rust/vrs_solver/src/sheet.rs
?? canvases/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t18_irregular_candidate_generation.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation/
?? codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
?? codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.verify.log
?? scripts/smoke_jagua_irregular_candidate_generation.py
?? tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json
```

<!-- AUTO_VERIFY_END -->
