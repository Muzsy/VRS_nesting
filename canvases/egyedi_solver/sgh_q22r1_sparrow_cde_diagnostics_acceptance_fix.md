# SGH-Q22R1 — Sparrow CDE diagnostics and acceptance hardening

## Intent

Q22 created the first explicit `sparrow_experimental` kernel. That is valuable, but Q22 cannot be treated as a clean production-direction PASS while the CDE/Sparrow failure path loses Sparrow diagnostics, smoke tests skip CDE unsupported cases, and the benchmark report hides zero values / undercounts unsupported Sparrow runs.

This is not a cosmetic report fix. The goal remains full jagua_rs/Sparrow behavior. A Sparrow kernel that works only in bbox mode and cannot diagnose CDE failure is not sufficient.

## Required pre-audit

Read and audit:

```text
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json
codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
scripts/smoke_sgh_q22_sparrow_kernel.py
scripts/bench_sgh_q22_sparrow_kernel.py
```

Document these Q22 audit findings explicitly:

```text
- sparrow_experimental + bbox converges on small/medium fixtures;
- sparrow_experimental + cde returns unsupported / timeout on medium fixtures;
- unsupported Sparrow output currently drops optimizer_diagnostics;
- Q22 smoke skips CDE no-fallback if unsupported, therefore it does not prove the CDE success path;
- Q22 smoke boundary_recovery fixture does not actually start from boundary-violating adapter input;
- continuous_rotation_rescue smoke does not require convergence;
- benchmark table renders 0.0/0 as '-' in several fields;
- benchmark denominator excludes unsupported Sparrow runs, making convergence summary misleading;
- Q18B_RECOMMENDATION: NOT_REQUIRED_NOW is not justified if CDE Sparrow is 20s unsupported / timeout on small-medium fixtures.
```

## Mandatory fixes

### 1. Preserve Sparrow diagnostics on unsupported outputs

Add an unsupported-output helper that can include both:

```text
optimizer_diagnostics
collision_backend_diagnostics
```

For `sparrow_experimental`, all failure exits must preserve Sparrow diagnostics:

```text
SPARROW_NO_FEASIBLE_LAYOUT
SPARROW_COMMIT_VIOLATION_BACKEND
CDE unsupported / timeout-style controlled failure if represented inside solver
```

The output must include at least:

```text
pipeline_used = "sparrow_experimental"
sparrow_invoked = true
sparrow_converged = false
sparrow_initial_raw_loss
sparrow_final_raw_loss
sparrow_best_infeasible_raw_loss
sparrow_iterations
sparrow_moves_attempted
sparrow_moves_accepted
sparrow_rollbacks
sparrow_collision_graph_initial_pairs
sparrow_collision_graph_final_pairs
sparrow_boundary_violations_initial
sparrow_boundary_violations_final
sparrow_search_position_calls
sparrow_search_position_samples
sparrow_severity_* counts
```

If status is `unsupported`, diagnostics are more important, not less.

### 2. Do not silently skip CDE acceptance in smoke

Change `scripts/smoke_sgh_q22_sparrow_kernel.py`:

- It must have at least one tiny CDE Sparrow fixture that is required to finish successfully with `status in ("ok", "partial")`, `sparrow_converged == true`, and `bbox_fallback_queries == 0`.
- If CDE returns unsupported for that tiny fixture, smoke must fail.
- Medium CDE may remain unsupported only if diagnostics are present and Q18B is recommended.

### 3. Honest boundary/rotation smoke semantics

Fix smoke names and assertions:

- If a smoke fixture is called `boundary_recovery`, it must actually test boundary recovery through a lower-level unit/integration path, or be renamed to `already_feasible_single_item`.
- `continuous_rotation_rescue` must either require convergence on a fixture where rotation matters, or be documented as exploratory and not counted as proof of rescue.

Do not claim recovery/rescue when the assertion does not require it.

### 4. Benchmark accounting must be honest

Fix `scripts/bench_sgh_q22_sparrow_kernel.py`:

- Count every `sparrow_experimental` run in `sparrow_total`, including `unsupported` and timeout.
- Count convergence only when `sparrow_converged == true`.
- Render `0`, `0.0`, and `false` as actual values, not `-`.
- Keep timeout/unsupported reason rows.
- Add summary by backend: bbox vs cde.

The report must clearly show that CDE is currently the bottleneck if it fails.

### 5. Correct Q18B recommendation

If any of the measured CDE Sparrow medium fixtures remain unsupported or timeout due to query/build cost, then the report must say:

```text
Q18B_RECOMMENDATION: REQUIRED
```

or a more precise marker:

```text
Q18B_RECOMMENDATION: REQUIRED_FOR_CDE_SCALE
```

Do not keep `NOT_REQUIRED_NOW` while CDE Sparrow cannot converge small-medium fixtures within the measured budget.

### 6. CDE/Sparrow quick viability gate

Add or update tests/smoke so that Q22R1 proves all of this:

```text
sparrow_experimental + bbox tiny overlap -> converged
sparrow_experimental + cde tiny overlap -> converged, bbox_fallback_queries == 0
sparrow_experimental + cde no-feasible/unsupported case -> optimizer_diagnostics present
medium cde failure, if any -> diagnostics present + Q18B_REQUIRED marker
same seed determinism preserved
```

## PASS criteria

PASS only if:

```text
- unsupported Sparrow outputs preserve optimizer diagnostics;
- tiny CDE Sparrow smoke converges and proves bbox_fallback_queries == 0;
- medium CDE unsupported/timeout is honestly measured and carries diagnostics;
- benchmark denominator and zero-value rendering are fixed;
- smoke assertions no longer overclaim boundary/rotation behavior;
- Q18B recommendation is consistent with the CDE benchmark result;
- cargo test --lib is green;
- Q22 smoke and benchmark are green;
- report first line is PASS and markers are correct.
```

## Required commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter -- sparrow_pipeline
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q22_sparrow_kernel.py
python3 scripts/bench_sgh_q22_sparrow_kernel.py --quick
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
```

## Report markers

PASS report must end with:

```text
SGH-Q22R1_STATUS: READY_FOR_AUDIT
SGH-Q22_STATUS: READY_FOR_AUDIT
SPARROW_EXPERIMENTAL_STATUS: TESTABLE_WITH_CDE_MICRO
SGH-Q23_STATUS: READY|HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|REQUIRED_FOR_CDE_SCALE|NOT_REQUIRED_NOW
```

`NOT_REQUIRED_NOW` is allowed only if CDE Sparrow is demonstrably viable on tiny and medium quick fixtures.
