# Checklist — SGH-Q07R `sgh_q07r_rotation_policy_global_wiring_fix`

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md` létezik
- [x] A report első sora `PASS`

## Preflight reads

- [x] AGENTS.md
- [x] docs/codex/overview.md
- [x] docs/codex/yaml_schema.md
- [x] docs/codex/report_standard.md
- [x] docs/qa/testing_guidelines.md
- [x] canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
- [x] docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
- [x] canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r_rotation_policy_global_wiring_fix.yaml

## Pre-fix audit

- [x] `rg "rotation_policy" rust/vrs_solver/src`
- [x] `rg "resolve_part_rotation_angles\([^\n]*None, 0, 8" rust/vrs_solver/src`
- [x] `rg "expand_instances\(&input.parts\)" rust/vrs_solver/src`
- [x] `rg "can_fit_any_stock\(" rust/vrs_solver/src`
- [x] A pre-fix előfordulások dokumentálva a reportban

## Implementation

- [x] Rotation resolve context bevezetve (`RotationResolveContext`, seed deriváció)
- [x] `item` policy-aware helper API-k: `expand_instances_with_policy`, `can_fit_any_stock_with_policy`, `build_item_geometry_store_with_policy`
- [x] `adapter::solve` global policy + seed wiring bekötve
- [x] Optimizer path javítva (initializer/separator/compress/moves/repair/sheet_elimination)
- [x] `multisheet`/`phase`/`bpp_phase` bridge: context átadás
- [x] Nincs megmaradt production `resolve_part_rotation_angles(..., None, 0, 8)`

## Required regressions

- [x] `global_forty_five_policy_affects_expand_instances_when_part_has_no_legacy_rots`
- [x] `global_continuous_policy_affects_expand_instances_when_part_has_no_legacy_rots`
- [x] `adapter_solve_global_forty_five_places_100x20_on_90x90_sheet`
- [x] `adapter_solve_legacy_allowed_rotations_overrides_global_policy`
- [x] `part_policy_overrides_global_policy_in_real_solve_path`
- [x] `continuous_policy_same_seed_deterministic_through_solve`
- [x] `continuous_policy_different_seed_changes_resolved_candidate_angles`
- [x] `no_remaining_production_none_zero_eight_policy_resolution_without_justification`

## Verification

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml item`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md`
