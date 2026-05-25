# Checklist — SGH-Q07 `sgh_q07_rotation_policy_continuous_foundation`

## Dependency gate

- [x] SGH-Q06 report létezik: `codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md`
- [x] SGH-Q06 report első sora: PASS
- [x] SGH-Q06 report tartalmazza: `SGH-Q07_STATUS: READY`
- [x] Q06 fájlok nem módosítva ebben a taskban

## Preflight reads

- [x] AGENTS.md átolvasva
- [x] docs/codex/overview.md átolvasva
- [x] docs/codex/yaml_schema.md átolvasva
- [x] docs/codex/report_standard.md átolvasva
- [x] docs/qa/testing_guidelines.md átolvasva
- [x] docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md átolvasva
- [x] docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md átolvasva
- [x] docs/egyedi_solver/sgh_q06_loss_model_contract.md átolvasva
- [x] canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md átolvasva
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07_rotation_policy_continuous_foundation.yaml átolvasva

## Sparrow source audit

- [x] `./scripts/ensure_sparrow.sh` futtatva (Sparrow source elérhető)
- [x] `.cache/sparrow/src/sample/uniform_sampler.rs` ténylegesen olvasva
  - `ROT_N_SAMPLES = 16` — continuous rotation sample count
  - `sample_rotation()` uniform_sampler implementáció auditálva
- [x] `jagua-rs-0.6.4/src/geo_enums.rs` ténylegesen olvasva
  - `RotationRange::None` / `Continuous` / `Discrete` enum auditálva
- [x] `.cache/sparrow/src/search/coord_descent.rs` ténylegesen olvasva
  - `CDAxis::Wiggle` — coordinate descent rotation wiggle

## Implementation

- [x] `rust/vrs_solver/src/rotation_policy.rs` létrehozva
  - `RotationPolicyKind` enum: Locked, HalfTurn, Orthogonal (default), FortyFive, Discrete(Vec<f64>), Continuous
  - `candidate_angles(kind, seed, sample_count) -> Vec<AngleDeg>` 
  - `ContinuousRng` — xorshift64 determinisztikus mintavételező
  - `normalize_angle`, `dedup_angles`
  - `dims_for_rotation_f64`, `rotated_bbox_min_offset_f64`, `placement_anchor_from_rect_min_f64`
- [x] `rust/vrs_solver/src/lib.rs` frissítve (`pub mod rotation_policy`)
- [x] `rust/vrs_solver/src/io.rs` frissítve
  - `Placement.rotation_deg: i64` → `f64`
  - `serialize_rotation_deg` custom serializer (integer szögek `.0` nélkül)
  - `SolverInput.rotation_policy: Option<RotationPolicyKind>`
- [x] `rust/vrs_solver/src/item.rs` teljesen újraírva
  - `Part.rotation_policy: Option<RotationPolicyKind>`
  - `Instance.allowed_rotations_deg: Vec<f64>`
  - `resolve_part_rotation_angles(part, global_policy, seed, sample_count)` — precedence logic
  - `dims_for_rotation`, `rotated_bbox_min_offset`, `placement_anchor_from_rect_min` infallible f64
  - `normalize_allowed_rotations` → `Vec<f64>` (no restriction to 0/90/180/270)
- [x] `rust/vrs_solver/src/optimizer/mod.rs` frissítve (`try_place_on_sheet` f64)
- [x] `rust/vrs_solver/src/optimizer/initializer.rs` frissítve
- [x] `rust/vrs_solver/src/optimizer/separator.rs` frissítve
- [x] `rust/vrs_solver/src/optimizer/compress.rs` frissítve
- [x] `rust/vrs_solver/src/optimizer/moves.rs` frissítve (`CandidateMove::Rotate f64`, epsilon comparisons)
- [x] `rust/vrs_solver/src/optimizer/repair.rs` frissítve (`RepairItem.allowed_rotations: Vec<f64>`)
- [x] `rust/vrs_solver/src/optimizer/sheet_elimination.rs` frissítve

## Tesztek

### rotation_policy.rs tesztek (15 db)

- [x] `rotation_policy_locked_generates_only_zero`
- [x] `rotation_policy_half_turn_generates_0_180`
- [x] `rotation_policy_orthogonal_matches_legacy_0_90_180_270`
- [x] `rotation_policy_forty_five_generates_8_angles`
- [x] `legacy_allowed_rotations_deg_still_supported`
- [x] `part_policy_overrides_global_policy`
- [x] `global_policy_used_when_part_has_no_explicit_policy`
- [x] `arbitrary_45_degree_bbox_math_is_correct`
- [x] `continuous_policy_generates_non_orthogonal_angles`
- [x] `continuous_policy_same_seed_is_deterministic`
- [x] `continuous_rotation_can_fit_rectangle_that_orthogonal_cannot`
- [x] `separator_uses_rotation_policy_not_hardcoded_orthogonal`
- [x] `compression_uses_rotation_policy_not_hardcoded_orthogonal`
- [x] `rotated_bbox_min_offset_canonical_angles_correct`
- [x] `placement_anchor_keeps_bbox_inside_rect`

## Verification

- [x] `cargo test rotation_policy` → 15/15 PASS
- [x] `cargo test item` → 21/21 PASS
- [x] `cargo test optimizer::initializer` → 15/15 PASS
- [x] `cargo test optimizer::separator` → 28/28 PASS
- [x] `cargo test optimizer::compress` → 4/4 PASS
- [x] `cargo test optimizer::moves` → 19/19 PASS
- [x] `cargo test optimizer::sheet_elimination` → 11/11 PASS
- [x] `cargo test --lib` → 211/211 PASS
- [x] `./scripts/verify.sh --report ...` → lásd report AUTO_VERIFY szekció

## Default no-downgrade gate

- [x] `allowed_rotations_deg: [0, 90]` → Discrete [0.0, 90.0] — korábbi viselkedés megőrízve
- [x] `RotationPolicyKind::default()` → `Orthogonal`
- [x] JSON output: integer szögek `.0` nélkül (custom serializer)
- [x] Minden pre-Q07 teszt zöld maradt (192 → 211, 19 új)

## Documentation

- [x] `docs/egyedi_solver/sgh_q07_rotation_policy_contract.md` létrehozva
- [x] `codex/codex_checklist/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md` elkészült
- [x] `codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md` elkészült

## No-scope-violation gate

- [x] jagua-rs CDE backend: NEM módosítva
- [x] Exact irregular polygon collision: NEM módosítva
- [x] Hole/cavity kezelés: NEM módosítva
- [x] DXF/preflight: NEM módosítva
- [x] Q06 fájlok: NEM módosítva
- [x] PlacementTransform.rotation_deg (state.rs): NEM módosítva (i64 megmarad)
- [x] Python runner: NEM módosítva
- [x] frontend/API: NEM módosítva
