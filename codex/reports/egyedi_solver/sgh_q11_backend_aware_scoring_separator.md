PASS

# Report — SGH-Q11 `sgh_q11_backend_aware_scoring_separator`

## Status

PASS. Backend-aware scoring and separator loss path is wired through all PhaseOptimizer internal search paths. All 277 library tests pass.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md`: first line `PASS`
- `SGH-Q10_STATUS: READY`: present

## Pre-audit

Command run:

```bash
rg -n "validate_placements_for_backend|score_with_backend|collision_backend|compute_backend_decisions" rust/vrs_solver/src/optimizer/
```

### Internal scoring/validation points before Q11

All internal search paths (separator, moves, explore, compress, bpp_phase) used `find_violations` (bbox only) and `score_model.score()` (bbox only). The `collision_backend` selected in `SolverInput` was wired to the production acceptance gate (Q10) but not to the internal optimizer loop.

## Scope summary

### Production files modified

- `rust/vrs_solver/src/optimizer/phase.rs` — `PhaseConfig.collision_backend` field (default `Bbox`)
- `rust/vrs_solver/src/adapter.rs` — `phase_config_from_input` propagates `collision_backend`
- `rust/vrs_solver/src/optimizer/repair.rs` — `validate_placements_for_backend` central helper with sentinel pattern
- `rust/vrs_solver/src/optimizer/score.rs` — `score_layout_from_violations` + `ScoreModel::score_with_backend`
- `rust/vrs_solver/src/optimizer/moves.rs` — `MoveExecutor.collision_backend` + `commit_gate_ok` + `run_separator_fix`
- `rust/vrs_solver/src/optimizer/separator.rs` — `VrsSeparatorConfig.collision_backend` + `compute_backend_decisions` + Unsupported hard penalty
- `rust/vrs_solver/src/optimizer/explore.rs` — `LargeItemSwapDisruption.collision_backend` + `ExplorationPhase::run` backend-aware paths
- `rust/vrs_solver/src/optimizer/compress.rs` — `CompressionPhase::run` backend-aware paths
- `rust/vrs_solver/src/optimizer/bpp_phase.rs` — `BppPhase::run` backend-aware paths

### Not modified (out of scope)

- No CDE full implementation
- No exact backend as default
- No hole/cavity semantics
- No DXF/preflight refactor
- No new stochastic coordinate descent
- No new full polygon penetration-depth loss algorithm
- No `legacy_multisheet` default replacement
- No breaking JSON output change

## Implementation details

### 1. PhaseConfig.collision_backend

`PhaseConfig` gains `pub collision_backend: CollisionBackendKind` defaulting to `Bbox`. `PhaseConfig::deterministic_default()` sets this explicitly. `phase_config_from_input` in adapter.rs assigns it from `resolve_backend_kind(input)`.

### 2. validate_placements_for_backend (repair.rs)

Central helper routing to:
- `Bbox` → `find_violations` (unchanged pre-Q11 behaviour)
- `JaguaPolygonExact` → `validate_placements_with_backend_checked`; if `unsupported_queries > 0`, appends sentinel `(usize::MAX, BoundaryOrSheet)` so callers checking `is_empty()` correctly reject
- `Cde` → same sentinel path (always Unsupported)

The sentinel pattern eliminates any possibility of silent bbox fallback in internal search paths.

### 3. ScoreModel::score_with_backend (score.rs)

- `Bbox`: delegates to `score()` — bit-identical, zero overhead
- Non-Bbox: calls `validate_placements_for_backend` then `score_layout_from_violations`

`score_layout_from_violations` is a `pub(super)` helper extracted from `score_layout` to share logic between the two paths.

### 4. MoveExecutor.collision_backend (moves.rs)

All existing constructors default to `Bbox` — no behaviour change. `new_with_backend_and_rotation_context` allows explicit override. `commit_gate_ok` and `run_separator_fix` now use the configured backend.

### 5. Separator loss strategy for Q11 (separator.rs)

`compute_backend_decisions` free function computes initial exact/Cde decisions for all pairs/boundaries. The VrsCollisionTracker transitional strategy:
- `NoCollision` → `pair_loss = 0`
- `Collision` → bbox surrogate loss (unchanged)
- `Unsupported` → hard penalty `1_000_000.0`

### 6. Phase wiring

All three phases (Explore, Compress, Bpp) create `MoveExecutor` via `new_with_backend_and_rotation_context`, pass `collision_backend` to `VrsSeparatorConfig`, and replace `find_violations` + `score_model.score` with backend-aware variants.

## Test results

```
test result: ok. 277 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.54s
```

### New Q11 tests (12)

| Test | Module |
|---|---|
| `separator_config_backend_default_bbox` | separator.rs |
| `separator_tracker_exact_notch_pair_loss_zero_when_bbox_positive` | separator.rs |
| `same_seed_same_backend_is_deterministic` | separator.rs |
| `phase_config_defaults_collision_backend_bbox` | phase.rs |
| `adapter_phase_optimizer_passes_collision_backend_to_phase_config` | adapter.rs |
| `score_with_backend_bbox_matches_legacy_score` | score.rs |
| `score_with_backend_exact_notch_false_positive_removed` | score.rs |
| `move_executor_backend_aware_commit_gate_rejects_exact_unsupported` | moves.rs |
| `exploration_phase_uses_backend_aware_validation_for_exact` | explore.rs |
| `compression_phase_uses_backend_aware_validation_for_exact` | compress.rs |
| `bpp_phase_uses_backend_aware_commit_gate_for_exact` | bpp_phase.rs |
| `explicit_exact_no_silent_bbox_fallback_in_internal_search` | repair.rs |

<!-- AUTO_VERIFY_END -->

SGH-Q12_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-26T20:49:19+02:00 → 2026-05-26T20:52:34+02:00 (195s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.verify.log`
- git: `main@703c3a1`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs             |  25 +++
 rust/vrs_solver/src/optimizer/bpp_phase.rs |  38 +++-
 rust/vrs_solver/src/optimizer/compress.rs  |  61 +++++-
 rust/vrs_solver/src/optimizer/explore.rs   |  87 +++++++-
 rust/vrs_solver/src/optimizer/moves.rs     |  56 ++++-
 rust/vrs_solver/src/optimizer/phase.rs     |  20 ++
 rust/vrs_solver/src/optimizer/repair.rs    | 126 +++++++++++-
 rust/vrs_solver/src/optimizer/score.rs     | 140 ++++++++++++-
 rust/vrs_solver/src/optimizer/separator.rs | 315 +++++++++++++++++++++++++++--
 9 files changed, 827 insertions(+), 41 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/optimizer/bpp_phase.rs
 M rust/vrs_solver/src/optimizer/compress.rs
 M rust/vrs_solver/src/optimizer/explore.rs
 M rust/vrs_solver/src/optimizer/moves.rs
 M rust/vrs_solver/src/optimizer/phase.rs
 M rust/vrs_solver/src/optimizer/repair.rs
 M rust/vrs_solver/src/optimizer/score.rs
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
?? codex/codex_checklist/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q11_backend_aware_scoring_separator.yaml
?? codex/prompts/egyedi_solver/sgh_q11_backend_aware_scoring_separator/
?? codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
?? codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.verify.log
?? docs/egyedi_solver/sgh_q11_backend_aware_scoring_contract.md
```

<!-- AUTO_VERIFY_END -->
