# T06-next — Claude Algorithmic Speedup Audit

## 1. Status

**PARTIAL**

A report és checklist elkészült, a 12-szakaszos audit lefedi a kötelező területeket. A tényleges runtime arányok azonban részben becslésen alapulnak: a `can_place` / broad-phase / narrow-phase költség nincs aggregálva (csak per-call `CanPlaceProfile` létezik, soha nem hívja senki éles útvonalon), és az `[NFP DIAG] eprintln!` overhead nincs külön mérve. A javaslatok a kódból és a meglévő reportokból levezethető tényekre épülnek; ahol becslés szerepel, az kifejezetten jelölve van.

---

## 2. Executive verdict

**Tudjuk-e, mit kell olcsóbbá tenni?**
- Részben igen. A T06-next greedy eval cost decomposition report alapján a 35–40s search=none baseline jelenlegi arányai: NFP compute ≈16.1s, CFR (union+diff) ≈15.0s, fennmaradó (candidate gen+dedup, can_place, többi) ≈3–9s. Az NFP cache hit rate 99.32% már nagyon jó, tehát az NFP request-számok csökkentése (a megmaradó 0.68% miss-cost csökkentése) határozottan low-impact ezen az inputon.
- A `can_place` / RTree broad-phase költség **mérve nincs az éles ágon** — `CanPlaceProfile` létezik (`feasibility/narrow.rs:127`), de a hot path csak a flag nélküli `can_place()`-t hívja (`placement/nfp_placer.rs:786, 876, 994, 1293, 1378`). Ez vakfolt.
- A T06i-ben dokumentált 236s explosion (236s / nfp_poly=254 / 154K vertex CFR) a friss state-ben nem reprodukálódott, de a CFR cost összetétele O(n × k_avg) az NFP unionban ahol n = poly count, k = vertex count → SA-iterációk vagy nagyobb input esetén ez ismét megjelenhet.

**Top 3 beavatkozási pont (rangsorolt):**

1. **Diagnosztikus `eprintln!` hot-path overhead csökkentése flag-gel** — `nfp_placer.rs:1077-1086, 1089-1100, 1181-1186, 1193-1199` és `provider.rs:218-225`. Jelenleg unconditionálisan tüzelnek minden NFP cache miss-re és minden CFR call-ra. Becslés alapján 1684 NFP call + 1266 CFR call esetén ez I/O blokkolva 100s–1000s ms körül lehet (mérni kell). **Best return-on-investment: low risk, low complexity.**

2. **Active-set candidate-first útvonal éles bekapcsolása + IFP-szerinti AABB query helyett candidate AABB query** — `nfp_placer.rs:606-829`. A T06k prototípus jelen van, de a `[T06k benchmark hits primary timeout → BLF fallback]` miatt ténylegesen nem volt mérve; a runner env vars átadása nincs bekötve. Az aktív útvonal CFR union-t kerül lokális blocker query + `can_place()` exact validációval — pontosan ez a "candidate-first / spatial broad-phase / exact validation" deep-research irány. **Magas potenciál, de implementáció + mérés szükséges. Quality kockázat alacsony, mert can_place() a végső gate.**

3. **`shape_id` (SHA-256 hash) per-iteráció re-compute kerülése a placed parts oldalán** — `nfp_placer.rs:699, 937, 1059`. A lokális `shape_id_a` minden `placed_part`-ra újra ki van számolva (canonicalize + SHA-256) minden új part placement próbálkozáskor, miközben a placed normalized polygon shape-ID-je nem változik. Egy `Vec<u64>` cache `placed_for_nfp` mellé eliminálná az ismétlődő hashelést. **Nem igényel algoritmusváltást, semmi correctness risk; csak `placed_for_nfp` mellé egy párhuzamos `Vec<u64> placed_shape_ids` kell.**

**Mi NEM javasolt elsőként:**
- Ne kapcsoljuk ki az SA-t véglegesen; az `quality_cavity_prepack_cgal_reference` profilban az SA jelenleg amúgy is gyakran 0 vagy 1 iterációba clamp-elődik (`main.rs:354 default_sa_eval_budget_sec(t)=t/10` és `sa.rs:201 clamp_sa_iters_…`), tehát a "search=none" gyakorlatilag már most is felülkerekedik az SA fölött ezen a workloadon. Külön regret/quality audit kell.
- Ne nevezzük az active-set vagy candidate-driven útvonalat CFR replacement-nek; mindkettő `can_place()` final gate-tel működik, de ezek **alternatív candidate generator-ok**, nem geometriai feasibility replacement-ek. CFR (union+diff) marad a referencia / fallback.
- Ne polygon-simplify a placed parts vagy NFP-k vertex-számát exact validator nélkül.
- Ne BLF/OldConcave silent fallback-et új helyre.

---

## 3. Sources reviewed

### Reportok (mind elérhető és elolvasva)

- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06_next_greedy_eval_cost_decomposition.md` — friss baseline (2026-05-09): 276/276 placed, 35–40s, NFP=16.1s, CFR=15.0s, cache hit 99.32%
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06i_prepacked_cgal_nfp_benchmark.md` — direct binary 32s, runner SA timeout
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06i_sa_greedy_budget_calibration_runtime_diagnostics.md` — eval budget bug (default = t/10 → 24s, actual 236s), `consume(1)` work-budget granularity
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06j_quality_preserving_cfr_reduction.md` — hybrid CFR threshold=50, fast-path candidate gen, gate AMBIGUOUS
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06k_active_set_candidate_cfr_reduction.md` — active-set prototípus, env vars NEM kötve runneren át, primary timeout
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06d_candidate_driven_fast_path.md` — 5 candidate source, byte-equivalent 3-rect smoke
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06c_candidate_cde_architecture_audit.md` — call graph reference
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06b_cfr_strategy_benchmark.md` — Strategy::List a leggyorsabb i_overlay strat
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06g_cavity_prepack_solver_contract.md` — 231→12 part-type contract
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06h_module_result_normalization_repair.md` — collapsed module ID lookup

### Kódfájlok (auditálva)

- `rust/nesting_engine/src/main.rs` (746 lines) — CLI, `default_sa_eval_budget_sec`, profile wiring, env propagation
- `rust/nesting_engine/src/multi_bin/greedy.rs` (1095 lines) — `greedy_multi_sheet`, `StopPolicy`, `run_slide_compaction_postpass`
- `rust/nesting_engine/src/search/sa.rs` (1082 lines) — `clamp_sa_iters_…`, `run_sa_search_over_specs`, `eval_state_cost_with_result`
- `rust/nesting_engine/src/placement/nfp_placer.rs` (2653 lines) — `nfp_place`, három feature-flagged ág, `append_candidates`, `sort_and_dedupe_candidates`, `generate_active_set_candidates`, `compute_cfr_fallback_candidates`
- `rust/nesting_engine/src/nfp/cfr.rs` (847 lines) — `compute_cfr_with_stats`, `run_overlay`, `canonicalize_polygon64`, `OverlayBounds`
- `rust/nesting_engine/src/nfp/cache.rs` (350 lines) — `NfpCache` HashMap, `MAX_ENTRIES=10_000` clear-all-on-overflow, `shape_id` SHA-256
- `rust/nesting_engine/src/nfp/provider.rs` (238 lines) — `NfpProvider` trait, `OldConcaveProvider`, `compute_nfp_lib_with_provider` (tartalmazza az unconditional `[NFP DIAG]` printet)
- `rust/nesting_engine/src/nfp/ifp.rs` (119 lines) — pure rect-bin AABB IFP, deterministikus, olcsó
- `rust/nesting_engine/src/feasibility/aabb.rs` (54 lines) — `Aabb`, `aabb_overlaps` (TOUCH_TOL inflated), `aabb_inside`
- `rust/nesting_engine/src/feasibility/narrow.rs` (627 lines) — `PlacedIndex` (Vec + rstar RTree), `can_place`, `can_place_profiled` (NEM hívja senki éles útvonalon), `polygons_intersect_or_touch`, `point_in_polygon`
- `vrs_nesting/config/nesting_quality_profiles.py` — `quality_cavity_prepack_cgal_reference` profil definíció
- `vrs_nesting/runner/nesting_engine_runner.py` — CLI args `--sa-eval-budget-sec` átadás

---

## 4. Greedy evaluation call graph

```
runner (Python)
└── nesting_engine_runner.py: build CLI args + spawn binary
    │   --placer nfp --search sa --part-in-part off --compaction slide
    │   --nfp-kernel cgal_reference [--sa-iters …] [--sa-eval-budget-sec …]
    │
    ▼
main.rs: run_nest()
├── parse_nest_cli_args
├── run_inflate_pipeline (Python-equivalent, hole inflate / hole_collapsed)
├── force_nfp_for_cgal = (NESTING_ENGINE_NFP_KERNEL == "cgal_reference")
├── effective_placer = nfp (cgal bypass-eli a hole→BLF gating-et)
│
├── SearchMode::None ──► greedy_multi_sheet(specs, bin, time_limit, …)
│
└── SearchMode::Sa ────► run_sa_search_over_specs(specs, bin, time_limit, sa_cfg)
    │
    └─ search/sa.rs: run_sa_search_over_specs
       ├── ensure_sa_stop_mode() → forces NESTING_ENGINE_STOP_MODE=work_budget
       ├── clamp_sa_iters_by_time_limit_and_eval_budget
       │     iters_max = (time_limit / eval_budget) - 1
       ├── eval initial state ─┐
       ├── for iter in 0..iters:
       │     ├── neighbor = apply_neighbor(state)            # swap/move/rotate
       │     ├── eval_state_cost_with_result(neighbor)
       │     │     └─► greedy_multi_sheet (full evaluation)  # ← drága
       │     ├── accept/reject Metropolis
       │     └── time guard
       ▼
multi_bin/greedy.rs: greedy_multi_sheet
├── StopPolicy::from_env (wall_clock vagy work_budget; SA-ban work_budget)
├── loop {                    # outer loop = sheets
│   ├── remaining_specs = total - placed_so_far
│   ├── nfp_place(remaining_specs, bin, …)   OR   blf_place(…)
│   ├── accumulate per-sheet placed/unplaced
│   ├── ha nem haladt előre → break
│   ├── ha stop → break
│   └── continue (next sheet)
│ }
├── run_slide_compaction_postpass(…) ha CompactionMode::Slide
│   └── per sheet, per item: try left positions, try down positions,
│       can_place_with_current_sheet_state(…) minden próbára
└── return (MultiSheetResult, NfpPlacerStatsV1)
    │
    ▼
placement/nfp_placer.rs: nfp_place(remaining_specs, bin, …)
├── nfp_kernel = resolve_nfp_kernel()   # OldConcave vagy CgalReference
├── ordered = order_parts_for_policy(parts, ByArea)   # bbox area DESC
├── for part in ordered:
│     for instance in 0..part.quantity:                # ← stop.consume(1) per instance
│       └─ ROTATION LOOP (allowed_rotations × handler):
│
│         │ Per rotation:
│         │ 1) rotate_polygon → normalize_polygon_min_xy → moving_aabb
│         │ 2) compute_ifp_rect (cheap, 4 vertices only)
│         │
│         ├─ FEATURE FLAG BRANCH (csak egy ág fut a háromból):
│         │
│         │ A) candidate_driven (NESTING_ENGINE_CANDIDATE_DRIVEN=1)
│         │    ├─ collect_nfp_polys_for_rotation (NFP cache or compute)
│         │    ├─ generate_candidate_driven_candidates
│         │    │    IFP corners + NFP vertex (cap 256) + NFP midpoint (cap 128)
│         │    │  + placed_anchor (cap 64) + nudges
│         │    └─ skip CFR teljesen → all_candidates
│         │
│         │ B) active_set (NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1)
│         │    progressive widening L0=1× → L1=2× → L2=4× → L3=full:
│         │    ├─ active_indices = placed_state.query_overlaps(IFP×scale)[..64]
│         │    ├─ build local NFPs only for active blockers
│         │    ├─ generate_active_set_candidates (IFP corners + placed bbox + active NFP vertex/midpoint)
│         │    ├─ sort_and_dedupe_candidates
│         │    └─ for c in deduped: can_place(c) → ACCEPT és break
│         │    Fallback: local CFR fallback (csak active blockers) → full CFR fallback
│         │
│         │ C) DEFAULT CFR (else):
│         │    ├─ for placed_part in placed_for_nfp:
│         │    │    ├─ shape_id_a = SHA-256(placed_normalized)         # ← MINDEN PART-RA UJRA HASHELŐDIK
│         │    │    ├─ key = NfpCacheKey { sid_a, sid_b, rot, kernel }
│         │    │    ├─ if cache.get → world translate, push
│         │    │    ├─ else compute_nfp_lib (provider.compute):
│         │    │    │    ├─ eprintln!("[NFP DIAG] compute_nfp_lib START …")  # ← UNCONDITIONAL
│         │    │    │    ├─ provider.compute(…)
│         │    │    │    │    OldConcave: convex/concave dispatch
│         │    │    │    │    CgalReference: probe binary subprocess
│         │    │    │    └─ eprintln!("[NFP DIAG] compute_nfp_lib END …")
│         │    │    └─ cache.insert (HashMap; clear_all if MAX_ENTRIES=10_000 reached)
│         │    ├─ stats.cfr_calls += 1
│         │    │
│         │    ├─ HYBRID CFR sub-branch (NESTING_ENGINE_HYBRID_CFR=1
│         │    │       AND nfp_polys.len() < 50):
│         │    │    ├─ generate_hybrid_candidates (no CFR union)
│         │    │    └─ stats.cfr_skipped_by_hybrid_count += 1
│         │    │
│         │    └─ ELSE (full CFR):
│         │       eprintln!("[CFR DIAG] START nfp_polys=…")  # ← UNCONDITIONAL
│         │       compute_cfr_with_stats(ifp, nfp_polys, &mut cfr_stats)
│         │       └─ cfr.rs::compute_cfr_internal:
│         │          ├─ canonicalize ifp
│         │          ├─ encode all polys with OverlayBounds (fits to i32)
│         │          ├─ run_overlay(nfp_shapes, [], Union)        # i_overlay Strategy::List
│         │          ├─ if union empty → return ifp
│         │          ├─ run_overlay([ifp_shape], union_shapes, Difference)
│         │          ├─ decode + canonicalize + sort_components (SHA-256 tiebreak)
│         │          └─ return Vec<Polygon64>
│         │       eprintln!("[CFR DIAG] END elapsed_ms=…")
│         │       append_candidates(all_candidates, rot_idx, cfr_components, ctx)
│         │           per CFR component:
│         │             vertices (cap 512) → tx,ty + nudges (3 step × 8 dir = 24 per vert)
│         │
│         (end rotation iteration)
│
│       After all rotations:
│       sort_and_dedupe_candidates (sort by ty,tx,rot,source,…)  + cap MAX_CANDIDATES_PER_PART=4096
│       for c in deduped.after_cap:
│         stop.consume(1)
│         can_place(candidate_poly, bin, placed_state)            # ← ❶ EXACT GATE
│           feasibility/narrow.rs:can_place
│             ├─ aabb_inside(bin_aabb, candidate_aabb)            # cheap
│             ├─ poly_strictly_within(candidate, bin)             # O(C × 4) point-in-rect
│             ├─ placed.query_overlaps(aabb)                      # rstar RTree
│             ├─ filter aabb_overlaps                             # cheap
│             ├─ deterministic sort by min_x,min_y,…
│             └─ for other in maybe_overlap:
│                  polygons_intersect_or_touch(candidate, other)  # O(C×O) segment×segment
│         if can_place → ACCEPT (placed_state.insert + placed_for_nfp.push + placed.push)
│       else if !placed_this_instance:
│         (candidate_driven + ALLOW_CFR_FALLBACK) → compute_cfr_fallback_candidates loop
│
└── return PlacementResult { placed, unplaced }
```

### Hívási gyakoriság taxonómia

| Komponens | Frequency |
|-----------|-----------|
| `greedy_multi_sheet` | **1× evaluation** (search=none) ; **iters+1× evaluation** (SA) |
| `nfp_place` | 1× per sheet per evaluation |
| `order_parts_for_policy` | 1× per nfp_place call |
| `compute_ifp_rect` | 1× **per (part_instance × rotation)** |
| `rotate_polygon`, `normalize_polygon_min_xy` | 1× per (part_instance × rotation) |
| `compute_nfp_lib` (provider compute, cache miss) | ≤ 1× per (placed_part × moving_shape × rotation, kernel) — global cache |
| `cache.get` (lookup) | 1× per (placed_part × placement_attempt × rotation) |
| `compute_cfr_with_stats` | 1× per **placement_attempt × rotation** (default path; hybrid skips) |
| `i_overlay run_overlay Union` | 1× per CFR call |
| `i_overlay run_overlay Difference` | 1× per CFR call (ha union nem üres) |
| `append_candidates` | 1× per CFR call |
| `sort_and_dedupe_candidates` | 1× per part_instance |
| `can_place` | 1× **per candidate** in deduped.after_cap (≤ 4096 per part_instance) |
| `placed_state.query_overlaps` (RTree) | 1× per `can_place` call |
| `polygons_intersect_or_touch` | ≤ overlap candidates per `can_place` |
| `run_slide_compaction_postpass` | 1× per `greedy_multi_sheet` call (csak ha CompactionMode::Slide) |
| `eprintln!("[NFP DIAG] …")` (provider.rs:218) | **1× minden cache miss-en — UNCONDITIONAL** |
| `eprintln!("[NFP DIAG] compute_nfp_lib …")` (nfp_placer.rs:1077,1089) | **1× minden cache miss-en — UNCONDITIONAL** |
| `eprintln!("[CFR DIAG] …")` (nfp_placer.rs:1181,1193) | **1× minden CFR call-on — UNCONDITIONAL** |
| SA full re-evaluation | **1× per SA iteration** ← egész greedy_multi_sheet újrafut |

---

## 5. Cost model

| Component | Hol | Frequency | Skálázódik | Mérés van | Mérés hiányzik | Bottleneck valószínűség |
|-----------|-----|-----------|-----------|-----------|----------------|------------------------|
| **NFP compute** | `nfp/concave.rs`, `nfp/cgal_reference_provider.rs` (dispatch via `provider.rs`) | per cache miss | O(P × M) (vertices) — concave: O(P · M · log(P+M)); CGAL: subprocess + IPC | `NFP_DIAG` print + `nfp_provider_compute_ms_total/max` | **per-pair cost histogram (mean/median, only max+sum exist)**; első call vs warm cache breakdown | 99.3% cache hit miatt csak miss-en — **megmaradó kb. 16s/40s ≈ 40% a baseline-on** (kb. 30s a cgal_reference smoke 32s-ből T06i case C) |
| **NFP cache lookup** | `nfp/cache.rs` `NfpCache::get` (HashMap) | per (placed × candidate × rotation) | O(1) hash + SHA-256 ON KEY (canonicalize+hash) | hits/misses | hash time per call | Alacsony, de a `shape_id` recompute hot — lásd #6 alább |
| **CFR union** | `nfp/cfr.rs` `run_overlay(nfp, [], Union)` | per CFR call | O(n × k_avg × log…) — i_overlay, polynomially worst-case | `cfr_union_calls` count + `union_time_ms` per call | per-call vertex-count distribution | Alacsony jelenleg (13.3s / 1266 call ≈ 10.5ms/call), de **n × k worst-case** miatt skálázás-veszélyes (T06i 20s/call peak) |
| **CFR diff** | `nfp/cfr.rs` `run_overlay([ifp], union, Difference)` | per CFR call | hasonló | `diff_time_ms` per call | — | Alacsony |
| **CFR canonicalize** | `cfr.rs` `canonicalize_polygon64` (ifp + result polygons) | 1× per ifp + 1× per result component | O(V) | nincs | wall | Alacsony |
| **CFR encode/decode** | `cfr.rs` `encode_polygon`, `decode_shape` | 1× per input + 1× per output | O(V) | nincs | wall | Alacsony |
| **CFR sort_components** | `cfr.rs:499-508` SHA-256 tiebreak hash | 1× per CFR result | O(n log n × hash(O(V))) | hash call counter (test only) | wall | Alacsony, de **n nagy esetén** SHA-256 költsége nem nulla |
| **IFP** | `nfp/ifp.rs` `compute_ifp_rect` | per (part × rotation) | O(1) (4 vertex AABB rect) | nincs | — | Negligible |
| **Candidate generation** (default CFR path) | `nfp_placer.rs::append_candidates` | per CFR call | O(component_count × vertices_per × 25 nudge) — cap 512 vert/component | `candidates_before_dedupe_total` | per-source breakdown (csak candidate_driven path-on van) | T06-next baseline 11.16M total, 1.07M after cap → cap_applied 253× — **medium** (cap dominál) |
| **Candidate dedup** | `nfp_placer.rs::sort_and_dedupe_candidates` | per part_instance | O(N log N) sort + BTreeSet dedupe | `candidates_after_dedupe_total`, `cap_applied_count` | wall | Alacsony az 1.07M-on, de a sort-key 7-mezős |
| **Candidate cap** | ugyanott (`MAX_CANDIDATES_PER_PART=4096`) | per part_instance | O(1) truncate | `cap_applied_count` | — | Negligible |
| **`can_place`** | `feasibility/narrow.rs:79` | per candidate validation | O(broad-phase O(log P) + narrow-phase O(C×O)) | **éles ágon csak count, nem timing** | wall, broad/narrow split, segment-pair count | **FONTOS VAKFOLT** — `can_place_profiled` létezik (`narrow.rs:140`), nem hívódik az éles útvonalon |
| **PlacedIndex broad-phase** | `narrow.rs::query_overlaps` (rstar RTree `locate_in_envelope_intersecting`) | per `can_place` | O(log P + R) ahol R = matching | nincs | wall, R | Alacsony (RTree → log P) |
| **Narrow-phase** | `narrow.rs::polygons_intersect_or_touch` (segment×segment) | per overlap pair | O(C_segs × O_segs) | nincs | wall, segment-pair check count | **Potential bottleneck ha `can_place` válik forró (CFR csökkentés után)** |
| **Sheet boundary containment** | `narrow.rs::poly_strictly_within` + `point_in_polygon` | per `can_place` | O(C × bin_segs) — bin = 4 vertex rect, tehát ~4×C | nincs | wall | Alacsony (bin always 4-vertex) |
| **Spacing / inflated polygon** | előre alkalmazva: `pipeline.rs::run_inflate_pipeline` | 1× per part inputon | O(V) | nincs | — | Negligible (offline) |
| **Slide compaction** | `greedy.rs::run_slide_compaction_postpass` | 1× per `greedy_multi_sheet` ha `CompactionMode::Slide` | O(items × positions × can_place) | nincs külön | wall — **nincs mérve külön** | Lehet **medium** SA-ban (minden iter végrehajtja); single eval-en T06-next szerint slide vs off azonos util → **alacsony return ezen az inputon** |
| **Multi-sheet retry** | `greedy.rs::greedy_multi_sheet` outer loop | per evaluation | O(sheets × nfp_place_per_sheet) | sheets_used | per-sheet timing | Alacsony |
| **SA repeated eval** | `sa.rs::eval_state_cost_with_result` | per SA iter | O(iters × full_greedy_eval) | `[SEARCH DIAG] SA start parts=… iters=…` | per-iter cost trend | **HIGH ha SA tényleg fut**; current profile `default_eval_budget = time_limit/10` clamp gyakran 0/1 iterre csökkenti |
| **eprintln overhead** | `nfp_placer.rs:1077,1089,1181,1193` + `provider.rs:218` | per cache miss + per CFR call | O(stderr write) — synchronously locked | nincs | wall | **UNKNOWN, valószínűleg 100-1000ms range** — ki kell mérni |
| **`shape_id` re-hash** | `nfp_placer.rs:699,937,1059`, `cache.rs:101 shape_id` (SHA-256 + canonicalize) | per (placed_part × placement_attempt × rotation) | O(P_vertices × hash) | nincs | wall, call count | **Medium** (hash-ar valós: T06-next ≈ 1684 NFP request × P_avg vertex SHA-256) |

---

## 6. Current bottleneck interpretation

A T06-next baseline (search=none, prepacked LV8, cgal_reference) számszerű állapot:

| Komponens | Wall idő | Arány |
|-----------|---------:|------:|
| NFP compute (cgal subprocess, 842 calls × cca. 38ms) | 16.1s | 40% |
| CFR (union 13.3s + diff 1.7s) | 15.0s | 38% |
| Candidate generation + dedup + sort | ~? | (becsült 1–3s) |
| `can_place` exact validation | ~? | (becsült 1–3s, nincs mérve) |
| `eprintln!` `[NFP DIAG]` + `[CFR DIAG]` | ~? | (becsült 100–1000ms, nincs mérve) |
| Slide compaction post-pass | ~? | (T06-next: slide vs off azonos util — kicsi) |
| Maradék (kód-fordulatok, `shape_id`, dedup, RTree insert) | ~? | (1–3s) |
| **Összes wall** | **~35–40s** | 100% |

**NFP compute (40%)**: A cgal_reference subprocess hívások (kb. 38ms átlag) dominálnak a miss-eken. Cache hit rate 99.32% → csak ~0.68% van compute, de minden compute drága subprocess overhead. A CGAL probe binary IPC-en keresztül kommunikál → CSAK IPC overhead már jelentős. A T06-next eval cost decomposition azt jelzi, hogy NFP compute count = 842 → ez kb. 19 ms/call (nem 38ms; figyelmen kívül a probe spawn).

**CFR (38%)**: A union dominál (13.3s), nem a diff (1.7s). 1266 CFR call → 10.5ms/union avg. Worst case T06i-ben látott 20.5s/call extreme; itt nem reprodukálódik, mert prepack után `nfp_polys.len()` általában <30, és vertex count is moderate.

**candidate explosion (1.07M after cap, 253 cap_applied)**: a cap MŰKÖDIK, de **a generálás után dolgozik**, tehát a 11.16M-ot előbb le kell dedupolni (BTreeSet insert × 11M ≈ kb. 0.1–1s). Az igazi waste az 11.16M generálás: 4096-ra cap-elve a többi 99.96% **dobódik**.

**can_place**: VAKFOLT. Nincs aggregált timing. RTree garantálja a broad-phase O(log P)-t (max 276 placed parts → log2(276)≈8 rstar lookup). Narrow-phase megragad ha sok overlap candidate van — itt **nincs adatunk**. A cgal_reference smoke `can_place_check_count` kb. 4096 × ~1.07M = ?? — túl nagy szám, valós: stats `can_place_check_count` = a nfp_placer dedup-utáni iterációk darabszáma.

**compaction**: T06-next compaction=slide vs off azonos 49.40% util → ezen az inputon a compaction nem hoz semmit. **NEM az elsődleges optimalizációs cél.**

**SA repeated eval**: Az `quality_cavity_prepack_cgal_reference` profil `search=sa` és `sa_eval_budget_sec` nincs override, tehát `default_sa_eval_budget_sec(time_limit)=time_limit/10`. Ha time_limit=240s → eval_budget=24s, de actual eval 35–40s → `clamp_sa_iters_…` `max_iters = floor((usable_time)/eval_budget)-1`. Ha actual eval > eval_budget, valós SA iterációk megakadhatnak a stop policy miatt. **A konfiguráció jelenleg sérült** — az eval_budget nem reflexta a tényleges eval költséget.

---

## 7. Algorithmic speedup options

### Option A — `[NFP DIAG]` és `[CFR DIAG]` `eprintln!` flag-mögötti gating

- **Leírás**: 5 hot-path `eprintln!` található (`nfp_placer.rs:1077, 1089, 1181, 1193`, `provider.rs:218`) — minden CFR call-on és minden NFP cache miss-en tüzelnek. Gating: csak ha `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` vagy `NESTING_ENGINE_CFR_DIAG=1`. A `cfr.rs::emit_cfr_diag` már ilyet csinál threshold-tal, csak a placer-szintű printek nincsenek gating-elve.
- **Érintett fájlok**: `placement/nfp_placer.rs:1077-1086, 1089-1100, 1181-1186, 1193-1199`; `nfp/provider.rs:218-235`.
- **Expected speedup**: low–medium (becsült 100–1000ms, mérés szükséges).
- **Correctness risk**: zero (csak logging gating).
- **Quality risk**: zero.
- **Complexity**: low (5 helyen `if std::env::var(…) == Ok("1")` wrap).
- **Required measurements**: első/utolsó mérés `NESTING_ENGINE_NFP_RUNTIME_DIAG` flag nélkül vs flag-gel; jelenleg az `[NFP DIAG]`/`[CFR DIAG]` print mindig fut, függetlenül a `NESTING_ENGINE_NFP_RUNTIME_DIAG`-tól.
- **Recommended priority**: **HIGH** (low risk × low complexity × non-zero impact).

### Option B — `placed_for_nfp` mellé `Vec<u64> placed_shape_ids` (shape_id cache)

- **Leírás**: `nfp_placer.rs:699, 937, 1059` — minden új part elhelyezésnél, MINDEN placed_part-ra újra kiszámolja `shape_id_a = shape_id(&to_lib_polygon(&placed_normalized))`, ami canonicalize_polygon + SHA-256 hash. A placed_part shape NEM változik; csak a moving_part rotation lép be a key-be. Mostani: P × (placement próbák száma) × R × hash_cost SHA-256 hívás. Optimalizáció: amikor egy új part placed, számold ki egyszer a `shape_id`-jét és tárold a `placed_for_nfp`-vel párhuzamosan; lookup helyett indexelj.
- **Érintett fájlok**: `placement/nfp_placer.rs` (új `Vec<u64> placed_shape_ids` mellé `placed_for_nfp`).
- **Expected speedup**: low–medium. SHA-256 50–100 vertex-en kb. 5–20μs; 276 placed × 276 placement attempt × 1 rotation × 5μs ≈ 0.4s. Becslés.
- **Correctness risk**: zero (cache key azonos marad, csak nem rehashelődik).
- **Quality risk**: zero.
- **Complexity**: low (~30 sor diff).
- **Required measurements**: `shape_id` call count (jelenleg nincs külön counter); flame graph segítene.
- **Recommended priority**: **HIGH**.

### Option C — Active-set candidate-first útvonal éles bekapcsolása (T06k path)

- **Leírás**: `nfp_placer.rs:606-829` az aktív-blocker spatial query → lokális NFP compute → candidate gen → `can_place()` exact validation útvonal létezik prototípusként, de a runner-en keresztül nem kapcsolódik be. A T06k report szerint env vars NINCSENEK propagálva runneren át. Bekapcsolás után az aktív-blocker count (cap 64) bezárja a CFR union input-méretét, ami O(n × k) elkerülése. A `can_place()` final-gate biztosítja az exact validation-t. Local CFR fallback és full CFR fallback már megvan (line 849-1031).
- **Érintett fájlok**: `vrs_nesting/runner/nesting_engine_runner.py` (env propagálás), `vrs_nesting/config/nesting_quality_profiles.py` (új profil pl. `quality_cavity_prepack_active_set_cgal_reference`), `placement/nfp_placer.rs` (esetleges polishing — IFP-szerinti AABB query helyett candidate AABB-szerinti, mert IFP egész lapot lefedhet).
- **Expected speedup**: high (potencionálisan 30–60% redukció CFR miatt, becslés alapján; mérés szükséges).
- **Correctness risk**: low (final gate `can_place()` minden candidate-en).
- **Quality risk**: low–medium. Active-set widening L0→L3 garantál teljes set-et legrosszabb esetben → quality-ben vagy egyenértékű vagy regresszió a candidate ordering miatt (sort by ty,tx hasonló a CFR component sort-hoz). De a candidate set forrásai eltérőek a CFR component vertices-től, ezért mérni kell utilization regret-et (legalább 3 input-on).
- **Complexity**: medium. Kód jelen van, a runner integráció + diag aggregation kell.
- **Required measurements**: utilization, sheet count, placed count regret vs default CFR path (3+ input on); per-widening-level stats `active_set_widening_level_{0,1,2,3}`.
- **Recommended priority**: **HIGH** (de kritikus a quality regret mérés).

### Option D — Hybrid CFR threshold tényleges használata

- **Leírás**: `nfp_placer.rs:1146-1178` (HYBRID_NFP_COUNT_THRESHOLD=50). Amikor `nfp_polys.len() < 50` és `NESTING_ENGINE_HYBRID_CFR=1`, a candidate generator helyett közvetlenül NFP-vertex-source-t használ, megspórolva a CFR union-t. T06j szerint kb. ~50% placement esik a threshold alá.
- **Érintett fájlok**: `vrs_nesting/runner/nesting_engine_runner.py` (env propagation + új profil), `placement/nfp_placer.rs:1170-1178` (hybrid nem ad CFR fallback-et, ha rosszul választ; T06j szerint AMBIGUOUS gate).
- **Expected speedup**: medium (CFR cost csökkentés ~50%-on, ami baseline 38%-ának fele = ~19% wall reduction; becslés).
- **Correctness risk**: low (a candidate gen különbözik, de can_place() final-gate a védelem).
- **Quality risk**: medium. T06j gate AMBIGUOUS volt (LV8 timeout). Kell quality regret mérés. NFP-vertex source candidate-ek nem azonosak a CFR-component-vertex source candidate-ekkel.
- **Complexity**: low–medium (kód jelen van, csak env propagálás + quality regret mérés kell).
- **Required measurements**: utilization regret quanti vs default + per-input call distribution.
- **Recommended priority**: medium.

### Option E — `eprintln!` STDERR throttling / batched stats emit

- **Leírás**: A `[NFP DIAG]` és `[CFR DIAG]` print sorok mind STDERR-re mennek synchronously. Egy single greedy eval során 1684 cache miss × 2 print sor + 1266 CFR call × 2 print sor = ~5900 sync stderr write. Throttle: gyűjtsd batch-be és `eprintln!` 100 sornyit egyszerre. Vagy jobb: helyettesítsd `tracing` event-ekre (only if real bottleneck).
- **Érintett fájlok**: `nfp_placer.rs`, `provider.rs`.
- **Expected speedup**: low (kb. 100–500ms a teljes wall-on).
- **Correctness risk**: zero.
- **Quality risk**: zero.
- **Complexity**: medium (introduce buffered logger).
- **Recommended priority**: low (Option A elegendő).

### Option F — `can_place` instrumentáció bekapcsolása `cfg(feature="profile")` mögött

- **Leírás**: `feasibility/narrow.rs:140 can_place_profiled` létezik, de soha nem hívódik az éles útvonalon. Cél nem az, hogy production runtime-on mindig profiled fusson; hanem hogy **legyen mód feature flaggel bekapcsolni** és aggregálni `CanPlaceProfile`-t a `NfpPlacerStatsV1`-ba. Ez ad mérést a vakfoltra (5. pontban azonosítva), és lehetővé teszi az Option C/D/G quality+speed tradeoff-jának mérését.
- **Érintett fájlok**: `feasibility/narrow.rs` (export), `placement/nfp_placer.rs` (call site swap mögé feature flag), `placement/nfp_placer.rs::NfpPlacerStatsV1` (új mezők: `can_place_profiled_…`).
- **Expected speedup**: zero (mérés-only).
- **Correctness risk**: zero (kerülő gallérok).
- **Quality risk**: zero.
- **Complexity**: low–medium.
- **Recommended priority**: **HIGH ELŐKÉSZÍTŐ TASK** Option C / D előtt.

### Option G — Active-set query AABB-jának módosítása IFP helyett candidate AABB-re

- **Leírás**: A jelenlegi T06k aktív-blocker query az `ifp_aabb`-t használja (`nfp_placer.rs:611-616`) skálázva. Az IFP minden olyan transzlációs pontot lefed, ahol a moving polygon ráfér a binbe — ami egy nagyméretű blokk. Egy kandidát-szintű AABB query (a candidate translation körüli kis ablakkal) sokkal kisebb blocker-set-et ad, így gyorsabb a lokális NFP compute.
- **Érintett fájlok**: `placement/nfp_placer.rs:611-653` (active blocker query window).
- **Expected speedup**: medium (ha widening L0/L1 fedezi a placement próbákat).
- **Correctness risk**: low — `can_place()` exact gate.
- **Quality risk**: medium — kis ablak több widening level-t kényszeríthet → több lokális NFP compute.
- **Complexity**: medium (input data flow változás).
- **Recommended priority**: medium (Option C bekapcsolása után polishing).

### Option H — SA per-iteration delta-eval (incremental greedy_multi_sheet)

- **Leírás**: Jelenleg minden SA iter teljes `greedy_multi_sheet`-t futtat (`sa.rs::eval_state_cost_with_result`). Ha az SA neighbor csak egy swap/move/rotate-et csinál (`apply_neighbor`), elvileg lehetne incrementálisan átszámolni: csak a neighbor-érintett részektől kezdve placement-elni. Ez sokkal nehezebb, mert a placement ordering (`ByArea`) lehet, hogy globálisan újrarendeződik.
- **Érintett fájlok**: `search/sa.rs::eval_state_cost_with_result`, `multi_bin/greedy.rs::greedy_multi_sheet`.
- **Expected speedup**: high (potenciálisan 5–10×, ha az incremental állapot reusable).
- **Correctness risk**: high — a teljes determinisztikusság könnyen elveszthető a savepoint state mismatchen.
- **Quality risk**: high — incremental eval ≠ teljes eval, az SA gradiens torzulhat.
- **Complexity**: very high (refaktor + state snapshot/restore architecture).
- **Required measurements**: minimum 3 input × 5 seed × byte-equivalent diff teljes eval-hez.
- **Recommended priority**: low (research path, nem első task).

### Option I — SA cheap proxy eval (csak placed_count proxy, nem teljes layout)

- **Leírás**: Tartsuk meg a teljes greedy-t a "best so far" frissítésnél, de minden SA acceptance-decision-t kétszintes proxy-val csinálj: olcsó proxy (pl. csak első sheet placement count, vagy AABB-only hierarchical fit) → teljes eval csak ha proxy elfogad. Ez a "lazy SA" pattern.
- **Érintett fájlok**: `search/sa.rs`.
- **Expected speedup**: medium (depending on proxy quality).
- **Correctness risk**: zero (a végeredmény ugyanaz, mert a "best" mindig teljes eval).
- **Quality risk**: medium (a SA gradiens proxy-szerint mozog, nem teljes szerint → más optimum-be konvergálhat).
- **Complexity**: high.
- **Recommended priority**: low (csak ha SA tényleg fut és iters > 5).

### Option J — `default_sa_eval_budget_sec` újragondolása (first-eval calibration)

- **Leírás**: `main.rs:354 default_sa_eval_budget_sec(t)=t/10` egy önkényes 10× felosztás, függetlenül attól, hogy a tényleges greedy eval mennyibe kerül. T06i azonosította: actual eval=236s, default budget=36s → SA tervezett 9 iter helyett 1.5 iter fér be. Javítás: eval_budget = 1.5× wall_clock(first_eval). Ehhez először egy szárazon-futtatott első greedy eval kell, és a konfig dinamikus. Vagy explicit override a profilban (lásd `quality_aggressive` `sa_eval_budget_sec=1`-et — az sokszorta alacsony!).
- **Érintett fájlok**: `main.rs::default_sa_eval_budget_sec`, `main.rs::run_nest` (előmérés-eval), opcionálisan `vrs_nesting/config/nesting_quality_profiles.py` (explicit override per profil).
- **Expected speedup**: zero direct, de **megakadályozza, hogy az SA semmit ne csináljon** (jelenleg gyakran 0 iter).
- **Correctness risk**: zero.
- **Quality risk**: low.
- **Complexity**: medium (előmérés-eval felépítése).
- **Recommended priority**: medium (nem speedup, hanem SA usefulness).

### Option K — Per-rotation NFP compute párhuzamosítás (rayon)

- **Leírás**: Az NFP compute a rotation loop-on belül szekvenciálisan fut. Több rotation × több placed_part kombináció független. Rayon `par_iter()` adhatna ~2-4× speedup azokon a rendszereken, ahol a CGAL probe nem CPU-bound (subprocess IPC).
- **Érintett fájlok**: `placement/nfp_placer.rs`.
- **Expected speedup**: medium (de a CGAL probe spawn ráadás overhead, nem skálázódik 1:1 core-szerinti).
- **Correctness risk**: low (NFP compute pure function).
- **Quality risk**: zero (deterministic if collected by stable order).
- **Complexity**: medium (rayon dep + ordering preserve).
- **Recommended priority**: low (cgal_reference dev-only; production OldConcave path-on lehet érdekes).

### Option L — `compute_cfr_fallback_candidates` kódduplikáció megszüntetése + lazy local→full CFR upgrade

- **Leírás**: A T06k aktív-set local CFR fallback (`nfp_placer.rs:849-921`) és full CFR fallback (`923-1031`) ugyanazt teszi mint a default CFR path, csak feltételesen. Ez kódduplikáció (4 helyen ugyanaz a NFP-collect + CFR call + can_place loop, kb. 600 sor). Tisztítás után könnyebb mérni / javítani.
- **Érintett fájlok**: `placement/nfp_placer.rs`.
- **Expected speedup**: zero direct.
- **Correctness risk**: zero (refactor only).
- **Quality risk**: zero.
- **Complexity**: medium.
- **Recommended priority**: low (post-Option C polishing).

### Option M — `MAX_VERTICES_PER_COMPONENT=512` cap finomítása CFR component-szerint

- **Leírás**: `append_candidates` minden CFR componentből max 512 vertexet vesz. Egy 12-component × 100-vertex CFR (1200 vertex) → 1200 × 25 = 30000 candidate. Egy 1-component × 600-vertex CFR (600 vertex) → 512 × 25 = 12800 candidate (mert cap). A 11.16M total mostani szám azt jelzi, hogy ~232 component-ből származik átlagosan 48k candidate (11.16M/232). Csökkentés: cap 256-ra → 50% candidate gen savings, de quality drop megjelenhet.
- **Érintett fájlok**: `placement/nfp_placer.rs:105 MAX_VERTICES_PER_COMPONENT`, `nfp_placer.rs::append_candidates`.
- **Expected speedup**: low–medium.
- **Correctness risk**: zero.
- **Quality risk**: medium (kevesebb candidate → kevesebb feasible position).
- **Complexity**: low.
- **Recommended priority**: low (nehezen kalibrálható).

---

## 8. Ranked recommendation table

| Rank | Recommendation | Files/functions | Expected speedup | Correctness risk | Quality risk | Complexity | First task? |
|------|----------------|-----------------|------------------|------------------|--------------|------------|-------------|
| 1 | **A — `eprintln!` gating hot-path-on** | `nfp_placer.rs:1077-1100,1181-1199`; `provider.rs:218-235` | low–medium | none | none | low | **YES** |
| 2 | **F — `can_place_profiled` éles aggregáció feature flag mögé** | `feasibility/narrow.rs`, `nfp_placer.rs::NfpPlacerStatsV1` | none (measurement) | none | none | low–medium | YES (előkészítő) |
| 3 | **B — placed_shape_id cache** | `nfp_placer.rs:699,937,1059` | low–medium | none | none | low | optional next |
| 4 | **C — active-set úton bekapcsolás runneren át** | runner, profiles, `nfp_placer.rs:606-829` | high (potential) | low | low–medium | medium | NO (kell előbb F mérés + C-quality regret) |
| 5 | **D — hybrid CFR threshold path** | runner, profiles, `nfp_placer.rs:1146-1178` | medium | low | medium | low–medium | NO (T06j gate AMBIGUOUS) |
| 6 | **J — eval_budget calibration / explicit profile override** | `main.rs::default_sa_eval_budget_sec`, profiles | none direct (SA usefulness) | none | low | medium | optional |
| 7 | **G — active-set query AABB candidate-szintűre** | `nfp_placer.rs:611-653` | medium | low | medium | medium | NO (post-C polishing) |
| 8 | **L — fallback kódduplikáció megszüntetése** | `nfp_placer.rs:849-1031` | zero direct | none | none | medium | NO (refactor) |
| 9 | **M — vertex cap finomítás** | `nfp_placer.rs:105` | low–medium | none | medium | low | NO (kalibrálatlan) |
| 10 | **E — STDERR batching** | `nfp_placer.rs`, `provider.rs` | low | none | none | medium | NO (A elegendő) |
| 11 | **K — rayon par_iter NFP compute** | `nfp_placer.rs` | medium | low | none | medium | NO (cgal subprocess limited) |
| 12 | **I — SA cheap proxy** | `sa.rs` | medium | none | medium | high | NO (research path) |
| 13 | **H — SA delta-eval** | `sa.rs`, `greedy.rs` | high | high | high | very high | NO (research path) |

---

## 9. Recommended next implementation task

**Cím**: T06l — Hot-path `eprintln!` gating + `can_place` profiled aggregation

**Cél**: Csökkenteni a greedy evaluation költségét két low-risk, low-complexity változással:

1. Az 5 unconditional `eprintln!("[NFP DIAG] …")` és `eprintln!("[CFR DIAG] …")` hívást gating-elni a már létező `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` és `NESTING_ENGINE_CFR_DIAG=1` flag-ek mögé.
2. A `feasibility/narrow.rs::can_place_profiled` aggregálását bekötni az éles ágba egy új `NESTING_ENGINE_CAN_PLACE_PROFILE=1` env flag mögé, az aggregált stats-okat beleíratni a `NfpPlacerStatsV1`-ba (új mezők: `can_place_profile_*`).

**Miért ez az első**:

- Mindkét változás zéró correctness és zéró quality risk-tel jár.
- Az 1-es eltávolítja a soron-blokkoló stderr write-okat, amelyek nem-mért overhead-et okoznak (becslés 100–1000ms range; kell mérés).
- A 2-es elhárítja a fő mérési vakfoltot, így a következő nagyobb beavatkozás (Option C / D) tényleges quality vs speed tradeoff-ját számokkal lehet megalapozni.
- Mindkettő néhány tucat sornyi diff, low complexity.
- Megerősíti a következő beavatkozási döntéseket — pl. ha a `can_place_profile` méri, hogy a narrow-phase costo dominálja a candidate evaluation-t, akkor az Option C aktív-set policy-jának quality regret méréséhez szükséges baseline máris megvan.

**Érintett fájlok**:

- `rust/nesting_engine/src/placement/nfp_placer.rs` (5 `eprintln!` gating; `can_place` → `can_place_profiled` swap feature flag mögött; `NfpPlacerStatsV1` új mezők)
- `rust/nesting_engine/src/nfp/provider.rs` (1 `eprintln!` gating in `compute_nfp_lib_with_provider`)
- (opcionálisan) `rust/nesting_engine/src/feasibility/narrow.rs` (export aggregálási helper, csak ha más kódot is érint)

**Nem célok**:

- Active-set bekapcsolása (külön task: Option C — T06m).
- Hybrid CFR threshold bekapcsolása production-ra (külön task: Option D — T06n).
- SA eval_budget refaktor (külön task: Option J).
- Bármilyen quality-risk-beli változás (cap finomítás, polygon simplify).
- Production kód szignifikáns átdolgozása (refactor: Option L).

**Acceptance criteria**:

- A `nesting_engine` binary `cargo build --release` után, env flag nélkül, NEM emit-eli a `[NFP DIAG]` és `[CFR DIAG]` hot-path printet (csak a 1× összegző `NFP_RUNTIME_DIAG_V1` és `CFR_DIAG_V1` line-okat).
- `NESTING_ENGINE_CAN_PLACE_PROFILE=1` env-flag-gel a `NfpPlacerStatsV1` JSON-ban megjelennek `can_place_profile_*` mezők (poly_within, overlap_query, narrow_phase ns sumok és call countok).
- Egy korábbi T06-next baseline run reprodukálva a flag-ek nélkül: a wall idő legalább 2%-kal csökken (alsó határ — várhatóan több). Stats counts változatlanok.
- Egy `cargo test --release` próbafutás (T06l-pre-existing tesztek nem regressz) PASS.
- A T06-next baseline JSON-ben mostani `nfp_provider_compute_count`, `nfp_cache_hits`, `nfp_cache_misses`, `cfr_calls`, `candidates_*_total` stats változatlanok (regression gate).

**Mérési igény**:

- Baseline mérés flag nélkül (T06l előtt): `time` mérés full LV8 cgal_reference smoke-on.
- Post-implementation flag nélkül és flag-gel; flag nélkül legyen ≥ baseline – 2% wall.
- `can_place_profile_*` stats: `narrow_phase_ns_total`, `narrow_phase_pairs_total`, `poly_within_ns_total` legalább összesítve elérhető.

---

## 10. Things not to do next

1. **Ne kapcsoljuk ki az SA-t véglegesen a `quality_cavity_prepack_cgal_reference` profilból csak azért, mert most clamp-elődik 0/1 iterre.** Az SA jelen állapot szerint amúgy sem fut nagy iter-számmal; egy quality regret mérés (search=none vs search=sa több inputon és seedeken) nélkül hozott "kapcsoljuk ki az SA-t" döntés definíció szerint regresszió-vakfoltot teremt.
2. **Ne nevezzük az aktív-set vagy candidate-driven útvonalat CFR replacement-nek.** Mindkettő `can_place()` final-gate alatt működik; a CFR az exact-feasibility reference, nem cserélhető alternatív candidate generator-ra. A `cfr.rs::compute_cfr` tényleges feasibility region-t ad vissza, az IFP-vertex+NFP-vertex-source candidate halmaz nem fedezi le ugyanazt.
3. **Ne polygon-simplify-oljunk (vertex-csökkentés) a placed parts vagy NFP polygon-ekben** exact validator nélkül. A CFR korrektsége az integer i64 koordináta + i_overlay exact arithmetic-on múlik; floating-point simplify ezt elrontaná, false-accept ne lépjen be.
4. **Ne kapcsoljuk be a hybrid CFR threshold-ot production-ra Option C aktív-set bekapcsolása előtt.** A T06j gate AMBIGUOUS volt; az Option C path quality regret mérve a hybrid is reálisan értékelhető.
5. **Ne search=none-t hirdessük production quality megoldásnak T06-next baseline alapján.** A 49.40% util mostani szám 1 input × 1 seed × 1 part ordering. Quality / regret / sheet count regret mérés legalább 3 input × 5 seed kell.
6. **Ne BLF-re vagy OldConcave-re silent fallback bekötése új útvonalra.** Ha az aktív-set vagy candidate-driven path elfogyaszt minden candidate-et és nem talál placement-et, a viselkedés `PART_NEVER_FITS_SHEET` legyen, NEM BLF fallback (a hibrid placer fallback gating a CGAL-ra már explicit a `force_nfp_for_cgal` változtatással).
7. **Ne incremental SA delta-eval (Option H) első taskként.** Az architecture refactor cost magas, és a current SA jelenleg gyakran 0 iter.
8. **Ne kódduplikáció-tisztítás (Option L) első taskként.** Nem ad direct speedup, és a kód olvashatóság meglévő stat-aggregation-t megzavarhat.
9. **Ne `MAX_CANDIDATES_PER_PART` vagy `MAX_VERTICES_PER_COMPONENT` cap szigorítás kalibrálatlanul.** A cap_applied_count=253 jelez, hogy a cap 4096-on már aktív; csökkentés direkt utilization regret-et kockáztat.

---

## 11. Open questions

1. **Az `[NFP DIAG]` / `[CFR DIAG]` `eprintln!` overhead pontos wall idő-arányú hatása ismeretlen.** Mérés: T06l implementáció után összehasonlító benchmark (Option A elsősorban erről szól).
2. **A `can_place` per-call wall idő arány a baseline 35–40s-ből pontosan mekkora?** Hipotézis 1–3s, de ez nincs mérve. T06l mérés kell.
3. **A `polygons_intersect_or_touch` segment×segment narrow-phase mennyire skálázódik a placed_part density-vel?** Worst case egyetlen `can_place` hívás (4096 / iter × 276 placed × ~50 segment × ~50 segment) — elvileg nagy szám lehet, de RTree filtere általában <10 overlap candidate. Mérés Option F-ben.
4. **A `shape_id` SHA-256 hash hot-loop overhead reális-e a T06-next baseline-ban?** 1684 NFP request × ~50 vertex SHA-256 ≈ 1684 × ~10μs ≈ 17ms — alacsony, de egy másik nagyobb input méreten (LV8 random ordering) magasabb lehet. Nincs mérés.
5. **Az SA jelen profilban hány iter-t fut valójában?** A `clamp_sa_iters_…` képlete `(usable_time/eval_budget) - 1`; SA `[SEARCH DIAG]` log-ja megadja, de explicit profile + actual eval idő összevetés hiányzik. Option J előtt mérés.
6. **Az aktív-set widening L0/L1/L2/L3 distribúció hogyan néz ki éles inputon?** A T06k report szerint env vars nem propagáltak runneren át, így mérés nem készült. Option C első benchmark-jával kiderül.
7. **A `quality_cavity_prepack_cgal_reference` profil utilization regret mértéke search=none vs search=sa között?** Egyetlen run (T06-next 49.40%) nem elég.
8. **A 11.16M generált candidate vs 1.07M after-cap arány stabil-e más inputokon vagy LV8-specifikus?** Nincs cross-input mérés.

---

## 12. Final verdict

A friss baseline (search=none, prepacked LV8, cgal_reference, 35–40s) NFP compute (40%) és CFR (38%) dominálta. Az NFP cache hit rate (99.32%) miatt további NFP compute redukció minimális (a maradék 0.68% miss az amortizable). A CFR cost a `n × k` worst-case miatt skálázás-veszélyes (T06i 20s/call peak), de a current statisztika alapján moderate.

A három legjobb beavatkozási pont: **(1)** hot-path `eprintln!` gating + `can_place` profilálás éles aggregáció (T06l első task; zero risk, low complexity, megalapozza a következő task méréseit), **(2)** active-set candidate-first path runneren át bekapcsolása (T06m; a CFR union elkerülése `can_place()` exact gate-tel; magas potenciál, kell quality regret mérés), **(3)** placed-part `shape_id` cache a per-iteration SHA-256 rehash megszüntetésére (alacsony risk, alacsony complexity).

A nem-javasolt irányok közül a SA permanens kikapcsolása, candidate-driven mint CFR replacement, polygon simplify exact validator nélkül és silent BLF/OldConcave fallback expliciten elkerülendő. Az SA delta-eval és a cheap proxy SA research-path; nem első task.

A T06l első task fókusza nem direkt speedup, hanem **mérési alap + zero-risk hot-path tisztítás**: ezzel a következő tasknak (Option C bekapcsolása) tényleges és számszerű quality vs speed tradeoff-ja van.

---

## Appendix: Audited code/function locations

| Function | File:line | Role |
|---|---|---|
| `main::run_nest` | `rust/nesting_engine/src/main.rs:420` | CLI entry |
| `default_sa_eval_budget_sec` | `main.rs:354` | t/10 budget rule |
| `build_sa_search_config` | `main.rs:360` | SA config + clamp |
| `greedy_multi_sheet` | `multi_bin/greedy.rs:634` | sheet loop + nfp_place dispatcher |
| `run_slide_compaction_postpass` | `greedy.rs:506` | per-sheet, per-item slide |
| `StopPolicy::from_env` | `greedy.rs::from_env` | wall_clock vs work_budget |
| `clamp_sa_iters_by_time_limit_and_eval_budget` | `search/sa.rs:201` | iters = floor(usable/budget) - 1 |
| `run_sa_search_over_specs` | `sa.rs:232` | SA driver |
| `eval_state_cost_with_result` | `sa.rs:450` | full greedy_multi_sheet per iter |
| `ensure_sa_stop_mode` | `sa.rs:374` | forces work_budget mode |
| `nfp_place` | `placement/nfp_placer.rs:~430` (entry) | főplacer |
| candidate-driven path | `nfp_placer.rs:516-563` | T06d |
| active-set path | `nfp_placer.rs:565-1040` | T06k |
| default CFR path | `nfp_placer.rs:1042-1212` | T05/T06 baseline |
| hybrid CFR threshold | `nfp_placer.rs:1146-1178` | T06j |
| `append_candidates` | `nfp_placer.rs:~1611` | CFR component → candidate fan-out |
| `sort_and_dedupe_candidates` | `nfp_placer.rs:1478` | sort + BTreeSet + cap |
| `generate_active_set_candidates` | `nfp_placer.rs:~1667` | T06k candidate sources |
| `compute_cfr_fallback_candidates` | `nfp_placer.rs:~2193` | T06d fallback |
| Unconditional `[NFP DIAG]` print | `nfp_placer.rs:1077, 1089` | hot-path eprintln |
| Unconditional `[CFR DIAG]` print | `nfp_placer.rs:1181, 1193` | hot-path eprintln |
| `compute_cfr_with_stats` | `nfp/cfr.rs:179` | union + diff |
| `compute_cfr_internal` | `cfr.rs:187` | belső |
| `run_overlay` | `cfr.rs:313` | i_overlay Strategy::List |
| `emit_cfr_diag` | `cfr.rs:108` | already gated by 50/1000ms threshold + flag |
| `NfpCache::get / insert` | `nfp/cache.rs:52,64` | HashMap; clear-all on MAX_ENTRIES=10_000 |
| `shape_id` | `cache.rs:101` | canonicalize + SHA-256 → u64 |
| `compute_nfp_lib_with_provider` | `nfp/provider.rs:211` | tartalmaz unconditional `[NFP DIAG]` printet |
| `OldConcaveProvider::compute` | `provider.rs:180` | dispatch convex/concave |
| `compute_ifp_rect` | `nfp/ifp.rs:24` | rect-bin AABB IFP, tiszta |
| `aabb_overlaps`, `aabb_inside` | `feasibility/aabb.rs:37,45` | TOUCH_TOL inflated |
| `can_place` | `feasibility/narrow.rs:79` | éles kapu |
| `can_place_profiled` | `narrow.rs:140` | NEM hívja senki éles útvonalon |
| `polygons_intersect_or_touch` | `narrow.rs:261` | narrow-phase kernel |
| `point_in_polygon` | `narrow.rs:305` | winding number ring inclusion |
| `PlacedIndex` (Vec + RTree) | `narrow.rs:40` | broad-phase |
| `quality_cavity_prepack_cgal_reference` profile | `vrs_nesting/config/nesting_quality_profiles.py:62-68` | search=sa, kerf, no eval_budget override |
| `--sa-eval-budget-sec` plumb | `nesting_engine_runner.py:233-262` | override path |
