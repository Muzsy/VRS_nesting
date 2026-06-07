# Run prompt — SGH-Q30 local Sparrow search/CDE profiler module

You are working in the VRS_nesting repo.

Execute exactly this task:

- Canvas: `canvases/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q30_local_sparrow_search_profiler_module.yaml`
- Checklist: `codex/codex_checklist/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`
- Report: `codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`

Hard rules:

1. Read `AGENTS.md`, `docs/codex/yaml_schema.md`, and `docs/codex/report_standard.md` first.
2. Follow the YAML outputs rule. Do not edit files not listed in the active step outputs.
3. This is a measurement/instrumentation task, not an optimization task.
4. Do not run or compare upstream Sparrow in Q30.
5. Do not change solver semantics, GLS, worker ordering, sample budgets, touching policy, compression, LBF behavior, or search acceptance logic.
6. Add a reusable Rust profiling module; do not scatter ad-hoc print/debug timers only.
7. The profiler must be explicit-flagged, preferably `SGH_Q30_SEARCH_PROFILE=1`.
8. The main target is to break down the Q29 `other_unaccounted` search cost.
9. Required LV8/dense measurement must use the current local `sparrow_cde` solver only.

Required measured fields include at minimum:

```text
sample_generation_ms
best_samples_insert_dedup_ms
coord_descent_total_ms
evaluate_sample_calls
evaluate_sample_total_ms
evaluator_orchestration_ms
rng_shuffle_sample_loop_ms
rng_shuffle_or_sample_loop_count
per_candidate_avg_ms
per_evaluate_sample_avg_ms
per_search_avg_ms
```

Required final commands:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
python3 scripts/profile_sgh_q30_local_search_breakdown.py
python3 scripts/smoke_sgh_q30_local_search_profiler_module.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md
```

The final report must include:

```md
## Final answer — mi viszi el az időt?

1. A medium case fő költségei
2. Az LV8 subset fő költségei
3. A dense191 fő költségei
4. Mi maradt other_unaccounted és miért
5. Melyik következő optimalizációs irányt indokolja a mérés, de optimalizáció NEM történt ebben a taskban
```
