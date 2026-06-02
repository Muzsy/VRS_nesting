# Checklist — SGH-Q25-R3 Upstream Sparrow core port closure

## Scope / hygiene

- [ ] Record `git status --porcelain=v1` before editing.
- [ ] Record `git diff --name-only` before editing.
- [ ] List pre-existing dirty files separately.
- [ ] Do not modify out-of-scope files.
- [ ] End with `OUT_OF_SCOPE_NEW_CHANGES: NONE` or mark `REVISE_SCOPE_BLOCKED`.

## Upstream reading

- [ ] Record `.cache/sparrow` commit hash.
- [ ] Read upstream specialized CDE pipeline.
- [ ] Read upstream LBFBuilder.
- [ ] Read upstream search / uniform sampler / coordinate descent.
- [ ] Read upstream worker / separator / explore / quantify / tracker.

## Specialized CDE pipeline closure

- [ ] Implement pole pre-pass before edge traversal.
- [ ] Use upstream area-threshold logic for poles.
- [ ] Early terminate after pole hazards when loss bound exceeded.
- [ ] Keep bit-reversed edge traversal.
- [ ] Keep containment pass.
- [ ] Collector accumulates weighted loss during CDE traversal.
- [ ] No post-query-only batch accumulation.
- [ ] Report does not claim pole pre-pass is skipped or future work.

## LBF closure

- [ ] LBF ordering uses convex-hull-area × diameter equivalent.
- [ ] LBF placement path is `search_placement + LBFEvaluator` only.
- [ ] LBF accepts only clear placements.
- [ ] No fake least-infeasible constructive success.
- [ ] No shelf/fallback/recovery/AABB-overlap LBF shortcut.
- [ ] No dense-specific `instances.len() >= 100` shortcut.
- [ ] Fixed-sheet bootstrap, if needed, is outside LBF and explicitly documented.

## Search/sampler closure

- [ ] Uniform sampler precomputes rotation entries.
- [ ] Supports none/discrete/continuous rotations.
- [ ] Continuous rotation sampling uses upstream-equivalent 16 samples unless mapped constant says otherwise.
- [ ] Computes valid x/y ranges by intersecting sample bbox and container bbox with rotated-shape bbox compensation.
- [ ] Uses focused sampler and container-wide sampler as separate concepts.
- [ ] Adds reference/current placement candidate where applicable.
- [ ] Uses `BestSamples` with uniqueness threshold based on item min dimension.
- [ ] Runs first coordinate descent over best samples.
- [ ] Runs second/final coordinate descent on best sample.
- [ ] Rotation wiggle supported where rotations allow.

## Regression prevention

- [ ] No `WorkingLayout` / `VrsCollisionTracker` in `optimizer/sparrow`.
- [ ] Compression remains excluded.
- [ ] SeparationEvaluator does not use bbox/AABB/extent ranking.
- [ ] Quantification remains overlap-proxy + shape penalty.
- [ ] Worker acceptance remains moved-item weighted-loss based.
- [ ] Separator best worker remains total weighted-loss based.
- [ ] Exploration keeps pool/restore/disrupt/contained relocation.

## Report / verification

- [ ] Write `PORT_CLOSURE_MAPPING_TABLE` with no non-compression open gaps.
- [ ] Only allowed non-PORTED status besides fixed-sheet no-semantic-loss is compression deferred.
- [ ] Run build.
- [ ] Run lib tests.
- [ ] Run Q25-R3 smoke.
- [ ] Run `scripts/check.sh`.
- [ ] Run `scripts/verify.sh --report ...`.
