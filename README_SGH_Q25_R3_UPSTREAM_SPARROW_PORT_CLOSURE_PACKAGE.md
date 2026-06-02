# SGH-Q25-R3 package — Upstream Sparrow core port closure, compression excluded

Q25 created the upstream-mapped module structure. Q25-R1/R2 removed major stubs and proxy logic. Q25-R3 is the port-closure task: finish the remaining non-compression upstream Sparrow core semantics so the project can stop spending tasks on “almost Sparrow” corrections.

This is **not** an LV8 benchmark task and not a dense-layout tuning task. Runtime checks are only guardrails against breakage. The objective is source-level upstream semantic parity.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_R3_UPSTREAM_SPARROW_PORT_CLOSURE_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark/run.md`
- Smoke: `scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py`
- Report to write: `codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md`

## Non-negotiable outcome

Q25-R3 must close the remaining semantic gaps from Q25-R2:

1. Specialized CDE pipeline must include the upstream pole pre-pass + bit-reversed edge traversal + containment pass with loss-bound early termination.
2. LBF must be an upstream-style LBFBuilder path: upstream ordering, `search_placement + LBFEvaluator`, clear-only acceptance. Fixed-sheet unresolved handling may exist, but not inside LBF as a fake constructive success.
3. Search/sampler must match upstream Algorithm 6 shape: focused sampler, container-wide sampler, `BestSamples`, two-stage coordinate descent, continuous/discrete rotation sampling. No dense-specific algorithm shortcuts.
4. Worker/separator/explore/quantify/tracker must remain upstream-semantic and must not regress to pair-count, AABB ranking, fake LBF, or batch-only collector shortcuts.
5. The mapping report must have zero open non-compression semantic gaps. Fixed-sheet deviations are allowed only when they are unavoidable consequences of fixed multisheet instead of infinite strip, and they must not change core semantics.

Compression remains explicitly deferred and disabled.
