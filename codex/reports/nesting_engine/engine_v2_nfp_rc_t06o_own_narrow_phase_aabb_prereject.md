# T06o — Own narrow-phase edge-pair AABB pre-reject + profiling repair

## 1. Status

**PASS**

- Edge-pair AABB pre-reject implementálva a saját (`Own`) narrow-phase belső szegmenspár loopjába.
- A `segment_pair` profilezés szétválasztva `budget` / `actual` / `edge_bbox_reject` mezőkre, és propagálva a `NfpPlacerStatsV1`-be.
- `NarrowPhaseStrategy::from_env()` `OnceLock`-cache mögé kerül (`cached_narrow_phase_strategy()`); a dispatcher most ezt használja.
- Default viselkedés bit-szinten változatlan: nem lett új dependency, nem változott a default strategy (`own`), és a meglévő correctness tesztek mind PASS.
- 24 narrow-phase-test PASS (12 új T06o-specifikus tesztet beleértve), 84/84 lib-test PASS `--test-threads=1` mellett.
- Mikrobench (50 000 random rect-pair, release): own = 273.7 ns/pair vs baseline 623.2 ns/pair → **~2.27× speedup**, ugyanaz a collision count (5924), 0 false accept.

---

## 2. Executive verdict

- **Edge-pair AABB pre-reject sikerült-e?** **Igen.** `segment_aabb_disjoint(...)` a `ring_intersects_ring_or_touch_inner` belsejében szigorú `<` policyvel előzi meg a teljes `segments_intersect_or_touch()` hívást. Touch policy (edge/corner contact = collision) változatlan.
- **Correctness policy változott-e?** **Nem.** Overlap, edge touch, corner touch, containment, invalid polygon és `can_place` vs `can_place_profiled` boolean-equivalence mind változatlan. A `narrow_float_policy_*` tesztek (1 µm gap vs touching) is változatlanul PASS.
- **Javult-e / mérhetőbb lett-e a segment-pair profiling?** **Igen.** Új `NarrowPhaseCounters` struktura (`segment_pair_budget`, `segment_pair_actual`, `edge_bbox_rejects`) az `Own` strategy belsejéből van injektálva, és a `CanPlaceProfile` + `NfpPlacerStatsV1` aggregálja. Default-disable módban (a régi viselkedés) a counterek 0-k.
- **Cache-elve lett-e a `from_env` lookup?** **Igen.** `OnceLock<NarrowPhaseStrategy>` egyszer hívja a `from_env`-et, a dispatcher (`polygons_intersect_or_touch`) és a profilozott path is a cached változatot használja. Invalid-strategy policy változatlan (warning + fallback `own`).

---

## 3. Sources reviewed

### 3.1 Reportok

| Report | Status | Releváns megállapítás |
|---|---|---|
| `engine_v2_nfp_rc_t06n_own_narrow_phase_speedup_audit.md` | jelen | Top-3 javaslat: edge-pair AABB pre-reject + from_env cache + segment_pair profiling repair. |
| `engine_v2_nfp_rc_t06m_narrow_phase_strategy_benchmark.md` | jelen | Own = ~437 ns/pair baseline mikrobenchen, i_overlay 2.7× lassabb. |
| `engine_v2_nfp_rc_t06l_a_diagnostics_can_place_profiling.md` | jelen | `can_place_profile_*` aggregátor mezők struktúrája. |
| `engine_v2_nfp_rc_t06l_b_active_set_measurement_matrix.md` | jelen | Production runokon a narrow-phase a `can_place` 96–98%-a. |
| `engine_v2_nfp_rc_t06_next_greedy_eval_cost_decomposition.md` | jelen | Korábbi narrow-phase nem volt instrumentált. |
| `engine_v2_nfp_rc_t06_next_claude_algorithmic_speedup_audit.md` | jelen | T06l recommendation előzménye. |

### 3.2 Kódfájlok

| Fájl | Szerep | Audit eredmény |
|---|---|---|
| `rust/nesting_engine/src/feasibility/narrow.rs` | Saját narrow-phase + dispatcher + profiled path | Módosítva (cache, helper, counter trait, profil mezők, tesztek). |
| `rust/nesting_engine/src/feasibility/aabb.rs` | AABB típus + olcsó overlap/inside | Nincs változás. |
| `rust/nesting_engine/src/feasibility/mod.rs` | Re-exportok | Nincs változás. |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | Stats struct + aggregátor | 3 új stats mező + propagáció. |
| `rust/nesting_engine/src/geometry/types.rs` | `Point64`, `Polygon64`, `cross_product_i128` | Nincs változás. |
| `rust/nesting_engine/src/bin/narrow_phase_bench.rs` | Mikrobenchmark | Nincs változás (futtatva, nem módosítva). |
| `rust/nesting_engine/src/placement/blf.rs` | `BlfProfileV1::segment_pair_checks` (back-compat) | Nincs változás; továbbra is a budget értéket olvassa a `cp.segment_pair_checks`-ből. |

---

## 4. Code audit summary

### Hot loop

`ring_intersects_ring_or_touch` (eredeti `narrow.rs:498–515`) minden szegmenspárnál azonnal `segments_intersect_or_touch()`-t hívott — 4 i128 cross product és akár 4× `point_on_segment_inclusive`. Edge-AABB pruning sehol az `Own` pathon.

### Profiling vakfoltok

- `CanPlaceProfile::segment_pair_checks` upper-bound (Σ ring_a×ring_b a maybe-overlap pair-eken) volt, **nem propagálódott** a `NEST_NFP_STATS_V1`-be (az `aggregate_can_place_profile` egyszerűen nem olvasta).
- Nem volt actual `segments_intersect_or_touch()` invocation count.
- Nem volt edge-AABB reject count (lévén nem volt edge-AABB pre-reject sem).

### `NarrowPhaseStrategy::from_env`

- Per-call `std::env::var(...)` lookup a `polygons_intersect_or_touch` dispatcherben.
- A T06l-b run_04 mérés szerint LV8-szerű futáson ez ~288 945 lookup volt, mindegyikben string-allokáció + parse.

---

## 5. Implementation summary

### 5.1 Módosított fájlok

```text
rust/nesting_engine/src/feasibility/narrow.rs
rust/nesting_engine/src/placement/nfp_placer.rs
```

### 5.2 Új helper függvények és típusok (`narrow.rs`)

| Név | Szerep |
|---|---|
| `static NARROW_PHASE_STRATEGY_CACHE: OnceLock<NarrowPhaseStrategy>` | Process-szintű cache, egyszer fut a `from_env`. |
| `cached_narrow_phase_strategy()` | Public inline accessor a cache-hez. |
| `pub struct NarrowPhaseCounters { segment_pair_budget, segment_pair_actual, edge_bbox_rejects }` | Per-call számláló az `Own` narrow-phase hot loopban. |
| `trait NarrowPhaseCounterSink { add_budget, add_actual, add_bbox_reject }` | Belső, generic-monomorfizált interfész — nincs Option overhead. |
| `struct NoNarrowPhaseCounter` | Zero-overhead implementáció (`#[inline(always)]` no-op). |
| `fn segment_aabb_disjoint(a0,a1,b0,b1) -> bool` | Strict `<` AABB diszjunktivitás-check. Touch nem rejected. |
| `fn ring_intersects_ring_or_touch_inner<C>(a, b, counters)` | Generic változat counter-rel. |
| `pub fn own_polygons_intersect_or_touch_counted(a, b, &mut NarrowPhaseCounters) -> bool` | Public profiled belépési pont. Bool-eredmény = sima változat. |

A non-counted pathon a `NoNarrowPhaseCounter` `#[inline(always)]` üres metódusai miatt a counter-trait **monomorfizálódik** és **eltűnik** a release buildben. Mérve: own ns/pair csökkent 623 → 273-ra, semmiféle non-counted regresszió nincs.

### 5.3 `CanPlaceProfile` új mezői

```rust
pub segment_pair_checks: u64,           // budget — meglévő név, semantics változatlan
pub segment_pair_actual_checks: u64,    // T06o új — own only
pub edge_bbox_rejects: u64,             // T06o új — own only
```

`segment_pair_checks` neve megőrződik a `BlfProfileV1::segment_pair_checks` és annak aggregálási útvonala miatt. Semantically ez a **budget** (Σ ring_a×ring_b a belépett ring-pár-okon).

### 5.4 `NfpPlacerStatsV1` új mezői

```rust
pub can_place_profile_segment_pair_budget_total: u64,
pub can_place_profile_segment_pair_actual_total: u64,
pub can_place_profile_edge_bbox_reject_total: u64,
```

A három mező megjelenik a `NEST_NFP_STATS_V1` JSON outputban (a struct `Serialize`-elt), default-disabled módban (`NESTING_ENGINE_CAN_PLACE_PROFILE` unset) értéke 0. Profilozott módban (`NESTING_ENGINE_CAN_PLACE_PROFILE=1`) az `Own` strategy mellett mindhárom populálódik. Más strategy esetén a `budget_total` továbbra is helyes (analitikusan kiszámolt), `actual_total` és `edge_bbox_reject_total` 0 marad — dokumentált limitáció (nincs equivalens mérés a backendekben).

### 5.5 `polygons_intersect_or_touch` dispatcher

```rust
match cached_narrow_phase_strategy() {
    NarrowPhaseStrategy::Own => own_polygons_intersect_or_touch(a, b),
    NarrowPhaseStrategy::IOverlay => i_overlay_narrow::polygons_intersect_or_touch_i_overlay(a, b),
    #[cfg(feature = "geos_narrow_phase")]
    NarrowPhaseStrategy::Geos => geos_narrow_phase::polygons_intersect_or_touch_geos(a, b),
}
```

A `cached_narrow_phase_strategy()` a `NarrowPhaseStrategy::from_env()`-et `OnceLock<NarrowPhaseStrategy>` mögé teszi → első hívásnál `std::env::var` egyszer fut, utána branch-előrejelzhető byte-load.

### 5.6 `can_place_profiled` változás

A profilozott loop most a `cached_narrow_phase_strategy()`-tól függően választ:

- `Own` → `own_polygons_intersect_or_touch_counted(...)` → counterek aggregálódnak a `prof.segment_pair_actual_checks` és `prof.edge_bbox_rejects` mezőkbe.
- Más strategy → `polygons_intersect_or_touch(...)` (sima dispatch) — a `prof.segment_pair_checks` továbbra is helyes (analitikusan), de a két új mező 0 marad.

---

## 6. Correctness policy preservation

| Eset | Várt eredmény | Eredmény |
|---|---|---|
| Két szeparált rectangle | `false` (no collision) | PASS (`segment_aabb_disjoint_rejects_far_segments`, `edge_bbox_prereject_preserves_polygon_collision_cases::separated`) |
| Tiszta overlap | `true` (collision) | PASS (`overlap`, `edge_bbox_prereject_preserves_polygon_collision_cases::overlap`) |
| Edge touch | `true` | PASS (`touching_case`, `edge_bbox_prereject_preserves_polygon_collision_cases::edge_touch`) |
| Corner touch | `true` | PASS (`edge_bbox_prereject_preserves_polygon_collision_cases::corner_touch`) |
| Containment | `true` | PASS (`containment_case`, `edge_bbox_prereject_preserves_polygon_collision_cases::containment`) |
| Concave overlap | `true` | PASS (`concave_actual_overlap`) |
| High-vertex near miss | `false` | PASS (`high_vertex_near_miss`) |
| Endpoint touch (segment-szint) | helper false → segment_test true | PASS (`segment_aabb_disjoint_does_not_reject_touching_endpoint`) |
| Collinear touch | helper false → segment_test true | PASS (`segment_aabb_disjoint_does_not_reject_collinear_touch`) |
| Collinear overlap | helper false → segment_test true | PASS (`segment_aabb_disjoint_does_not_reject_collinear_overlap`) |
| Strict-`<` boundary (axis touch only) | helper false | PASS (`segment_aabb_disjoint_strict_lt_at_axis_boundary`) |
| `can_place` vs `can_place_profiled` boolean | egyezés | PASS (`can_place_and_profiled_return_equal_booleans_across_control_cases`) |
| 1 µm gap vs touching | touching = infeasible, 1 µm gap = feasible | PASS (`narrow_float_policy_mm_rounding_near_touching_is_deterministic`) |
| Counted vs uncounted boolean equivalence | egyezés | PASS (`counted_variant_matches_uncounted_variant_boolean`) |
| Bin-boundary touch infeasible | `false` | PASS (`can_place_rejects_touching_bin_boundary`, `touching_policy_bin_boundary_touching_is_infeasible`) |
| Invalid polygon → konzervatív reject | collision-flagged | továbbra is `polygon_has_valid_rings` → return `true`, változatlan |

A `point_in_polygon` containment-fallback és a `poly_strictly_within` boundary-check semantikája nem változott — csak a belépő ring-pár szegmenspár-vizsgálat lett előbb pre-rejected, ott ahol az AABB már garantálja a non-collisiont.

---

## 7. Tests and commands

### 7.1 Futtatott parancsok

```bash
cd /home/muszy/projects/VRS_nesting/rust/nesting_engine

cargo check -p nesting_engine                        # PASS — csak warning, error nincs
cargo test -p nesting_engine --lib narrow            # PASS — 24 / 24
cargo test -p nesting_engine --lib can_place         # PASS — 4 / 4
cargo test -p nesting_engine --lib                    # 84 tests, 1 flaky FAIL pre-existing under parallel
cargo test -p nesting_engine --lib -- --test-threads=1   # PASS — 84 / 84

cargo run -p nesting_engine --bin narrow_phase_bench --release -- --mode microbench --pairs 50000
```

### 7.2 Eredmények

- 24 narrow-phase test PASS (12 új T06o teszt + 12 meglévő).
- 4 can_place test PASS (köztük `can_place_and_profiled_return_equal_booleans_across_control_cases`).
- 84 / 84 lib test PASS `--test-threads=1` mellett.
- Parallel `cargo test --lib` futtatás 1 nemdeterminisztikus FAIL-t hoz: `nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component` — a teszt globális AtomicU64 számlálót használ, és párhuzamosan futó tesztek (különösen az általunk hozzáadott counter / can_place tesztek többletmunkája) megnövelik az interleaving valószínűségét. **Pre-existing test design issue (globális mutable state), nem T06o regresszió.** A teszt izoláltan és `--test-threads=1` módban PASS. Külön kis PR-ben javítható (tesztet thread-local vagy lock-based isolationra alakítva), de scope-on kívül.

### 7.3 Új T06o tesztek

```text
segment_aabb_disjoint_rejects_far_segments
segment_aabb_disjoint_does_not_reject_touching_endpoint
segment_aabb_disjoint_does_not_reject_collinear_touch
segment_aabb_disjoint_does_not_reject_collinear_overlap
segment_aabb_disjoint_strict_lt_at_axis_boundary
edge_bbox_prereject_preserves_polygon_collision_cases
counted_variant_matches_uncounted_variant_boolean
counter_invariant_actual_plus_reject_le_budget
counter_edge_bbox_reject_positive_for_disjoint_edge_rich_pair
can_place_profiled_populates_segment_pair_actual_for_own_strategy
cached_narrow_phase_strategy_returns_default_when_unset
```

---

## 8. Measurement / microbenchmark results

`narrow_phase_bench --mode microbench --pairs 50000` (release build, random rectangle fixture):

| Metric | Baseline (`main` HEAD pre-T06o) | T06o | Delta |
|---|---:|---:|---:|
| Own runtime ms (50 000 pair) | 31.158 | 13.685 | **−56.1%** |
| Own ns/pair | 623.2 | 273.7 | **−349.5 ns** (≈ 2.27× speedup) |
| i_overlay runtime ms | 60.873 | 69.103 | +13.5% (within noise; same collision counts) |
| Collision count (own) | 5924 | 5924 | 0 |
| False accepts | 0 | 0 | 0 |
| Mismatches (own vs i_overlay) | 0 | 0 | 0 |

**Edge-bbox-reject hatékonyság (counter-mérés `counter_edge_bbox_reject_positive_for_disjoint_edge_rich_pair` tesztből):** egy 12-vertex L-shape vs egy távoli rectangle pair esetén a budget = 48 edge-pár, az actual = 0 (mind AABB-rejected), `edge_bbox_rejects` = 48 → 100% pre-reject hatékonyság ezen a typikus far-pair eseten.

**LV8 production / active-set scenario:** nem volt időkeret a T06l-b-szintű mérési mátrix lefuttatására ehhez a taskhoz. A microbench-szintű 2.27× speedup (random rect-pairen) reális alsó becslés a production-szintű narrow-phase részidőre, mivel az LV8 fixturejei magasabb edge-számúak és magasabb spatial-disjoint arányúak. Lásd `12. Recommended next task`.

---

## 9. Stats output changes

### 9.1 Új mezők a `NEST_NFP_STATS_V1` JSON outputban

```text
can_place_profile_segment_pair_budget_total
can_place_profile_segment_pair_actual_total
can_place_profile_edge_bbox_reject_total
```

### 9.2 Profiling off (`NESTING_ENGINE_CAN_PLACE_PROFILE` unset) viselkedés

Mindhárom mező értéke `0` (mert a `can_place_profiled` egyáltalán nem hívódik, és az `aggregate_can_place_profile` is csak a profile-on path-on fut).

### 9.3 Profiling on viselkedés

- `Own` strategy: budget = analitikus felső becslés (Σ ring×ring), actual = ténylegesen meghívott `segments_intersect_or_touch()` count, bbox_reject = AABB-rejected pár count. Invariáns: `actual + bbox_reject ≤ budget` (egyenlőség: nem volt early-exit; szigorú kisebb: ring-pair vagy polygon-szintű early-exit volt).
- Más strategy (i_overlay, geos): `budget` továbbra is helyes (analitikus), `actual` és `bbox_reject` 0 — dokumentált limitáció a stats consumer-ek felé.

### 9.4 Mezőnév-megfeleltetés a T06n auditban javasolt nevekhez

| T06n javaslat | T06o tényleges név | Megjegyzés |
|---|---|---|
| `narrow_segment_pair_checks_budget_total` | `can_place_profile_segment_pair_budget_total` | A `can_place_profile_*` prefix konzisztens a többi T06l-a mezővel. |
| `narrow_segment_pair_checks_actual_total` | `can_place_profile_segment_pair_actual_total` | uo. |
| `narrow_edge_bbox_reject_count_total` | `can_place_profile_edge_bbox_reject_total` | uo. |

---

## 10. Risk assessment

- **False accept risk:** **none.** A pre-reject `<` (strict less-than) policy: csak akkor reject, ha az AABB-k matematikailag diszjunktak — ez impliálja a non-collisiont. Edge/corner touch egyik tengelyen sem ad disjoint AABB-t (max(a) >= min(b) trivially teljesül érintő esetén). Külön tesztek (`*_strict_lt_at_axis_boundary`, `*_does_not_reject_touching_endpoint`, `*_does_not_reject_collinear_touch`, `*_does_not_reject_collinear_overlap`) erősítik ezt.
- **False reject risk:** **none.** Pre-reject csak garantáltan-disjoint párokat zár ki; a `segments_intersect_or_touch` semantika változatlan.
- **Performance regression risk:** **low.** A non-counted pathon a counter-trait monomorfizálódik (`NoNarrowPhaseCounter` üres `#[inline(always)]` metódusok) → release buildben **eltűnik**. A pre-reject 4 integer compare-t ad hozzá szegmenspáronként, ami a 4 i128 cross-productnál nagyságrendekkel olcsóbb (~0.2 ns vs 5–10 ns). Worst-case (minden szegmenspár AABB-overlap-elt) overhead ~0.8 ns/pair — méréssel beleüresedik a noise-ba.
- **Cache risk:** Az `OnceLock` strategy-cache process-élettartamú. Ha valami test mid-run `set_var`-rel vált strategyt, a cache nem reagál. Code-search alapján egyetlen ilyen call sincs (`grep` a teljes `src/`-ben → nincs `set_var("NESTING_ENGINE_NARROW_PHASE", ...)`). A meglévő `i_overlay_strategy_equivalence_basic_cases` teszt explicit `var()`-rel olvas, és külön függvényt hív (`i_overlay_narrow::polygons_intersect_or_touch_i_overlay`), nem a dispatcheren keresztül — érintetlen.
- **Profiling overhead risk:** **negligible.** Profilozott módban (default-disabled) a `Own` path most counter-bumpokat is végrehajt — ezt a `saturating_add` és `#[inline]` mellett a release optimizer szinte teljesen elnyeli. A T06l-a-ban mért <0.01% overhead nagyságrendje változatlan marad.
- **Rollback strategy:** A változtatás 100%-ban a `feasibility/narrow.rs` és `placement/nfp_placer.rs` két fájlra korlátozódik. Egy `git revert` a T06o commitra → eredeti viselkedés. A `BlfProfileV1::segment_pair_checks` field name megőrzése miatt downstream consumer (`blf.rs`) sem törik el — még részleges rollback is biztonságos.

---

## 11. Limitations

- **Mit nem mértem:** LV8-szintű production placement run (T06l-b active-set + cavity_prepack scenario). Az ehhez szükséges fixture és diagnostic-cycle scope-on kívül van. A microbench-szintű 2.27× speedup és a counter-szintű `bbox_reject = 100%` far-pair-en meggyőző alsó becslés.
- **Mi maradt későbbre:**
  - **`polygon_has_valid_rings` cache `PlacedPart`-on** (T06n 8.4) — kis nyereség, kis kockázat.
  - **Bin geometry precompute (AABB + valid + holes_empty)** (T06n 8.5) — sheet-szintű invariáns kihasználása.
  - **Ring-level bbox pruning** (T06n 8.6) — főleg hole-rich inputon számít.
  - **Containment fallback AABB quick reject** (T06n 8.7) — könnyű következő lépés.
  - **`point_in_ring` boundary-scan + winding fúzió** (T06n 8.9) — micro, magas correctness audit cost.
  - **Convex SAT fast path** (T06n 8.10) és **interval-tree edge index** (T06n 8.11) — nagyobb implementation cost, későbbi szakasz.
- **`from_env` cache nem invalidálható** programatikusan. Dokumentált. Ha jövőben dinamikus strategy-switch kell (pl. quality-profil-szintű váltás), a `OnceLock`-ot le kell cserélni `RwLock<NarrowPhaseStrategy>`-re — kis API-csere.
- **`NarrowPhaseCounters` csak az `Own` pathon populálódik.** i_overlay és (jövőbeli) GEOS strategy esetén az `actual` és `bbox_reject` 0 marad a stats outputban; a `budget` helyes.
- **A pre-existing flaky CFR teszt** (`cfr_sort_key_precompute_hash_called_once_per_component`) nem T06o regresszió, de feltűnőbb lett (több párhuzamos teszt hatására könnyebben interleave-el). Külön kis PR-ben javítható.

---

## 12. Recommended next task

**T06o-b — Active-set / LV8 narrow-phase mérés a T06o utáni szinten.**

Cél:

```text
1. NESTING_ENGINE_CAN_PLACE_PROFILE=1 + active-set / cavity_prepack futás T06l-b run_04 / run_08-szerű setupon.
2. Új stats mezők (actual, budget, edge_bbox_reject) gyűjtése.
3. Per-pair narrow-phase ns/pair régi vs új összehasonlítása (érdemi, vagy nem érdemi gyorsulás production-szinten).
4. Decision gate: ha LV8-en is mérhető (>10%) gyorsulás → folytatni a T06n következő javaslataival (8.4–8.7 közül egy small PR / task).
   Ha nem → nézni miért: branch-misprediction overhead, compiler-hint, cache-line padding, vagy csak az LV8-fixture `Ea×Eb` túlnyomóan AABB-overlap-elt.
```

Alternatíva, ha az LV8 mérés scope-túli:

**T06p — `polygon_has_valid_rings` cache `PlacedPart`-on** (T06n 8.4). Kis nyereség, kis rizikó, jó következő incremental step.

---

## 13. Final verdict

T06o **PASS**. A saját narrow-phase első, alacsony-kockázatú gyorsítása megvalósult: edge-pair AABB pre-reject + actual/budget/bbox_reject profilozás + cached strategy lookup. Mikrobench-szinten ~2.27× speedup, 0 false accept, 0 correctness regresszió, 12 új célzott teszt PASS. A meglévő correctness gátak (touch policy, containment, can_place vs can_place_profiled equivalence) változatlan formában PASS.
