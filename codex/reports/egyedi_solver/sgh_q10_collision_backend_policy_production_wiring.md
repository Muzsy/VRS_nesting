PASS

# Report — SGH-Q10 `sgh_q10_collision_backend_policy_production_wiring`

## Status

PASS. The collision backend production acceptance policy is wired. All 265 library tests pass and the full repo gate is green.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md`: first line `PASS`
- `SGH-Q10_STATUS: READY`: present

## Pre-audit

Command run:

```bash
rg -n "find_violations\(|find_violations_with_backend|validate_and_commit|CollisionBackend|BboxCollisionBackend|JaguaPolygonExactBackend|CdeCollisionBackend" rust/vrs_solver/src
```

### Production bbox validation points (before Q10)

- `adapter.rs:160` — `find_violations(&layout.placements, ...)` (PhaseOptimizer path)
- `adapter.rs:71` — `layout.validate_and_commit(parts, sheets)` (phase_commit_or_unsupported)
- `working.rs:103` — `find_violations(...)` inside `validate_for_commit`
- `moves.rs`, `separator.rs`, `compress.rs`, `explore.rs`, `bpp_phase.rs`, `sheet_elimination.rs` — internal bbox find_violations for scoring/repair (unchanged, Q11 scope)

### Q08 exact backend helper points (before Q10)

- `collision_backend.rs` — `BboxCollisionBackend`, `JaguaPolygonExactBackend`, `CdeCollisionBackend`
- `repair.rs` — `find_violations_with_backend` (with silent bbox fallback on Unsupported)
- No production path used the exact backend for acceptance gates

### Policy wiring added in Q10

- `io.rs`: `CollisionBackendKind` enum + `SolverInput.collision_backend` optional field
- `collision_backend.rs`: `BackendValidationDiagnostics` struct
- `repair.rs`: `BackendValidationResult` + `validate_placements_with_backend_checked` (no silent fallback)
- `working.rs`: `WorkingCommitError::UnsupportedBackend` + `BackendCommitResult` + `validate_and_commit_with_backend`
- `adapter.rs`: backend-aware routing on both Phase1 paths; `collision_backend_diagnostics` output field

## Scope summary

### Permitted production files modified

- `rust/vrs_solver/src/io.rs` — new types, new fields
- `rust/vrs_solver/src/optimizer/collision_backend.rs` — `BackendValidationDiagnostics`
- `rust/vrs_solver/src/optimizer/repair.rs` — `BackendValidationResult`, `validate_placements_with_backend_checked`
- `rust/vrs_solver/src/optimizer/working.rs` — `UnsupportedBackend` variant, `BackendCommitResult`, `validate_and_commit_with_backend`
- `rust/vrs_solver/src/adapter.rs` — backend routing, output field

### Not modified (out of scope)

- `phase.rs` — no PhaseConfig backend field needed (gate is at commit point)
- `separator.rs`, `compress.rs`, `explore.rs`, `bpp_phase.rs`, `moves.rs` — internal scoring unchanged (QUALITY_RISK below)

## Implementation details

### 1. Input enum / policy

`CollisionBackendKind { Bbox, JaguaPolygonExact, Cde }` with `serde(rename_all = "snake_case")`.  
Missing `collision_backend` field → `None` → `resolve_backend_kind` returns `Bbox` default.  
Backward-compatible: existing JSON without this field is unchanged.

### 2. Checked validation helper

`validate_placements_with_backend_checked` in `repair.rs`:
- No silent bbox fallback on `Unsupported`
- Counts `unsupported_queries` per boundary and overlap query
- `bbox_fallback_queries` always 0 in this path
- Violations still reported as before for confirmed Collision cases

### 3. WorkingLayout commit helper

`validate_and_commit_with_backend`:
- `Bbox`: delegates to `validate_for_commit` — 100% identical to pre-Q10 behavior
- `JaguaPolygonExact`: blocks if `unsupported_queries > 0` (`JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY`) or violations present
- `Cde`: always returns `UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED" }`

### 4. Adapter routing

`LegacyMultisheet`: backend gate added only for non-bbox backends (no output change for bbox default).  
`PhaseOptimizer`: double `find_violations` + `validate_and_commit` replaced by single `validate_and_commit_with_backend`.  
No silent fallback for explicit exact/cde.

### 5. Optional diagnostics

`SolverOutput.collision_backend_diagnostics` populated when a backend gate runs (non-bbox or explicit bbox on phase_optimizer path with a successful commit). Absent for bbox default on legacy_multisheet path.

## Test coverage

All 9 required tests implemented:

| Test | Location | Status |
|---|---|---|
| `solver_input_collision_backend_defaults_to_bbox` | adapter | ok |
| `explicit_bbox_matches_implicit_default_output` | adapter | ok |
| `phase_optimizer_with_bbox_backend_preserves_q09_behavior` | adapter | ok |
| `jagua_polygon_exact_backend_can_be_selected_in_solver_input` | adapter | ok |
| `jagua_polygon_exact_invalid_outer_points_returns_unsupported_not_bbox_fallback` | adapter | ok |
| `cde_backend_returns_unsupported_not_bbox_fallback` | adapter | ok |
| `backend_validation_bbox_matches_find_violations` | repair | ok |
| `backend_validation_reports_unsupported_count` | repair | ok |
| `same_seed_same_backend_is_deterministic` | adapter | ok |
| `jagua_polygon_exact_l_shape_notch_does_not_report_bbox_false_positive` | adapter (optional) | ok |

Total library tests: 265 passing, 0 failing.

## QUALITY_RISK

**QUALITY_RISK-Q11**: The separator, compress, BPP, and explore phases use `find_violations` (bbox) internally for candidate scoring and move evaluation. When `collision_backend: "jagua_polygon_exact"` is selected, the production acceptance gate is exact but the optimizer's internal search heuristic is still bbox-based. This means the optimizer cannot exploit notch areas during search, only validate that a placement is collision-free at commit time.

The production acceptance gate is correct: no false positives on exact geometry, and invalid geometry is not silently downgraded. But the optimizer's ability to find better packings using exact geometry is deferred to Q11 (backend-aware scoring/separator loss path).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-26T19:58:41+02:00 → 2026-05-26T20:01:45+02:00 (184s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.verify.log`
- git: `main@38ac8b4`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     | 293 +++++++++++++++++++--
 rust/vrs_solver/src/io.rs                          |  31 +++
 rust/vrs_solver/src/optimizer/collision_backend.rs |  11 +
 rust/vrs_solver/src/optimizer/repair.rs            | 136 +++++++++-
 rust/vrs_solver/src/optimizer/working.rs           | 108 +++++++-
 5 files changed, 556 insertions(+), 23 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/collision_backend.rs
 M rust/vrs_solver/src/optimizer/repair.rs
 M rust/vrs_solver/src/optimizer/working.rs
?? canvases/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
?? codex/codex_checklist/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q10_collision_backend_policy_production_wiring.yaml
?? codex/prompts/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring/
?? codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
?? codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.verify.log
?? docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md
```

<!-- AUTO_VERIFY_END -->

SGH-Q11_STATUS: READY
