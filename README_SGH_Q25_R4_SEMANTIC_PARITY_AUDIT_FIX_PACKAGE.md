# SGH-Q25-R4 package — Sparrow semantic parity audit/fix, no benchmark focus

Q25-R3 claimed upstream Sparrow core port closure, but the post-audit found concrete semantic risk points that must be fixed before the porting phase can be treated as closed:

1. `sample/coord_descent.rs` appears to use `ScoredPlacement.placement.x/y` as the next sampled coordinate even though local evaluators consume rect-min coordinates and `SparrowPlacement` stores anchor coordinates.
2. `eval/lbf_evaluator.rs` reports Q25-R3 parity as “collision → Invalid”, but the current source can still return a colliding `ScoredPlacement` with `is_clear=false`.
3. Fixed-sheet bootstrap must remain explicitly outside LBF and must not be presented as upstream LBF success.
4. The new report must correct Q25-R3 mapping claims where the source did not actually match the report.

This is **not** an LV8 benchmark task, not dense-layout tuning, and not compression work. It is a source-level semantic audit/fix task.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/run.md`
- Smoke: `scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py`
- Report to write: `codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`

## Non-negotiable outcome

Q25-R4 may pass only if:

1. There is one explicit sample-space convention across sampler/search/evaluator/coordinate-descent: sampled coordinates are rect-min coordinates; output placements remain anchor coordinates.
2. `ScoredPlacement` or an equivalent structure carries the sample-space rect-min coordinates so `BestSamples` and coordinate descent never use anchor coordinates as if they were sample coordinates.
3. `LBFEvaluator` treats collision as `Invalid`/rejection, not as a colliding candidate. LBF constructive placement remains clear-only.
4. Fixed-sheet bootstrap remains outside LBF and is documented as a fixed-sheet separator bootstrap, not upstream LBF parity.
5. The new report explicitly corrects the Q25-R3 report/source mismatch.
6. No legacy `WorkingLayout`, `VrsCollisionTracker`, compression, bbox/AABB ranking, or dense benchmark objective is reintroduced.
