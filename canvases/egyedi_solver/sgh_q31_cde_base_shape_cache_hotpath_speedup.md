# SGH-Q31 — CDE base-shape cache hot-path speedup

## 0. Kontextus

A Q30-R1 exkluzív profiling kimutatta, hogy dense191 esetben a search hot path fő költsége nem a CDE collect, nem a sample generation, nem a BestSamples, hanem a `prepare_base_shape_native` ismételt futtatása.

Q30-R1 baseline dense191:

```text
total_solver_runtime_ms:        ~200437.6
search_total_ms:                 ~27210.4
prepare_base_shape_native_ms:     ~21433.1  (~78.8% of search)
evaluate_sample_total_ms:          ~5587.0
cde_query_collect_ms:              ~5139.7
placed: 191/191
status: partial
final_pairs: 80
```

Ez azt jelenti: a base CDE shape előkészítése search-callonként újra lefut, pedig a base shape a part geometriától függ, nem függ candidate pozíciótól, sheet-től vagy aktuális layout állapottól.

## 1. Cél

Q31 célja: **a `prepare_base_shape_native` kivezetése a search/LBF/tracker hot pathból part-level cache-sel**, szemantika-változtatás nélkül.

A várt production modell:

```text
SparrowProblem::from_solver_input
  -> unique part geometry / part_id alapján CdeBaseShape cache építése
  -> SPInstance { base_shape: Rc<CdeBaseShape>, ... }

native_search_placement
  -> inst.base_shape használata
  -> transform_base_to_candidate(...) candidate-enként
  -> nincs prepare_base_shape_native(&inst.part)

LBFBuilder::find_clear_placement
  -> inst.base_shape használata
  -> nincs prepare_base_shape_native(&inst.part)

SparrowCollisionTracker::prepare_item / update_after_move / initial/final tracker build
  -> transform_base_to_candidate(inst.base_shape, placement.x, placement.y, placement.rotation_deg)
  -> nincs prepare_shape_native(&inst.part, ...)
```

## 2. Nem-cél

Nem része Q31-nek:

- geometry simplification / vertex reduction;
- surrogate config módosítása;
- CDE/jagua-rs algoritmus átírása;
- sample budget csökkentése;
- worker ordering módosítása;
- GLS/acceptance/touching policy módosítása;
- compression;
- upstream Sparrow A/B;
- dense191 optimalizációs tuning.

Ez egy **cache / reuse** feladat, nem solver-viselkedés módosítás.

## 3. Kötelező implementációs elvek

### 3.1 Cache granularity

Első körben part-level cache kell:

```rust
HashMap<String, Rc<CdeBaseShape>> // part.id / part_id key
```

Elfogadható erősebb kulcs is, ha dokumentált és determinisztikus, például geometry fingerprint. De tilos minden instance-hez külön új base shape-et építeni, ha ugyanazt a partot képviselik.

### 3.2 SPInstance kiegészítése

`SPInstance` kapjon cache-elt base shape mezőt:

```rust
pub base_shape: Rc<CdeBaseShape>
```

Ha emiatt `CdeBaseShape`-hez `Debug` kell, add hozzá biztonságosan a `cde_adapter.rs`-ben.

### 3.3 Hot path tiltás

Q31 után ezekben a production hot pathokban nem maradhat közvetlen:

```rust
prepare_base_shape_native(&inst.part)
prepare_shape_native(&inst.part, ...)
```

Érintett minimum helyek:

```text
rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
rust/vrs_solver/src/optimizer/sparrow/lbf.rs
rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
```

A `prepare_base_shape_native` természetesen maradhat a cache felépítési ponton, jellemzően `SparrowProblem::from_solver_input()` alatt.

### 3.4 Tracker reuse

A tracker item shape rebuildje is használja a cache-t:

```rust
transform_base_to_candidate(&inst.base_shape, p.x, p.y, p.rotation_deg)
```

Ezzel nemcsak a search, hanem a tracker initial build / update_after_move / final validation költsége is csökkenhet.

## 4. Profiler / diagnosztika követelmények

A Q30-R1 profiler maradjon, és bővüljön legalább ezekkel:

```text
base_shape_cache_build_ms
base_shape_cache_hits
base_shape_cache_misses
base_shape_cache_unique_parts
base_shape_cache_reused_instances
prepare_base_shape_native_hotpath_calls
prepare_base_shape_native_hotpath_ms
tracker_transform_from_base_ms
lbf_base_shape_cache_hits
search_base_shape_cache_hits
```

Ha a meglévő `prepare_base_shape_native_ms` mezőt megtartod, akkor a reportban egyértelműen különítsd el:

```text
cache construction prepare time
vs
hot-path prepare time
```

Tilos a cache build idejét search hot-path prepare időnek számolni.

## 5. Mérési követelmény

Kötelező futtatni saját solverrel:

```text
medium
lv8_subset
Dense191
```

Kötelező artefaktumok:

```text
artifacts/benchmarks/sgh_q31/base_shape_cache_summary.json
artifacts/benchmarks/sgh_q31/base_shape_cache_report.md
artifacts/benchmarks/sgh_q31/inputs/dense191.json
artifacts/benchmarks/sgh_q31/inputs/lv8_subset.json
```

A dense191 a fő acceptance case.

## 6. Acceptance gate

Q31 csak akkor PASS, ha dense191-en mind teljesül:

1. `placed_count == 191`.
2. `status` nem rosszabb, mint Q30-R1 baseline (`partial` elfogadható, `unsupported` / error nem).
3. `final_pairs <= 88` *(Q30-R1 baseline 80 + 10% tolerancia)*.
4. `prepare_base_shape_native_hotpath_calls == 0` vagy bizonyítottan nincs search/LBF/tracker hot-path prepare call.
5. `prepare_base_shape_native_hotpath_ms <= 2143.31 ms` *(Q30-R1 baseline 21433.1 ms 10%-a)*.
6. `base_shape_cache_misses <= unique_part_count + 2`.
7. `base_shape_cache_hits >= instance_count - unique_part_count`.
8. A smoke validator PASS.
9. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md` PASS.

Ha bármelyik nem teljesül: a report státusz **FAIL** vagy **PARTIAL**, nem PASS.

## 7. Kötelező report tartalom

A report végén legyenek ezek a marker sorok:

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

## 8. Sikeres kimenet értelmezése

Ha a task sikeres, a várható következtetés:

```text
A Q30-R1-ben kimért search-hotspotból a prepare_base_shape_native ismételt újraépítését kivettük.
A következő hotspot már nem ez, hanem a profiler által jelzett új domináns bucket.
```

Ha a runtime nem javul jelentősen, de a prepare-base hot-path költség eltűnik, azt őszintén jelezni kell: akkor a teljes runtime következő domináns költsége lesz a Q32 célpontja.
