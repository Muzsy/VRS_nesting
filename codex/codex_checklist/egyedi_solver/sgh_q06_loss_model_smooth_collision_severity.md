# Checklist — SGH-Q06 `sgh_q06_loss_model_smooth_collision_severity`

## Dependency gate

- [x] SGH-Q05R report létezik: `codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md`
- [x] SGH-Q05R report első sora: PASS
- [x] SGH-Q05R report tartalmazza: `SGH-Q06_STATUS: READY`
- [x] SGH-Q05R2 projektgazdai override: elfogadottnak tekintve (Q05R2 report PASS, SGH-Q06_STATUS: READY)
- [x] Q05/Q05R/Q05R2 fájlok nem módosítva ebben a taskban

## Preflight reads

- [x] AGENTS.md átolvasva
- [x] docs/codex/overview.md átolvasva
- [x] docs/codex/yaml_schema.md átolvasva
- [x] docs/codex/report_standard.md átolvasva
- [x] docs/qa/testing_guidelines.md átolvasva
- [x] docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md átolvasva
- [x] docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md átolvasva
- [x] docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md átolvasva
- [x] canvases/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md átolvasva
- [x] codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q06_loss_model_smooth_collision_severity.yaml átolvasva
- [x] codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md átolvasva
- [x] codex/reports/egyedi_solver/sgh_q05r2_bpp_contract_score_semantics_cleanup.md átolvasva

## Sparrow source audit

- [x] `./scripts/ensure_sparrow.sh` futtatva (Sparrow source elérhető)
- [x] `.cache/sparrow/src/quantify/overlap_proxy.rs` ténylegesen olvasva
  - `overlap_area_proxy(sp1, sp2, epsilon)` függvény auditálva
  - Sparrow Algorithm 3 formula: `pd = (r1+r2) - dist(c1,c2)`, smooth decay, `total * PI`
- [x] `.cache/sparrow/src/quantify/tracker.rs` ténylegesen olvasva
  - `restore_but_keep_weights`: loss-only restore, weights megmaradnak (ugyanaz a contract)
  - jagua-rs CDE backend: nem VRS-kompatibilis közvetlen importra (adaptáció szükséges)

## Implementation

- [x] `rust/vrs_solver/src/optimizer/loss_model.rs` létrehozva
  - `LossQualityRisk` enum: `BboxOnlyProxy`, `SmoothBboxSurrogate`
  - `LossModelKind` enum: `BboxArea` (default), `PolePenetrationSmooth`
  - `smooth_decay(pd, epsilon)` pub helper függvény
  - `LossModelKind::pair_loss()` — enum dispatch
  - `LossModelKind::compute_boundary_loss()` — enum dispatch
  - `LossModelKind::name()`, `quality_risk()`
  - Known limitations dokumentálva a doc comment-ekben
- [x] `rust/vrs_solver/src/optimizer/mod.rs` frissítve
  - `pub mod loss_model;` export hozzáadva
- [x] `rust/vrs_solver/src/optimizer/separator.rs` frissítve
  - `BOUNDARY_LOSS_PROXY` és `bbox_overlap_area` eltávolítva (BboxAreaLoss mögé kerültek)
  - `VrsCollisionTracker.boundary_losses: Vec<f64>` hozzáadva
  - `VrsCollisionTracker.loss_model_kind: LossModelKind` hozzáadva
  - `LossSnapshot.boundary_losses: Vec<f64>` hozzáadva
  - `VrsCollisionTracker::build_with_model()` bevezetve
  - `VrsCollisionTracker::build()` backward-compatible (BboxArea default)
  - `pair_loss()` → LossModelKind dispatch
  - `boundary_loss()` → boundary_losses[i] precomputed
  - `update_placement()` → boundary_losses[idx] frissítve
  - `restore_item()` → boundary_losses[idx] frissítve (signature + boundary_loss: f64)
  - `snapshot_loss()` → boundary_losses snapshotolva
  - `restore_but_keep_weights()` → boundary_losses visszaállítva
  - `VrsSeparatorConfig.loss_model: LossModelKind` hozzáadva (default: BboxArea)
  - `find_best_candidate_for_target()` → loss_model.pair_loss() a candidate rankinghez
  - `run()` → build_with_model(..., config.loss_model)

## Tesztek

### loss_model.rs tesztek (6 db)

- [x] `bbox_area_loss_matches_legacy_overlap_area`
- [x] `bbox_area_loss_preserves_binary_boundary_proxy`
- [x] `smooth_penetration_decay_is_continuous_at_epsilon`
- [x] `smooth_pair_loss_increases_with_overlap_depth`
- [x] `smooth_pair_loss_is_shape_scaled`
- [x] `smooth_boundary_loss_increases_with_violation_depth`

### separator.rs SGH-Q06 tesztek (5 db)

- [x] `separator_default_loss_model_preserves_existing_behavior`
- [x] `separator_can_use_smooth_loss_model`
- [x] `restore_but_keep_weights_preserves_weights_with_loss_model`
- [x] `same_seed_same_loss_model_determinism`
- [x] `smoke_bbox_vs_smooth_loss_model_on_dense_fixture`

## Verification

- [x] `cargo test optimizer::loss_model` → 6/6 PASS
- [x] `cargo test optimizer::separator` → 28/28 PASS (22 meglévő + 5 új + smoke)
- [x] `cargo test --lib` → 192/192 PASS (181 meglévő + 11 új)
- [x] `./scripts/verify.sh --report ...` → lásd report AUTO_VERIFY szekció

## Default no-downgrade gate

- [x] `VrsSeparatorConfig::default()` → `loss_model: LossModelKind::BboxArea`
- [x] `separator_fixes_simple_overlap` teszt: `initial_loss == 900.0` (30*30 = 900) — PASS
- [x] `tracker_valid_layout_total_loss_zero` — PASS
- [x] `tracker_overlap_gives_positive_pair_loss` — PASS
- [x] `tracker_boundary_violation_gives_positive_boundary_loss` — PASS
- [x] Minden meglévő 181 teszt zöld maradt

## Documentation

- [x] `docs/egyedi_solver/sgh_q06_loss_model_contract.md` létrehozva
- [x] `codex/codex_checklist/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md` elkészült
- [x] `codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md` elkészült

## No-scope-violation gate

- [x] RotationPolicy / continuous rotation: NEM módosítva
- [x] CollisionBackend / jagua-rs CDE backend: NEM módosítva
- [x] Exact irregular polygon collision: NEM módosítva
- [x] DXF/preflight: NEM módosítva
- [x] IO contract: NEM módosítva
- [x] Python runner: NEM módosítva
- [x] frontend/API: NEM módosítva
- [x] SheetElimination/BPP refaktor: NEM módosítva
- [x] PhaseOptimizer refaktor: NEM módosítva
- [x] Q05/Q05R/Q05R2 fájlok: NEM módosítva
