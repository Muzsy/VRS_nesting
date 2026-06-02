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

        fn scored(
            score: f64,
            rect_min_x: f64,
            rect_min_y: f64,
            anchor_x: f64,
            anchor_y: f64,
            rotation_deg: f64,
        ) -> ScoredPlacement {
            ScoredPlacement {
                score,
                collision_loss: 0.0,
                is_clear: true,
                rect_min_x,
                rect_min_y,
                placement: SparrowPlacement {
                    instance_idx: 0,
                    sheet_index: 0,
                    x: anchor_x,
                    y: anchor_y,
                    rotation_deg,
                },
            }
        }

        struct RecordingEvaluator {
            samples: Vec<(f64, f64, f64)>,
        }

        impl SampleEvaluator for RecordingEvaluator {
            fn evaluate_sample(
                &mut self,
                x: f64,
                y: f64,
                rot: f64,
                _upper_bound: Option<SampleEval>,
                _diag: &mut SparrowDiagnostics,
            ) -> Option<ScoredPlacement> {
                self.samples.push((x, y, rot));
                Some(scored(
                    1.0 + self.samples.len() as f64,
                    x,
                    y,
                    x + 900.0,
                    y + 800.0,
                    rot,
                ))
            }

            fn n_evals(&self) -> usize {
                self.samples.len()
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
                placements: vec![pl(0, 20.0, 20.0), pl(1, 30.0, 30.0)],
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
                placements: vec![pl(0, 20.0, 20.0), pl(1, 100.0, 100.0)],
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
                placements: vec![pl(0, 20.0, 20.0), pl(1, 30.0, 30.0)],
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
                placements: vec![pl(0, 20.0, 20.0), pl(1, 30.0, 30.0)],
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
        fn coord_descent_uses_rect_min_for_rotated_anchor_candidates() {
            let init = scored(0.0, 10.0, 20.0, 910.0, 820.0, 45.0);
            let mut evaluator = RecordingEvaluator {
                samples: Vec::new(),
            };
            let mut rng = DeterministicRng::new(11);
            let mut diag = SparrowDiagnostics::default();
            let mut config = cfg(CollisionBackendKind::Cde);
            config.coord_descent_steps = 1;

            let _ = refine_coord_desc(
                init,
                &mut evaluator,
                100.0,
                &config,
                &mut rng,
                &mut diag,
                false,
                false,
                config.rotation_wiggle_deg,
            );

            assert!(
                !evaluator.samples.is_empty(),
                "coordinate descent evaluated candidate samples"
            );
            assert!(
                evaluator
                    .samples
                    .iter()
                    .all(|(x, y, _)| (x - 10.0).abs() < 200.0 && (y - 20.0).abs() < 200.0),
                "coordinate descent must mutate rect-min coordinates, not anchor output coordinates: {:?}",
                evaluator.samples
            );
        }

        #[test]
        fn best_samples_deduplicates_in_rect_min_sample_space() {
            let mut best = BestSamples::new(4, 0.1);
            let first = scored(10.0, 12.0, 34.0, 100.0, 200.0, 45.0);
            let better_same_sample = scored(5.0, 12.02, 34.01, 300.0, 400.0, 45.0);

            assert!(best.report(first));
            assert!(best.report(better_same_sample));
            assert_eq!(
                best.samples.len(),
                1,
                "same rect-min sample-space key deduplicates even when anchor differs"
            );
            assert_eq!(best.samples[0].score, 5.0);
        }

        #[test]
        fn lbf_evaluator_rejects_colliding_candidates_as_invalid() {
            let parts = vec![make_part("P", 50.0, 50.0, 2)];
            let stocks = vec![make_stock("S", 120.0, 120.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let sheet = &problem.container.sheets[0];
            let sheet_shape = prepare_shape_from_sheet(sheet).expect("sheet shape");
            let placed = prepare_shape_native(&problem.instances[0].part, 0.0, 0.0, 0.0)
                .expect("placed shape");
            let session = CdeCandidateSession::build(vec![(0, Rc::new(placed))], &sheet_shape)
                .expect("session");
            let base = prepare_base_shape_native(&problem.instances[1].part).expect("base");
            let evaluator = LBFEvaluator {
                inst: &problem.instances[1],
                sheet,
                sheet_idx: 0,
                session: &session,
                base: &base,
                n_evals: 0,
            };

            assert!(
                evaluator.score_lbf_candidate(0.0, 0.0, 0.0).is_none(),
                "colliding LBF sample must be rejected, not returned as is_clear=false"
            );
        }

        #[test]
        fn fixed_sheet_bootstrap_is_outside_lbf_and_marked_infeasible() {
            let parts = vec![make_part("P", 100.0, 100.0, 2)];
            let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");

            let lbf_result = LBFBuilder::new(&problem).construct();
            assert_eq!(
                lbf_result.layout.placements.len(),
                0,
                "strict clear-only LBF rejects exact boundary-touching fit"
            );
            assert_eq!(
                lbf_result.unresolved.len(),
                2,
                "both perfectly fitting items are unresolved on a fixed sheet"
            );

            let bootstrapped = build_native_constructive_seed(&problem);
            assert_eq!(
                bootstrapped.placements.len(),
                2,
                "fixed-sheet bootstrap seeds unresolved item outside LBF"
            );
            let tracker = SparrowCollisionTracker::build(
                &bootstrapped,
                &problem.instances,
                &problem.container.sheets,
            );
            assert!(
                !tracker.is_feasible(),
                "bootstrap seed is honestly infeasible and left for separator resolution"
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
                let problem = SparrowProblem::from_solver_input(
                    &parts,
                    &sheets,
                    &ctx(),
                    vec![],
                    config.clone(),
                )
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
            let problem =
                SparrowProblem::from_solver_input(&parts, &sheets, &ctx, vec![], config.clone())
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

        #[test]
        fn cde_sparrow_strict_reports_touching_rectangles_as_collision() {
            let part = make_part("P", 30.0, 20.0, 1);
            let left = prepare_shape_native(&part, 0.0, 0.0, 0.0).expect("left shape");
            let right = prepare_shape_native(&part, 30.0, 0.0, 0.0).expect("right shape");
            let adapter = CdeAdapter::new(crate::optimizer::cde_adapter::CdeAdapterConfig {
                touching_policy: crate::optimizer::cde_adapter::CdeTouchingPolicy::SparrowStrict,
                ..crate::optimizer::cde_adapter::CdeAdapterConfig::default()
            });
            assert_eq!(adapter.query_pair(&left, &right), CdeQueryResult::Collision);
        }

        #[test]
        fn cde_vrs_touch_allowed_reports_touching_rectangles_as_no_collision() {
            let part = make_part("P", 30.0, 20.0, 1);
            let left = prepare_shape_native(&part, 0.0, 0.0, 0.0).expect("left shape");
            let right = prepare_shape_native(&part, 30.0, 0.0, 0.0).expect("right shape");
            let adapter = CdeAdapter::with_vrs_touch_allowed();
            assert_eq!(
                adapter.query_pair(&left, &right),
                CdeQueryResult::NoCollision
            );
        }

        #[test]
        fn sparrow_strict_boundary_touching_is_not_feasible() {
            let parts = vec![make_part("P", 30.0, 30.0, 1)];
            let stocks = vec![make_stock("S", 30.0, 30.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let layout = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0)],
            };
            let tracker =
                SparrowCollisionTracker::build(&layout, &problem.instances, &sheets);
            assert_eq!(tracker.boundary_violations(), 1);
            assert!(!tracker.is_feasible());
        }

        #[test]
        fn strict_worker_orders_colliding_items_by_rng_shuffle_only() {
            let parts = vec![make_part("P", 30.0, 30.0, 3)];
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
            let layout = SparrowLayout {
                placements: vec![pl(0, 0.0, 0.0), pl(1, 5.0, 5.0), pl(2, 10.0, 10.0)],
            };
            let tracker = SparrowCollisionTracker::build(&layout, &problem.instances, &sheets);
            let config = cfg(CollisionBackendKind::Cde);
            let mut expected = tracker.colliding_indices();
            let mut expected_rng = DeterministicRng::new(123);
            expected_rng.shuffle(&mut expected);
            let mut worker_rng = DeterministicRng::new(123);
            let ordered =
                ordered_colliding_items_for_worker(&tracker, &config, 2, &mut worker_rng);
            assert_eq!(ordered, expected);
        }

        #[test]
        fn strict_separator_uses_upstream_loop_limits() {
            let config = cfg(CollisionBackendKind::Cde).scaled_for_instance_count(500);
            assert_eq!(config.worker_count, SPARROW_PARITY_WORKERS);
            assert_eq!(
                config.focused_samples,
                SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES
            );
            assert_eq!(config.coord_descent_steps, SPARROW_PARITY_COORD_DESCENTS);
            let sample_config = separator_sample_config(&config);
            assert_eq!(
                sample_config.n_container_samples,
                SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES
            );
            assert_eq!(
                sample_config.n_focused_samples,
                SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES
            );
            assert_eq!(
                sample_config.n_coord_descents,
                SPARROW_PARITY_COORD_DESCENTS
            );
            assert_eq!(SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT, 200);
            assert_eq!(SPARROW_PARITY_STRIKE_LIMIT, 3);
        }

        #[test]
        fn strict_explore_uses_biased_pool_restore_not_seed_modulo() {
            let optimizer = SparrowOptimizer::new(cfg(CollisionBackendKind::Cde));
            let mut rng = DeterministicRng::new(0x5150);
            let selected = optimizer.select_biased_pool_index(8, &mut rng);
            assert!(selected < 8);
            assert_eq!(SPARROW_PARITY_SOLUTION_POOL_STDDEV, 0.25);
        }

        #[test]
        fn strict_disruption_selects_random_large_item_pair_not_always_top_two() {
            let parts = vec![
                make_part("A", 80.0, 20.0, 1),
                make_part("B", 30.0, 30.0, 1),
                make_part("C", 10.0, 10.0, 1),
                make_part("D", 10.0, 10.0, 1),
            ];
            let stocks = vec![make_stock("S", 240.0, 120.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            let layout = SparrowLayout {
                placements: vec![
                    pl(0, 0.0, 0.0),
                    pl(1, 90.0, 0.0),
                    pl(2, 130.0, 0.0),
                    pl(3, 150.0, 0.0),
                ],
            };
            let mut diag = SparrowDiagnostics::default();
            let state =
                SparrowState::new_with_diag(layout, &problem.instances, &sheets, &mut diag);
            let optimizer = SparrowOptimizer::new(problem.config.clone());
            let mut saw_non_top_two = false;
            for seed in 1..100 {
                let mut rng = DeterministicRng::new(seed);
                if let Some((a, b)) =
                    optimizer.select_large_item_swap_pair(&state, &problem.instances, &mut rng)
                {
                    let mut pair = [a, b];
                    pair.sort();
                    if pair != [0, 1] {
                        saw_non_top_two = true;
                        break;
                    }
                }
            }
            assert!(saw_non_top_two);
        }

        #[test]
        fn fixed_sheet_extensions_are_documented_after_upstream_swap() {
            let parts = vec![make_part("P", 50.0, 50.0, 3)];
            let stocks = vec![make_stock("S", 50.0, 50.0, 2)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let problem = SparrowProblem::from_solver_input(
                &parts,
                &sheets,
                &ctx(),
                vec![],
                cfg(CollisionBackendKind::Cde),
            )
            .expect("problem");
            assert_eq!(problem.container.sheets.len(), 2);
            let lbf_result = LBFBuilder::new(&problem).construct();
            assert!(
                !lbf_result.unresolved.is_empty(),
                "fixed sheets cannot be widened; unresolved items stay explicit for separator/bootstrap"
            );
        }
    }
}
