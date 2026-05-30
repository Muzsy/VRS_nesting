# SGH-Q24R1 — Native Sparrow parity lifecycle + LV8 gate completion

This package is a hard REVISE-fix after SGH-Q24.

Q24 made useful progress, but it did not implement the required jagua_rs/Sparrow lifecycle. It only delivered search-budget uplift and a CDE-separation loss identity while the hard LV8 gates timed out and the exploration/compression rewrites remained `NOT_REWRITTEN`.

Q24R1 must not be a local speed patch. The task is to transplant the original Sparrow lifecycle into the VRS fixed-sheet solver as faithfully as possible:

- native-style separation loop with strike/no-improvement attempts;
- worker `move_items` parity: every currently colliding item gets a move opportunity per worker;
- search parity: focused + container-wide sampling + BestSamples + two-stage coordinate descent;
- CDE session reuse across the whole target search, not per candidate;
- CDE/shape-aware collision quantification, not bbox surrogate primary loss;
- exploration pool + biased restore + large-item disruption;
- fixed-sheet compression analogue: restore → compact/shrink proposal → separate → accept/reject;
- LV8 hard gates must pass.

Start from:

```bash
codex/prompts/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle/run.md
```
