# Runner — SGH-Q20 continuous rotation refinement v1

You are working in the `VRS_nesting` repo. Implement SGH-Q20 exactly as specified by:

```text
canvases/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q20_continuous_rotation_refinement.yaml
codex/codex_checklist/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
```

## Hard gate before edits

Read and understand these files before changing code:

```text
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
rust/vrs_solver/src/rotation_policy.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
```

If Q16 or Q18A-R1 is not PASS/READY_FOR_AUDIT in the repo, stop and report BLOCKED.

## Goal

Implement deterministic Continuous rotation refinement v1:

1. stronger coarse continuous angle coverage;
2. local incumbent-neighborhood wiggle/refinement candidates;
3. compression phase wiring;
4. backend-aware commit gate;
5. diagnostics and tests.

This is the next quality-producing solver task. Do not do Q19 benchmark gate, Q18B session/cache rewrite, or Q21 full loss-model rewrite.

## Required implementation details

### A. Candidate generation

Audit current `RotationPolicyKind::Continuous`. Improve it so the candidate set is deterministic and quality-useful.

Required properties:

- stable across runs for same seed/config;
- includes canonical angles;
- includes useful diagonal/coarse coverage when sample_count >= 8/16;
- normalized and deduped;
- no policy precedence regression.

A good implementation is one of:

- uniform linspace base over `[0, 360)` plus canonical dedupe, optionally with deterministic seed-jitter extras; or
- existing seeded candidates plus deterministic coarse grid that includes 45°/22.5° style values.

Do not rely on purely random-looking samples as the only non-canonical coverage.

### B. Local refinement helper

Add a helper, preferably near `rotation_policy.rs` or a new optimizer module, that computes local refinement candidate angles.

Suggested API shape:

```rust
pub fn continuous_refinement_angles(
    current_deg: f64,
    effective_policy: &RotationPolicyKind,
    base_candidates: &[f64],
    max_candidates: usize,
) -> Vec<f64>
```

This is only a suggestion. Use repo style if a better fit exists.

Required behavior:

- only adds local extra candidates for `Continuous`;
- does not add unsupported candidates for Discrete/Orthogonal/FortyFive/HalfTurn/Locked;
- uses symmetric offsets around the incumbent rotation;
- deterministic order;
- max candidate cap;
- normalizes to `[0, 360)` and dedupes.

### C. Compression phase wiring

In `CompressionPhase::run`, extend the current rotation loop so continuous placements also try refinement candidates.

Commit rules:

- call existing move/reinsert path or equivalent;
- validate with `validate_placements_for_backend` before accepting;
- accept only if score improves;
- preserve incumbent on all rejection paths;
- do not fallback to bbox under CDE/Jagua exact.

### D. Diagnostics

Add minimal diagnostics to `PhaseDiagnostics` and `OptimizerDiagnosticsOutput`.

Suggested fields:

```text
rotation_refinement_attempts
rotation_refinement_accepts
rotation_refinement_rejections
rotation_refinement_best_delta
rotation_refinement_enabled
```

Exact names can differ, but the report must map them clearly.

### E. Tests

Add tests for all of these:

1. Continuous candidate generation includes deterministic coarse diagonals.
2. Continuous local refinement returns symmetric normalized angles and dedupes.
3. Non-continuous policies do not receive extra unsupported angles.
4. Compression phase attempts refinement under Continuous.
5. Accepted refinement is backend-gated and score-improving.
6. Default determinism remains stable.
7. CDE path still reports `bbox_fallback_queries == 0`.

Add a smoke script if practical:

```text
scripts/smoke_sgh_q20_continuous_rotation_refinement.py
```

The smoke should be small and deterministic. It should not be an LV8 benchmark gate.

## Verification

Run at least:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q18a_cde_observability.py
python3 scripts/smoke_sgh_q20_continuous_rotation_refinement.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
```

If a command cannot run, mark the report `BLOCKED` or `REVISE` unless there is an explicit repo-compatible reason and equivalent evidence.

## Report

Create:

```text
codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
```

The first line must be exactly one of:

```text
PASS
REVISE
BLOCKED
```

PASS report must include:

```text
SGH-Q20_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY|HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

Also include:

- modified files;
- implementation summary;
- exact tests/commands and results;
- diagnostics field names;
- proof that default determinism is not polluted by timing/runtime randomness;
- proof that CDE final commit still has no bbox fallback;
- known limitations.
