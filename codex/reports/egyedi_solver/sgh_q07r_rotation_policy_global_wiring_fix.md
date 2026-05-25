PASS

# Report — SGH-Q07R `sgh_q07r_rotation_policy_global_wiring_fix`

## Status

PASS — A global `SolverInput.rotation_policy` és `seed` wiring végigvezetve a valós solve pathon. A hardcoded `resolve_part_rotation_angles(..., None, 0, 8)` production minták megszűntek, context-aware vagy instance-resolved hívásra cserélve.

## Meta

- Task slug: `sgh_q07r_rotation_policy_global_wiring_fix`
- Canvas: `canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r_rotation_policy_global_wiring_fix.yaml`
- Date: 2026-05-25

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md` first line: `PASS`

## Pre-fix audit evidence

Parancs: `rg "resolve_part_rotation_angles\([^\n]*None, 0, 8" rust/vrs_solver/src`

Találatok pre-fix:

- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/optimizer/initializer.rs`
- `rust/vrs_solver/src/optimizer/separator.rs`
- `rust/vrs_solver/src/optimizer/compress.rs`
- `rust/vrs_solver/src/optimizer/moves.rs`
- `rust/vrs_solver/src/optimizer/repair.rs`
- `rust/vrs_solver/src/optimizer/sheet_elimination.rs`

Parancs: `rg "expand_instances\(&input.parts\)" rust/vrs_solver/src`

- `rust/vrs_solver/src/adapter.rs` (global policy nélkül hívta)

Parancs: `rg "can_fit_any_stock\(" rust/vrs_solver/src`

- `rust/vrs_solver/src/adapter.rs` (global policy nélkül hívta)

## Solution summary

- `RotationResolveContext` és determinisztikus seed-mixelés bevezetve (`rotation_policy.rs`).
- `item` policy-aware helper API-k bevezetve (`*_with_policy`) és wrapper backward compatibility megtartva.
- `adapter::solve` global policy + seed wiring bekötve:
  - `expand_instances_with_policy`
  - `can_fit_any_stock_with_policy`
  - `MultiSheetManager::new_with_rotation_context`
- Optimizer call site javítások:
  - `initializer`: separator fallback az `Instance.allowed_rotations_deg` listát használja.
  - `separator`: `resolve_instance_rotation_angles` + context.
  - `compress`: instance-aware rotation resolve.
  - `moves`: instance-aware rotation resolve + separator context.
  - `repair`: `run_repair_with_rotation_context`.
  - `sheet_elimination`: context-aware `resolve_dims` + separator context.
  - `multisheet`: context-aware initializer/repair/elimination hívások.
  - `phase`/`bpp_phase`: context bridge mező és továbbadás.

## Post-fix audit evidence

Parancs: `rg "resolve_part_rotation_angles\([^\n]*None, 0, 8" rust/vrs_solver/src`

- Eredmény: nincs találat.

Következtetés: nincs megmaradt production hardcoded `None, 0, 8` feloldás indoklás nélkül.

## Required regression tests

PASS:

- `global_forty_five_policy_affects_expand_instances_when_part_has_no_legacy_rots`
- `global_continuous_policy_affects_expand_instances_when_part_has_no_legacy_rots`
- `adapter_solve_global_forty_five_places_100x20_on_90x90_sheet`
- `adapter_solve_legacy_allowed_rotations_overrides_global_policy`
- `part_policy_overrides_global_policy_in_real_solve_path`
- `continuous_policy_same_seed_deterministic_through_solve`
- `continuous_policy_different_seed_changes_resolved_candidate_angles`
- `no_remaining_production_none_zero_eight_policy_resolution_without_justification`

## Commands run

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml item`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`

SGH-Q08_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T21:49:23+02:00 → 2026-05-25T21:52:25+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.verify.log`
- git: `main@3dafead`
- módosított fájlok (git status): 20

**git diff --stat**

```text
 .../sgh_q07_rotation_policy_contract.md            |  23 +++
 rust/vrs_solver/src/adapter.rs                     | 160 ++++++++++++++++++++-
 rust/vrs_solver/src/item.rs                        | 119 ++++++++++++---
 rust/vrs_solver/src/optimizer/bpp_phase.rs         |   6 +-
 rust/vrs_solver/src/optimizer/compress.rs          |  10 +-
 rust/vrs_solver/src/optimizer/initializer.rs       |  28 +++-
 rust/vrs_solver/src/optimizer/moves.rs             |  33 +++--
 rust/vrs_solver/src/optimizer/multisheet.rs        |  46 ++++--
 rust/vrs_solver/src/optimizer/phase.rs             |   4 +
 rust/vrs_solver/src/optimizer/repair.rs            |  38 ++++-
 rust/vrs_solver/src/optimizer/separator.rs         |  14 +-
 rust/vrs_solver/src/optimizer/sheet_elimination.rs |  25 +++-
 rust/vrs_solver/src/rotation_policy.rs             |  99 +++++++++++++
 13 files changed, 548 insertions(+), 57 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/item.rs
 M rust/vrs_solver/src/optimizer/bpp_phase.rs
 M rust/vrs_solver/src/optimizer/compress.rs
 M rust/vrs_solver/src/optimizer/initializer.rs
 M rust/vrs_solver/src/optimizer/moves.rs
 M rust/vrs_solver/src/optimizer/multisheet.rs
 M rust/vrs_solver/src/optimizer/phase.rs
 M rust/vrs_solver/src/optimizer/repair.rs
 M rust/vrs_solver/src/optimizer/separator.rs
 M rust/vrs_solver/src/optimizer/sheet_elimination.rs
 M rust/vrs_solver/src/rotation_policy.rs
?? README_SGH_Q07R_PACKAGE.md
?? canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r_rotation_policy_global_wiring_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix/
?? codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
?? codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.verify.log
```

<!-- AUTO_VERIFY_END -->
