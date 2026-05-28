# Checklist — SGH-Q20R Sparrow search_position + coordinate descent, updated after Q20

## Dependency

- [x] Q16 report PASS
- [x] Q18A report PASS
- [x] Q18A-R1 report PASS/READY
- [x] Q20 report PASS
- [x] Q20 contains `SGH-Q20_STATUS: READY_FOR_AUDIT`

## Source audit

- [x] Q20 rotation refinement implementation audited
- [x] `continuous_refinement_angles` audited and planned for reuse
- [x] `VrsSeparator::find_best_candidate_for_target` audited
- [x] `generate_candidates_with_sheets` finite LBF dependency documented
- [x] current GLS tracker/weights audited
- [x] current active backend APIs audited
- [x] current rotation precedence audited

## SearchPosition module

- [x] `optimizer/search_position.rs` or equivalent exists
- [x] module exported from optimizer mod
- [x] config struct exists
- [x] diagnostics struct exists
- [x] transform candidate struct exists
- [x] deterministic seed mixing exists

## Sampling

- [x] global uniform sheet sampling implemented
- [x] focused sampling around current placement implemented
- [x] deterministic for same seed/instance/iteration/worker
- [x] allowed sheet filter honored
- [x] Q20 continuous candidates reused
- [x] non-continuous policies receive no illegal rotations

## Evaluation

- [x] boundary evaluation uses active backend
- [x] pair evaluation uses active backend
- [x] CDE/Jagua unsupported samples rejected
- [x] CDE/Jagua no silent bbox fallback
- [x] temporary bbox/smooth severity proxy documented as Q21 gap if still used

## Coordinate descent

- [x] x-axis refinement
- [x] y-axis refinement
- [x] rotation-axis refinement for Continuous
- [x] step halving or equivalent stop criteria
- [x] no incumbent mutation during refinement
- [x] top-k sample refinement

## Separator integration

- [x] VrsSeparator uses search_position before LBF candidates
- [x] LBF fallback explicit and diagnostic-counted if retained
- [x] primary smoke path has `search_position_lbf_fallback_used == 0`
- [x] GLS rollback/update behavior preserved
- [x] multi-worker determinism preserved
- [x] search_position diagnostics aggregated into separator/phase/optimizer output or report

## Tests

- [x] global sampling deterministic
- [x] focused sampling deterministic
- [x] non-continuous rotation policy respected
- [x] Q20 continuous candidates reused
- [x] continuous rotation axis used in coordinate descent
- [x] backend unsupported samples rejected
- [x] CDE path has no bbox fallback
- [x] separator uses search_position before LBF candidates
- [x] separator reduces simple overlap
- [x] coordinate descent improves or preserves eval
- [x] Q20 rotation refinement regression still passes

## Smoke/verify

- [x] `scripts/smoke_sgh_q20r_sparrow_search_position.py` exists
- [x] overlap separation scenario covered
- [x] boundary correction scenario covered
- [x] continuous rotation rescue covered
- [x] CDE bbox_fallback_queries == 0 covered
- [x] primary LBF fallback not used in CDE smoke
- [x] determinism scenario covered
- [x] cargo tests run
- [x] verify.sh run

## Report

- [x] Report first line PASS/REVISE/BLOCKED
- [x] PASS contains `SGH-Q20R_STATUS: READY_FOR_AUDIT`
- [x] PASS contains `SGH-Q21_STATUS: READY`
- [x] PASS contains `Q19_STATUS: HOLD`
- [x] PASS contains `Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE`
