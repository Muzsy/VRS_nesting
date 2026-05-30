# SGH-Q24 — Sparrow parity quality hardening package

This package defines the next implementation task after Q23R3.

Q23R3 is accepted as the first real production `sparrow_cde` cutover milestone, but it is not yet equivalent to the original jagua_rs/Sparrow solver in search quality. Q24 must close the most important remaining code-level gaps:

1. production search strength is still too low;
2. exploration is only a minimal restart/disruption mechanism;
3. compression is still a primitive left/down compaction pass;
4. loss/quantification still carries bbox/extent proxy legacy;
5. LV8 proof is only a tiny 3-item subset.

Q24 is an implementation task, not an audit and not a benchmark-only task.

Start from:

```bash
codex/prompts/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening/run.md
```

Hard outcome required for PASS:

- existing Q23R3 medium gate remains `12/12 ok`;
- production `sparrow_cde` uses non-trivial sampling/refinement budgets;
- exploration has a real infeasible/incumbent pool and deterministic disruption policy;
- compression uses restore -> compact/shrink objective -> separate -> accept/reject lifecycle;
- collision/loss is no longer primarily `BboxArea` in production `sparrow_cde`;
- LV8 12-types-x1 and deterministic 24-instance subset pass under `sparrow_cde` with CDE backend and no fallback;
- larger LV8 50/100/full-276 rows are measured honestly, even if they are not yet hard PASS gates.
