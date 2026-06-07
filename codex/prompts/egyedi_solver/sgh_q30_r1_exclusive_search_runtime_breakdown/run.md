# Run prompt — SGH-Q30-R1 exclusive search runtime breakdown

Feladat: hajtsd végre a `sgh_q30_r1_exclusive_search_runtime_breakdown` canvas és YAML alapján a Q30 profiler javító taskot.

## Kötelező bemenetek

Olvasd el sorrendben:

1. `AGENTS.md`
2. `docs/codex/yaml_schema.md`
3. `docs/codex/report_standard.md`
4. `canvases/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md`
5. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q30_r1_exclusive_search_runtime_breakdown.yaml`
6. Q30 előzmény:
   - `codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`
   - `artifacts/benchmarks/sgh_q30/local_search_profile_summary.json`
   - `artifacts/benchmarks/sgh_q30/local_search_profile_report.md`

## Kemény cél

Q30 után dense191-nél a `search_total_ms` kb. 79%-a `other_unaccounted` maradt. Ezt kell exkluzív kódszintű timing tree-re bontani.

Nem elég új mezőket hozzáadni. Nem elég nested mezőkkel vagy aliasokkal PASS-t írni.

A task csak akkor PASS, ha dense191-re:

```text
search_timing_accounting_mode == "exclusive"
search_unaccounted_ratio_pct <= 15.0
total_runtime_accounted_ratio_pct >= 75.0
```

Ha nem teljesül, a report státusza legyen PARTIAL vagy FAIL.

## Szigorú tiltások

Ne módosíts:

- solver search/acceptance logikát,
- sample budgetet,
- worker orderingot,
- GLS-t,
- touching policyt,
- CDE semanticsot,
- compressiont,
- dense191 acceptance elvárásokat.

Ne futtass upstream Sparrow A/B-t. Ez csak saját solver profiling task.

## Kötelező implementáció

A meglévő `rust/vrs_solver/src/optimizer/sparrow/profile.rs` modult bővítsd exkluzív scope/timer API-val. Ne hozz létre szétszórt ad-hoc timer kódot.

Instrumentáld legalább:

- `adapter.rs`
- `optimizer.rs`
- `separator.rs`
- `worker.rs`
- `lbf.rs`
- `explore.rs`
- `sample/search.rs`
- `sample/best_samples.rs`
- `sample/coord_descent.rs`
- `sample/uniform_sampler.rs`, ha releváns
- `eval/sep_evaluator.rs`
- `eval/specialized_cde_pipeline.rs`
- `quantify/tracker.rs`
- `io.rs`
- `diagnostics.rs`

## Kötelező artifactok

Hozd létre:

```text
artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_summary.json
artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_report.md
artifacts/benchmarks/sgh_q30_r1/inputs/medium.json
artifacts/benchmarks/sgh_q30_r1/inputs/lv8_subset.json
artifacts/benchmarks/sgh_q30_r1/inputs/dense191.json
artifacts/benchmarks/sgh_q30_r1/inputs/full276_optional.json
```

## Kötelező scriptek

Hozd létre:

```text
scripts/profile_sgh_q30_r1_exclusive_search_runtime_breakdown.py
scripts/smoke_sgh_q30_r1_exclusive_search_runtime_breakdown.py
```

A smoke validator legyen kemény. Ha a dense191 search unaccounted ratio > 15%, bukjon.

## Kötelező futtatás

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
python3 scripts/profile_sgh_q30_r1_exclusive_search_runtime_breakdown.py
python3 scripts/smoke_sgh_q30_r1_exclusive_search_runtime_breakdown.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md
```

## Report vége — kötelező marker

A report végén pontosan legyen:

```text
Q30_R1_STATUS: PASS|PARTIAL|FAIL
DENSE191_SEARCH_UNACCOUNTED_RATIO: <number>%
DENSE191_RUNTIME_UNACCOUNTED_RATIO: <number>%
NEXT_HOTSPOT: <concrete path::function>
```

Ha `NEXT_HOTSPOT` nem konkrét fájl+függvény, a task nem kész.
