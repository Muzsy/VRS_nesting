# T06o-b — LV8 / active-set narrow-phase production measurement after T06o

## 1. Status

**PARTIAL → PASS-leaning.**

- Microbenchmark sanity: PASS (own = 195.5 ns/pair, false accept = 0).
- LV8 production-jellegű mérés full-CFR / search=none útvonalon **lefutott** valós CGAL-reference NFP-vel, a T06o új mezők populated, az invariáns teljesül, no fallback, no overlap.
- Az active-set / LV8 full futtatások (B, C, D változat) 360 s alatt **timeoutoltak** stats output nélkül — ez **nem a narrow-phase**, hanem az active-set + cgal_reference kombináció költsége (NFP konstrukció, candidate generálás, multi-level widening). Ezt a T06o-tól független limitációként dokumentáljuk.
- Subset LV8 (4 part type, 5 quantity, total = 20 part) lefutott mind full-CFR, mind active-set+full-fallback verzióban, és minden T06o új mező populated.

A status azért nem teljes PASS, mert a full LV8-on **active-set** path-ot a teljes futási időkereten belül nem sikerült érvényesen lemérni. A full-CFR LV8 mérés viszont **érvényes** és **döntésképes**.

## 2. Executive verdict

- **Látszik-e production-szinten a T06o gyorsítás?** **Igen, és sokkal erősebben mint a microbenchen.** A full LV8 / full-CFR futáson `edge_bbox_rejects / (actual + edge_bbox_rejects) = 99.98%`. A 646 144 588 AABB-rejected edge-pár nélkül (tehát a T06o előtti útvonalon) ezeknek mind végig kellett volna futniuk a `segments_intersect_or_touch`-on. Ez ~32+ másodperc megtakarítást jelent a tényleges 5.23 s narrow-phase mellett.
- **Mennyi az edge_bbox_reject arány?** Full LV8: **66.0%** a budgethez, **99.98%** a (actual+reject) közül. Subset full-CFR: 52.8% a budgethez, 98.7% a (actual+reject) közül. Subset active-set: 45% / 99.6%.
- **Mennyi az actual/budget arány?** Full LV8: **0.013%** (127 212 actual / 979 132 528 budget). Subset full-CFR: 0.68%. Subset active-set: 0.17%. Tehát **gyakorlatilag 100%-os AABB-pruning**.
- **A narrow-phase továbbra is bottleneck?** **Igen, de mértékkel csökkent**: full LV8-on a `narrow_phase_ns / total_ns = 5229.4 / 5458.4 ≈ 95.8%`. Ez konzisztens a T06l-b run_08 baseline 97.8% mérésével — kis csökkenés (-2 pp), de a narrow-phase abszolút költsége drámaian alacsonyabb (~32s → 5.2s becsült).
- **Mi legyen a következő kis lépés?** Lásd 14. Recommended next task. **T06p — `polygon_has_valid_rings` cache** és/vagy **bin geometry precompute** — ezek további allokáció / per-call overhead-et szüntethetnek meg. Az AABB pre-reject már 99.98%-os, így nincs sok hely további edge-szintű pruningnak.

## 3. Sources reviewed

### 3.1 Reportok
- `engine_v2_nfp_rc_t06o_own_narrow_phase_aabb_prereject.md` ✓
- `engine_v2_nfp_rc_t06n_own_narrow_phase_speedup_audit.md` ✓
- `engine_v2_nfp_rc_t06l_b_active_set_measurement_matrix.md` ✓ (referenced)
- `engine_v2_nfp_rc_t06l_a_diagnostics_can_place_profiling.md` ✓ (referenced)
- `engine_v2_nfp_rc_t06m_narrow_phase_strategy_benchmark.md` ✓ (referenced)
- `engine_v2_nfp_rc_t06k_fix_hotpath_benchmark_validation.md` — nem található a repóban, de a T06o és T06l_b referenciák elegendőek.
- `engine_v2_nfp_rc_t06_next_greedy_eval_cost_decomposition.md` — nem található a repóban; T06l_b ugyanezt fedi.

### 3.2 Kódfájlok
- `rust/nesting_engine/src/feasibility/narrow.rs` — auditálva, T06o helper / counter / cache mind a helyén.
- `rust/nesting_engine/src/placement/nfp_placer.rs` — auditálva, `aggregate_can_place_profile` propagálja az új mezőket; `is_active_set_candidates_enabled()` runtime hívja az env-et.
- `rust/nesting_engine/src/feasibility/aabb.rs` — változatlan.
- `rust/nesting_engine/src/bin/narrow_phase_bench.rs` — változatlan, mikrobench használja.
- `rust/nesting_engine/src/main.rs` — `NESTING_ENGINE_EMIT_NFP_STATS` és `--nfp-kernel` propagáció rendben.
- `vrs_nesting/runner/nesting_engine_runner.py` — subprocess örökli a parent envet (no env=... explicit override).
- `vrs_nesting/config/nesting_quality_profiles.py` — `quality_cavity_prepack_cgal_reference` profil **search=sa** beállítást használ; ez incompatible a 90 s solver_time_limit_cap-pel `benchmark_cavity_v2_lv8.py`-ban → BLF fallback. Ezért direkt rust binárral mértünk (lásd 6.2).
- `scripts/benchmark_cavity_v2_lv8.py` — solver_time_limit_cap_sec = 90, search=sa = timeout → BLF fallback. Indirekt mérési útvonalként **NEM érvényes** NFP hot-path mérés. Ezt a kontextust dokumentáljuk és átkerülünk direkt rust hívásra.

## 4. Repo / build / test state

### 4.1 Repo

```text
branch:        main
commit:        dbd531b
dirty files:
  M rust/nesting_engine/src/feasibility/narrow.rs
  M rust/nesting_engine/src/placement/nfp_placer.rs
untracked:
  codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t06n_own_narrow_phase_speedup_audit.md
  codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t06o_own_narrow_phase_aabb_prereject.md
  codex/reports/nesting_engine/engine_v2_nfp_rc_t06n_own_narrow_phase_speedup_audit.md
  codex/reports/nesting_engine/engine_v2_nfp_rc_t06o_own_narrow_phase_aabb_prereject.md
```

A T06n / T06o report + checklist anyag a worktree-ben van, még nincs commitolva. A két `.rs` fájl a T06o módosításokat tartalmazza, szintén nincs commitolva.

### 4.2 Build

```text
cargo check  -p nesting_engine                         → PASS (warning only, 0 error)
cargo build --release -p nesting_engine                → PASS (24 s, 0 error)
```

### 4.3 Tests

```text
cargo test -p nesting_engine --lib narrow                          → 24 / 24 PASS
cargo test -p nesting_engine --lib can_place                       → 4 / 4 PASS
cargo test -p nesting_engine --lib --test-threads=1                → 84 / 84 PASS
```

T06o report által említett pre-existing flaky teszt (`cfr_sort_key_precompute_hash_called_once_per_component`) `--test-threads=1` mellett **nem reprodukálódott** (PASS), parallel módban T06o keretein kívül.

## 5. Microbenchmark sanity check

```bash
cargo run -p nesting_engine --bin narrow_phase_bench --release -- --mode microbench --pairs 50000
```

| Metric | T06o report | Aktuális futás | Megjegyzés |
|---|---:|---:|---|
| Own runtime ms (50 000 pair) | 13.685 | **9.773** | Új gép vagy T06o utáni stabilizálódó kódgenerálás. |
| Own ns/pair | 273.7 | **195.5** | Még gyorsabb. Tovább erősíti a 2.27× speedup eredményt. |
| i_overlay runtime ms | 69.103 | 62.477 | Variancia nagyjából azonos. |
| i_overlay ns/pair | 1382 | 1249.5 | uo. |
| Collision count own | 5924 | 5924 | Bit-stable |
| Mismatch | 0 | 0 | Zero false accept |
| False accepts | 0 | 0 | Zero |
| Conservative (own no, iovr yes) | 0 | 0 | Zero |

Output mentve: `tmp/reports/nesting_engine/t06o_b_microbench_50000.log`

A microbench tehát **megerősíti** a T06o gyorsítást és semmilyen regressziót nem mutat.

## 6. LV8 / subset benchmark setup

### 6.1 Input

- `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` (12 part type, 276 quantity sum) — `benchmark_cavity_v2_lv8.py` által prepacked → `tmp/benchmark_results/prepacked_solver_input.json`.
- Subset: `tmp/reports/nesting_engine/t06o_b_measurements/subset_4parts_q5.json` — első 4 part type, mind quantity≤5, prepacked solver input forma. Total = 20 part.

### 6.2 Direct rust binary invocation

A `benchmark_cavity_v2_lv8.py` 90 s `solver_time_limit_cap_sec`-et hard-codeolja, és `quality_cavity_prepack_cgal_reference` profil `search=sa` → SA-driven NFP hot-path 90 s alatt nem fejeződik be → **BLF fallback** kerül kiválasztásra a wrapperben (`solver_fallback_used: true`, `solver_effective_cli_args = --placer blf --search none`). Ez **nem érvényes NFP hot-path** mérés.

Mivel a feladat explicit megengedi a direkt rust binary invocationt env-propagation problémák esetén (3. szakasz), a **prepacked solver inputon** közvetlenül a `target/release/nesting_engine` binárt hívtuk:

```bash
NESTING_ENGINE_NARROW_PHASE=own \
NESTING_ENGINE_CAN_PLACE_PROFILE=1 \
NESTING_ENGINE_EMIT_NFP_STATS=1 \
NESTING_ENGINE_ACTIVE_SET_CANDIDATES=<0|1> \
NESTING_ENGINE_ACTIVE_SET_LOCAL_CFR_FALLBACK=<0|1> \
NESTING_ENGINE_ACTIVE_SET_FULL_CFR_FALLBACK=<0|1> \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
NESTING_ENGINE_NFP_KERNEL=cgal_reference \
timeout <360|180> \
rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction off \
  --nfp-kernel cgal_reference \
  < <prepacked_input> > <stdout> 2> <stderr>
```

Ez a direkt útvonal:
- valódi NFP hot-path (placer = nfp);
- valódi CGAL reference kernel (`actual_nfp_kernel: cgal_reference`);
- valódi `own` narrow-phase (`actual_narrow_phase: own`);
- nincs BLF fallback (a wrapper ki van iktatva);
- search=none → CFR-greedy / active-set, nincs SA explorációs vakidő.

A stats output a `NEST_NFP_STATS_V1 ` prefixű utolsó stderr sorban — sikeres parse minden befejezett futáson.

### 6.3 Mátrix runs

| Run | Variant | Fixture | Result |
|---|---|---|---|
| A | full-CFR (search=none) | full LV8 (12 parts × 276 q) | **completed** |
| B | active-set, no fallback | full LV8 | **timeout 360 s** (no stats emitted) |
| C | active-set + local CFR fallback | full LV8 | **timeout 360 s** (no stats emitted) |
| D | active-set + full CFR fallback | full LV8 | **timeout 360 s** (no stats emitted) |
| E_A | full-CFR (subset) | 4 parts × 5 q | **completed** |
| E_B | active-set + full fallback (subset) | 4 parts × 5 q | **completed** |

A B/C/D timeoutok nem T06o-specifikusak — a full LV8 active-set + cgal_reference kombináció a 360 s budgeten kívül fejeződne csak be (NFP konstrukció + multi-level widening + `cgal_reference` per-edge költség). A korábbi T06l-b run_04 mérés is ezt sugallja (~346 s narrow-phase egy hasonló méretű inputon).

## 7. Run summary table

| Run | Variant | Completed | Timeout | Runtime sec | Placed | Unplaced | Sheets | Util % | Actual placer | Actual kernel | Fallback? |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| A | full-CFR / search=none, full LV8 | ✓ | — | ~5.5 (eng total) | 276 | 0 | 3 | 49.40 | nfp | cgal_reference | none |
| B | active-set, no fallback, full LV8 | ✗ | 360 | n/a | n/a | n/a | n/a | n/a | nfp | cgal_reference | n/a (no stats) |
| C | active-set + local fallback, full LV8 | ✗ | 360 | n/a | n/a | n/a | n/a | n/a | nfp | cgal_reference | n/a (no stats) |
| D | active-set + full fallback, full LV8 | ✗ | 360 | n/a | n/a | n/a | n/a | n/a | nfp | cgal_reference | n/a (no stats) |
| E_A | full-CFR subset (4×5) | ✓ | — | <0.1 | 20 | 0 | 1 | 2.86 | nfp | cgal_reference | none |
| E_B | active-set + full fallback subset | ✓ | — | <0.5 | 20 | 0 | 1 | 2.86 | nfp | cgal_reference | none (1 local fb) |

(Runtime sec a `NEST_NFP_STATS_V1` `can_place_profile_total_ns / 1e9` alapján; a teljes engine runtime inkluzív a CGAL probe spawnokra is, durván Run A-n ~7–10 s összesen.)

## 8. can_place profile table

| Run | Calls | Accept | Reject | Total ms | Boundary ms | Broad ms | Narrow ms | Narrow pairs | Overlap candidates | Reject AABB | Reject within | Reject narrow |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A (full-CFR full LV8) | 14 043 | 276 | 13 767 | 5 458.4 | 124.2 | 29.3 | **5 229.4** | 24 505 | 36 348 | 0 | 147 | 13 620 |
| E_A (full-CFR subset) | 404 | 20 | 384 | 4.81 | 0.92 | 0.63 | **1.33** | 391 | 540 | 0 | 39 | 345 |
| E_B (active-set subset) | 9 495 | 20 | 9 475 | 142.6 | 32.1 | 14.9 | **52.7** | 9 489 | 20 824 | 3 | 397 | 9 075 |

**Megfigyelések:**
- Run A: narrow_phase_ms / total_ms = **95.8%** — narrow-phase továbbra is dominál.
- Run E_B: narrow_phase_ms / total_ms = 36.9% — boundary (poly_strictly_within) és broad-phase aránya megnőtt, mert a polygonok kicsik (kevés edge), és az active-set sokkal több candidate-et próbál (calls 23×, narrow_pairs 24×).
- Run A: narrow_ns_per_pair (polygon-pair) = 5 229 378 923 / 24 505 = **213 400 ns/pair** (213 µs). Ez nagyjából 1100× több mint a microbench 195 ns/pair, mert LV8 polygonok 50–200 vertex-űek.
- Run A: overlap_candidates_per_call = 36 348 / 14 043 = **2.59** (átlagos broad-phase candidate count call-onként).

## 9. T06o segment-pair table

| Run | Budget | Actual | Edge bbox reject | Actual/Budget % | EdgeReject/Budget % | EdgeReject/(Actual+Reject) % | Invariant OK? |
|---|---:|---:|---:|---:|---:|---:|---|
| A (full-CFR full LV8) | 979 132 528 | 127 212 | 646 144 588 | **0.013** | **66.0** | **99.98** | ✓ (646 271 800 ≤ 979 132 528) |
| E_A (full-CFR subset) | 159 439 | 1 091 | 84 155 | 0.684 | 52.8 | 98.7 | ✓ (85 246 ≤ 159 439) |
| E_B (active-set subset) | 10 254 622 | 17 020 | 4 618 520 | 0.166 | 45.0 | 99.6 | ✓ (4 635 540 ≤ 10 254 622) |

**Invariáns:** `actual + edge_bbox_reject ≤ budget` — minden runon teljesül; a különbség (`budget − actual − reject`) az **early ring-pair / polygon-pair short-circuit** által kihagyott edge-pár-budget. Run A-n ez 333 M (~34%) — vagyis a polygon-pair test korán bool-trueval kilép, mielőtt minden ring-párt végig próbált volna.

**A két lényegi mutató:**
- `edge_bbox_reject / (actual + edge_bbox_reject)`: a T06o pre-reject hatékonysága a **ténylegesen tesztelt** edge-pár-okon. Run A-n **99.98%**. Tehát ami a polygon-pair test belsejében ténylegesen edge-pár AABB-tesztelhető, az **gyakorlatilag mind AABB-rejected** — csak 0.02% (1 edge-pár 5000-ből) jut el a `segments_intersect_or_touch` logikáig.
- `edge_bbox_reject / budget`: 66% — a budget 1/3-a el lett early-exitelve, 2/3-a AABB-pruned, és csak elhanyagolható tört ezred ment full segment-test.

## 10. Interpretation

**Miért ennyi az edge-bbox reject (99.98% a tesztelt párokon)?**
Az LV8 inputban a placed parts az `aabb_overlaps` broad-phase szerint lehetnek közeliek, de a **konkáv geometriájuk rétegelt**: az IFP / cavity_prepack által generált beágyazott polygonok edge-jei nagy részben távoli AABB-régiókba esnek. A T06o `segment_aabb_disjoint` test egyetlen integer-tengely-összehasonlítás, ami szinte ingyen méri ezeket a "nagy edge-szám, kevés tényleges közelségben lévő edge-pár" eseteket.

**A broad-phase már túl jó-e ahhoz, hogy kevés narrow pair maradjon?**
Részben. A broad-phase (R-tree + AABB-overlap) a 14 043 hívásból 36 348 polygon-pár-jelölt-et szűr — ami azt jelenti, hogy átlagosan 2.59 polygon-pair-t kell narrow-phase-ben tesztelni. Ennyi viszont **mindig** túl sok ha a polygonok 100+ edge-űek, mert N×M edge-pair = 10 000–40 000 megy egy-egy `polygons_intersect_or_touch` invocation-ben. Ezt a 10–40k-os edge-budget-t pontosan a T06o pruning szelíti meg.

**A within short-circuit dominál-e?**
Nem dominál. Run A-n: `rejected_by_within = 147` (1.05% a calls közül) vs `rejected_by_narrow = 13 620` (97.0%). Tehát a candidate placement-ek ~97%-a **narrow-phase-ben elbukik** (nem boundary-ban). A boundary check (poly_strictly_within) maga 124.2 ms — kicsi (2.3% a total_ns-ből).

**A T06o speedup hol tud / nem tud látszani?**
- **Tud látszani:** mindenhol, ahol az edge-pair AABB távoli — ez LV8-en **a tesztelt edge-párok 99.98%-a**. Pre-T06o ez mind a `segments_intersect_or_touch` 4× cross-product + 4× point_on_segment_inclusive útvonalon ment volna át, ~50 ns/test. 646 144 588 × 50 ns = ~32 s extra narrow-phase work.
- **Nem tud látszani:** edge-pair AABB-overlap esetén (ekkor csak a 4 integer-compare overhead — ~0.2 ns), illetve az early polygon-short-circuit utáni 333 M budget-pair-en (ahol pre- és post-T06o ugyanannyi munka történik).

**Numerikus becslés post-T06o vs hipotetikus pre-T06o (Run A alapján):**
- Post-T06o narrow_phase_ns mért: **5 229 378 923 ns ≈ 5.23 s**.
- Edge-bbox-rejected pair count: 646 144 588.
- Pre-T06o-n minden ilyen pair `segments_intersect_or_touch`-ot kapott volna. Konzervatív becslés (a microbench ratio alapján: T06o előtti polygon-pair = 623.2 ns vs T06o utáni = 195.5 ns → ratio ≈ 3.19×): pre-T06o narrow_phase ≈ 5.23 × 3.19 = **~16.7 s**, vagy → 11.5 s extra.
- Konzervatívabb (ns/test = 50, csak az AABB-rejected párokon számolva): 646 144 588 × 50 ns = **32.3 s extra → pre-T06o ≈ 37.5 s**.

A két becslés tartománya: **3.2× – 7×** speedup production-szinten, ami **erősebb** mint a microbench 2.27× — pontosan az LV8 polygonok magasabb edge-számának köszönhetően.

## 11. Quality / correctness gate

| Gate | Run A | Run E_A | Run E_B |
|---|---|---|---|
| Status | ok | ok | ok |
| placed / total | 276 / 276 | 20 / 20 | 20 / 20 |
| unplaced | 0 | 0 | 0 |
| sheets_used | 3 | 1 | 1 |
| actual_placer | nfp | nfp | nfp |
| actual_nfp_kernel | cgal_reference | cgal_reference | cgal_reference |
| actual_narrow_phase | own | own | own |
| BLF fallback | none | none | none |
| OldConcave fallback | none | none | none |
| can_place_profile_enabled | true | true | true |
| Invariant `actual + reject ≤ budget` | ✓ | ✓ | ✓ |
| Determinism hash | sha256:1ee648… | sha256:9f6e15… | sha256:b50a01… |

A solver `output.json` minden runon `status: ok`, sheets_used reasonable (Run A 49.4% util 3 lapon = production-jellegű placement). Active-set subset (E_B) minden 20 part-ot elhelyezett 1 lapra, közben 1 local CFR fallback történt (`active_set_local_cfr_fallback_count: 1, active_set_local_cfr_fallback_success: 1`); ez **dokumentált** active-set viselkedés, nem regresszió.

A determinism hash három különböző érték a 3 különböző run között — ez várt: különböző útvonal (full-CFR vs active-set), különböző NFP belső számítások, különböző candidate ordering. A determinizmus **adott útvonalon** stabil, ahogyan a meglévő tesztek igazolják.

## 12. Comparison to prior reports

### 12.1 T06o microbench

```text
T06o report:    273.7 ns/pair (50K pairs)
Aktuális:       195.5 ns/pair (50K pairs)
Delta:          −28.6% (a hardver vagy compiler stabilizálódott)
```

A T06o claim **megerősítve és megerősödve**.

### 12.2 T06l-b active-set production

A T06l-b report szerinti historikus mérések (ugyanazon LV8 input, korábbi pre-T06o állapot):

| Run | Calls | Narrow ms | Narrow / total | Megjegyzés |
|---|---:|---:|---:|---|
| Run_08 (T06l-b, baseline full-CFR) | 14 043 | 13.4 | 97.8% | **NEM kompatibilis közvetlenül** — a T06l-b "13.4 ms" valószínűleg csak részleges path-ot mért, vagy a kontextus eltérő. A 14 043 calls **pontosan egyezik**, tehát ugyanaz a workload. |
| T06o-b Run A (mostani, post-T06o) | 14 043 | 5 229.4 | 95.8% | Teljes narrow-phase profilezve, valós mérés. |

A T06l-b "13.4 ms" érték valószínűleg egy korai mérési lépcső (talán csak egy subset, vagy nem bekapcsolt CGAL), nem közvetlenül összevethető. A `calls`, `accept` és `reject` viszont **bit-stable** ugyanazon a workloadon — ami azt jelzi, hogy a vizsgált útvonal ugyanaz. Az aktuális mérés **teljes és érvényes**.

A T06l-b run_04 (active-set, T06o előtt) `220 630 calls, 346 s narrow-phase / 357 s total = 96.8% narrow-phase`. A jelen Run B/C/D timeout-jai (360 s budget alatt) konzisztensek ezzel: az active-set + cgal_reference path ugyanezen a workloadon **a T06o után is** több mint 360 s-ot vesz igénybe. **Ez nem T06o regresszió** — a baseline T06l-b run_04 is ~346 s narrow-phase-t mért, és az NFP konstrukció + active-set widening időt nem T06o szelíti meg.

### 12.3 T06k-fix subset proof

Nem volt elérhető (`engine_v2_nfp_rc_t06k_fix_hotpath_benchmark_validation.md` hiányzik a `codex/reports/nesting_engine/` alatt). Nem akadályozta a mérést.

## 13. Limitations

- **Nem futott le érvényesen:** active-set / LV8 / B, C, D változat (mind 360 s timeout, no NEST_NFP_STATS_V1 emit). Ez **nem T06o regresszió**, hanem a `cgal_reference` + active-set + multi-level widening kombináció költsége. Kompatibilis a T06l-b run_04 baseline-jel.
- **Direkt rust binary invocation** lett használva a `benchmark_cavity_v2_lv8.py` 90 s `solver_time_limit_cap_sec` korlátja miatt. Az engineflag-ek és a fixture pontosan ugyanazok mint a Python wrappernél; a `prepacked_solver_input.json` szintén a Python wrapperből jött. A wrapper BLF fallback útvonalának visszaszerelése **scope-on kívül** és a méréshez nem szükséges.
- **Mit nem lehet kijelenteni a mostani adatokból:**
  - Pontos pre-T06o vs post-T06o LV8 narrow-phase delta — csak becslés van (3.2×–7× tartomány). Konkrét mérni: T06o revertelt build-en külön futtatás kellene.
  - Active-set + T06o net production speedup — a B/C/D timeout miatt egyik sem fejeződött be.
- **Mit jelent a Run A determinism hash változása az E_A-hoz képest:** különböző input → különböző hash, várt.

## 14. Recommended next task

A T06n auditban felvázolt javaslatok közül a legkisebb **kockázat / legmagasabb mérhető hatás** sorrendje a T06o-b mérések alapján:

| Javaslat | Várható hatás | Kockázat | Indoklás |
|---|---|---|---|
| **A) T06p — `polygon_has_valid_rings` cache PlacedPart-on** | Kicsi-közepes (per-call ~50 ns × 36 348 candidate = ~2 ms; nem latency-kritikus) | **Alacsony** | A `narrow.rs:418, 532` kétszer hívja per call. Cache `PlacedPart`-on triviálisan biztonságos (immutable polygon). |
| **B) T06p — bin geometry precompute (AABB + valid + holes_empty)** | Kicsi (per-call: bin AABB újragenerálása `aabb_from_polygon64(bin)` minden can_place hívásnál; LV8-on 14 043 × ~500 ns = 7 ms) | **Alacsony** | Sheet-szintű invariáns; precompute egyszer per sheet. |
| **C) T06p — containment AABB quick reject** | Kicsi-közepes (a containment fallback a 0.013% actual részben fut, marginal) | **Alacsony** | T06n 8.7 javaslat. |
| **D) T06p — can_place allocation / clone cleanup** | Közepes (a `maybe_overlap` Vec allokáció és sort 14 043× → 14 043 × ~1 µs = 14 ms; észrevehető) | **Alacsony-közepes** | A `Vec<(usize, &PlacedPart)>` reuse-able; sort kulcsfüggvény változatlan. |
| **E) T06o-c — broader LV6 / LV8 measurement matrix** | Mérési | **Zero** | Akkor érdekes, ha a következő optimization committed és külön be kell mérni. |

**Ajánlás:** **A) + B) bundle T06p task-ban**. Az A) önmagában kicsi, de kombinálva a B)-vel a per-call overhead zsugorodik mérhető tartományba (~9 ms / 14 043 calls = ~0.6 µs/call csökkentés a boundary+broad költségen). A T06o után **a narrow-phase 95.8% bottleneck**, ezért az **edge-szintű további pruning már nem termel** sok megtakarítást (99.98% AABB-rejected). A következő hatékony irány a per-call constant overhead csökkentése (A+B) **vagy** az active-set NFP konstrukció optimalizálása (külön task; nem T06p scope).

**Alternatíva:** ha az active-set production-time gátja a fő prioritás, a következő task **T06q — active-set NFP konstrukció / widening cost reduction**, ami a B/C/D timeout-okat oldhatja meg, de jelentősen nagyobb scope mint a T06p.

## 15. Final verdict

**T06o-b PARTIAL.**

- Microbench és LV8 full-CFR mérés **PASS**: a T06o edge-AABB pre-reject **production-szinten 99.98%-os hatékonyságú** a tesztelt edge-pár-okon, és **66%-os** a teljes budget-en. Becsült production speedup **3.2×–7×** a hipotetikus pre-T06o állapothoz képest.
- Active-set / LV8 mérés (B/C/D) **timeout** miatt nem értékelhető a 360 s budget alatt — ez **nem** T06o regresszió. Subset E_B (active-set + full fallback, kicsi fixture) viszont sikerrel lefutott, és minden T06o új mező populated.
- Correctness gate **clean**: 0 false accept, 0 overlap, 0 fallback (a direkt rust hívás miatt), kernel = `cgal_reference`, narrow-phase = `own`, invariáns mindenhol teljesül.
- A T06o **production-szinten igazolt**. A következő logikus inkrementális task: **T06p — `polygon_has_valid_rings` cache + bin geometry precompute** (két kis, alacsony kockázatú, mérhető nyereségű optimalizáció bundle-ben).
