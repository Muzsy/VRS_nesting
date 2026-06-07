# Codex checklist — sgh_q30_local_sparrow_search_profiler_module

## Kötelező workflow

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/yaml_schema.md`
- [x] Elolvastam: `docs/codex/report_standard.md`
- [x] Canvas pontos: `canvases/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`
- [x] Goal YAML pontos: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q30_local_sparrow_search_profiler_module.yaml`
- [x] A task elején rögzítettem a `git status --short` állapotot.
- [x] Átnéztem a Q29 local profiler artifactokat és reportot.
- [x] Nem futtattam upstream Sparrow A/B mérést, mert Q30 kizárólag saját solver profiling.

## Profiling modul

- [x] Létrejött külön Rust profiling modul, nem ad-hoc println/szétszórt hack.
- [x] A modul be van kötve a Sparrow optimizer modulrendszerbe.
- [x] A profiler explicit flag mögött fut: `SGH_Q30_SEARCH_PROFILE=1` vagy dokumentált ekvivalens.
- [x] Default futásban a solver szemantikája nem változik.
- [x] A modul tartalmaz strukturált snapshot/export adatot.
- [x] A report leírja, hogyan lehet később run artifactba / admin felületre továbbítani.

## Kötelező mérőpontok

- [x] Mérve: `sample_generation_ms`.
- [x] Mérve: `BestSamples` insert/dedup idő (`best_samples_insert_dedup_ms`).
- [x] Mérve: `best_samples_insert_attempts`, `best_samples_inserted`, `best_samples_dedup_rejects`.
- [x] Mérve: `coord_descent_total_ms`.
- [x] Mérve: `coord_descent_runs`, `coord_descent_steps`.
- [x] Mérve: `evaluate_sample_calls`.
- [x] Mérve: `evaluate_sample_total_ms`.
- [x] Mérve: `evaluator_orchestration_ms`.
- [x] Mérve: `rng_shuffle_sample_loop_ms` és/vagy indokolt sample-loop overhead.
- [x] Mérve: `rng_shuffle_or_sample_loop_count`.
- [x] Mérve: `per_candidate_avg_ms`.
- [x] Mérve: `per_evaluate_sample_avg_ms`.
- [x] Mérve: `per_search_avg_ms`.
- [x] Megmaradt és szerepel: `candidate_transform_prepare_ms`.
- [x] Megmaradt és szerepel: `cde_query_collect_ms`.
- [x] Megmaradt és szerepel: `specialized_pipeline_ms`.
- [x] Megmaradt és szerepel: `hazard_loss_ms`.
- [x] Megmaradt és szerepel: `boundary_check_ms`.
- [x] Megmaradt és szerepel: `session_build_ms`.
- [x] Megmaradt és szerepel: `deregister_reregister_ms`.
- [x] Megmaradt és szerepel: `broadphase_reject_count`.
- [x] Megmaradt és szerepel: `early_termination_count`.
- [x] Számolt: `other_unaccounted_ms`.
- [x] Szerepel: `timing_accounting_mode` és magyarázat.

## Mérési futások

- [x] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` PASS.
- [x] `python3 scripts/profile_sgh_q30_local_search_breakdown.py` PASS.
- [x] Medium sanity case lefutott.
- [x] LV8-derived subset case lefutott.
- [x] Dense191 LV8 case lefutott, vagy konkrét, reprodukálható skipped_reason szerepel.
- [x] Full276 optional case futott vagy indokoltan skipped, és nem acceptance gate.
- [x] Létrejött: `artifacts/benchmarks/sgh_q30/local_search_profile_summary.json`.
- [x] Létrejött: `artifacts/benchmarks/sgh_q30/local_search_profile_report.md`.
- [x] Létrejöttek az input snapshotok az `artifacts/benchmarks/sgh_q30/inputs/` alatt.

## Smoke + quality gate

- [x] `python3 scripts/smoke_sgh_q30_local_search_profiler_module.py` PASS (246/246).
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS (464 tests).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md` PASS.
- [x] AUTO_VERIFY blokk frissült.
- [x] DoD → Evidence Matrix teljes.

## Tiltások ellenőrzése

- [x] Nem vezettem be compressiont.
- [x] Nem módosítottam strict touching policy szemantikát.
- [x] Nem módosítottam sample budgetet.
- [x] Nem módosítottam worker orderingot.
- [x] Nem módosítottam GLS-t.
- [x] Nem módosítottam search acceptance logikát.
- [x] Nem optimalizáltam a solver algoritmusát; csak mérést/instrumentációt adtam hozzá.
- [x] Nem állítottam upstream összehasonlítást Q30-ban.

## Végső válasz a reportban

- [x] Medium case: top költségek és other_unaccounted arány.
- [x] LV8 subset: top költségek és other_unaccounted arány (82.6%).
- [x] Dense191: top költségek és other_unaccounted arány (79.4% — Q29 80.1% megerősítve).
- [x] Pontos következtetés: mi viszi el az időt.
- [x] Ha maradt nagy other_unaccounted, megvan a következő mérőpont helye és oka.
