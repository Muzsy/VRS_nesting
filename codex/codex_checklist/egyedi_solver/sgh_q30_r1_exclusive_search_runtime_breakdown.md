# Codex checklist — sgh_q30_r1_exclusive_search_runtime_breakdown

## Kötelező workflow

- [ ] Elolvastam: `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`.
- [ ] Rögzítettem a task eleji `git status --short` állapotot.
- [ ] Elolvastam a Q30 reportot és artifactokat.
- [ ] Rögzítettem, hogy Q30 dense191 `other_unaccounted` kb. 79% volt, ezért Q30-R1 PASS csak exkluzív bontással adható.
- [ ] Nem futtattam upstream Sparrow A/B-t; ez nem Q30-R1 scope.

## Nem-célok megőrzése

- [ ] Nem módosítottam sample budgetet.
- [ ] Nem módosítottam worker orderingot.
- [ ] Nem módosítottam GLS / weight / acceptance logikát.
- [ ] Nem módosítottam touching policyt vagy CDE semanticsot.
- [ ] Nem vezettem be compressiont.
- [ ] Nem próbáltam dense191 `ok` státuszt kikényszeríteni.
- [ ] Nem lazítottam Q26/Q28/Q29/Q30 gate-et.

## Profiling modul

- [ ] A meglévő `rust/vrs_solver/src/optimizer/sparrow/profile.rs` bővült, nem új ad-hoc mérőrendszer készült.
- [ ] Van exkluzív scope/timer API.
- [ ] Van Rust-side snapshot/finalize.
- [ ] A finalize vagy ekvivalens lezárás ténylegesen meghívódik a solve pathon.
- [ ] A profiler explicit flag mögött van (`SGH_Q30_R1_EXCLUSIVE_PROFILE=1` vagy dokumentált kompatibilis mód).
- [ ] Default futásban nincs solver-szemantikai változás.

## Total runtime exkluzív bontás

- [ ] `total_solver_runtime_ms` mérve.
- [ ] `adapter_solve_total_ms` vagy ekvivalens mérve.
- [ ] `sparrow_optimizer_solve_total_ms` mérve.
- [ ] `seed_lbf_total_ms` mérve.
- [ ] `separator_total_ms` mérve.
- [ ] `separator_iteration_total_ms` mérve.
- [ ] `worker_competition_total_ms` mérve.
- [ ] `worker_pass_total_ms` mérve.
- [ ] `tracker_initial_build_ms` mérve.
- [ ] `tracker_final_validation_ms` mérve.
- [ ] `output_mapping_ms` mérve.
- [ ] dense191 total runtime accounted ratio >= 75%, vagy a report nem PASS.

## Search exkluzív bontás

- [ ] `native_search_placement_total_ms` mérve.
- [ ] `native_search_setup_ms` mérve.
- [ ] `prepare_base_shape_native_ms` mérve.
- [ ] `fixed_shapes_clone_ms` mérve.
- [ ] `sheet_order_build_ms` mérve.
- [ ] `sheet_loop_total_ms` mérve.
- [ ] `sheet_loop_overhead_ms` mérve.
- [ ] `global_loop_total_ms` mérve.
- [ ] `focused_loop_total_ms` mérve.
- [ ] `sample_acceptance_loop_ms` mérve.
- [ ] `best_samples_best_ms` mérve.
- [ ] `best_samples_clone_ms` mérve.
- [ ] `deadline_check_ms` mérve.
- [ ] `rng_shuffle_ms` külön mérve, nem alias.
- [ ] `rng_sample_generation_ms` külön mérve.
- [ ] `search_unaccounted_ms` és `search_unaccounted_ratio_pct` Rust-side vagy summary szinten számolva.
- [ ] dense191 `search_unaccounted_ratio_pct <= 15%`, vagy a report nem PASS.

## Coord descent / evaluator bontás

- [ ] `coord_descent_eval_ms` mérve.
- [ ] `coord_descent_ask_ms` mérve.
- [ ] `coord_descent_tell_ms` mérve.
- [ ] `coord_descent_overhead_ms` mérve.
- [ ] `evaluate_sample_total_ms` mérve.
- [ ] `evaluate_sample_exclusive_overhead_ms` mérve.
- [ ] `evaluator_orchestration_ms` mérve.
- [ ] `candidate_transform_prepare_ms` mérve.
- [ ] `cde_query_collect_ms` mérve.
- [ ] `specialized_pipeline_ms` mérve vagy explicit nestedként jelölve.
- [ ] `hazard_loss_ms` mérve vagy konkrétan indokolt not_available.
- [ ] `boundary_check_ms` mérve.
- [ ] `broadphase_reject_ms` mérve vagy 0 indokolt.

## Counters

- [ ] `native_search_calls`.
- [ ] `evaluate_sample_calls`.
- [ ] `evaluate_sample_calls_from_global`.
- [ ] `evaluate_sample_calls_from_focused`.
- [ ] `evaluate_sample_calls_from_coord_descent`.
- [ ] `candidates_evaluated`.
- [ ] `global_samples_generated`.
- [ ] `focused_samples_generated`.
- [ ] `best_samples_insert_attempts`.
- [ ] `best_samples_inserted`.
- [ ] `best_samples_dedup_rejects`.
- [ ] `best_samples_best_calls`.
- [ ] `best_samples_clone_calls`.
- [ ] `coord_descent_runs`.
- [ ] `coord_descent_steps`.
- [ ] `deadline_checks`.
- [ ] `sheet_loop_iterations`.
- [ ] `worker_passes`.
- [ ] `worker_candidates_evaluated`.
- [ ] `worker_candidates_accepted`.

## Artifacts

- [ ] `artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_summary.json` létrejött.
- [ ] `artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_report.md` létrejött.
- [ ] `inputs/medium.json` snapshot létrejött.
- [ ] `inputs/lv8_subset.json` snapshot létrejött.
- [ ] `inputs/dense191.json` snapshot létrejött.
- [ ] `inputs/full276_optional.json` létrejött vagy dokumentált skipped/attempted státusz van.
- [ ] Dense191 case jelen van és profile-olt.
- [ ] Summary `timing_accounting_mode == "exclusive"`.
- [ ] Summary `status` csak akkor PASS, ha a hard gates teljesülnek.

## Smoke / verifikáció

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` PASS.
- [ ] `python3 scripts/profile_sgh_q30_r1_exclusive_search_runtime_breakdown.py` lefutott.
- [ ] `python3 scripts/smoke_sgh_q30_r1_exclusive_search_runtime_breakdown.py` PASS, vagy ha nem, report nem PASS.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md` lefutott.

## Végső marker

- [ ] Report vége tartalmazza: `Q30_R1_STATUS: PASS|PARTIAL|FAIL`.
- [ ] Report vége tartalmazza: `DENSE191_SEARCH_UNACCOUNTED_RATIO: <number>%`.
- [ ] Report vége tartalmazza: `DENSE191_RUNTIME_UNACCOUNTED_RATIO: <number>%`.
- [ ] Report vége tartalmazza: `NEXT_HOTSPOT: <concrete path::function>`.
- [ ] `NEXT_HOTSPOT` nem általános szöveg.
