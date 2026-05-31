# SGH-Q24R9 package — Exact upstream-style tracker/evaluator/search semantics, compression excluded

This package targets the remaining hard gap after Q24R8: the native Sparrow architecture exists, but several core internals are still proxy implementations.

Q24R9 is **not** an architecture cutover task, not a compression task, and not a dense-LV8 tuning task. It is a core-semantics parity task.

## Install / apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q24R9_EXACT_UPSTREAM_STYLE_TRACKER_EVALUATOR_SEARCH_SEMANTICS_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the task prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics/run.md`
- Smoke: `scripts/smoke_sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.py`

## Non-negotiable direction

Production `sparrow_cde` must keep the Q24R5+ native model:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

Q24R9 must replace the remaining proxy core with upstream-style semantics:

```text
CDE-confirmed hazards
-> quantified pair/container loss, not bbox overlap proxy
-> tracker weights/GLS exactly driving evaluators
-> SeparationEvaluator/LBFEvaluator with upper-bound pruning
-> search_placement BestSamples + sampler + two-stage coordinate descent + rotation wiggle
-> worker acceptance by upstream loss semantics
-> separator/exploration using the native tracker consistently
```

Compression remains explicitly out of scope.
