#[cfg(test)]
mod tests {
    use super::super::*;
    mod tests {
        use super::*;
        use crate::sheet::{expand_sheets, Stock};
    
        fn make_part(id: &str, w: f64, h: f64, qty: i64) -> Part {
            Part {
                id: id.to_string(),
                width: w,
                height: h,
                quantity: qty,
                allowed_rotations_deg: vec![0],
                holes_points: None,
                prepared_holes_points: None,
                outer_points: None,
                prepared_outer_points: None,
                rotation_policy: None,
            }
        }
    
        fn make_part_rot(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
            Part {
                id: id.to_string(),
                width: w,
                height: h,
                quantity: qty,
                allowed_rotations_deg: rots,
                holes_points: None,
                prepared_holes_points: None,
                outer_points: None,
                prepared_outer_points: None,
                rotation_policy: None,
            }
        }
    
        fn make_stock(id: &str, w: f64, h: f64, qty: i64) -> Stock {
            Stock {
                id: id.to_string(),
                quantity: qty,
                width: Some(w),
                height: Some(h),
                outer_points: None,
                holes_points: None,
                cost_per_use: None,
            }
        }
    
        fn ctx() -> RotationResolveContext {
            RotationResolveContext::legacy_default()
        }
    
        fn cfg(backend: CollisionBackendKind) -> SparrowConfig {
            SparrowConfig::from_solver_input(3.0, backend, ctx(), 7)
        }
    
        fn pl(idx: usize, x: f64, y: f64) -> SparrowPlacement {
            SparrowPlacement {
                instance_idx: idx,
                sheet_index: 0,
                x,
                y,
                rotation_deg: 0.0,
            }
        }
    
        #[test]
        fn from_solver_input_expands_instances_with_stable_indices() {
            let parts = vec![make_part("P", 30.0, 20.0, 3)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            assert_eq!(
                problem.instances.len(),
                3,
                "3 instances expanded from quantity 3"
            );
            for (i, inst) in problem.instances.iter().enumerate() {
                assert_eq!(inst.idx, i, "native index is stable + dense");
                assert_eq!(inst.part_id, "P");
                assert!(
                    !inst.instance_id.is_empty(),
                    "external instance_id retained"
                );
            }
            assert!(problem.pre_unplaced.is_empty());
        }
    
        #[test]
        fn from_solver_input_projects_never_fits_to_pre_unplaced() {
            let parts = vec![make_part("BIG", 500.0, 500.0, 1)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            assert!(
                problem.instances.is_empty(),
                "never-fit part is not a placeable instance"
            );
            assert_eq!(
                problem.pre_unplaced.len(),
                1,
                "never-fit retained, not silently dropped"
            );
            assert_eq!(problem.pre_unplaced[0].reason, "PART_NEVER_FITS_STOCK");
        }
    
        #[test]
        fn constructive_seed_is_rotation_aware_for_oversized_at_zero() {
            // A 280x100 part does not fit a 150x300 sheet at 0deg (280>150) but fits at 90deg.
            let parts = vec![make_part_rot(
                "WIDE",
                280.0,
                100.0,
                1,
                vec![0, 90, 180, 270],
            )];
            let stocks = vec![make_stock("S", 150.0, 300.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            assert_eq!(
                problem.instances.len(),
                1,
                "rotatable oversized part is placeable"
            );
            let seed = build_native_constructive_seed(&problem);
            assert_eq!(
                seed.placements.len(),
                1,
                "seed must place the rotation-only-fitting part"
            );
            let rot = seed.placements[0].rotation_deg;
            assert!(
                (rot - 90.0).abs() < 1e-9 || (rot - 270.0).abs() < 1e-9,
                "seed picked a fitting rotation, got {rot}"
            );
        }
    
        #[test]
        fn native_tracker_quantified_loss_is_not_binary_count() {
            // Two overlapping 30x30 parts: a deep overlap must yield a LARGER quantified
            // pair loss than a shallow overlap (gradient, not a 1.0 count).
            let parts = vec![make_part("P", 30.0, 30.0, 2)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let insts = &problem.instances;
    
            let deep = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 5.0, 5.0)],
            };
            let shallow = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 25.0, 25.0)],
            };
            let t_deep = SparrowCollisionTracker::build(&deep, insts, &sheets);
            let t_shallow = SparrowCollisionTracker::build(&shallow, insts, &sheets);
            assert!(
                t_deep.colliding_pairs() == 1 && t_shallow.colliding_pairs() == 1,
                "both overlap once"
            );
            let l_deep = t_deep.total_raw_loss();
            let l_shallow = t_shallow.total_raw_loss();
            assert!(
                l_deep > QUANT_FLOOR && l_shallow > QUANT_FLOOR,
                "confirmed collisions have positive quantified loss"
            );
            assert!(
                l_deep > l_shallow + 1e-6,
                "deeper overlap must have strictly larger quantified loss ({l_deep} vs {l_shallow})"
            );
            assert!(
                l_deep != 1.0 && l_shallow != 1.0,
                "loss must not be a binary 1.0 count"
            );
        }
    
        #[test]
        fn native_tracker_cde_detects_overlap_and_separation() {
            let parts = vec![make_part("P", 30.0, 30.0, 2)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let insts = &problem.instances;
    
            let overlap = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)],
            };
            let t_overlap = SparrowCollisionTracker::build(&overlap, insts, &sheets);
            assert!(
                !t_overlap.unsupported,
                "rect-rect overlap must be CDE-supported"
            );
            assert!(
                t_overlap.colliding_pairs() >= 1,
                "overlap yields >=1 colliding pair"
            );
            assert!(!t_overlap.is_feasible(), "overlapping layout is infeasible");
    
            let apart = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 100.0, 100.0)],
            };
            let t_apart = SparrowCollisionTracker::build(&apart, insts, &sheets);
            assert_eq!(
                t_apart.colliding_pairs(),
                0,
                "separated layout has no colliding pairs"
            );
            assert_eq!(
                t_apart.boundary_violations(),
                0,
                "separated layout inside sheet"
            );
            assert!(t_apart.is_feasible(), "separated layout is feasible");
        }
    
        #[test]
        fn native_tracker_update_after_move_resolves_collision_incrementally() {
            let parts = vec![make_part("P", 30.0, 30.0, 2)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let insts = &problem.instances;
    
            let mut layout = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)],
            };
            let mut tracker = SparrowCollisionTracker::build(&layout, insts, &sheets);
            assert!(!tracker.is_feasible(), "starts overlapping");
            let before = tracker.incremental_updates;
    
            layout.placements[1] = pl(1, 120.0, 120.0);
            let mut diag = SparrowDiagnostics::default();
            tracker.update_after_move(1, &layout, insts, &sheets, &mut diag);
            assert_eq!(
                tracker.incremental_updates,
                before + 1,
                "incremental update counter advanced"
            );
            assert_eq!(
                diag.native_tracker_incremental_updates, 1,
                "diag incremental update recorded"
            );
            assert_eq!(
                tracker.colliding_pairs(),
                0,
                "collision resolved after move"
            );
            assert!(tracker.is_feasible(), "feasible after separating move");
        }
    
        #[test]
        fn native_tracker_snapshot_restore_preserves_gls_weights() {
            let parts = vec![make_part("P", 30.0, 30.0, 2)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let insts = &problem.instances;
    
            let layout = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)],
            };
            let mut tracker = SparrowCollisionTracker::build(&layout, insts, &sheets);
            let snap = tracker.snapshot();
            tracker.update_weights();
            let weighted_after_bump = tracker.total_weighted_loss();
            let raw = tracker.total_raw_loss();
            assert!(
                weighted_after_bump > raw,
                "GLS weight bump raises weighted loss above raw"
            );
    
            tracker.restore_keep_weights(snap);
            assert!(
                (tracker.total_weighted_loss() - weighted_after_bump).abs() < 1e-6,
                "weights survive snapshot/restore"
            );
        }
    
        #[test]
        fn native_optimizer_solve_feasible_projects_all_placements() {
            let parts = vec![make_part("P", 30.0, 20.0, 4)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let config = cfg(CollisionBackendKind::Cde);
            let problem =
                SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], config.clone())
                    .expect("problem");
            let n = problem.instances.len();
            let result = SparrowOptimizer::new(config).solve(problem);
    
            assert!(result.feasible, "tiny problem converges natively");
            assert!(
                result.diagnostics.converged,
                "diagnostics report convergence"
            );
            assert_eq!(
                result.placements.len(),
                n,
                "every instance projected to a Placement"
            );
            assert_eq!(
                result.diagnostics.collision_graph_final_pairs, 0,
                "no residual collisions"
            );
            assert_eq!(
                result.diagnostics.boundary_violations_final, 0,
                "no residual boundary violations"
            );
            assert!(result.diagnostics.native_model_active);
            assert!(result.diagnostics.native_tracker_active);
            assert!(!result.diagnostics.old_core_used);
            assert_eq!(result.diagnostics.native_problem_instances, n);
            assert_eq!(
                result.diagnostics.excluded_phase_passes, 0,
                "excluded phase disabled by default"
            );
        }
    
        #[test]
        fn native_optimizer_worker_competition_is_active() {
            // An oversubscribed-but-individually-fitting case must exercise the real worker competition
            // and quantified tracker: worker_count>=2, candidates evaluated, incremental
            // updates, and search calls all > 0. (Full convergence/timing is covered by
            // the release runtime smoke; this debug unit test only proves activity.)
            let parts = vec![make_part("P", 90.0, 90.0, 8)];
            let stocks = vec![make_stock("S", 180.0, 180.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let config = cfg(CollisionBackendKind::Cde);
            let problem =
                SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], config.clone())
                    .expect("problem");
            let result = SparrowOptimizer::new(config).solve(problem);
            let d = &result.diagnostics;
            assert!(
                d.worker_count >= 2,
                "worker competition active, got {}",
                d.worker_count
            );
            assert!(d.worker_passes > 0, "at least one worker pass ran");
            assert!(
                d.worker_candidates_evaluated > 0,
                "workers evaluated candidates"
            );
            assert!(d.search_position_calls > 0, "search invoked");
            assert!(d.search_position_samples > 0, "search sampled candidates");
            assert!(
                d.native_tracker_incremental_updates > 0,
                "incremental tracker updates happened"
            );
            assert!(
                d.quantified_pair_queries > 0,
                "quantified pair separation probed"
            );
            assert!(
                d.multi_target_items_attempted > 0,
                "worker move targets attempted"
            );
        }
    
        #[test]
        fn native_optimizer_solve_is_deterministic_for_same_seed() {
            let parts = vec![make_part("P", 25.0, 25.0, 5)];
            let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let run = || {
                let config = cfg(CollisionBackendKind::Cde);
                let problem =
                    SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], config.clone())
                        .expect("problem");
                SparrowOptimizer::new(config).solve(problem).placements
            };
            let a = run();
            let b = run();
            assert_eq!(a.len(), b.len(), "same placed count");
            for (pa, pb) in a.iter().zip(b.iter()) {
                assert_eq!(pa.instance_id, pb.instance_id);
                assert!(
                    (pa.x - pb.x).abs() < 1e-9 && (pa.y - pb.y).abs() < 1e-9,
                    "deterministic coords"
                );
                assert!(
                    (pa.rotation_deg - pb.rotation_deg).abs() < 1e-9,
                    "deterministic rotation"
                );
            }
        }
    
        #[test]
        fn coord_descent_rotation_wiggle_executes_for_continuous_rotation() {
            // A continuous-rotation, over-capacity fixture forces the separator to run
            // the coordinate-descent refinement; the rotation-wiggle axis must execute
            // nonzero rotation steps (proof the wiggle path is live, not hard-zero).
            let parts = vec![make_part("P", 70.0, 50.0, 6)];
            let stocks = vec![make_stock("S", 150.0, 150.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let ctx = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 7, 8);
            let config =
                SparrowConfig::from_solver_input(3.0, CollisionBackendKind::Cde, ctx.clone(), 7);
            let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx, vec![], config.clone())
                .expect("problem");
            assert!(
                problem.instances.iter().all(|i| i.continuous_rotation),
                "continuous policy enables rotation wiggle"
            );
            let result = SparrowOptimizer::new(config).solve(problem);
            assert!(
                result.diagnostics.search_rotation_wiggle > 0,
                "coordinate-descent executed nonzero rotation-wiggle steps, got {}",
                result.diagnostics.search_rotation_wiggle
            );
        }
    }
}
