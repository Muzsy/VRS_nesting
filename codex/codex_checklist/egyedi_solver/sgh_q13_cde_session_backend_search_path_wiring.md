# Checklist — SGH-Q13 CDE session backend + search-path wiring

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md` first line: `PASS`
- [x] Q12 report contains `SGH-Q13_STATUS: READY`

## jagua-rs CDE API audit

- [x] `HazardEntity::Exterior` — usable (sheet boundary)
- [x] `HazardEntity::Hole { idx }` — usable (placed item pair queries)
- [x] `HazardEntity::PlacedItem { pk: PItemKey }` — requires SlotMap PItemKey; NOT usable without full jagua layout state
- [x] `NoFilter` — usable
- [x] `CDEngine::register_hazard` / `deregister_hazard_by_entity` — public but requires stable hazard map; no tentative-query API
- [x] Self-hazard filter — NOT cleanly available without `HazardEntity::PlacedItem` + SlotMap
- [x] Session CDEngine conclusion documented: `PerCallOnly` is honest for live search

## CDE session contract (cde_session.rs)

- [x] `CdeSessionCapability` enum: `FullSession | QueryBatch | PerCallOnly { reason }`
- [x] `query_capability()` returns `PerCallOnly { reason }` — honest status
- [x] `CdeDiagnostics` struct: `cde_queries`, `cde_engine_builds`, `cde_unsupported_count`, `cde_session_capability`
- [x] No fake session created; no bbox fallback named as CDE session
- [x] `pub mod cde_session` added to `optimizer/mod.rs`

## Separator CDE wiring

- [x] `compute_backend_decisions(Cde)` — no longer all-Unsupported; uses `CdeCollisionBackend`
- [x] `update_placement(Cde)` — no longer all-Unsupported; uses `CdeCollisionBackend`
- [x] `candidate_loss_for_backend(Cde)` — no longer `f64::MAX`; uses `CdeCollisionBackend`
- [x] Bbox arm unchanged
- [x] JaguaPolygonExact arm unchanged

## Backend diagnostics

- [x] `CdeDiagnostics.cde_queries` — query counter
- [x] `CdeDiagnostics.cde_engine_builds` — engine build counter (= queries for PerCallOnly)
- [x] `CdeDiagnostics.cde_unsupported_count` — unsupported query counter
- [x] `CdeDiagnostics.cde_session_capability` — capability string field

## Required tests (10/10 passing)

- [x] `cde_tracker_build_uses_cde_backend_not_all_unsupported`
- [x] `cde_separator_candidate_backend_loss_is_not_always_max`
- [x] `cde_separator_repairs_simple_overlap_or_reports_real_unsupported`
- [x] `cde_phase_optimizer_valid_rect_fixture_has_no_backend_unsupported`
- [x] `cde_score_with_backend_matches_validation_for_valid_rects`
- [x] `cde_session_capability_reports_truthful_lifecycle_status`
- [x] `cde_session_or_batch_matches_per_call_adapter_for_pair_matrix`
- [x] `bbox_default_still_matches_pre_q13_behavior`
- [x] `jagua_polygon_exact_path_unchanged`
- [x] `no_silent_bbox_fallback_for_cde_search_path`

## Verify

- [x] `cargo test --lib` → 310 passed, 0 failed
- [x] `./scripts/verify.sh --report ...` → PASS
