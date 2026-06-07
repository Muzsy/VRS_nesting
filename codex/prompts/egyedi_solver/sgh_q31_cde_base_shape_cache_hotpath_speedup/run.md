# Run prompt — SGH-Q31 CDE base-shape cache hot-path speedup

Olvasd el és hajtsd végre pontosan:

1. `AGENTS.md`
2. `docs/codex/yaml_schema.md`
3. `docs/codex/report_standard.md`
4. `canvases/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md`
5. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q31_cde_base_shape_cache_hotpath_speedup.yaml`
6. `codex/codex_checklist/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md`
7. Q30-R1 artefaktumok:
   - `artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_summary.json`
   - `artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_report.md`

## Feladat

A Q30-R1 mérés kimutatta, hogy dense191-en a search-idő döntő része `prepare_base_shape_native` ismételt futása. Ezt ne mikrotuningold, hanem vedd ki a hot pathból part-level `CdeBaseShape` cache-sel.

Kötelező cél:

```text
SparrowProblem::from_solver_input
  -> unique part id / geometry szerint CdeBaseShape cache
  -> SPInstance { base_shape: Rc<CdeBaseShape>, ... }

sample/search.rs
  -> inst.base_shape használata
  -> nincs prepare_base_shape_native(&inst.part)

lbf.rs
  -> inst.base_shape használata
  -> nincs prepare_base_shape_native(&inst.part)

quantify/tracker.rs
  -> transform_base_to_candidate(inst.base_shape, ...)
  -> nincs routine prepare_shape_native(&inst.part, ...)
```

## Szigorú tiltások

Ne módosítsd:

- sample budgeteket;
- worker orderinget;
- GLS / acceptance / touching policy-t;
- compressiont;
- geometry simplificationt / vertex reductiont;
- upstream A/B-t;
- dense191 input méretét úgy, hogy könnyebb legyen.

Tilos PASS-t írni, ha a `prepare_base_shape_native` továbbra is search/LBF/tracker hot pathból fut.

## Kötelező acceptance dense191-en

Q30-R1 baseline:

```text
prepare_base_shape_native_ms ≈ 21433.1 ms
search_total_ms ≈ 27210.4 ms
final_pairs = 80
placed = 191/191
status = partial
```

Q31 PASS feltétel:

```text
placed_count == 191
status in {partial, ok}
final_pairs <= 88
prepare_base_shape_native_hotpath_calls == 0
prepare_base_shape_native_hotpath_ms <= 2143.31
base_shape_cache_misses <= unique_part_count + 2
base_shape_cache_hits >= instance_count - unique_part_count
```

Ha bármelyik nem teljesül: report `PARTIAL` vagy `FAIL`, nem `PASS`.

## Verifikáció

Futtasd:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/profile_sgh_q31_base_shape_cache_speedup.py
python3 scripts/smoke_sgh_q31_cde_base_shape_cache_hotpath_speedup.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md
```

## Report

A report Report Standard v2 szerint készüljön.

Kötelező marker sorok a report végén:

```text
Q31_STATUS: PASS|PARTIAL|FAIL
DENSE191_BASE_SHAPE_HOTPATH_CALLS: <integer>
DENSE191_BASE_SHAPE_HOTPATH_MS: <number>
DENSE191_BASE_SHAPE_CACHE_MISSES: <integer>
DENSE191_BASE_SHAPE_CACHE_HITS: <integer>
DENSE191_PREPARE_BASE_REDUCTION_PCT: <number>%
DENSE191_FINAL_PAIRS: <integer>
NEXT_HOTSPOT: <concrete path::function or NONE>
```

## Végrehajtási megjegyzés

Ez célzott speedup task. Nem általános profiler, nem új solver-port, nem dense191 benchmark-tuning. A helyes eredmény az, hogy ugyanazzal a solver-viselkedéssel a base shape előkészítés nem fut újra minden search/LBF/tracker itemre.
