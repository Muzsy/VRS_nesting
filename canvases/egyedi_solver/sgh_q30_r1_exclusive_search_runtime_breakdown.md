# SGH-Q30-R1 — Exclusive Sparrow search runtime breakdown, no evasion

## 🎯 Cél

A Q30 bevezetett egy újrahasználható `SearchProfiler` modult, de a mérés fő kérdését nem zárta le: a dense LV8 / dense191 futásban a `search_total_ms` kb. 79–83%-a továbbra is `other_unaccounted_ms` maradt. Ez nem elfogadható végállapot.

A Q30-R1 célja **nem optimalizálás**, hanem a Q30 profiler keményítése úgy, hogy exkluzív, kódszintű timing tree-t adjon a saját `sparrow_cde` solverről. A cél: megmondani, hol ég el az idő a dense LV8 futásban.

A task akkor tekinthető késznek, ha a dense191 mérésnél az új exkluzív breakdown **nem hagyhatja névtelenül** a `native_search_placement` / `search_placement` költség döntő részét.

## Előzmény — miért kell javító task

Q30 eredmény dense191-re:

```text
status: partial
placed: 191/191
final_pairs: 80
runtime_ms: ~202 907
search_total_ms: ~26 176
other_unaccounted_ms: ~20 784 = 79.4% of search_total
```

Q30 hasznos volt, mert bizonyította:

```text
session_build_ms ≈ 0
deregister/reregister elhanyagolható
sample_generation elhanyagolható
BestSamples insert/dedup elhanyagolható
candidate_transform kicsi
boundary_check kicsi
CDE collect kb. 19% search_total
```

De Q30 nem bontotta fel:

```text
search_placement loop infrastructure
worker/separator szintű költségek
coord_descent exkluzív overhead
evaluate_sample orchestration pontos részei
BestSamples::best / clone / iteration költség
base-shape prepare és sheet setup költség
full solver runtime vs search_total különbség
```

Ezért Q30-R1 nem adhat PASS-t pusztán új mezőkre. **A lényeg az exkluzív költségfa.**

## Nem-célok — tilos kikerülni a lényeget

- Nem cél gyorsítás.
- Nem cél upstream Sparrow A/B.
- Nem cél sample budget, worker ordering, GLS, touching policy, CDE semantics, strict policy, LBF, exploration vagy acceptance logika módosítása.
- Nem cél compression bevezetése.
- Nem cél dense191 `ok` kikényszerítése.
- Nem cél a Q30 mezők kozmetikázása vagy átnevezése.
- Tilos alias mezőket használni bizonyítékként, pl. `rng_shuffle_sample_loop_ms = sample_generation_ms`.
- Tilos nested mezőket exkluzívként jelenteni.
- Tilos PASS-t írni, ha a dense191 `search_unaccounted_ratio_pct` nagy marad.
- Tilos `other_unaccounted` magyarázatként általános listát adni mérés nélkül.
- Tilos a smoke validátort lazítani a feladat végén.

## Kemény acceptance szabály

A Q30-R1 **csak akkor PASS**, ha a dense191 case-ben:

```text
search_timing_accounting_mode == "exclusive"
search_accounted_ms <= search_total_ms * 1.10
search_accounted_ms >= search_total_ms * 0.85
search_unaccounted_ratio_pct <= 15.0
```

Ha ez nem teljesül, a task report státusza **FAIL** vagy **PARTIAL**, nem PASS.

Továbbá a total solver runtime szinten is kötelező bontás:

```text
total_runtime_accounting_mode == "exclusive"
total_runtime_accounted_ms >= total_solver_runtime_ms * 0.75
```

A teljes solver runtime bontásnál maradhat több unaccounted, de pontosan meg kell nevezni, hogy worker/separator/final-validation/IO/adapter mely szintjén maradt.

## Profiling architektúra — Q30 modul bővítése, nem új ad-hoc mérés

A meglévő modult kell bővíteni:

```text
rust/vrs_solver/src/optimizer/sparrow/profile.rs
```

Elvárás:

- legyen továbbra is explicit flag mögött, például `SGH_Q30_SEARCH_PROFILE=1`, vagy ha Q30-R1-hez külön flag kell: `SGH_Q30_R1_EXCLUSIVE_PROFILE=1`;
- default futásban ne módosítsa a solver outputot és ne vigyen jelentős overheadet;
- legyen strukturált exkluzív scope API;
- a modul tartalmazzon `finalize()` vagy ekvivalens függvényt, amelyet a production solve path ténylegesen meghív;
- a derived mezőket Rust oldalon is számolja, ne csak Python runnerben;
- legyen később admin/observability kimenetre köthető.

Javasolt fogalmak:

```rust
SearchProfiler
SearchProfileScope
ExclusiveTimer
SearchProfileSnapshot
SearchProfileCaseSummary
SearchTimingTree
RuntimeTimingTree
```

## Kötelező exkluzív timing tree — total solver runtime

A teljes saját solver futásnál legalább ezeket kell mérni:

```text
total_solver_runtime_ms
adapter_solve_total_ms
sparrow_optimizer_solve_total_ms
seed_lbf_total_ms
separator_total_ms
separator_iteration_total_ms
worker_competition_total_ms
worker_pass_total_ms
exploration_total_ms
tracker_initial_build_ms
tracker_final_validation_ms
output_mapping_ms
other_solver_unaccounted_ms
other_solver_unaccounted_ratio_pct
```

A cél: lássuk, miért sokkal nagyobb a dense191 teljes runtime, mint a `search_total_ms`.

## Kötelező exkluzív timing tree — native_search_placement / search_placement

A Q30-R1 fő célja a `search_total_ms` felbontása. Legalább ezek kellenek:

```text
native_search_placement_total_ms
native_search_setup_ms
prepare_base_shape_native_ms
fixed_shapes_clone_ms
sheet_order_build_ms
sheet_loop_total_ms
sheet_loop_overhead_ms
global_loop_total_ms
focused_loop_total_ms
sample_generation_ms
sample_acceptance_loop_ms
best_samples_insert_dedup_ms
best_samples_best_ms
best_samples_clone_ms
coord_descent_total_ms
coord_descent_eval_ms
coord_descent_ask_ms
coord_descent_tell_ms
coord_descent_overhead_ms
evaluate_sample_total_ms
evaluate_sample_exclusive_overhead_ms
evaluator_orchestration_ms
candidate_transform_prepare_ms
cde_query_collect_ms
specialized_pipeline_ms
hazard_loss_ms
boundary_check_ms
broadphase_reject_ms
session_build_ms
deregister_reregister_ms
deadline_check_ms
rng_shuffle_ms
rng_sample_generation_ms
search_unaccounted_ms
search_unaccounted_ratio_pct
```

Ha egy mező nem létező útvonalon nem érintett, legyen `0`. Ha technikailag nem mérhető, legyen `not_available`, de dense191 PASS csak akkor adható, ha a fő search költségfa legalább 85%-ban accounted.

## Kötelező számlálók

Legalább:

```text
native_search_calls
evaluate_sample_calls
evaluate_sample_calls_from_global
evaluate_sample_calls_from_focused
evaluate_sample_calls_from_coord_descent
candidates_evaluated
global_samples_generated
focused_samples_generated
best_samples_insert_attempts
best_samples_inserted
best_samples_dedup_rejects
best_samples_best_calls
best_samples_clone_calls
coord_descent_runs
coord_descent_steps
coord_descent_ask_calls
coord_descent_tell_calls
deadline_checks
sheet_loop_iterations
worker_passes
worker_candidates_evaluated
worker_candidates_accepted
early_termination_count
broadphase_reject_count
```

## Kötelező mérési inputok

Csak saját solver. Nincs upstream.

Kötelező case-ek:

1. **medium sanity**
   - gyors profil validáció;
   - ha seedingből megoldódik és `search_total_ms=0`, reportban külön jelölni.

2. **LV8-derived subset**
   - legalább a Q29/Q30 67 instance LV8 subset vagy hasonló;
   - cél: real geometry, még nem dense.

3. **dense191 LV8**
   - preferált input:

```text
rust/vrs_solver/tests/fixtures/sgh_q28_dense191_benchmark/dense_191_lv8_derived.json
```

   - ez a fő acceptance case;
   - nem kell `ok` státusz;
   - `partial` elfogadható, de teljes profiling kell.

4. **full276 LV8 diagnostic**
   - ha 300s vagy beállított max budget alatt futtatható, futtasd;
   - ha nem futtatható, ne kamu skip legyen: legyen `attempted=false`, `skipped_reason`, és a report magyarázza meg.
   - nem acceptance gate.

## Artifactok

Új Q30-R1 artifact könyvtár:

```text
artifacts/benchmarks/sgh_q30_r1/
```

Kötelező fájlok:

```text
artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_summary.json
artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_report.md
artifacts/benchmarks/sgh_q30_r1/inputs/medium.json
artifacts/benchmarks/sgh_q30_r1/inputs/lv8_subset.json
artifacts/benchmarks/sgh_q30_r1/inputs/dense191.json
artifacts/benchmarks/sgh_q30_r1/inputs/full276_optional.json
```

## Summary JSON minimális séma

```json
{
  "task": "sgh_q30_r1_exclusive_search_runtime_breakdown",
  "status": "PASS|PARTIAL|FAIL",
  "profile_flag": "SGH_Q30_R1_EXCLUSIVE_PROFILE=1",
  "timing_accounting_mode": "exclusive",
  "non_goals_preserved": {
    "no_solver_optimization": true,
    "no_upstream_ab": true,
    "no_compression": true,
    "no_sample_budget_change": true,
    "no_acceptance_change": true
  },
  "cases": [
    {
      "case_id": "dense191",
      "status": "partial|ok|timeout|error",
      "runtime_ms": 0.0,
      "placed_count": 191,
      "final_pairs": 0,
      "iterations": 0,
      "search_accounting": {
        "mode": "exclusive",
        "search_total_ms": 0.0,
        "accounted_ms": 0.0,
        "unaccounted_ms": 0.0,
        "unaccounted_ratio_pct": 0.0,
        "buckets": {
          "native_search_setup_ms": 0.0,
          "prepare_base_shape_native_ms": 0.0,
          "fixed_shapes_clone_ms": 0.0,
          "sheet_order_build_ms": 0.0,
          "global_loop_total_ms": 0.0,
          "focused_loop_total_ms": 0.0,
          "coord_descent_overhead_ms": 0.0,
          "evaluate_sample_total_ms": 0.0,
          "best_samples_best_ms": 0.0,
          "best_samples_clone_ms": 0.0,
          "deadline_check_ms": 0.0,
          "rng_shuffle_ms": 0.0
        }
      },
      "runtime_accounting": {
        "mode": "exclusive",
        "total_solver_runtime_ms": 0.0,
        "accounted_ms": 0.0,
        "unaccounted_ms": 0.0,
        "unaccounted_ratio_pct": 0.0,
        "buckets": {
          "sparrow_optimizer_solve_total_ms": 0.0,
          "seed_lbf_total_ms": 0.0,
          "separator_total_ms": 0.0,
          "worker_competition_total_ms": 0.0,
          "tracker_final_validation_ms": 0.0,
          "output_mapping_ms": 0.0
        }
      },
      "counters": {
        "native_search_calls": 0,
        "evaluate_sample_calls": 0,
        "coord_descent_runs": 0,
        "worker_passes": 0
      },
      "top_exclusive_costs": [
        {"bucket": "...", "ms": 0.0, "pct_of_search": 0.0}
      ]
    }
  ]
}
```

## Markdown report minimális tartalom

A reportnak magyarul vagy angolul, de egyértelműen tartalmaznia kell:

1. Q30 probléma rövid összefoglalása.
2. Milyen új exkluzív mérőpontok kerültek be.
3. Case-enként táblázat:
   - runtime,
   - search total,
   - accounted/unaccounted,
   - top 10 exkluzív bucket,
   - számlálók.
4. Dense191 külön szakasz:
   - pontos válasz: mi viszi el a `search_total_ms`-t;
   - pontos válasz: mi viszi el a teljes runtime-ot;
   - ha maradt `unaccounted`, miért és melyik konkrét függvényben kell tovább mérni.
5. Explicit kijelentés:
   - `Q30_R1_STATUS: PASS|PARTIAL|FAIL`
   - `DENSE191_SEARCH_UNACCOUNTED_RATIO: x%`
   - `DENSE191_RUNTIME_UNACCOUNTED_RATIO: x%`

## Smoke validator

Hozz létre / frissíts:

```text
scripts/smoke_sgh_q30_r1_exclusive_search_runtime_breakdown.py
```

Ez legyen kemény validator, ne mérés. Bukjon, ha:

- nincs summary JSON;
- nincs dense191 case;
- `timing_accounting_mode != exclusive`;
- dense191 `search_unaccounted_ratio_pct > 15`;
- a required bucketek hiányoznak;
- a régi Q30 alias megoldás él tovább (`rng_shuffle_sample_loop_ms == sample_generation_ms` és nincs külön `rng_sample_generation_ms` / `rng_shuffle_ms` bontás);
- a report PASS-t ír, miközben a fenti feltételek nem teljesülnek;
- `SearchProfiler::finalize()` vagy megfelelő Rust-side finalizálás nincs ténylegesen meghívva;
- a task közben sample budget / acceptance / compression / worker ordering módosult.

## Verifikáció

Kötelező parancsok:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
python3 scripts/profile_sgh_q30_r1_exclusive_search_runtime_breakdown.py
python3 scripts/smoke_sgh_q30_r1_exclusive_search_runtime_breakdown.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md
```

Ha a dense191 futás túl lassú, nem lehet egyszerűen kihagyni. A futási budgetet dokumentálni kell, és legalább egy valós dense191 profiled run artifactnak létre kell jönnie, még `partial` státusszal is.

## Kimeneti verdikt

A Codex report végén kötelező:

```text
Q30_R1_STATUS: PASS|PARTIAL|FAIL
DENSE191_SEARCH_UNACCOUNTED_RATIO: <number>%
DENSE191_RUNTIME_UNACCOUNTED_RATIO: <number>%
NEXT_HOTSPOT: <concrete function/path>
```

Ha `NEXT_HOTSPOT` általános szöveg, például „search loop overhead”, a task nem tekinthető késznek. Konkrét fájl + függvény kell.
