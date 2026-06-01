# SGH-Q25 Upstream Sparrow core module-by-module port reset, compression excluded

## Why this task exists

The previous tasks repeatedly stated that the goal was the full jagua_rs/Sparrow implementation, yet the implementation still drifted toward a local/proxy solver:

- Q24R5 made the architectural cutover to a native model.
- Q24R6–Q24R9 added tracker/search/evaluator/worker concepts.
- But the implementation is still mostly a large single `rust/vrs_solver/src/optimizer/sparrow/mod.rs` file.
- Several internal mechanisms are local fixed-sheet shortcuts rather than direct upstream Sparrow ports.
- Runtime progress on the 191 first-sheet LV8 probe is still weak, because the core algorithm is not yet truly upstream-like.

The failure mode is now clear: broad “Sparrow-like” tasks allow the coding agent to implement small local substitutes that pass smoke checks while leaving the actual upstream logic unported.

Q25 changes the execution method.

## Strategic reset

This is not a tuning task and not another semantics patch.

The goal is to port the upstream Sparrow core **module by module** into the VRS native solver, with only explicitly documented fixed-sheet adaptations.

Do not write a new alternative heuristic. Do not preserve the Q24R9 monolith as the production implementation. Do not keep proxy helpers as hidden fallback.

## Upstream source of truth

Use the local clone expected at:

```text
.cache/sparrow
```

Read and map at least these upstream files before coding:

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

If the local clone is missing, use the repo’s existing `scripts/ensure_sparrow.sh` / documented Sparrow setup, then pin and report the exact commit.

## Required local module structure

Create or refactor to this structure:

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

`mod.rs` must become a thin public wiring module. It must not remain the implementation monolith.

## Required upstream-to-local mapping report

Write this report:

```text
codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
```

It must include a table with these exact columns:

```text
Upstream file | Upstream type/function | Local file | Local type/function | Status | Fixed-sheet deviation | Evidence
```

For every relevant upstream type/function in the required source files, the status must be one of:

```text
PORTED
ADAPTED_FIXED_SHEET
DEFERRED_COMPRESSION_ONLY
NOT_APPLICABLE_IO_ONLY
```

Rules:

- `ADAPTED_FIXED_SHEET` requires a concrete explanation.
- `DEFERRED_COMPRESSION_ONLY` may only be used for compression-specific upstream logic.
- “Equivalent”, “similar”, “Sparrow-like”, “resolution-based alternative”, and “future work” are not acceptable as status explanations.
- Any non-compression `MISSING`, `TODO`, or undocumented deviation means `REVISE`.

## Non-negotiable implementation rules

### 1. No monolith

The production implementation must not live primarily in `sparrow/mod.rs`.

Reject if:

- `sparrow/mod.rs` still contains large implementations of tracker/evaluator/search/LBF/worker/separator/explore.
- a single `.rs` file under `optimizer/sparrow` exceeds a reasonable module boundary without documented reason.
- required modules are missing.

### 2. No local proxy replacements

Reject if production Sparrow code still uses local shortcuts such as:

```text
aabb_penetration(...)
ix * iy overlap proxy
overlap_score += ...
shelf_construct(...)
fallback_anchor(...)
lowest pair-count wins
new_total < old_total || new_pairs < old_pairs worker acceptance
```

This is not about banning bounding boxes for harmless diagnostics. It is about banning them as the production evaluator/quantification/search-ranking truth.

### 3. Upstream tracker/quantify parity

Port the upstream quantification model as the default. Do not invent a different primary loss model unless it is placed behind a separate experimental flag and not used by production `sparrow_cde`.

The production tracker must store and expose:

- pair collision loss,
- container/boundary collision loss,
- GLS weights,
- item raw loss,
- item weighted loss,
- total weighted loss,
- incremental recompute/update semantics consistent with the upstream model.

### 4. Upstream evaluator parity

Port the upstream evaluator pipeline:

- sample evaluator trait/interface,
- separation evaluator,
- LBF evaluator,
- specialized CDE/jagua pipeline equivalent,
- upper-bound pruning,
- tracker-weighted hazard loss.

The separation evaluator must not rank candidates via AABB penetration.

### 5. Upstream search parity

Port the upstream search structure:

- `BestSamples`,
- focused sampler,
- container-wide sampler,
- two-stage coordinate descent,
- random-axis or equivalent upstream step semantics,
- rotation wiggle when the rotation policy allows it.

### 6. Upstream worker/separator/explore parity

Port:

- worker item ordering and move semantics,
- worker acceptance by weighted loss semantics,
- multi-worker snapshot/load-back by lowest weighted loss,
- exploration infeasible pool,
- biased restore,
- disruption including contained/practically-contained item relocation adapted to fixed sheets.

### 7. Fixed-sheet adaptation rules

We are not solving Sparrow’s original infinite strip exactly. This project targets fixed-sheet/multisheet nesting.

Allowed deviations:

- strip width shrink/expand can be replaced by fixed-sheet container set handling;
- compression remains disabled;
- multisheet container choice may be added where upstream assumes a strip/container;
- final output projection may remain compatible with the current VRS API.

Not allowed:

- replacing LBF/search/evaluator/tracker with shelf/proxy shortcuts;
- using “fixed-sheet adaptation” to avoid porting the upstream logic;
- keeping old VRS-core concepts inside production `sparrow_cde`.

## Runtime proof requirements

Runtime is evidence, not the primary goal. Still run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_upstream_sparrow_core_module_port_reset.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md
```

Minimum runtime gates:

- medium CDE regression passes;
- LV8 12 types × 1 regression passes;
- LV8 first-sheet 191 run is real, not guarded or faked;
- dense 191 may remain partial, but must show real worker/search/evaluator activity and no proxy shortcut use;
- compression passes remain `0`.

## Acceptance statement

This task passes only if the production native Sparrow core is visibly and structurally ported from upstream modules.

A runtime improvement without module-by-module upstream parity is **REVISE**.
