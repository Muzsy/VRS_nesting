# SGH-Q24R8 package — Full native Sparrow core parity, compression excluded

This package is a hard reset to the real objective: complete the **jagua_rs/Sparrow-native solver logic** in the VRS production `sparrow_cde` path.

It is not a dense-LV8 tuning task, not another guard/diagnostic task, and not a compression task.

## Install / apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q24R8_FULL_NATIVE_SPARROW_CORE_PARITY_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the task prompt:

```bash
cat codex/prompts/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression/run.md
```

## Task identity

- Canvas: `canvases/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r8_full_native_sparrow_core_parity_no_compression.yaml`
- Prompt: `codex/prompts/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression/run.md`
- Smoke: `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py`

## Non-negotiable direction

After this task, production `sparrow_cde` must be a real native Sparrow implementation, compression excluded:

```text
SparrowProblem / SPInstance
→ LBFBuilder-equivalent native initial construction
→ CollisionTracker with real jagua/CDE hazard collection + quantified loss
→ SeparationEvaluator / SampleEvaluator
→ BestSamples + UniformBBoxSampler + two-stage coordinate descent search
→ SeparatorWorker::move_items over all colliding items
→ Separator Alg. 9 / move_items_multi Alg. 10
→ Exploration phase / infeasible pool / biased restore / disruption Alg. 12 adaptation
→ full final CDE validation
→ SparrowSolution output projection only at API boundary
```

Do not add or harden compression in this task.
