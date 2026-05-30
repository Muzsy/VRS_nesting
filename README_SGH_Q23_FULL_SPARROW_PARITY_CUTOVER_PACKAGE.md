# SGH-Q23 package — Full Sparrow parity cutover

This package supersedes the earlier `full_sparrow_cde_cutover` wording.

The central target is **not bbox exclusion**. The central target is a production solver path whose algorithmic behavior follows the actual local `.cache/sparrow` implementation, adapted to fixed-sheet nesting.

Bbox restrictions are only guardrails derived from that goal.

## Required local reference

```text
.cache/sparrow
```

The executing agent must inspect this clone and create:

```text
docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
```

## Files

```text
canvases/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q23_full_sparrow_parity_cutover.yaml
codex/prompts/egyedi_solver/sgh_q23_full_sparrow_parity_cutover/run.md
codex/codex_checklist/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
README_SGH_Q23_FULL_SPARROW_PARITY_CUTOVER_PACKAGE.md
```

## Main acceptance idea

PASS means a real Sparrow-style production path exists and is tested on fixed-sheet CDE fixtures.

If full cutover cannot be achieved in one run, the correct result is `REVISE` with exact blockers and measurements, not a weak PASS.
