# SGH-Q64 - Role-aware admission authority cutover

## Goal

The user wants the first practical fix for the observed regression: the production critical-admission
path should stop falling back too early to the older generic admission logic when a role-aware
Anchor / Interlock / BandInsert path is available.

## Scope

- Strengthen the production `try_admit_critical()` decision path in the Sparrow BPP builder.
- Ensure skeleton-role critical admission does not let the generic direct density path short-circuit
  the role-routed production path.
- Keep the existing Anchor feature-vs-catalog winner ordering stable while the role-aware path gets
  first authority ahead of the generic direct fallback.
- Keep the change narrowly scoped to authority/wiring behavior, without redesigning the whole
  builder.
- Add focused tests for the new authority rules.

## Non-goals

- No full Q56-Q60 architecture rewrite.
- No new benchmark family beyond what is required to verify the authority cutover safely.
- No claim yet that this single change alone solves the Full276 2-sheet target.

## Acceptance

- In the skeleton production path, known roles do not short-circuit through the older generic direct
  admission branch before their role-routed production logic is attempted.
- The older generic direct density path remains available only as a second-line fallback inside the
  same admission attempt, so proven legacy wins are not silently dropped.
- The existing Anchor feature path remains the primary winner when it already finds a feasible
  skeleton candidate; the Anchor catalog stays the fallback until a safer ranking rule exists.
- The change is covered by focused automated tests.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q64_role_aware_admission_authority_cutover.md`
  passes.
