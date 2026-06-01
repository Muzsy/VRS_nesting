# Checklist — SGH-Q25-R2 Complete upstream Sparrow core semantic port

## Scope hygiene

- [ ] Capture `git status --porcelain=v1` before coding.
- [ ] Capture `git diff --name-only` before coding.
- [ ] Record `PRE_TASK_GIT_STATUS` in the report.
- [ ] Record pre-existing dirty files separately.
- [ ] Do not revert pre-existing dirty files.
- [ ] Do not modify out-of-scope files.
- [ ] If out-of-scope changes are required, stop and mark `REVISE_SCOPE_BLOCKED`.
- [ ] At the end, report `TASK_CHANGED_FILES` and `OUT_OF_SCOPE_NEW_CHANGES`.

## Upstream source

- [ ] Confirm `.cache/sparrow` exists or run `./scripts/ensure_sparrow.sh`.
- [ ] Record upstream commit hash.
- [ ] Read upstream eval, quantify, sample, lbf, worker, separator, explore, optimizer files before coding.
- [ ] Maintain an upstream-to-local semantic mapping table.

## Collector/evaluator

- [ ] Implement bounded/visitor-style CDE hazard collection or equivalent local CDE adapter support.
- [ ] `collect_poly_collisions_in_detector_custom` is not just `session.query(candidate)` followed by post-processing.
- [ ] `SeparationEvaluator` uses collector reload + upper bound + early termination.
- [ ] Candidate loss/ranking is tracker-weighted collector loss.
- [ ] No bbox/AABB/extent separation loss/ranking.

## Quantify/tracker

- [ ] Default pair/container loss uses upstream overlap-proxy + shape penalty semantics.
- [ ] Stale resolution-distance production terminology/counters removed or clearly non-default experimental.
- [ ] Tracker exposes pair/container loss, item weighted loss, total weighted loss, GLS update, moved item update, collision item extraction.
- [ ] Local indexing deviations are documented as fixed-sheet/indexing adaptation.

## LBF

- [ ] No shelf/anchor/recovery/fallback/least-infeasible constructive success path.
- [ ] LBF placement uses `search_placement + LBFEvaluator` only.
- [ ] Fixed-sheet no-clear case is represented honestly as unresolved/partial or documented infeasible seed adaptation.
- [ ] No AABB proxy candidate placement is introduced.

## Search/sampler/coord descent

- [ ] `BestSamples` is evaluator-score ordered with upper-bound behavior.
- [ ] Focused + uniform/container-wide sampling are both used.
- [ ] Coordinate descent follows upstream step success/fail and axis semantics.
- [ ] Rotation refinement is active where rotations are allowed.
- [ ] No benchmark-specific dense throttling changes algorithm semantics.

## Worker/separator/explore

- [ ] Worker iterates tracker-derived colliding/problem items.
- [ ] Worker accepts moves only if moved-item weighted loss does not increase.
- [ ] Separator picks lowest total weighted loss worker state.
- [ ] Pair count/raw loss are not primary selection criteria.
- [ ] Strike/no-improvement loop is upstream-mapped.
- [ ] Exploration pool/restore/disruption are upstream-mapped.
- [ ] Contained-item relocation fixed-sheet equivalent is present and geometry/CDE meaningful.

## Verification

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [ ] `python3 scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py`
- [ ] `./scripts/check.sh`
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md`
- [ ] Report status is honest and not benchmark-driven.
