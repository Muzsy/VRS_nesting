# Checklist — SGH-Q24R1 Native Sparrow parity lifecycle

## Reference/parity gates

- [ ] `.cache/sparrow` was read directly.
- [ ] Report includes file-by-file Sparrow → VRS reference map.
- [ ] Optimizer lifecycle maps original optimize/explore/separate/compress to VRS fixed-sheet logic.
- [ ] Fixed-sheet differences are explicitly justified, not used as excuses to skip Sparrow lifecycle.

## CDE gates

- [ ] Target-search CDE session is built once per worker/target search, not per sample candidate.
- [ ] Candidate samples/refinements/probes reuse the same target-search session where possible.
- [ ] Active-set filtering is broad-phase only.
- [ ] Full CDE final validation still runs.
- [ ] `cde_pairwise_fallback_queries == 0`.
- [ ] `cde_session_reuse_ratio >= 0.80` on LV8 hard rows.

## Search/worker gates

- [ ] Worker loop processes all currently colliding/boundary-violating items, or a documented bounded window with diagnostics.
- [ ] More than one colliding item is seen per worker pass on medium/LV8 hard rows.
- [ ] Worker accepted moves do not increase weighted loss except documented disruption cases.
- [ ] Search has focused samples, container samples, BestSamples, pre-refine CD, final refine CD.
- [ ] Production search budgets are not effectively disabled.

## Loss/tracker gates

- [ ] Production `sparrow_cde` tracker/graph loss is CDE/shape-driven, not bbox overlap/penetration.
- [ ] `loss_bbox_proxy_queries == 0` for production tracker/graph loss.
- [ ] `loss_model_used` is not `BboxAreaLoss` or `PolePenetrationSmoothLoss` for production rows.
- [ ] Bbox only appears as broad-phase/hazard filtering.

## Exploration/compression gates

- [ ] Exploration has bounded infeasible pool.
- [ ] Failed infeasible local best layouts are inserted into the pool.
- [ ] Pool restore is biased toward low loss.
- [ ] Large-item disruption is active.
- [ ] Compression uses restore → compact/shrink pressure → separate → accept/reject.
- [ ] Compression calls separation, not just one-millimeter left/down moves.

## Benchmark gates

- [ ] `medium_10_to_20_items`: `ok 12/12`.
- [ ] `lv8_12types_x1`: `ok 12/12`.
- [ ] `lv8_24_instances`: `ok 24/24`.
- [ ] Hard rows have zero final collision pairs and zero boundary violations.
- [ ] Hard rows use `sparrow_cde` + `cde_adapter`.
- [ ] No bbox/LBF/legacy fallback in hard rows.
- [ ] Timeouts/errors count in denominator.

## Reject conditions

- [ ] Only CDE timeout is fixed but exploration/compression remain `NOT_REWRITTEN`.
- [ ] LV8 hard rows are downgraded to soft gates.
- [ ] Per-candidate CDE session builds remain in production hot path.
- [ ] Loss is renamed but still bbox-driven in tracker/graph production path.
- [ ] PASS is claimed without Q24R1 smoke success.
