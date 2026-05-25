PASS

# SGH-Q09 PhaseOptimizer production wiring contract

## Scope

SGH-Q09 adds an explicit opt-in Phase1 production solve path for the existing
`PhaseOptimizer` pipeline.

Default behavior remains the legacy Phase1 `MultiSheetManager` route. The
PhaseOptimizer route is selected only when the input contains:

```json
{
  "solver_profile": "jagua_optimizer_phase1_outer_only",
  "optimizer_pipeline": "phase_optimizer"
}
```

## Input contract

`SolverInput.optimizer_pipeline` is optional and backward-compatible.

Accepted values:

```text
legacy_multisheet
phase_optimizer
```

Missing value is equivalent to `legacy_multisheet`.

## Production routing

Current production routing evidence:

```text
rust/vrs_solver/src/adapter.rs: Phase1 solve path routes through MultiSheetManager by default.
rust/vrs_solver/src/optimizer/phase.rs: PhaseOptimizer owns exploration, compression, and BPP orchestration.
rust/vrs_solver/src/optimizer/multisheet.rs: legacy production route runs construction, repair, and sheet elimination.
```

Q09 routing:

```text
legacy_multisheet:
  expand_instances_with_policy
  can_fit_any_stock_with_policy prefilter
  MultiSheetManager::run
  SolverOutput

phase_optimizer:
  expand_instances_with_policy
  can_fit_any_stock_with_policy prefilter
  build_initial_layout_with_rotation_context
  WorkingLayout::new
  PhaseOptimizer::run
  WorkingLayout::validate_and_commit
  SolverOutput
```

## Budget split

The explicit `phase_optimizer` route derives deterministic sub-budgets from
`time_limit_s`:

```text
exploration: 60%
compression: 25%
bpp: 15%
```

`time_limit_s` is clamped to at least `1.0` before splitting, so no phase gets a
negative budget.

## Diagnostics

The output may include optional `optimizer_diagnostics` for the explicit phase
route:

```text
pipeline_used
phase_optimizer_invoked
exploration_iterations
compression_iterations
bpp_attempts
```

Legacy output does not emit this optional diagnostic field, preserving the
existing default output shape.

## No silent fallback

When `optimizer_pipeline = phase_optimizer`, the adapter must not silently return
a legacy layout. If the phase layout fails the `WorkingLayout` commit gate, the
solver returns:

```text
status = unsupported
unsupported_reason = PHASE_OPTIMIZER_COMMIT_VIOLATION
```

Accepted phase output must be violation-free.

## Out of scope

```text
CDE full implementation
exact backend default switch
hole/cavity semantics
DXF/preflight refactor
new stochastic optimizer algorithm
LossModel redesign
rotation policy redesign
legacy default output change
```
