# SGH-Q25-R6 package — Strict parity semantic hardening, no benchmark focus

This package is a narrow follow-up to Q25-R5. It does **not** start another broad Sparrow porting round. It only hardens the remaining yellow-flag areas from the Q25-R5 audit:

1. Large-item disruption must use a convex-hull-area key, not `width * height` / bbox area.
2. Strict touching and boundary semantics must be covered by stronger edge-case tests.
3. The local strict profile must be rechecked against the pinned upstream `.cache/sparrow` source with a line/function mapping report.

Compression remains intentionally deferred. Fixed multisheet remains the required local production model and is not a defect.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_R6_STRICT_PARITY_SEMANTIC_HARDENING_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/run.md`
- Smoke: `scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py`
- Report to write: `codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`

## Non-negotiable outcome

Q25-R6 may pass only if:

1. Strict large-item disruption uses convex-hull-area-derived ordering/cutoff, not bbox `width * height`.
2. There are targeted tests proving strict pair touching, corner touching, exact boundary fit, epsilon-inside and epsilon-outside boundary behavior.
3. The report contains an upstream `.cache/sparrow` commit and line/function mapping audit for the touched strict-profile functions.
4. Q25-R5 strict profile behavior remains intact: upstream-like budgets, no strict downscaling, RNG worker ordering, 200/3 separator limits, strict touching policy.
5. No compression, LV8 benchmark acceptance, `WorkingLayout`, `VrsCollisionTracker`, bbox/AABB ranking, or legacy VRS core is reintroduced.
