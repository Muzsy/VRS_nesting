# SGH-Q25-R5 package — Strict Sparrow parity profile, no benchmark focus

This package addresses the remaining non-compression, non-fixed-multisheet semantic gaps after Q25-R4.

It introduces a strict Sparrow parity profile and makes the following differences explicit/fixed:

1. Touching policy: `SparrowStrict` vs `VrsTouchAllowed` must be explicit. Strict parity must not silently downgrade touching to `NoCollision`.
2. Sample budgets: strict profile must use upstream-like budgets: separator 50/25/3, LBF 1000/0/3.
3. Separator limits: strict profile must use 200 / 3 rather than the local short loop.
4. Worker ordering: strict profile must shuffle colliding items by RNG only, without worker-index ordering bias.
5. Exploration/disruption: restore must use normal-biased pool selection and disruption must select a random pair from the large-item candidate pool, with fixed-sheet extensions documented separately.

This is **not** an LV8 benchmark task, not dense-layout tuning, not compression work, and not a fixed-sheet rollback. Fixed multisheet remains the target model.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q25_R5_STRICT_SPARROW_PARITY_PROFILE_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/run.md`
- Smoke: `scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py`
- Report to write: `codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`

## Non-negotiable outcome

Q25-R5 may pass only if:

1. `SparrowStrictParity` is explicit and used for Sparrow parity claims.
2. Touching-as-NoCollision is moved behind an explicit non-parity VRS policy.
3. Strict profile uses upstream-like LBF and separator budgets.
4. Strict profile disables instance-count based budget downscaling.
5. Strict worker ordering is RNG shuffle only.
6. Strict separator limits are 200 / 3.
7. Exploration restore/disruption follows upstream semantics except documented fixed-sheet extensions.
8. No compression, LV8 quality benchmark gate, legacy core, bbox/AABB ranking, or old VRS tracker is reintroduced.
