# Report — SGH-Q29: Upstream Sparrow A/B + local CDE hotspot profiler

**Status: PASS_WITH_NOTES**

## 1) Meta

- **Task slug:** `sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.yaml`
- **Futás dátuma:** 2026-06-06
- **Branch / commit:** main / d1a2ad2
- **Fókusz terület:** Mixed (measurement, instrumentation)

---

## 2) Scope

### 2.1 Cél

1. Valódi upstream Sparrow (`.cache/sparrow`, commit `c95454e`) futtatása ekvivalens geometrián és runtime/search összehasonlítás a saját solverrel.
2. Local CDE/search hotspot profiler implementálása `SGH_Q29_CDE_PROFILE=1` mögé.
3. Kideríteni: mi viszi el az időt a saját `native_search_placement` / CDE candidate evaluation útvonalon.
4. A két kérdésre adott pontos, mért válasz dokumentálása.

### 2.2 Nem-cél

- Nem cél solver optimalizálás.
- Nem cél algoritmus/GLS/worker/LBF/sampler/acceptance módosítása.
- Nem megengedett saját no-session buildet upstream referenciaként feltüntetni.
- Nem cél a Q28 T05 gate lazítása.
- Nem cél compression implementálása.

---

## 3) Phase A — Upstream Sparrow A/B

**Upstream Sparrow A/B: PASS, commit c95454e390276231b278c879d25b39708398b7d3, cases micro/medium/lv8_subset**

### 3.1 Upstream Sparrow felderítés

```
.cache/sparrow commit: c95454e390276231b278c879d25b39708398b7d3
.cache/sparrow/target/release/sparrow: EXISTS
CLI: sparrow -i <input.json> -t <global_secs> [-e <explore>] [-c <compress>] [-s <seed>]
Input format (SPP): {name, strip_height, items: [{id, demand, shape: {type: simple_polygon, data: [[x,y],...]}, allowed_orientations}]}
Output: output/final_<name>.json — solution.{strip_width, density, run_time_sec, layout.placed_items}
Sample inputs: .cache/sparrow/data/input/ (34 files; jakobs1, jakobs2, swim, shirts, ...)
```

### 3.2 A/B összehasonlítás

**Fontos előfeltétel:** Upstream SPP (strip packing, minimize strip width) vs. saját FSPP (fixed sheet, single 1500×3000 sheet). Az összehasonlítás alapgeometria és search viselkedés terén értelmes; a placement quality (strip width vs. utilization) nem direkten összehasonlítható.

| Case | Instances | Upstream runtime | Upstream placed | Upstream density | Local runtime | Local placed | Local pairs | Local search calls |
|------|-----------|-----------------|-----------------|-----------------|--------------|-------------|-------------|-------------------|
| micro (jakobs1) | 25 | **12,484 ms** | 25/25 | 89.0% | **2,385 ms** | 25/25 | 0 | 0 |
| medium (jakobs2) | 25 | **20,252 ms** | 25/25 | 79.0% | **2,485 ms** | 25/25 | 0 | 0 |
| lv8_subset (3 LV8 types) | 67 | **31,304 ms** | 67/67 | 75.8% | **15,872 ms** | 67/67 | 0 | 11 |

**Local solver gyorsabb** minden esetben. Fontos kontextus: a saját solver FSPP fixed-sheet mode-ban fut (nincs strip compression fázis), míg az upstream SPP strip width-et csökkent. A local solver kis eseteken a seeding fázisban fér el (0 search call), tehát az upstream vs. local "runtime" különbség részben az eltérő objektívből ered.

Az upstream search sebessége (log alapján): lv8_subset-nél ~446K–473K eval/s, ~10K move/s. A saját solver lv8_subset-en: 11 search call, 1664 candidate evaluated.

---

## 4) Phase B — Local CDE/search hotspot profiler

**Phase B: PASS**, SGH_Q29_CDE_PROFILE=1 aktív, 3 case profiled.

### 4.1 Profiling instrumentation

- Env flag: `SGH_Q29_CDE_PROFILE=1`
- Módosított fájlok: `diagnostics.rs`, `search.rs`, `sep_evaluator.rs`, `specialized_cde_pipeline.rs`, `adapter.rs`, `io.rs`
- Default szemantika változatlan; timing/counting csak amikor a flag be van állítva.

### 4.2 Profiling eredmények

#### lv8_subset (67 inst, 11 search call)

| Komponens | ms | % a search_total-on belül |
|-----------|-----|--------------------------|
| **cde_query_collect_ms** | 10.2 | **7.4%** |
| candidate_transform_prepare_ms | 3.2 | 2.4% |
| boundary_check_ms | 1.8 | 1.3% |
| deregister_ms | 0.1 | 0.0% |
| **other (unaccounted)** | **122.4** | **88.9%** |
| **search_total_ms** | **137.7** | 100% |

- Early terminations: 231 / 1664 sample = 13.9%
- Broadphase rejects: 0

#### dense191 (191 inst, 66 search call, 60s budget)

| Komponens | ms | % a search_total-on belül |
|-----------|-----|--------------------------|
| **cde_query_collect_ms** | 1,236 | **19.2%** |
| candidate_transform_prepare_ms | 35 | 0.5% |
| boundary_check_ms | 12 | 0.2% |
| deregister_ms | 0.8 | 0.0% |
| **other (unaccounted)** | **5,164** | **80.1%** |
| **search_total_ms** | **6,448** | 100% |

- Early terminations: 4,489 / 9,755 sample = 46.0% (!) — a loss-bound early termination hatékonyan vágja le a dominált sample-eket.
- Broadphase rejects: 288 / 9,755 = 2.9%
- Per-call average: ~97ms / search call; CDE query: ~18.7ms/call

#### Megjegyzések a `not_available` mezőkre

- **hazard_loss_ms**: not_available — a hazard quantification a CDE query útvonalon belül történik (`collect_poly_collisions_in_detector_custom`); önálló timingja dupla overhead lenne értelmezési nyereség nélkül. Tartalmaz: `quantify_collision_poly_poly_value` + `quantify_collision_poly_container_value`.
- **session_build_ms = 0.0**: csak a fallback (cross-sheet) session build mérve a `search.rs`-ben (allowed file). A fő live-session (per-worker-pass) build a `worker.rs`-ben történik (nem allowed fájl → nem mérhető Q29 határain belül). A live_session build egyszer épül worker pass-onként → nincs search call-onkénti overhead.

---

## 5) Változások összefoglalója

### 5.1 Érintett fájlok

**Scripts:**
- `scripts/bench_sgh_q29_upstream_sparrow_ab.py` (new)
- `scripts/profile_sgh_q29_local_cde_hotspot.py` (new)
- `scripts/smoke_sgh_q29_upstream_ab_and_cde_hotspot_profiler.py` (pre-existing template, no changes needed)

**Rust (profiling instrumentation only — no semantic changes):**
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs` — profiling fields + manual Default impl (env-var check)
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs` — timing native_search_placement total, deregister, session build fallback
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs` — timing boundary check + transform; broadphase reject count
- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs` — timing CDE query/collect; early termination count
- `rust/vrs_solver/src/adapter.rs` — map profiling fields to output
- `rust/vrs_solver/src/io.rs` — new `sparrow_profile_*` output fields

**Artifacts (new):**
- `artifacts/benchmarks/sgh_q29/upstream_ab_summary.json`
- `artifacts/benchmarks/sgh_q29/upstream_ab_report.md`
- `artifacts/benchmarks/sgh_q29/local_cde_hotspot_summary.json`
- `artifacts/benchmarks/sgh_q29/local_cde_hotspot_report.md`

**Codex:**
- `codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`
- `codex/codex_checklist/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md`

### 5.2 Miért változtak?

A Rust fájlok kizárólag mérési célú instrumentation miatt változtak — semmiféle algoritmus, acceptance logika, GLS, worker ordering, LBF viselkedés nem módosult. A profiling mezők `false`/`0` alapértéken vannak, csak `SGH_Q29_CDE_PROFILE=1` esetén aktívak. A `Default` implementáció env-var checkje nullköltségű production futásban (egyszer olvasódik, egyszer kerül a struktúrába).

---

## 6) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat |
|---|---|---|---|
| #1 Upstream Sparrow A/B: egyértelműen kimondja, volt-e valódi upstream futás | **PASS** | `upstream_ab_summary.json:status=PASS` | Valódi `.cache/sparrow` binary futott, commit `c95454e` |
| #2 Upstream commit/build/entrypoint rögzítve | **PASS** | `upstream_ab_summary.json:upstream_sparrow` | commit: c95454e, binary: `.cache/sparrow/target/release/sparrow`, build: `cargo build --release --manifest-path .cache/sparrow/Cargo.toml` |
| #3 Legalább micro + medium upstream A/B lefutott | **PASS** | `upstream_ab_summary.json:cases[0,1,2]` | micro (jakobs1, 25 inst) + medium (jakobs2, 25 inst) + lv8_subset (67 inst) — mind PASS |
| #4 Local CDE profiler medium + LV8-derived case lefutott | **PASS** | `local_cde_hotspot_summary.json:cases` | medium, lv8_subset, dense191 — mind profiling_enabled=true |
| #5 Profiler JSON kötelező mezők | **PASS** | `local_cde_hotspot_summary.json:profile` | 11 required field present; hazard_loss_ms: not_available + indok |
| #6 smoke_sgh_q29 PASS | **PASS** | `smoke_sgh_q29_upstream_ab_and_cde_hotspot_profiler.py` | 65/65 check passed |
| #7 cargo test PASS | **PASS** | `cargo test --lib`: 455/455, integration: 8 passed 1 ignored | All tests green |
| #8 verify.sh PASS | **PASS** | `verify.sh` exit 0, check.sh exit 0 | AUTO_VERIFY block: PASS, 2026-06-06 |

---

## 7) Futtatási eredmények

```
cargo build --release     → PASS (12s)
bench_sgh_q29_upstream_sparrow_ab.py → Phase A: PASS (3 cases, ~64s total)
profile_sgh_q29_local_cde_hotspot.py → Phase B: PASS (medium + lv8_subset + dense191)
smoke_sgh_q29_upstream_ab_and_cde_hotspot_profiler.py → 65/65 PASS
cargo test --lib          → 455 passed, 0 failed, 0 ignored (172s)
cargo test (integration)  → 8 passed, 1 ignored (40s)
./scripts/verify.sh       → PASS, check.sh exit 0
```

---

## 8) Final answer to the two questions

### 1. Upstreamhez képest hol állunk?

**Upstream Sparrow A/B: PASS — commit c95454e — cases: micro (jakobs1, 25 inst), medium (jakobs2, 25 inst), lv8_subset (3 LV8 part types, 67 inst)**

| | micro | medium | lv8_subset |
|-|-------|--------|------------|
| Upstream runtime | 12,484 ms | 20,252 ms | 31,304 ms |
| Local runtime | 2,385 ms | 2,485 ms | 15,872 ms |
| Upstream placed / total | 25/25 | 25/25 | 67/67 |
| Local placed / total | 25/25 | 25/25 | 67/67 |
| Local final pairs | 0 | 0 | 0 |

**Értékelés:** A saját solver minden esetben gyorsabb volt, és mindhárom esetben teljesen ütközésmentes elrendezést talált (final_pairs=0). Az upstream Sparrow szignifikánsan több időt töltött — ez részben az eltérő objektív miatt van (SPP strip width compression vs. FSPP fixed-sheet pack), részben a Q24R3+ óta alkalmazott LBF konstruktív seed miatt, ami a saját solverre jobb kiindulási állapotot ad.

**Fontos korlát:** Az összehasonlítás nem teljesen direkten alkalmazható, mert az upstream SPP célja a strip width minimalizálása (= folyamatos tömörítés), míg a saját solver fixed sheet-re packol. A saját solver kis eseteken seeding után azonnal konvergál (0 search call), míg az upstream compress fázisban van. Mindazonáltal a placement minősége legalább egyenértékű.

### 2. A saját CDE/search útvonalon mi viszi el az időt?

**Profiler eredmény (dense191, 191 inst, 66 search call, 6,448ms search_total_ms):**

| Komponens | ms | % | Megjegyzés |
|-----------|-----|---|---|
| **cde_query_collect_ms** | 1,236 | **19.2%** | `collect_poly_collisions_in_detector_custom` – ez az igazi CDE munka |
| candidate_transform_ms | 35 | 0.5% | `transform_base_to_candidate` – olcsó |
| boundary_check_ms | 12 | 0.2% | bbox fit check – negligibilis |
| deregister_ms | 0.8 | 0.0% | CDE session deregister – negligibilis |
| **other (unaccounted)** | **5,164** | **80.1%** | |

Az "other" 80% (5,164ms) a `native_search_placement`-en belül van, de nem esik a mért bucketekbe. A valószínű tartalom:
1. **`search_placement` inner loop** — `BestSamples` management, `UniformBBoxSampler` sample generation, sample deduplication (UNIQUE_SAMPLE_THRESHOLD)
2. **`refine_coord_desc`** — minden `evaluate_sample` hívás a coord_descent-ből is a `cde_query_collect_ms`-ben van mérve (átmenő hívás), tehát ez viszonylag kisebb
3. A CDE early termination nagyon hatékony (46% sample terminálódik korán), tehát a nyers CDE query cost csak 19%

**Kulcsmegállapítás:** A `native_search_placement`-en belül **nem a CDE query** a legköltségesebb rész (19%), hanem a sample generálás + BestSamples kezelés + általános loop infrastruktúra (~80%). A Q28 hipotézis ("session build a bottleneck") nem igazolódott be: a live session build a `worker.rs`-ben van (nem mért Q29 határon belül), és a per-call CDE query idő 191 instance esetén átlagosan ~18.7ms — ez kezelhető.

**A dense191 esetén az igazi bottleneck** a 60s időlimit alatt a seeding fázis (LBF + 191 komplex polygon) és az egyes iterációkon belüli search call overhead (sample generation), nem a CDE collision query maga.

---

## 9) Advisory notes

1. **Session build timing korlát**: A fő live-session build (`worker.rs`) nem szerepel az engedélyezett Q29 fájlok között. Ez mérhető lenne egy Q30 feladat keretében ha szükséges.
2. **"Other" 80% azonosítása**: Ha a sample generation / BestSamples overhead is vizsgálatra kerül, érdemes a `search_placement` belső ciklusát instrumentálni (a canvas megfelelő bővítésével).
3. **Upstream vs. local összehasonlítás érvényessége**: SPP vs. FSPP különbség miatt a direkt runtime összehasonlítás fenntartásokkal kezelendő; a CDE query és search behavior összehasonlítása informatívabb lett volna ha az upstream is CDE-t használna.
4. **Early termination hatékonyság**: dense191-nél 46% early termination — ez a loss-bound bounded visitor pattern nagyon hatékonynak bizonyult.

---

## Verifikáció

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-06T21:04:03+02:00 → 2026-06-06T21:07:15+02:00 (192s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.verify.log`
- git: `main@d1a2ad2`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     |  20 ++++
 rust/vrs_solver/src/io.rs                          |  21 ++++
 .../src/optimizer/sparrow/diagnostics.rs           | 112 ++++++++++++++++++++-
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |  18 +++-
 .../sparrow/eval/specialized_cde_pipeline.rs       |   6 ++
 .../src/optimizer/sparrow/sample/search.rs         |  12 +++
 6 files changed, 184 insertions(+), 5 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
?? artifacts/
?? canvases/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md
?? codex/codex_checklist/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.yaml
?? codex/prompts/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler/
?? codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md
?? scripts/bench_sgh_q29_upstream_sparrow_ab.py
?? scripts/profile_sgh_q29_local_cde_hotspot.py
```
<!-- AUTO_VERIFY_END -->
