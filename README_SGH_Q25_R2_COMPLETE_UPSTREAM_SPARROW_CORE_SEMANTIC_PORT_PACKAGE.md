# SGH-Q25-R2 package — Complete upstream Sparrow core semantic port, no benchmark focus

Q25 created the upstream-mapped module tree. Q25-R1 removed several obvious stubs/proxies. Q25-R2 must finish the remaining semantic port gaps instead of optimizing LV8 benchmark numbers.

This task is **not** a dense-LV8 tuning task. The target is the complete upstream jagua_rs/Sparrow core logic, compression excluded.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_R2_COMPLETE_UPSTREAM_SPARROW_CORE_SEMANTIC_PORT_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/run.md`
- Smoke: `scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py`
- Report to write: `codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md`

## Non-negotiable outcome

The implementation must move from “upstream-shaped local approximation” to a complete semantic port of the upstream Sparrow core modules:

- collector/evaluator/search/LBF/worker/separator/explore/quantify/tracker semantics must be ported module-by-module;
- no benchmark-driven shortcuts;
- no `least-infeasible` success path in LBF as a substitute for upstream strip expansion;
- no post-query-only collector that pretends to be upstream early termination;
- no dirty-repo ambiguity: pre-existing out-of-scope changes must be recorded, not reverted or absorbed into this task.

Compression remains explicitly deferred.
