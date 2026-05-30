# Runner — SGH-Q22R1 Sparrow CDE diagnostics and acceptance hardening

Implement the corrective task described in:

```text
canvases/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.yaml
codex/codex_checklist/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
```

Do not treat this as a cosmetic marker fix. The goal is to make `sparrow_experimental` honestly testable in CDE mode and diagnostically useful when it fails.

Hard requirements:

1. Unsupported Sparrow outputs preserve optimizer diagnostics.
2. Tiny CDE Sparrow success path is required by smoke.
3. CDE unsupported/timeout no longer counts as pass evidence.
4. Benchmark denominator includes unsupported/timeouts.
5. Zero metrics render as `0`, not `-`.
6. Q18B recommendation follows the measured CDE result.

Run:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter -- sparrow_pipeline
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q22_sparrow_kernel.py
python3 scripts/bench_sgh_q22_sparrow_kernel.py --quick
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q22r1_sparrow_cde_diagnostics_acceptance_fix.md
```

Report first line must be PASS, REVISE, or BLOCKED.
