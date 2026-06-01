# SGH-Q25-R1 package — Semantic upstream Sparrow core parity fix, compression excluded

Q25 successfully split the previous native Sparrow monolith into upstream-mapped modules, but the audit found that several modules are only structural ports. Q25-R1 is the semantic parity correction.

This task is **not** a dense-LV8 tuning task and not another architecture rewrite. The module tree created by Q25 stays. The job is to replace the remaining stubs/proxies/adapted-only shortcuts with real upstream Sparrow semantics, except for explicitly documented fixed-sheet differences and the deliberately deferred compression phase.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_R1_SEMANTIC_SPARROW_CORE_PARITY_FIX_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r1_semantic_sparrow_core_parity_fix.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix/run.md`
- Smoke: `scripts/smoke_sgh_q25_r1_semantic_sparrow_core_parity_fix.py`
- Report to write: `codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`

## Non-negotiable outcome

The production `sparrow_cde` path must remain:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

But now the internal modules must be semantic ports, not just names:

- no stub `SpecializedCdeHazardCollector`,
- no bbox/extent ranking in `SeparationEvaluator`,
- no `fixed_sheet_recovery_candidate` / AABB-overlap LBF fallback,
- no non-upstream primary quantification model hidden as “exact”,
- no pair-count-first worker/rollback semantics,
- no shallow disruption without contained-item relocation equivalent,
- no compression.

If the implementation cannot fully port one upstream behavior because of fixed-sheet adaptation, the report must mark it `ADAPTED_FIXED_SHEET` and explain the exact reason. “Equivalent”, “Sparrow-like”, “future work”, “resolution-distance alternative”, or “progress improved” are not valid substitutes.
