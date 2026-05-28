PASS

# Report — SGH-Q20 continuous rotation refinement v1

## Dependency gate

```
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md  → PASS
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md → PASS
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md → PASS (SGH-Q20_STATUS: READY)
```

Dependency gate: **PASS**

## What Q20 implements

### A. Candidate generation — `rust/vrs_solver/src/rotation_policy.rs`

`DEFAULT_CONTINUOUS_SAMPLE_COUNT` raised from 8 to 16. Sparrow-aligned: 22.5° spacing, includes
45° diagonal angles. Coarse coverage is deterministic linspace (seed parameter renamed `_seed`,
unused). Canonical angles [0, 90, 180, 270] are always inserted if not already present.

```rust
pub const DEFAULT_CONTINUOUS_SAMPLE_COUNT: usize = 16;
```

New `continuous_refinement_angles()` helper:
- Returns empty vec for all non-Continuous policies.
- Emits symmetric ±offset candidates: `REFINEMENT_OFFSETS = [0.75, 1.5, 3.0, 7.5, 15.0]` degrees.
- Deduplicates against `base_candidates` and against its own accumulation.
- Capped at `REFINEMENT_MAX_CANDIDATES = 10`.

8 new unit tests in `rotation_policy::tests` covering:
- coarse linspace includes diagonals at n=16
- canonical angles always present
- seed independence (linspace is deterministic regardless of seed)
- refinement symmetry, normalization, boundary wrapping
- non-Continuous policies return empty refinement vec
- cap respected
- base deduplication

### B. `effective_policy_kind` helper — `rust/vrs_solver/src/item.rs`

New pub function resolving effective `RotationPolicyKind` from part + context (same precedence
as `resolve_instance_rotation_angles`):
1. Part-level `rotation_policy` wins.
2. Non-empty `allowed_rotations_deg` → `Discrete`.
3. Context global policy.
4. Fallback: `Orthogonal`.

Existing seed-sensitivity test replaced by `continuous_policy_linspace_is_seed_independent`,
confirming linspace produces identical candidates across seeds.

### C. Phase diagnostics extension — `rust/vrs_solver/src/optimizer/phase.rs`

`PhaseDiagnostics` extended with 4 new fields (all zero/false by default):

```rust
pub rotation_refinement_enabled: bool,
pub rotation_refinement_attempts: usize,
pub rotation_refinement_accepts: usize,
pub rotation_refinement_best_delta: f64,
```

`PhaseDiagnostics::summary()` updated. `PhaseOptimizer::run` wires compression-phase refinement
diagnostics into `PhaseResult::diagnostics`.

### D. Compression phase refinement loop — `rust/vrs_solver/src/optimizer/compress.rs`

After the main per-placement rotation loop, for each placement where `effective_policy_kind` is
`Continuous`:
1. Compute `continuous_refinement_angles` against already-tried rotations.
2. For each refinement candidate:
   - Seed placement at `(ax, ay)` = `placement_anchor_from_rect_min(0, 0, w, h, ref_rot)`.
   - Run `VrsSeparator` scoped to the current sheet only.
   - Reject if not converged/zero-loss.
   - Reject if placement count changed.
   - Reject if `validate_placements_for_backend` (with configured backend) returns violations.
   - Accept only if `try_score.total_cost < incumbent_score`.
   - On accept: update incumbent, record `best_delta`, increment `rotation_refinement_accepts`.
3. CDE invariant preserved: `VrsSeparatorConfig` propagates `collision_backend`, so no bbox fallback.

4 new tests in `optimizer::compress::tests`:
- `compression_rotation_refinement_enabled_for_continuous_policy`: enabled flag set, attempts > 0.
- `compression_refinement_output_is_violation_free`: bbox-based validation clean after continuous refinement.
- `compression_refinement_not_triggered_for_orthogonal_policy`: attempts == 0 for Orthogonal.
- `compression_refinement_cde_bbox_fallback_zero`: CDE-backend validation (not bbox) confirms clean
  placements; CDE counter structural invariant `pair + boundary == total` holds.

### E. IO output — `rust/vrs_solver/src/io.rs`

`OptimizerDiagnosticsOutput` extended with 5 non-optional fields (placed before timing fields):

```rust
pub rotation_refinement_enabled: bool,
pub rotation_refinement_attempts: usize,
pub rotation_refinement_accepts: usize,
pub rotation_refinement_rejections: usize,
pub rotation_refinement_best_delta: f64,
```

`rotation_refinement_rejections` = `attempts − accepts` (computed in adapter).
Timing fields remain `Option<f64>` governed by `VRS_CDE_OBSERVABILITY_TIMING=1` (Q18A-R1 policy).

### F. Adapter wiring — `rust/vrs_solver/src/adapter.rs`

`OptimizerDiagnosticsOutput` construction updated to include all 5 refinement fields.
`rotation_refinement_rejections` = `rotation_refinement_attempts.saturating_sub(rotation_refinement_accepts)`.

### G. Smoke script — `scripts/smoke_sgh_q20_continuous_rotation_refinement.py`

5 fixtures:

| # | Fixture | Expected |
|---|---------|----------|
| 1 | Continuous + phase_optimizer | `rotation_refinement_enabled=true`, `attempts>0`, `accepts+rejections==attempts` |
| 2 | Orthogonal + phase_optimizer | `rotation_refinement_enabled=false`, `attempts==0` |
| 3 | Continuous + CDE | `bbox_fallback_queries==0`, `backend_used=cde_adapter`, `rotation_refinement_enabled=true` |
| 4 | Linspace fit-rescue: 100×20 in 90×90 | continuous places ≥ orthogonal; continuous places ≥ 1 |
| 5 | Default output, no timing fields | all 5 timing fields absent |

## Verification results

```
cargo test --lib rotation_policy                          → 24 passed, 0 failed
cargo test --lib optimizer::compress                      → 12 passed, 0 failed
cargo test --lib adapter                                  → 55 passed, 0 failed
cargo test --lib (full suite)                             → 368 passed, 0 failed
python3 scripts/smoke_sgh_q18a_cde_observability.py      → 49 passed, 0 failed (SMOKE: PASS)
python3 scripts/smoke_sgh_q20_continuous_rotation_refinement.py → 24 passed, 0 failed (SMOKE: PASS)
```

Smoke fixture 1 observed: `attempts=156, accepts=13, rejections=143, best_delta=64.9`
Smoke fixture 3 observed: `cde_total_queries=2597, refinement_attempts=38, bbox_fallback=0`
Smoke fixture 4 confirmed: orthogonal `placed=0 unplaced=2`, continuous `placed=1 unplaced=1`

## Status markers

SGH-Q20_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: NOT_REQUIRED_NOW

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-28T21:31:39+02:00 → 2026-05-28T21:34:33+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.verify.log`
- git: `main@9bd3d23`
- módosított fájlok (git status): 13

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs            |  13 +-
 rust/vrs_solver/src/io.rs                 |   7 +
 rust/vrs_solver/src/item.rs               |  42 +++++-
 rust/vrs_solver/src/optimizer/compress.rs | 194 +++++++++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/phase.rs    |  16 ++-
 rust/vrs_solver/src/rotation_policy.rs    | 204 +++++++++++++++++++++++-------
 6 files changed, 421 insertions(+), 55 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/item.rs
 M rust/vrs_solver/src/optimizer/compress.rs
 M rust/vrs_solver/src/optimizer/phase.rs
 M rust/vrs_solver/src/rotation_policy.rs
?? canvases/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
?? codex/codex_checklist/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q20_continuous_rotation_refinement.yaml
?? codex/prompts/egyedi_solver/sgh_q20_continuous_rotation_refinement/
?? codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
?? codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.verify.log
?? scripts/smoke_sgh_q20_continuous_rotation_refinement.py
```

<!-- AUTO_VERIFY_END -->
