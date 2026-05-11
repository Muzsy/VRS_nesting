# T06n — Own narrow-phase speedup audit

## 1. Status

**PASS**

- Audit-only futás. Production kód nem módosult (csak a már korábban dirty `nfp_placer.rs` a worktree-ben).
- A saját `own` narrow-phase pontos call graphja, költségmodellje, és correctness policy-ja dokumentálva.
- 12 konkrét gyorsítási javaslat dokumentálva, mindegyik external-library-független, false-accept risk értékelve.
- Konkrét következő implementációs task megfogalmazva (edge-pair AABB pre-reject + segment_pair_checks profiling repair).

---

## 2. Executive verdict

- **Gyorsítható-e érdemben a saját narrow-phase?** **Igen.** A T06l-b mérés alapján a `can_place` költség 96–98%-a `polygons_intersect_or_touch()` (narrow-phase). Több, alacsony kockázatú (low-risk) micro-opt forrás létezik a jelenlegi kódban.
- **Top 3 első beavatkozás (rangsorolva):**
  1. **Edge-pair AABB pre-reject** a [narrow.rs:498–515](rust/nesting_engine/src/feasibility/narrow.rs#L498-L515) `ring_intersects_ring_or_touch` belső szegmenspár loopjába (4 integer compare a `segments_intersect_or_touch` előtt). Várható nagy nyereség, false-accept risk = 0, unit-teszttel könnyen védhető.
  2. **`NarrowPhaseStrategy::from_env()` caching** ([narrow.rs:319–328](rust/nesting_engine/src/feasibility/narrow.rs#L319-L328)) — jelenleg minden ring-pár szintű hívás (százezres nagyságrend egy LV8 futáson) végez egy `std::env::var()` lookupot. `OnceLock<NarrowPhaseStrategy>` cseréli le. Triviális, nincs viselkedésváltozás default módban.
  3. **`segment_pair_checks` profiling repair + propagation** ([narrow.rs:441–449](rust/nesting_engine/src/feasibility/narrow.rs#L441-L449), [nfp_placer.rs:280–283](rust/nesting_engine/src/placement/nfp_placer.rs#L280-L283)). A jelenlegi szám az upper-bound (Σ ring×ring vertex), nem a ténylegesen lefuttatott edge-pair vizsgálatok száma; emellett a stats aggregátor a mezőt nem továbbítja a `NEST_NFP_STATS_V1`-be. Mérési vakfolt javítás a következő optimalizációkhoz.
- **Mit NEM javasolt elsőként:**
  - Sweep-line / BVH / interval-tree alapú szegmensindex → magas implementation-complexity, kis polygon vertex-számra negatív speedup.
  - Convex polygon SAT fast path → LV8 inputjában dominánsan konkáv alakzatok, nyereség marginális.
  - `point_in_ring` boundary-scan + winding loop fúzió → micro, méghozzá a jelenlegi két-loop forma jól verifikálható.
  - Approximate-collision elfogadás bármilyen formában → szabálytalan policy-sértés.

---

## 3. Sources reviewed

### 3.1 Reportok

| Report | Status | Releváns megállapítás |
|---|---|---|
| `engine_v2_nfp_rc_t06m_narrow_phase_strategy_benchmark.md` | jelen | Own = 437 ns/pair (random rect microbench), i_overlay 2.7× lassabb, GEOS skip. Own marad default. |
| `engine_v2_nfp_rc_t06l_a_diagnostics_can_place_profiling.md` | jelen | `can_place_profile_*` 14 mező aggregálva. Default path bit-for-bit identikus. |
| `engine_v2_nfp_rc_t06l_b_active_set_measurement_matrix.md` | jelen | Run_04 active-set: 220,630 calls, 346s narrow-phase / 357s total = **96.8% narrow-phase**. Run_08 baseline: 14,043 calls, 13.4ms narrow / 13.7ms total = **97.8% narrow-phase**. Production per-pair ≈ 1,198 ns/pair (LV8 valódi alakzatokon). |
| `engine_v2_nfp_rc_t06_next_claude_algorithmic_speedup_audit.md` | jelen | T06l = recommendation A (eprintln gating + can_place profiling). |
| `engine_v2_nfp_rc_t06_next_greedy_eval_cost_decomposition.md` | jelen | A korábbi T06-next mérés explicit megjegyzi: `can_place / broad-phase / narrow-phase nem volt instrumentált` — most már igen, T06l-a óta. |
| `engine_v2_nfp_rc_t06k_fix_hotpath_benchmark_validation.md` | jelen | Hotpath benchmark validation kontextus. |

### 3.2 Kódfájlok

| Fájl | LOC | Audit cél |
|---|---|---|
| [rust/nesting_engine/src/feasibility/narrow.rs](rust/nesting_engine/src/feasibility/narrow.rs) | 971 | Saját narrow-phase, profiled variant, dispatcher |
| [rust/nesting_engine/src/feasibility/aabb.rs](rust/nesting_engine/src/feasibility/aabb.rs) | 54 | AABB típus + olcsó overlap/inside helperek |
| [rust/nesting_engine/src/feasibility/mod.rs](rust/nesting_engine/src/feasibility/mod.rs) | 11 | Re-exportok |
| [rust/nesting_engine/src/placement/nfp_placer.rs](rust/nesting_engine/src/placement/nfp_placer.rs) | 2857 | `can_place_dispatch`, `aggregate_can_place_profile`, `PlacedPart` konstrukciós call site-ok |
| [rust/nesting_engine/src/geometry/types.rs](rust/nesting_engine/src/geometry/types.rs) | 143 | `Point64`, `Polygon64`, `cross_product_i128`, `is_convex` |

---

## 4. Current `can_place` / narrow-phase call graph

```
can_place(candidate, bin, placed)                                  [narrow.rs:330]
├── polygon_has_valid_rings(candidate)                             [narrow.rs:462]   — recomputed every call
├── polygon_has_valid_rings(bin)                                   [narrow.rs:462]   — recomputed every call (bin invariant!)
├── aabb_from_polygon64(candidate)                                 [aabb.rs:52]      — O(|outer|) every call
├── aabb_from_polygon64(bin)                                       [aabb.rs:52]      — O(|outer|) every call (bin invariant!)
├── aabb_inside(&bin_aabb, &candidate_aabb)                        [aabb.rs:45]      — bin-bbox quick reject (cheap)
├── poly_strictly_within(candidate, bin)                           [narrow.rs:466]
│   ├── polygon_has_valid_rings(candidate)        ── recomputed (third time!)
│   ├── polygon_has_valid_rings(bin)              ── recomputed (third time!)
│   ├── for vertex in candidate.outer:
│   │     point_in_polygon(vertex, bin)           [narrow.rs:517] ── O(|bin.outer| + Σ|bin.holes|) per vertex
│   ├── ring_intersects_polygon_boundaries(candidate.outer, bin)   [narrow.rs:494]
│   │     └── for each ring of bin:
│   │            ring_intersects_ring_or_touch(candidate.outer, ring)   [narrow.rs:498]
│   │                  └── for ea in candidate.outer × eb in ring:
│   │                        segments_intersect_or_touch(...)     [narrow.rs:608]   ← inner-most hot loop
│   └── for hole in container.holes:                              ── usually empty for prepacked LV8
│           point_in_polygon(hole[0], candidate)
├── placed.query_overlaps(candidate_aabb)                          [narrow.rs:277]   — RTree broad-phase
├── filter aabb_overlaps(candidate_aabb, p.aabb)                   [aabb.rs:37]      — TOUCH_TOL slack overlap
├── sort by (min_x, min_y, max_x, max_y, idx)
└── for (_, other) in maybe_overlap:
        polygons_intersect_or_touch(candidate, &other.inflated_polygon)   [narrow.rs:319]
        ├── NarrowPhaseStrategy::from_env()                         [narrow.rs:35]   ← env var lookup PER CALL
        └── own_polygons_intersect_or_touch(a, b)                   [narrow.rs:301]
            ├── polygon_has_valid_rings(a)                         ── recomputed each pair
            ├── polygon_has_valid_rings(b)                         ── recomputed each pair (placed invariant!)
            ├── for ring_a in polygon_rings(a):                    [narrow.rs:490]   ── once+chain iter
            │     for ring_b in polygon_rings(b):
            │        ring_intersects_ring_or_touch(ring_a, ring_b) ── O(Ea × Eb) — no ring-bbox prune
            │           └── segments_intersect_or_touch(a0,a1,b0,b1) — no edge-bbox prune
            │                ├── 4× orient (4× cross_product_i128, all i128)
            │                └── up to 4× point_on_segment_inclusive
            └── point_in_polygon(a.outer[0], b) || point_in_polygon(b.outer[0], a)  ── containment fallback
                  └── point_in_ring(point, ring)                    [narrow.rs:534]
                        ├── O(|ring|) boundary scan via point_on_segment_inclusive (full pass first)
                        └── O(|ring|) winding loop (second pass)    ── 2× ring traversal even when far from edges
```

### Observations on the graph

- **`polygon_has_valid_rings` runs up to 7×** per `can_place` call (twice in `can_place`, twice inside `poly_strictly_within`, twice inside each call to `own_polygons_intersect_or_touch` — once per maybe-overlap pair).
- **`aabb_from_polygon64(bin)` runs once per call** even though `bin` does not change throughout a sheet placement loop; `bin` is identical across all `can_place_dispatch` call sites within a sheet (see [nfp_placer.rs:975, 1065, 1183, 1494, 1579](rust/nesting_engine/src/placement/nfp_placer.rs#L975) — the `bin_polygon` is the same reference).
- **`NarrowPhaseStrategy::from_env()` runs per maybe-overlap pair** — for run_04 in T06l-b that means **288,945 env var lookups in a single placement run**, plus another lookup tree from `is_can_place_profile_enabled()` etc.
- **No edge-level AABB pruning** anywhere on the path. `segments_intersect_or_touch` always commits to 4 i128 multiplies up front.
- **`point_in_ring` is two passes** even when point is far from the ring boundary (the boundary scan never short-circuits early on a near-trivial point).

---

## 5. Current correctness policy (must NOT regress)

```
overlap                    → collision (infeasible)
edge touch                 → collision (infeasible)
corner / point touch       → collision (infeasible)
containment (a ⊂ b)        → collision (infeasible)
container hole containment → infeasible
invalid polygon ring       → conservative reject (treated as collision)
boundary touch with bin    → infeasible (bin-touch = collision per policy)
false accept tolerance     → 0
```

Implementation evidence:

- `polygons_intersect_or_touch` returns `true` (= collision) on `polygon_has_valid_rings(...)` failure → conservative reject.
- `aabb_overlaps` uses `TOUCH_TOL` slack on both sides → broad-phase is conservative.
- `can_place` returns `false` on touch in narrow-phase `polygons_intersect_or_touch` (boundary contact = collision).
- Bin boundary touch: `poly_strictly_within` requires every candidate.outer vertex to be **`Inside`** (not `OnBoundary`) → `OnBoundary` is rejected. Confirmed by test `can_place_rejects_touching_bin_boundary`.
- Boolean equivalence between `can_place` and `can_place_profiled.0` is enforced by test `can_place_and_profiled_return_equal_booleans_across_control_cases` ([narrow.rs:813](rust/nesting_engine/src/feasibility/narrow.rs#L813)).

Any optimization that risks promoting `Inside` → `OnBoundary` ambiguity, dropping touch detection, or short-circuiting based on approximate predicates is rejected outright.

---

## 6. Cost model

| Komponens | Hely | Hívási gyakoriság | Skálázódási driver | Meglévő mérés | Hiányzó mérés | Bottleneck valószínűség |
|---|---|---|---|---|---|---|
| `polygon_has_valid_rings` recompute | narrow.rs:462 | 7× per `can_place` call worst case | O(\|outer\| + Σ\|holes\|) | nincs | per-call elapsed | low (egyenként olcsó, de redundáns) |
| `aabb_from_polygon64(bin)` recompute | narrow.rs:336, 403 | 1× per `can_place` call | O(\|bin.outer\|) | nincs | bin-AABB compute time | low–medium (LV8 bin polygon kis vertex-szám) |
| `poly_strictly_within` boundary check | narrow.rs:466 | 1× per `can_place` call (ha AABB-inside) | O(\|cand.outer\| × (\|bin.outer\|+holes)) point-in-polygon + ring×ring boundary intersection | `poly_within_ns` (jelen) | per-vertex cost split | medium (T06l-b: ~9.7s in run_04) |
| broad-phase RTree query | narrow.rs:277 | 1× per `can_place` call | O(log n + k) | `overlap_query_ns`, `overlap_candidates` | nincs | low (T06l-b: ~0.4s vs 346s narrow) |
| `polygons_intersect_or_touch` per pair | narrow.rs:319 | k× per call (k = maybe_overlap.len(), átl. ~1.3) | O(Ea × Eb) inner; +O(\|outer\|) containment fallback | `narrow_phase_ns`, `narrow_phase_pairs` | per-pair time, per-edge-pair count | **HIGH** (T06l-b: 96–98% of can_place wall) |
| `NarrowPhaseStrategy::from_env()` | narrow.rs:35 | k× per call (per maybe-overlap pair) | O(env var len) | nincs | per-call elapsed | low (egyedileg olcsó, de számossága magas) |
| `segments_intersect_or_touch` | narrow.rs:608 | (Σ Ea×Eb across ring-pairs and overlap pairs) | 4× i128 mul + up to 4× i128 cross | nincs | actually-executed count | **HIGH** (a tényleges micro-hot loop) |
| `point_in_ring` (két-pass) | narrow.rs:534 | a containment fallback és poly_strictly_within mentén | O(2 × \|ring\|) per pont | nincs | per-call elapsed | low–medium |

**Per-pair observed cost (T06l-b run_04):** `narrow_phase_ns_total / narrow_phase_pair_count_total = 346,057 ms / 288,945 = ~1,198 ns/pair`. Microbench (T06m random rect): 437 ns/pair. A 2.7× szorzó az LV8 valódi konkáv alakzatok edge-számának köszönhető.

---

## 7. Profiling accuracy audit

### 7.1 `segment_pair_checks` jelenlegi viselkedése — gyanús

A [narrow.rs:443–449](rust/nesting_engine/src/feasibility/narrow.rs#L443-L449) blokk minden maybe-overlap pair előtt **mindig** a teljes `Σ ring_a.len() × ring_b.len()` szorzatot hozzáadja, függetlenül attól, hogy a tényleges narrow-phase loop early-exitelt-e. Ez **upper bound**, nem actual count. Az inner `polygons_intersect_or_touch` az első ring-pár találatra kilép, így a valós végrehajtott `segments_intersect_or_touch` hívások száma drasztikusan kevesebb lehet.

A számláló továbbá **nem propagálódik** a `NEST_NFP_STATS_V1`-be: az `aggregate_can_place_profile` ([nfp_placer.rs:246–296](rust/nesting_engine/src/placement/nfp_placer.rs#L246-L296)) a `profile.segment_pair_checks` mezőt egyáltalán nem olvassa, ezért semmilyen run a `segment_pair_checks` valós értékét nem látja a stats kimeneten. Ez egyszerre dokumentálandó hiányosság és vakfolt.

### 7.2 `narrow_phase_pairs`

Az értelme: hány maybe-overlap par mentén hívódott meg `polygons_intersect_or_touch`. Az implementáció pre-incrementál: a számláló nő **mielőtt** az inner `polygons_intersect_or_touch` lefutna, tehát az utolsó (a rejekciót okozó) párt is beleszámolja. Ez konzisztens definíció és helyes. Nincs javítás szükséges.

### 7.3 `narrow_phase_ns`

A `t2 = Instant::now()` a maybe-overlap loop előtt indul, és minden iteráció után frissül (`prof.narrow_phase_ns = t2.elapsed().as_nanos() as u64`). Ez **wall-clock from t2 to current**, így a végén az **utolsó** hozzárendelés fog győzni. Reject path: `prof.narrow_phase_ns = t2.elapsed().as_nanos() as u64` az exit előtt. Accept path: a loop után. Mindkettő helyes.

A teljes-loop wall-time mérés azonban tartalmazza a `prof.segment_pair_checks` recompute-ot (a profiled-only inner double iterator overhead), így az LV8 mért narrow-phase 346s **kicsit túlbecsült**. Default path (`profile_enabled=false`) ezt nem szenvedi el — bit-for-bit identikus.

### 7.4 `broad_phase_ns` és `boundary_ns`

`overlap_query_ns` mér broad-phase + AABB filter + collect (helyes). `poly_within_ns` mér `poly_strictly_within` (helyes). Nincs javítás szükséges, csak dokumentálni érdemes a stats output README-ben.

### 7.5 Profiling overhead jellemző mérete

T06l-b run_04: 220,630 calls × 6 `Instant::now()` hívás = ~1.3M timer call. Linux clock_gettime ≈ 25 ns → ~33 ms overhead a 357,483 ms total-ből. **<0.01%** — elhanyagolható, nem torzít. A profilezés jelenlegi felbontása megfelelő.

### 7.6 Javasolt profiling javítások

1. **Új mező:** `narrow_segment_pair_checks_actual_total: u64` — `segments_intersect_or_touch` tényleges hívásszám, az `own_polygons_intersect_or_touch` belsejébe injektálható egy debug-counter argumentummal vagy thread-local számlálóval.
2. **Új mező:** `narrow_segment_pair_checks_budget_total: u64` — átnevezni a jelenlegi `segment_pair_checks`-et erre, és **propagálni a stats-ba** (jelenleg dropped). A két mező hányadosa megadja a tényleges early-exit hatékonyságot.
3. **Új mező:** `narrow_ring_pair_count_total: u64` — hány ring-pair-ig jutott. Diagnosztika a hole-rich vs hole-free inputok elkülönítésére.
4. **Új mező:** `narrow_edge_bbox_reject_count_total: u64` (csak ha az edge-pair AABB pre-reject implementálódik) — early-reject hatékonyság mérése.

A T06n következő implementációs taskja kizárólag a (1) és (2) bevezetését tartalmazza, hogy az utána következő edge-bbox-reject prototípus mérhető legyen.

---

## 8. Optimization options

> Skálák: speedup = low (<5%), medium (5–25%), high (>25%) on the narrow-phase total cost (T06l-b run_04 = ~346s). False-accept risk értékelése: **kötelezően low** minden első-körös ajánláshoz.

### 8.1 Edge-pair AABB pre-reject (`segments_intersect_or_touch` előtt)

- **Érintett fájl/függvény:** [`narrow.rs:498` ring_intersects_ring_or_touch](rust/nesting_engine/src/feasibility/narrow.rs#L498); opcionálisan inline check `narrow.rs:608` `segments_intersect_or_touch` legelején.
- **Leírás:** Mielőtt 4 i128 cross-productot számolunk, 4 integer compare a két szegmens AABB-jén (`max(a0.x,a1.x) < min(b0.x,b1.x) || …`) — ha disjoint x vagy y range, azonnal `continue`/`return false`.
- **Miért gyorsít:** A valós LV8 alakzatok esetén az `Ea × Eb` edge-pár-kombinációk **döntő többsége** (random konkáv alakzatpárra >90% becsült) spatially elkülönülő szegmenspárok. 4 integer compare ≈ 0.2 ns vs 4 i128 multiply ≈ 5–10 ns → várhatóan 5–20× gyorsulás a `segments_intersect_or_touch` előtt rejectelt párokon.
- **Mikor nem gyorsít:** Apró, sűrűn metsző alakzatok (pl. test rectangle pár random microbenchről) — itt a plusz branch hozadéka ≈ 0, mert minden szegmenspár overlap range-en van. A T06m baseline (random rect microbench) néhány %-os overhead-et láthat.
- **Correctness risk:** **None** — a pre-reject a `segments_intersect_or_touch` policy-ját nem érinti, csak nem-metsző párokat zár ki előbb.
- **False accept risk:** **low** (mindig false-pozitív irányba konzervatív: ha bármi kétely van, mégis lefut a teljes orient teszt).
- **False reject risk:** **low** (csak akkor reject a pre-checkben, ha matematikailag nem lehet érintkezés sem).
- **Implementation complexity:** **low** — ~10 sor kód, ablakoz egy if blokkban.
- **Expected speedup:** **medium–high** (a 96–98% narrow-phase domináns költségen 10–25% reálisan).
- **Measurement needed:** (a) microbenchmark random rect + LV8 part-pár fixture-ön; (b) T06l-b run_04-style aktív-set profilezett futás before/after; (c) `segments_intersect_or_touch` actual call count előtt/után.
- **Recommended priority:** **#1 — first task.**

### 8.2 `NarrowPhaseStrategy::from_env()` cache

- **Érintett fájl/függvény:** [`narrow.rs:319 polygons_intersect_or_touch`](rust/nesting_engine/src/feasibility/narrow.rs#L319), [`narrow.rs:35 from_env`](rust/nesting_engine/src/feasibility/narrow.rs#L35).
- **Leírás:** A jelenlegi dispatcher minden hívásnál meghívja a `from_env()`-et, ami `std::env::var()` lookupot végez. Csere: `OnceLock<NarrowPhaseStrategy>` és cache-elés az első hívásnál.
- **Miért gyorsít:** ~288,945 env var lookup futamonként; egyenként ~50–200 ns. Becslés: ~30–60 ms / futás megspórolható.
- **Mikor nem gyorsít:** Cache-elt esetben sem érzékelhető különbség <1000 hívás/run szcenárióban.
- **Correctness risk:** **None** — env-var change a futás közben nem támogatott jelenleg sem (egy `RefCell` vagy single-shot is OK).
- **False accept risk:** **none** (logikai döntés nem változik).
- **False reject risk:** **none**.
- **Implementation complexity:** **trivial** — ~5 sor.
- **Expected speedup:** **low** (~0.01–0.02% the narrow-phase wall time-on, kicsi).
- **Measurement needed:** Szintetikus per-call mikroméréssel egyszer; production runokon nem érzékelhető.
- **Recommended priority:** **#2 — easy alongside #1.** (Bónuszként a `is_can_place_profile_enabled()`, `is_nfp_runtime_diag_enabled()` is OnceLock-cache-elhető.)

### 8.3 `segment_pair_checks` profiling repair (actual + budget split)

- **Érintett fájl/függvény:** [`narrow.rs:443` (profiled inner)](rust/nesting_engine/src/feasibility/narrow.rs#L443), [`nfp_placer.rs:246 aggregate_can_place_profile`](rust/nesting_engine/src/placement/nfp_placer.rs#L246).
- **Leírás:** Lásd 7. fejezet. Bevezet egy actual-count mezőt az `own_polygons_intersect_or_touch` belsejébe, propagálja a `CanPlaceProfile`-ba, és a stats-ba. Az upper-bound mezőt átnevezi `..._budget_total`-ra.
- **Miért gyorsít:** Önmagában nem gyorsít, **mérési vakfoltot szüntet meg**. A 8.1 / 8.4 / 8.7 javaslatok mérése csak ezzel hitelesíthető.
- **Correctness risk:** **None** (csak diagnostic).
- **False accept risk:** **none**.
- **False reject risk:** **none**.
- **Implementation complexity:** **low** — counter argumentum egy belső függvénybe vagy thread-local AtomicU64.
- **Expected speedup:** **none (measurement only).**
- **Measurement needed:** Output diff a `NEST_NFP_STATS_V1` JSON-ban: új mezők megjelennek, default-disable módban 0.
- **Recommended priority:** **#3 — előfeltétel #1 méréséhez.** Implementálható #1-gyel azonos PR-ben.

### 8.4 `polygon_has_valid_rings` cache `PlacedPart`-on

- **Érintett fájl/függvény:** [`narrow.rs:230 PlacedPart`](rust/nesting_engine/src/feasibility/narrow.rs#L230); `polygon_has_valid_rings` callerek a `can_place`/`poly_strictly_within`/`own_polygons_intersect_or_touch` mentén.
- **Leírás:** `PlacedPart`-on cache flag: `pub valid_rings: bool`. A `PlacedIndex::insert(...)` időben kiszámolja egyszer; `own_polygons_intersect_or_touch` és `can_place` placed-side ringvalidálás helyett ezt olvassa. A bin polygon mellé hasonló cache (state struct).
- **Miért gyorsít:** Worst case 4–7 redundáns ringscan / `can_place` call megspórolva. LV8 inputon kis vertex-szám mellett kicsi.
- **Mikor nem gyorsít:** Apró polygonok esetén az érték ≈ 0.
- **Correctness risk:** **low** (a cache invariáns: PlacedPart immutable a beillesztés után). Risk: ha valaki módosítja a `PlacedPart::inflated_polygon` mezőt nem-konstruktoron át.
- **False accept risk:** **low** (csak ha cache rossz; immutable struktúrával garantált).
- **False reject risk:** **low**.
- **Implementation complexity:** **low–medium** — egy mező, módosított konstruktor; a publik API kompatibilis tartható.
- **Expected speedup:** **low** (~1–3% becsült).
- **Measurement needed:** Per-call elapsed `valid_rings_ns` új mező, before/after.
- **Recommended priority:** **#4 — alacsony rizikó, kis gain. Külön kis PR.**

### 8.5 Bin geometry precompute (AABB + ring AABB-k + valid + holes_empty)

- **Érintett fájl/függvény:** új `BinGeometry { aabb, valid_rings, holes_empty, ring_aabbs }` struct, használata a `can_place`/`poly_strictly_within` API-jában (új signature variant); `nfp_placer.rs:can_place_dispatch` átadja a precomputed bin geometriát.
- **Leírás:** A `bin` polygon a sheet placement loop teljes ideje alatt invariáns. `aabb_from_polygon64(bin)` és `polygon_has_valid_rings(bin)` kiszámolható egyszer / sheet, és átadható a `can_place` hívásoknak.
- **Miért gyorsít:** ~14,043–284,556 redundáns bin AABB recompute / run megspórolva (T06l-b table 6.4).
- **Mikor nem gyorsít:** Apró bin polygon esetén ≈ 0.
- **Correctness risk:** **low** (immutable bin fenntartva).
- **False accept risk:** **none** (csak invariáns érték cache).
- **False reject risk:** **none**.
- **Implementation complexity:** **medium** — API-csere a `can_place` 5 call site-ján; nem-default path is változik, ezért `can_place` vs `can_place_with_bin_geom` koexisztencia ajánlott.
- **Expected speedup:** **low** (~0.5–2%).
- **Measurement needed:** before/after `boundary_ns`.
- **Recommended priority:** **#6 — érdemes, de nem urgent. Külön kis PR.**

### 8.6 Ring-level bbox pruning a `polygons_intersect_or_touch`-on belül

- **Érintett fájl/függvény:** [`narrow.rs:301 own_polygons_intersect_or_touch`](rust/nesting_engine/src/feasibility/narrow.rs#L301), `PlacedPart`-on ring-AABB cache.
- **Leírás:** Ring-pár előtt `aabb_overlaps(ring_a_aabb, ring_b_aabb) → continue` short-circuit.
- **Miért gyorsít:** Hole-rich polygonok esetén jelentős — több ring-párt el lehet zárni edge-loop nélkül. Outer-only hole-free LV8 inputon **az outer × outer eset úgyis átmegy** (hiszen bbox-átfedik egymást, mert a broad-phase már átengedte a maybe-overlap szűrőt), tehát **prepacked LV8-on alig hoz**.
- **Mikor nem gyorsít:** Hole-free single-ring polygonokon (jelenlegi prepacked LV8 input).
- **Correctness risk:** **low** (AABB conservative, TOUCH_TOL slack nem ronthatja el).
- **False accept risk:** **low**.
- **False reject risk:** **low**.
- **Implementation complexity:** **medium** — PlacedPart kiterjesztése + candidate per-call ring-AABB számítás (kisebb cost, mint amit megspórol — esetleg).
- **Expected speedup:** **low** (prepacked LV8-on); medium hole-rich inputon (jelenleg nincs).
- **Measurement needed:** holes count szerint bontott microbenchmark.
- **Recommended priority:** **#8 — nem első kör. Csak ha holes-rich workload jön.**

### 8.7 Outer-AABB containment quick reject a containment fallback előtt

- **Érintett fájl/függvény:** [`narrow.rs:301 own_polygons_intersect_or_touch`](rust/nesting_engine/src/feasibility/narrow.rs#L301) végén a `point_in_polygon(a.outer[0], b)` előtt; opcionálisan [`narrow.rs:466 poly_strictly_within`](rust/nesting_engine/src/feasibility/narrow.rs#L466).
- **Leírás:** A containment fallback `point_in_polygon` előtt kiszámolja: ha `a.outer[0]` nincs `b` AABB-n belül, akkor biztos nem `Inside` → `Outside`. Hasonlóan a fordított irányban.
- **Miért gyorsít:** A `point_in_polygon` jelenleg full O(\|outer\| + Σ\|holes\|) winding loopot futtat akkor is, ha a pont eleve az AABB-n kívül van. Az AABB-check ezt **azonnali return**-né cseréli.
- **Mikor nem gyorsít:** Ha a polygon AABB-k szorosan átfednek (broad-phase épp ezért fogadta el).
- **Correctness risk:** **None** — point-in-AABB szigorúbb feltétel mint point-in-polygon, no false accept.
- **False accept risk:** **none**.
- **False reject risk:** **none** (csak `Outside` esetekre vág).
- **Implementation complexity:** **low**.
- **Expected speedup:** **low–medium** (a containment fallback csak a maybe-overlap pair-eknél fut, és csak ha edge-edge nem intersectel).
- **Measurement needed:** Per-pair `point_in_polygon` call count, before/after.
- **Recommended priority:** **#5 — könnyű win, jól verifikálható.**

### 8.8 Holes-empty fast path a `poly_strictly_within`-ben

- **Érintett fájl/függvény:** [`narrow.rs:466 poly_strictly_within`](rust/nesting_engine/src/feasibility/narrow.rs#L466).
- **Leírás:** `if container.holes.is_empty()` ágon az utolsó hole-loop kihagyható (jelenleg `for hole in &container.holes` üres iteráció), és a `polygon_rings(container)` is csak az outer-en megy keresztül a `ring_intersects_polygon_boundaries`-ben — ez utóbbi szám szerint így is történik, de explicit `if container.holes.is_empty()` ág kezelje a tényleges fast path-ot, és a containment-iterátor-allokáció overheadje is megszűnik.
- **Miért gyorsít:** A jelenlegi prepacked LV8 input bin polygonjának nincsenek holesai → a hole-iteráció üres, de az iterator chain (`std::iter::once(...).chain(holes.iter().map(...))`) érdemtelenül construct-olódik; a kompiler valószínűleg inline-olja, de megmérendő.
- **Mikor nem gyorsít:** Hole-rich bin polygon esetén ≈ 0.
- **Correctness risk:** **None**.
- **False accept risk:** **none**.
- **False reject risk:** **none**.
- **Implementation complexity:** **low** — konditcionális ág.
- **Expected speedup:** **low** (<0.5% becsült; mostly diagnostic).
- **Measurement needed:** `boundary_ns` before/after holes-empty inputon.
- **Recommended priority:** **#9 — apró cleanup, nem urgent.**

### 8.9 `point_in_ring` boundary-scan + winding fúzió

- **Érintett fájl/függvény:** [`narrow.rs:534 point_in_ring`](rust/nesting_engine/src/feasibility/narrow.rs#L534).
- **Leírás:** Két full-pass helyett egy single-pass: a winding loop közben egy edge-bbox check + collinearity teszt el tudja dönteni a `OnBoundary` esetet ugyanabban az iterációban.
- **Miért gyorsít:** O(2n) → O(n) per pont, plusz cache-friendlier.
- **Mikor nem gyorsít:** Apró ringnél (n<8) ≈ 0.
- **Correctness risk:** **medium** — fontos, hogy a `OnBoundary` detekciónak ugyanaz maradjon a precíz feltétele (`cross == 0 && pont az edge bbox-ban`). Subtle off-by-one (zárt vs nyílt szegmens) lehet.
- **False accept risk:** **medium** ha `OnBoundary` nem vetődik át. **Erős unit-teszt szükséges.**
- **False reject risk:** **low**.
- **Implementation complexity:** **medium**.
- **Expected speedup:** **low** (~1–3%).
- **Measurement needed:** per-call elapsed; existing `OnBoundary` test cases.
- **Recommended priority:** **#10 — micro, és nontrivial correctness audit. Nem első kör.**

### 8.10 Convex-polygon SAT fast path

- **Érintett fájl/függvény:** új modul `narrow_sat.rs`; `is_convex` ([types.rs:66](rust/nesting_engine/src/geometry/types.rs#L66)) precompute `PlacedPart`-on.
- **Leírás:** Konvex–konvex pár esetén SAT (Separating Axis Theorem) — ~`O(Va + Vb)` axisok, mind axison projection min/max. Jellemzően gyorsabb mint az edge-pair sweep konvex inputon.
- **Miért gyorsít:** Konvex párokon ~3–10× gyorsabb a brute-force edge-edge-nél.
- **Mikor nem gyorsít:** Az LV8 nesting inputban a részek **döntően konkávak** (hole-szerű notchok). A T06l-b és T06m benchmark fixturejei is konkáv-domináns. Ezért nyerni kevés párnál fog.
- **Correctness risk:** **medium** — a SAT touch-policyje (closed segment) a saját edge-pair policyhoz **pontosan illesztendő**, integer arithmetic figyelembe vételével.
- **False accept risk:** **medium** ha a SAT projection edge cases (collinear edges) nem tökéletesen illesztett.
- **False reject risk:** **low**.
- **Implementation complexity:** **high** — új implementáció, equivalence test 1000+ pár ellen.
- **Expected speedup:** **low** (LV8 dominánsan konkáv) — high (jövőbeli convex-rich workloadon).
- **Measurement needed:** convex-vs-mixed input fixture; equivalence test 10K párral.
- **Recommended priority:** **#11 — defer, magas implementation cost vs LV8-en kicsi gain.**

### 8.11 Sweep-line / interval-tree edge index `PlacedPart`-on

- **Érintett fájl/függvény:** új modul `narrow_segment_index.rs`; `PlacedPart`-on cache.
- **Leírás:** Minden placed polygon edge-eit interval-tree-be tesszük (y-tartomány szerint), `ring_intersects_ring_or_touch` `O(Ea × log Eb)` lesz `O(Ea × Eb)` helyett.
- **Miért gyorsít:** Magas vertex-számú alakzatokon (~100+ edge) érzékelhető. LV8 alakzatok jellemzően 50–200 vertex közöttiek.
- **Mikor nem gyorsít:** Kis vertex-szám alatt (n<20) az interval-tree konstans overhead lassít.
- **Correctness risk:** **low–medium** — touch-policy átemelése részletkérdés.
- **False accept risk:** **low** (a sweep csak query-t ad, a tényleges edge-pair test marad).
- **False reject risk:** **low**.
- **Implementation complexity:** **high** — új struktúra, cache-management, teszt.
- **Expected speedup:** **medium–high** valódi LV8-en ha ténylegesen 100+ edge átlag, **low** kis polygonokon.
- **Measurement needed:** vertex-count szerint bontott microbench, build-time + per-call elapsed.
- **Recommended priority:** **#12 — későbbi szakasz. Csak az edge-pair AABB pre-reject (8.1) megmérése után érdemes elindítani.**

### 8.12 Allocation / clone audit a hot pathon

- **Érintett fájl/függvény:** [`narrow.rs:330 can_place`](rust/nesting_engine/src/feasibility/narrow.rs#L330), [`narrow.rs:391 can_place_profiled`](rust/nesting_engine/src/feasibility/narrow.rs#L391), [`nfp_placer.rs PlacedPart` constructions](rust/nesting_engine/src/placement/nfp_placer.rs#L978).
- **Leírás:** Audit:
  - `placed.query_overlaps(...)` `Vec<usize>` allocál; aztán `into_iter().map(...).filter(...).collect()` egy újabb `Vec<(usize, &PlacedPart)>`-ot. Lehet egyetlen `Vec<(usize, &PlacedPart)>` allocációval, közvetlenül.
  - `let candidate_poly = translate_polygon(&c_ctx.moving_polygon, ...)` ([nfp_placer.rs:973](rust/nesting_engine/src/placement/nfp_placer.rs#L973)) minden candidate-re újat allokál; a `placed_state.insert(PlacedPart { inflated_polygon: candidate_poly.clone(), ... })` és `placed_for_nfp.push(PlacedPart { inflated_polygon: candidate_poly.clone(), ... })` **kétszer is klónolja**. Minor allocation cost, de mérhető.
- **Miért gyorsít:** Allokációk csökkentése csökkenti a malloc-pressure-t és cache-misseket.
- **Mikor nem gyorsít:** Ha a maybe-overlap üres set, a Vec allokáció triviális.
- **Correctness risk:** **None**.
- **False accept risk:** **none**.
- **False reject risk:** **none**.
- **Implementation complexity:** **low–medium**.
- **Expected speedup:** **low** (~1–3%).
- **Measurement needed:** alloc count (heaptrack vagy per-call alloc), `narrow_phase_ns` változás.
- **Recommended priority:** **#7 — érdemes egy önálló cleanup PR-ben.**

---

## 9. Ranked recommendation table

| Rank | Recommendation | Files/functions | Expected speedup | False accept risk | Complexity | First task? |
|------|----------------|-----------------|------------------|-------------------|------------|-------------|
| 1 | Edge-pair AABB pre-reject | `narrow.rs:498` `ring_intersects_ring_or_touch` | medium–high | low | low | **YES** |
| 2 | `from_env()` → `OnceLock` cache | `narrow.rs:319,35` | low | none | trivial | **YES** (bundle with #1) |
| 3 | `segment_pair_checks` profiling repair (actual + budget) | `narrow.rs:443`, `nfp_placer.rs:246` | none (measurement) | none | low | **YES** (bundle with #1) |
| 4 | `polygon_has_valid_rings` cache on `PlacedPart` + bin | `narrow.rs:230,462` | low | low | low–medium | **NO** (next iteration) |
| 5 | Outer-AABB containment quick reject | `narrow.rs:301,466` | low–medium | none | low | **NO** (next iteration) |
| 6 | Bin geometry precompute (AABB + valid) | new `BinGeometry`, `nfp_placer.rs:228` | low | none | medium | **NO** (next iteration) |
| 7 | Allocation / clone audit on hot path | `narrow.rs:330,391`, `nfp_placer.rs:973` | low | none | low–medium | **NO** |
| 8 | Ring-level bbox pruning | `narrow.rs:301`, PlacedPart cache | low (LV8) / medium (holes-rich) | low | medium | **NO** |
| 9 | Holes-empty fast path | `narrow.rs:466` | low | none | low | **NO** |
| 10 | `point_in_ring` boundary+winding fusion | `narrow.rs:534` | low | medium | medium | **NO** (defer; correctness audit needed) |
| 11 | Convex-polygon SAT fast path | new `narrow_sat.rs`, `types.rs:66` | low (LV8) / high (convex-rich) | medium | high | **NO** |
| 12 | Edge interval-tree per `PlacedPart` | new `narrow_segment_index.rs` | medium–high (high-vertex) / low (low-vertex) | low | high | **NO** |

---

## 10. Recommended next implementation task

### Cím

**T06o — Own narrow-phase: edge-pair AABB pre-reject + segment-pair profiling repair**

### Cél

1. Implementálni a 8.1 javaslatot (edge-pair AABB pre-reject) az `own_polygons_intersect_or_touch` belső szegmens-pár loopjába.
2. Ezzel együtt a 8.3 javaslat (profiling repair): bevezetni a `narrow_segment_pair_checks_actual_total` és `narrow_segment_pair_checks_budget_total` mezőket a `CanPlaceProfile`-ba és a `NEST_NFP_STATS_V1` JSON-ba; az új `narrow_edge_bbox_reject_count_total` mező ellenőrzi az edge-bbox short-circuit hatékonyságot.
3. Bónuszként az 8.2 javaslat (`from_env()` cache).

### Miért ez az első

- **Magas impact terület:** T06l-b alapján a narrow-phase a `can_place` 96–98%-a; a `segments_intersect_or_touch` az ezen belüli single hot loop. A 4-integer-compare pre-reject becslés szerint az edge-pár-vizsgálatok >50%-át early-exit-ezi LV8 alakzatokon.
- **Alacsony false-accept rizikó:** AABB-disjoint feltétel matematikailag konzervatív (csak nem-érintkező párokat zár ki).
- **Alacsony implementation cost:** ~30 sor kód a 8.1-re, ~30 sor a 8.3-ra, ~10 sor a 8.2-re. Egy PR-ben kezelhető.
- **Jól mérhető:** A 8.3 nélkül a 8.1 hatékonysága nem hitelesíthető — ezért a kettőt **egy PR-ben** kell megvalósítani.
- **Könnyen rollbackelhető:** Az új viselkedés nem érinti a `can_place`/`polygons_intersect_or_touch` viselkedését (csak a futási idő csökken). Egyetlen revert reset-eli.

### Érintett fájlok

- `rust/nesting_engine/src/feasibility/narrow.rs` — kódváltozás (3 függvény).
- `rust/nesting_engine/src/placement/nfp_placer.rs` — stats mezők hozzáadása + aggregator update; `NEST_NFP_STATS_V1` JSON szerializálás.
- `rust/nesting_engine/Cargo.toml` — nincs új dependency.

### Nem célok

- **NEM** módosítani a `can_place` boolean kimenetét. Equivalence-test marad sárga vonal.
- **NEM** módosítani a touch-policy-t.
- **NEM** átalakítani az `i_overlay` ágat vagy bármilyen külső library-bekötést.
- **NEM** átalakítani a `point_in_polygon`/`point_in_ring`/`poly_strictly_within` belsejét.
- **NEM** változtatni a `PlacedPart` API-t (ezt a #4 / #6 task fogja).

### Acceptance criteria

1. `cargo test -p nesting_engine` zöld (mind a 200+ jelenlegi teszt).
2. Új unit-tesztek:
   - `edge_bbox_pre_reject_does_not_change_intersect_result` — egzakt egyezés a 12 T06m equivalence case-en.
   - `edge_bbox_pre_reject_short_circuits_disjoint_segments` — a counter számolja az early rejecteket.
   - `segment_pair_checks_actual_count_matches_invocation_count` — actual ≤ budget invariant.
3. `can_place_and_profiled_return_equal_booleans_across_control_cases` (already existing) továbbra is PASS.
4. Manual check: `NESTING_ENGINE_CAN_PLACE_PROFILE=1` futás: az új `..._actual_total` és `..._budget_total` mezők megjelennek a `NEST_NFP_STATS_V1` JSON-ban.
5. Default path (`profile_enabled=false`) bit-for-bit identikus stdout a baseline-nal egy kontroll fixture-ön.
6. Microbenchmark a `narrow_phase_bench` binárisban: 10K random rect pár — own új implementáció ≤ 105% of baseline (a pre-reject valami micro-overhead lehet random rect-en, de ne haljon meg).

### Unit / microbenchmark terv

- **Unit (csak rövid futás, default):**
  - 12 case-es equivalence T06m fixture porting.
  - Edge-bbox-disjoint test pár (két axis-aligned szegmens messze egymástól).
  - Edge-bbox-overlap-but-no-intersect test pár (két szegmens egymás mellett, de nem érintkezve — pre-reject NEM rejekt-eli, a tényleges orient teszt rejekt-eli).
  - OnBoundary pontos érintkezés test pár.
- **Microbenchmark (külön utasításra futtatandó, nem default):**
  - Bővítés a `narrow_phase_bench.rs`-be: 10K random rect pair (T06m), 10K random concave 10–50 vertex pair, 1K LV8-realistic part pair.
  - Output: ns/pair before/after, edge_bbox_reject_pct.
- **Profiling smoke (külön utasításra futtatandó):**
  - T06l-b run_04-style aktívset prepacked LV8 fixture, `NESTING_ENGINE_CAN_PLACE_PROFILE=1`-gyel; before/after `narrow_phase_ns_total`, `narrow_segment_pair_checks_actual_total`, `narrow_edge_bbox_reject_count_total`.

---

## 11. Things not to do next

- **Ne** kezdjünk SAT/sweep-line / interval-tree / BVH átalakítást — magas implementation cost, LV8 inputon kicsi várt nyereség, ÉS az edge-pair AABB pre-reject (#1) eredménye nélkül nem megalapozott.
- **Ne** bontsuk a `point_in_ring` boundary-scan és winding loopjait — micro nyereség, magas correctness risk, magas regressziós veszély a `OnBoundary` policy-n.
- **Ne** vezessünk be approximate distance-based collision tolerance-t — false accept risket vinne be.
- **Ne** változtassuk a `PlacedPart` API-t #1-gyel együtt — két indok: a #1 mérése a #4-#6 nélkül érvényes; a #4-#6 önálló kis PR.
- **Ne** térjünk át i_overlay-ra. T06m igazolta, hogy 2.7× lassabb a saját implementációnál.
- **Ne** állítsuk át a touch-policy-t (touch = collision marad).

---

## 12. Open questions

1. **Tényleges edge-pair-overlap arány LV8 alakzatpárokon?** A pre-reject hatékonyságát csak a #3 (profiling repair) után tudjuk megmérni. A jelenlegi `segment_pair_checks` upper-bound-ja torzít.
2. **`point_in_polygon` per-pair gyakoriság aránya az edge-pair work-höz?** Jelenleg a `narrow_phase_ns` egységben van mérve. Egy `containment_fallback_ns` external counter (nem default) tisztábbá tenné a 8.7 priorizálást.
3. **A run_04 active-set 1,198 ns/pair vs run_08 baseline kismértékben megegyezik (??ns)?** Run_08 narrow-phase: 13.4ms / 14,043 pairs ≈ 954 ns/pair. Az LV8 szám 1.26× az aktív-set és baseline között — vajon a placed-set mérete vagy az alakzat méret/komplexitás hat erre? Diagnostikai bontás kellene placed_count vs vertex_count szerint.
4. **`maybe_overlap` átlagméret?** T06l-b: `overlap_candidate_count_total / can_place_calls = 220,589 / 220,630 ≈ 1.0`, azaz **átlagosan 1 maybe-overlap pair / call**. Ez azt jelenti, hogy a broad-phase + AABB filter már nagyon hatékony, és **a per-pair narrow-phase cost csökkentése a fő hozzáadott érték**. Megerősíti a #1 prioritást.
5. **Ring-AABB cache szükséges-e prepacked hole-free LV8-on?** Jelenlegi mérési adat alapján **nem szükséges** (a #6 priorizációja onnan jön, hogy holes-rich workload jövőben jöhet). Ha a hole-rich workload nem jelenik meg, a #6 deferable.
6. **Az aggregator most kihagyja a `profile.segment_pair_checks` mezőt** — szándékos volt a T06l-a-ban (ne legyen nyereségellopó), vagy elfelejtett propagation? A T06l-a doku szerint "informational rough-cut, recorded for diagnostics; not consumed by aggregation". A #3 javaslat ezt explicit propagálja.

---

## 13. Final verdict

**PASS.** Az own narrow-phase érdemben gyorsítható low-risk eszközökkel. A T06l-b mérési adatok (96–98% narrow-phase share, ~1,200 ns/pair production) megerősítik, hogy a `segments_intersect_or_touch` hot loopban egy 4-integer-compare AABB pre-reject a leggyorsabb visszahozható nyereség, false-accept rizikó nélkül. A jelenlegi `segment_pair_checks` profiling üres kalória — ezt egyúttal javítani kell, hogy a következő optimalizációk hitelesen mérhetők legyenek. Convex SAT, sweep-line és complex sztrukturális átalakítás defer státuszban — a T06l-b jellegű mérési bázis nélkül ezek priorizálása nem megalapozott.

A javasolt T06o (edge-pair AABB pre-reject + profiling repair + `from_env()` cache) egy compact, jól mérhető, könnyen rollbackelhető első lépés.
