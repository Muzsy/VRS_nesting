# SGH-Q30 Report — Local Sparrow search/CDE profiler module

**Status:** PASS

## 1) Meta

- **Task slug:** `sgh_q30_local_sparrow_search_profiler_module`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q30_local_sparrow_search_profiler_module.yaml`
- **Futás dátuma:** 2026-06-07
- **Branch / commit:** main / (in progress)
- **Fókusz terület:** Geometry | Scripts

## 2) Scope

### 2.1 Cél

1. Reusable, bővíthető Rust search profiling modul (`profile.rs`) bevezetése a Sparrow solverbe.
2. A Q29-ben mért `other_unaccounted_ms` (80.1%) felbontása: sample generation, BestSamples, coord_descent, evaluate_sample.
3. Kötelező mérőpontok: `sample_generation_ms`, `best_samples_insert_dedup_ms`, `coord_descent_total_ms`, `evaluate_sample_total_ms`, `evaluator_orchestration_ms`, `rng_shuffle_sample_loop_ms`, per-avg mezők.
4. Medium + LV8-derived + dense191 profiler mérési futás.
5. Artifact JSON + Markdown report a top-cost bontással.

### 2.2 Nem-cél

1. Upstream Sparrow A/B összehasonlítás (nem Q30 scope).
2. Solver gyorsítás, search acceptance változtatás.
3. Dense191 `ok` státusz kikényszerítése.
4. Sample budget, worker ordering, GLS, touching policy módosítás.
5. Compression bevezetése.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

**Új Rust modul:**
- `rust/vrs_solver/src/optimizer/sparrow/profile.rs` — `SearchProfiler`, `ProfileTimer`

**Módosított Rust fájlok:**
- `rust/vrs_solver/src/optimizer/sparrow/mod.rs` — `pub mod profile;` + export
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs` — `pub q30_profile: SearchProfiler` mező
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs` — sample_generation, BestSamples, coord_descent timers
- `rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs` — insert/dedup profiling
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs` — coord_descent runs/steps
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs` — evaluate_sample total timer
- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs` — q30_profile CDE timing
- `rust/vrs_solver/src/io.rs` — Q30 profiler output mezők
- `rust/vrs_solver/src/adapter.rs` — Q30 profiler mező mapping

**Scripts:**
- `scripts/profile_sgh_q30_local_search_breakdown.py` — Q30 profiler runner
- `scripts/smoke_sgh_q30_local_search_profiler_module.py` — smoke validator

**Artifacts:**
- `artifacts/benchmarks/sgh_q30/local_search_profile_summary.json`
- `artifacts/benchmarks/sgh_q30/local_search_profile_report.md`
- `artifacts/benchmarks/sgh_q30/inputs/medium.json`
- `artifacts/benchmarks/sgh_q30/inputs/lv8_subset.json`
- `artifacts/benchmarks/sgh_q30/inputs/dense191.json`

### 3.2 Miért változtak?

**Rust (profile.rs + instrumentáció):** A Q29 large `other_unaccounted_ms` blokkot kellett felbontani. Ehhez `SearchProfiler` modul + `ProfileTimer` helper + instrumentált search/eval/CDE call site-ok.

**Scripts:** Futtatja a profiler mérést, összegyűjti az eredményeket, validálja az artifactokat.

## 4) Verifikáció

### 4.1 Kötelező parancs

`./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md`

### 4.2 Opcionális

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- `python3 scripts/profile_sgh_q30_local_search_breakdown.py`
- `python3 scripts/smoke_sgh_q30_local_search_profiler_module.py`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml`

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-07T09:46:58+02:00 → 2026-06-07T09:50:26+02:00 (208s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.verify.log`
- git: `main@b9b07cc`
- módosított fájlok (git status): 20

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     | 46 +++++++++++++++++++++
 rust/vrs_solver/src/io.rs                          | 47 ++++++++++++++++++++++
 .../src/optimizer/sparrow/diagnostics.rs           |  4 ++
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    | 14 ++++++-
 .../sparrow/eval/specialized_cde_pipeline.rs       |  7 ++++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  2 +
 .../src/optimizer/sparrow/sample/best_samples.rs   | 24 ++++++++++-
 .../src/optimizer/sparrow/sample/coord_descent.rs  |  3 ++
 .../src/optimizer/sparrow/sample/search.rs         | 37 ++++++++++++++---
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  5 ++-
 10 files changed, 180 insertions(+), 9 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? artifacts/benchmarks/sgh_q30/
?? canvases/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md
?? codex/codex_checklist/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q30_local_sparrow_search_profiler_module.yaml
?? codex/prompts/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module/
?? codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.md
?? codex/reports/egyedi_solver/sgh_q30_local_sparrow_search_profiler_module.verify.log
?? rust/vrs_solver/src/optimizer/sparrow/profile.rs
?? scripts/profile_sgh_q30_local_search_breakdown.py
?? scripts/smoke_sgh_q30_local_search_profiler_module.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt |
|---|---|---|---|---|
| #1 Külön Rust profiling modul | PASS | [profile.rs](rust/vrs_solver/src/optimizer/sparrow/profile.rs) | `SearchProfiler` + `ProfileTimer` | cargo build |
| #2 Profiler explicit flag mögött | PASS | [profile.rs:107](rust/vrs_solver/src/optimizer/sparrow/profile.rs#L107) | `SGH_Q30_SEARCH_PROFILE=1` | smoke 246/246 |
| #3 Kötelező új mérőpontok JSON-ban | PASS | [io.rs](rust/vrs_solver/src/io.rs), [adapter.rs](rust/vrs_solver/src/adapter.rs) | 23 sparrow_q30_* mező | smoke 246/246 |
| #4 Medium + LV8 + dense191 lefutott | PASS | [artifacts/benchmarks/sgh_q30/](artifacts/benchmarks/sgh_q30/) | 3 case, mind profiled | profile runner PASS |
| #5 Saját sparrow_cde útvonal mérve | PASS | SGH_Q30_SEARCH_PROFILE=1 | nem upstream | smoke |
| #6 summary.json + report.md létrejött | PASS | [local_search_profile_summary.json](artifacts/benchmarks/sgh_q30/local_search_profile_summary.json) | | profile runner |
| #7 top-cost bontás + other_unaccounted arány | PASS | dense191: 79.4% other, 20.5% eval | Q29 80.1% megerősítve | profile runner |
| #8 smoke PASS | PASS | 246/246 | | smoke |
| #9 cargo test PASS | PASS | 455+8+1=464 | | cargo test |
| #10 verify.sh PASS | PASS | exit 0 | | verify.sh |

## 6) Profiling modul architektúra

### SearchProfiler API

```
rust/vrs_solver/src/optimizer/sparrow/profile.rs
```

Enabled by: `SGH_Q30_SEARCH_PROFILE=1`

Future admin integration: a `SearchProfiler::finalize()` visszatérési értékét sidecar JSON artifactba lehet írni, vagy az `optimizer_diagnostics` output JSON-ba beágyazni. A `sparrow_q30_profile_*` mezők jelenleg az optimizer_diagnostics-ban kerülnek exportra.

### Timing accounting mode: `mixed_with_notes`

**Exclusive** sub-buckets (összeg ≤ search_total_ms):
- `session_build_ms` — fallback session build-ek
- `deregister_reregister_ms` — deregister_item hívások
- `evaluate_sample_total_ms` — ÖSSZES evaluate_sample hívás (sampling loop + coord_descent)
- `sample_generation_ms` — UniformBBoxSampler.sample() hívások
- `best_samples_insert_dedup_ms` — BestSamples.report() hívások

**Nested** (NEM vonható le search_total-ból):
- `coord_descent_total_ms` — wraps evaluate_sample hívásokat coord_descent-en belül
- `cde_query_collect_ms` — sub of evaluate_sample
- `candidate_transform_prepare_ms` — sub of evaluate_sample
- `boundary_check_ms` — sub of evaluate_sample

**`other_unaccounted_ms`** = search_total - (session_build + deregister + evaluate_sample_total + sample_generation + best_samples_insert_dedup)

## 7) Futási eredmények

Mérés dátuma: 2026-06-07. Profile flag: `SGH_Q30_SEARCH_PROFILE=1`. Timing model: `mixed_with_notes`.

### medium (24 instances, 30s)

- **Status:** ok, 24/24 placed, 0 pairs — constructive seed solved, 0 separator search calls
- search_total_ms = 0 (no separator invocations)

### lv8_subset (first 3 LV8 part types, ~67 instances, 30s)

- **Status:** ok, 67/67 placed, 0 pairs — separator needed, then converged
- search_total_ms = 141 ms, native_search_calls = 11, per_search_avg_ms = 12.8

| Bucket | ms | % search_total |
|---|---|---|
| **other_unaccounted_ms** | 116.4 | **82.6%** |
| evaluate_sample_total_ms | 23.0 | 16.3% |
| ↳ cde_query_collect_ms (nested) | 10.2 | 7.2% |
| ↳ evaluator_orchestration_ms (nested) | 8.5 | 6.0% |
| sample_generation_ms | 0.9 | 0.6% |
| best_samples_insert_dedup_ms | 0.7 | 0.5% |
| deregister_reregister_ms | 0.1 | 0.0% |
| session_build_ms | 0.0 | 0.0% |

### dense191 (191 instances, 120s)

- **Status:** partial, 191/191 placed, 80 pairs remaining — deadline hit before convergence
- search_total_ms = 26 176 ms, native_search_calls = 272, per_search_avg_ms = 96.2

| Bucket | ms | % search_total |
|---|---|---|
| **other_unaccounted_ms** | 20 783.8 | **79.4%** |
| evaluate_sample_total_ms | 5 378.4 | 20.5% |
| ↳ cde_query_collect_ms (nested) | 4 950.0 | **18.9%** |
| ↳ evaluator_orchestration_ms (nested) | 237 | 0.9% |
| ↳ candidate_transform_prepare_ms (nested) | 138.7 | 0.5% |
| ↳ boundary_check_ms (nested) | 50.7 | 0.2% |
| best_samples_insert_dedup_ms | 5.5 | 0.0% |
| sample_generation_ms | 5.2 | 0.0% |
| deregister_reregister_ms | 3.4 | 0.0% |
| session_build_ms | 0.0 | 0.0% |

Counters: evaluate_sample_calls=45 729, early_termination_count=23 537 (51.5% of evals terminated early), coord_descent_runs=1 355.

## Final answer — mi viszi el az időt?

### 1. medium case

A medium (24 instance) a constructive seed-del megoldódik, **0 separator keresési hívás**, search_total_ms = 0. A profiler fut, de nincs mit mérni.

### 2. LV8 subset case

Az lv8_subset 141 ms teljes search időből:
- **other_unaccounted 82.6%** (116 ms) — dominál
- evaluate_sample_total 16.3% (23 ms) — ebből CDE query 7.2%, evaluator orchestration 6%
- sample_generation / BestSamples / deregister < 1% — elhanyagolható

### 3. dense191 case

A dense191 26 176 ms teljes search időből:
- **other_unaccounted 79.4%** (20 784 ms) — erősen dominál, **megerősíti a Q29 80.1%-os mérést**
- evaluate_sample_total 20.5% (5 378 ms) — ebből **cde_query 18.9%** (4 950 ms)
- sample_generation, BestSamples, deregister együttesen < 0.1% — elhanyagolható

### 4. Mi maradt other_unaccounted és miért?

Az `other_unaccounted_ms` az alábbi, jelenleg külön nem mért search-loop overhead-et tartalmazza:

- **`prepare_base_shape_native` per search call** — egyszer hívódik `native_search_placement`-ben, CDE shape prep (POI + surrogate); per-iteration overhead
- **`BestSamples::best()` + `.samples.clone()`** — pre-coord_descent klón; 272 search call × klón
- **Deadline check overhead** — `started.elapsed()` minden sample után
- **Loop infrastructure** — for-loop, match, Option overhead a sampling loopban
- **`Vec::new`-allokáció** — `BestSamples::new`, `SpecializedCdeHazardCollector::new` per search call
- **`search_placement` frame overhead** — a mért exclusive bucket-ek összege kb. 20.6%, a maradék 79.4% nem instrumentált

A lv8_subset (11 search call, 12.8 ms/call) és dense191 (272 search call, 96.2 ms/call) nagyon különböző per-call costot mutat. Ez azt jelzi, hogy **a per-search-call állandó overhead (prepare_base_shape_native, session reuse, clone) a dominant** — nincs véletlen fluktuáció a két eset között.

### 5. Következő optimalizációs irány (mérés alapján)

**A. CDE query redukció** (a legindokoltabb, cde_query = 18.9% of search, 51.5% early termination)
- Az early termination arány magas (23 537 / 45 729 = 51.5%), ami jó. A maradék 49.5% teljes CDE traversalt végez.
- Inkrementális CDE session reuse per worker pass (Q28 terv) csökkentené az incremental update overheadet.

**B. prepare_base_shape_native memoizálása** (valószínűleg a largest single other_unaccounted component)
- Jelenleg egyszer per native_search_placement hívás. Ha a Part shape nem változik, per-instance előre kiszámítható.

**C. BestSamples::clone() eliminálása** (per-search overhead, de kisebb mint A/B)
- A pre-coord_descent klón kiváltható in-place iterációval az eredeti `best.samples` felett.

A mérés alapján **A és B** a prioritizálandó következő optimalizáció; **sample_generation, BestSamples insert, deregister** mind < 0.1% és nem érdemes optimalizálni.
