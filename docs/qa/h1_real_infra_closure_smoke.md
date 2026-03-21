# H1 Real Infra Closure Smoke

This document defines the execution and evidence model for H1 real-infra closure checks.

## Scripts

- `scripts/smoke_h1_real_infra_closure.py`
  - Default mode: `infra-closure`
  - Validates real Supabase auth + RLS + storage + worker lifecycle.
- `scripts/smoke_h1_real_artifact_chain_closure.py`
  - Strict artifact-chain entrypoint.
  - Runs the real-infra smoke in `artifact-chain` mode using a deterministic placeable solver fixture.

## Pass Semantics

- `infra-closure` PASS means:
  - run lifecycle closure (`queued -> done`)
  - snapshot-ready + worker execution + projection persistence
  - run artifact persistence (at least `solver_output` + `log`)
  - storage-level cross-tenant isolation check passes
- `artifact-chain` PASS means everything above, plus:
  - at least one placement
  - at least one sheet projection row
  - `sheet_svg` and `sheet_dxf` artifacts are present

## Cleanup Scope

Current smoke cleanup scope is:

- project/domain table cleanup
- temporary auth user cleanup

Storage object cleanup is **not guaranteed** by this smoke and must not be reported as guaranteed evidence.

## Commands

```bash
python3 scripts/smoke_h1_real_infra_closure.py
python3 scripts/smoke_h1_real_artifact_chain_closure.py
```
