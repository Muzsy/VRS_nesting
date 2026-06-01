# SGH-Q25 — Upstream Sparrow core module-by-module port reset, compression excluded

## Read this first

The previous path failed because the agent repeatedly implemented local “Sparrow-like” substitutes instead of porting the upstream Sparrow core. Q25 is a reset of that method.

Your job is not to improve the dense LV8 number by tuning constants. Your job is to restructure and port the native Sparrow core module-by-module from upstream Sparrow into this repo.

Compression is explicitly out of scope.

## Absolute target

Production `sparrow_cde` must be implemented as a native Sparrow solver core whose modules correspond directly to upstream Sparrow modules:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

The code inside that path must be upstream-module-mapped, not a local monolith.

## Step 0 — establish source of truth

1. Work from repo root.
2. Confirm `.cache/sparrow` exists. If missing, use the repo’s documented Sparrow setup, likely `scripts/ensure_sparrow.sh`.
3. Record the upstream commit hash:

```bash
git -C .cache/sparrow rev-parse HEAD
```

4. Read these upstream files before coding:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/eval/sample_eval.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
.cache/sparrow/src/eval/specialized_jaguars_pipeline.rs
.cache/sparrow/src/quantify/mod.rs
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/quantify/pair_matrix.rs
```

Do not proceed by memory. Do not infer the upstream behavior from current VRS code.

## Step 1 — stop extending the monolith

The current file:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
```

must become a thin module boundary and public API wiring file. It may contain:

- `mod ...` declarations,
- public re-exports,
- `run_sparrow_pipeline` wiring if small,
- API boundary projection.

It must not contain full implementations of:

- tracker,
- quantification,
- evaluators,
- samplers,
- coordinate descent,
- LBF builder,
- worker,
- separator,
- exploration.

## Step 2 — create the upstream-mapped module tree

Implement this structure:

```text
rust/vrs_solver/src/optimizer/sparrow/
  mod.rs
  model.rs
  optimizer.rs
  lbf.rs
  worker.rs
  separator.rs
  explore.rs
  fixed_sheet.rs
  diagnostics.rs
  sample/
    mod.rs
    search.rs
    coord_descent.rs
    best_samples.rs
    uniform_sampler.rs
  eval/
    mod.rs
    sample_eval.rs
    sep_evaluator.rs
    lbf_evaluator.rs
    specialized_cde_pipeline.rs
  quantify/
    mod.rs
    tracker.rs
    pair_matrix.rs
    overlap_proxy.rs
```

If you need an additional helper file, add it only with a clear reason and include it in the mapping table.

## Step 3 — port modules, do not reinvent them

### Quantify/tracker

Port the upstream quantification and tracker semantics. The production default must not be Q24R9’s local resolution-distance alternative unless placed behind an explicit experimental flag that is not used by production `sparrow_cde`.

Required:

- pair matrix equivalent,
- pair/container loss storage,
- weights,
- raw/weighted item loss,
- total weighted loss,
- GLS-style update,
- recompute/update semantics.

### Eval

Port:

- sample evaluator abstraction,
- LBF evaluator,
- separation evaluator,
- specialized CDE/jagua pipeline equivalent.

Reject local AABB penetration ranking. Candidate ranking must be driven by upstream-style hazard/loss semantics and tracker weights.

### Sample/search

Port:

- `BestSamples`,
- uniform/focused sampler behavior,
- `search_placement`,
- coordinate descent with upstream step semantics,
- rotation wiggle where policy permits.

### LBF

Port upstream LBFBuilder behavior. Fixed sheet handling may replace strip expansion, but not by shelf/anchor shortcut.

Reject:

```text
shelf_construct
fallback_anchor
overlap_score += ...
```

### Worker/separator

Port upstream worker and separator behavior:

- colliding item order,
- per-worker snapshots,
- move acceptance based on upstream weighted loss semantics,
- best worker by lowest total weighted loss,
- preserve/restore weights correctly.

Reject pair-count-first best worker logic.

### Explore

Port upstream exploration pool, biased restore, and disruption semantics. Compression remains disabled. For fixed-sheet/multisheet, document the exact adaptation.

## Step 4 — document every deviation

Write:

```text
codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
```

The report must include:

```text
SGH-Q25_STATUS: PASS|REVISE
```

and a complete mapping table:

```text
Upstream file | Upstream type/function | Local file | Local type/function | Status | Fixed-sheet deviation | Evidence
```

Every non-compression relevant upstream function/type must be represented.

Allowed statuses:

```text
PORTED
ADAPTED_FIXED_SHEET
DEFERRED_COMPRESSION_ONLY
NOT_APPLICABLE_IO_ONLY
```

No “similar”, “equivalent”, “future work”, “not needed”, or vague language.

## Step 5 — verification

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_upstream_sparrow_core_module_port_reset.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
```

If any step fails, fix the implementation. Do not downgrade the task to partial unless there is a real external blocker. Runtime partial on dense 191 is allowed only if the upstream module port is structurally complete and the partial reason is diagnostic, not a shortcut.

## Acceptance bar

This task is PASS only if:

1. The native Sparrow core is split into upstream-mapped modules.
2. The production path does not call old VRS solver core.
3. The monolithic/proxy Q24R9 implementation is removed from production.
4. The upstream-to-local mapping table is complete.
5. Any deviation is explicitly fixed-sheet or compression-only.
6. Runtime gates still pass without fake dense guards.

A dense runtime improvement alone is not enough. A build-green monolith is not enough. A report claiming “exact parity” without the module map is not enough.
