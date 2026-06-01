# SGH-Q25 package — Upstream Sparrow core module-by-module port reset, compression excluded

This package is a hard reset of the implementation strategy after Q24R9.

Q24R5 created a native `SparrowProblem -> SparrowOptimizer -> SparrowSolution` route, and Q24R6–Q24R9 added increasingly Sparrow-like code. But the current implementation still concentrates most of the native solver inside `rust/vrs_solver/src/optimizer/sparrow/mod.rs` and still contains local fixed-sheet/proxy shortcuts.

Q25 is **not** another dense-LV8 tuning task. It is a module-by-module upstream Sparrow core port.

## Install / apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_UPSTREAM_SPARROW_CORE_MODULE_PORT_RESET_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the task prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_upstream_sparrow_core_module_port_reset.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_upstream_sparrow_core_module_port_reset/run.md`
- Smoke: `scripts/smoke_sgh_q25_upstream_sparrow_core_module_port_reset.py`

## Non-negotiable direction

Do **not** keep extending a monolithic `sparrow/mod.rs`.

Port the upstream Sparrow core module-by-module:

```text
.cache/sparrow/src/quantify/*      -> rust/vrs_solver/src/optimizer/sparrow/quantify/*
.cache/sparrow/src/eval/*          -> rust/vrs_solver/src/optimizer/sparrow/eval/*
.cache/sparrow/src/sample/*        -> rust/vrs_solver/src/optimizer/sparrow/sample/*
.cache/sparrow/src/optimizer/lbf.rs       -> rust/vrs_solver/src/optimizer/sparrow/lbf.rs
.cache/sparrow/src/optimizer/worker.rs    -> rust/vrs_solver/src/optimizer/sparrow/worker.rs
.cache/sparrow/src/optimizer/separator.rs -> rust/vrs_solver/src/optimizer/sparrow/separator.rs
.cache/sparrow/src/optimizer/explore.rs   -> rust/vrs_solver/src/optimizer/sparrow/explore.rs
```

Compression remains out of scope. It must not be implemented, optimized, or used in this task.
