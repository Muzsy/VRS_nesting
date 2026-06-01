# Checklist — SGH-Q25-R1 Semantic Sparrow core parity fix

## Source-of-truth

- [x] Confirm `.cache/sparrow` exists.
- [x] Record `git -C .cache/sparrow rev-parse HEAD` in the report.
- [x] Read upstream `specialized_jaguars_pipeline.rs`, `sep_evaluator.rs`, `quantify/*`, `lbf.rs`, `worker.rs`, `separator.rs`, `explore.rs`, and `sample/*` before coding.

## Specialized collector

- [x] `SpecializedCdeHazardCollector` has real fields/state.
- [x] `reload(loss_bound)` resets state and stores loss bound.
- [x] Collector accumulates pair/container hazards and weighted loss.
- [x] Collector supports empty/loss/early-terminate behavior.
- [x] Collection function performs real CDE/session hazard collection.

## Separation evaluator

- [x] No `hazard_extent_depth` / `aabb_penetration` / `ox.min(oy)` / `ix * iy` ranking loss.
- [x] Uses collector and tracker weights.
- [x] Uses upper-bound early termination.
- [x] AABB only used for fit/broad-phase, never loss/ranking.

## Quantification/tracker

- [x] Default pair quantification follows upstream overlap proxy + shape penalty.
- [x] Default container quantification follows upstream container loss + shape penalty.
- [x] Tracker stores pair/container loss and GLS weights.
- [x] Any resolution-distance probe is non-default experimental and honestly documented.

## LBF

- [x] No `fixed_sheet_recovery_candidate` production success path.
- [x] No shelf/anchor/AABB-overlap fallback.
- [x] LBF placement is via `search_placement + LBFEvaluator`.
- [x] If no clear placement exists on fixed sheets, report unresolved/partial honestly.

## Worker/separator/explore

- [x] Move acceptance follows moved item weighted-loss non-increase semantics.
- [x] Best worker load-back chooses minimum total weighted loss.
- [x] Strike/no-improvement loop follows upstream loss semantics.
- [x] Exploration disruption includes contained-item relocation equivalent.

## Verification

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `python3 scripts/smoke_sgh_q25_r1_semantic_sparrow_core_parity_fix.py`
- [x] `./scripts/check.sh`
- [x] Report written to `codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md`
- [x] Report status is honest: `PASS` only if all semantic gates pass.
