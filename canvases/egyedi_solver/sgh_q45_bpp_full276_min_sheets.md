# SGH-Q45 — coroush/sparrow BPP multisheet port + full276 minimal-sheet benchmark

## Goal

Port/adapt the `coroush/sparrow` BPP (bin-packing) sheet-reduction solver into the VRS native
Rust solver as the production `sparrow_cde_multisheet` path, with a **minimal used-sheet**
objective on 1500×3000 mm finite stock, and benchmark it on the full276 LV8 package with Q42
technology parameters (margin 5, spacing 8, kerf 0, continuous rotation).

## Source

`https://github.com/coroush/sparrow` commit `5df9ce15` (MIT, © 2025 Jeroen Gardeyn / KU Leuven).
Only the BPP layer (`src/bp_optimizer/{bp_lbf,bp_explore,bp_moves,bp_separator}.rs`) is the
reference — not the upstream JeroenGar/sparrow strip-packing solver. Attribution in
`THIRD_PARTY_NOTICES.md`. No `jagua-rs` source modified.

## Approach

A "bin" maps to a `sheet_index` in the flat `SparrowLayout`. The new module
`rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` reuses the existing native CDE
separator / collision tracker:

1. construct a feasible layout over the stock pool (FFD + LBF, existing-sheet-first);
2. area lower bound = ⌈Σ part area / max sheet area⌉;
3. sheet-reduction loop: eliminate the lowest-utilization sheet → redistribute its items →
   separate only the affected sheets → transfer/swap repair → compact → accept incumbent,
   with failed-candidate memory + perturbation;
4. final validation; `ok` only when all placed and collision-free / boundary-safe.

The legacy subset-attempt manager stays as a fallback behind `VRS_MULTISHEET_MODE=subset`.

## Deliverables

- `bpp_reduction.rs` (new solver), pipeline routing + `bpp_reduction` diagnostics, 7 unit tests.
- `scripts/bench_sgh_q45_bpp_full276_min_sheets.py` (configurable `--time-limit`, `--stock-qty`).
- `artifacts/benchmarks/sgh_q45/` (inputs, outputs, logs, renders, summaries).
- Report: `codex/reports/egyedi_solver/sgh_q45_bpp_full276_min_sheets.md`.

## Status

Implementation + tests complete (full `cargo test` green). Full276 1200s benchmark: see the
report (Run A / verdict). Reaching the 2-sheet area bound is not guaranteed (proven-feasible to
date is 3 sheets); a valid 3-sheet result with documented lower-bound gap is an acceptable
outcome.
