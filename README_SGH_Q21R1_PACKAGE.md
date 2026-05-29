# SGH-Q21R1 package — Full Sparrow-aligned collision severity hardening

This package is a corrective task after SGH-Q21.

## Important

This is not a minimal fix. The goal is always the full jagua_rs/Sparrow logic: backend-oracle geometry, high-quality collision quantification, GLS/search_position/separator integration, and honest diagnostics.

If the implementation remains partial, the report must be `REVISE`, not `PASS`.

## Files

```text
canvases/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q21r1_collision_severity_full_sparrow_alignment.yaml
codex/prompts/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment/run.md
codex/codex_checklist/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md
README_SGH_Q21R1_PACKAGE.md
```

## Core target

Replace the partial Q21 severity layer with a full Sparrow-aligned v1.1 severity core:

- multi-direction oracle probes;
- adaptive bracketing and binary refinement;
- capped industrial-scale initial step;
- complete query/probe/unsupported accounting;
- hard_unsupported_loss semantics;
- no bbox source-of-truth under CDE/Jagua;
- integration through search_position, separator/GLS, phase and adapter output;
- honest PASS/REVISE report markers.
