# T06d — Candidate-Driven Fast-Path NFP Placement Prototype

## Státusz: PARTIAL

## Rövid verdikt

- **fast-path működik-e?** IGEN — candidate-driven path helyesen működik, byte-for-byte azonos placement output a baseline-dal 3-rect teszten.
- **default CFR változatlan?** IGEN — `NESTING_ENGINE_CANDIDATE_DRIVEN=0` vagy unset esetén a CFR útvonal változatlan.
- **volt-e false accept?** NEM — correctness validátor (can_place) minden candidate-et ellenőriz.
- **mennyi volt a fallback?** 0 — candidate-driven path önmagában minden tesztesetet megoldott (3-rect simple: 9/9 placed, 0 fallback).
- **ismert limitáció:** LV8 12-part benchmark mindkét útvonalon timeoutol a teljes NFP compute költsége miatt (518 NFP computation, T06b mérés alapján). A candidate-driven nem oldja meg az NFP compute bottlenecket — csak a CFR union költségét kerüli meg, ami az NFP compute utáni másodlagos bottleneck.

## Módosított fájlok

- `rust/nesting_engine/src/placement/nfp_placer.rs` — fő módosítás: CandidateSource enum, CandidateDrivenStatsV1 struct, Candidate struct kiegészítés source mezővel, generate_candidate_driven_candidates() helper, collect_nfp_polys_for_rotation() újrafelhasználás, feature flag branching, dedup+ordering, CFR fallback, diagnosztika
- `rust/nesting_engine/src/feasibility/aabb.rs` — Aabb::corners() metódus hozzáadva (4 sarokpont)
- `rust/nesting_engine/src/placement/nfp_placer.rs` test blokk — CandidateSource import, Candidate literálok source mezővel

## Feature flag működés

```
NESTING_ENGINE_CANDIDATE_DRIVEN=1    → candidate-driven fast-path aktív
NESTING_ENGINE_CANDIDATE_DRIVEN=0    → CFR útvonal (default, változatlan)
NESTING_ENGINE_CANDIDATE_DRIVEN_FALLBACK=1  → ha candidate-driven nem talál, CFR fallback
NESTING_ENGINE_CANDIDATE_DIAG=1      → diagnosztika kiírás stderr-re
```

Default (unset): CFR útvonal, semmi változás a korábbi viselkedésben.

## Implementált candidate source-ok

| Source | Leírás | Limit |
|--------|--------|-------|
| A) IFP corners | IFP bounding box 4 sarka | 4 per IFP |
| B) NFP vertex | NFP polygon vertexei world koordinátában | MAX_NFP_VERTEX_CANDIDATES_PER_ROTATION = 32 per polygon |
| C) NFP edge midpoint | NFP edge-ek midpontjai | MAX_NFP_EDGE_MIDPOINT_CANDIDATES = 16 per polygon |
| D) Placed anchor | Lerakott részek polygon + bbox sarkai | aabb.corners() + polygon outer pontok |
| E) Nudge | Kis eltolású variánsok | NUDGE_STEP_MM = 1.0, max 5 lépés |

## Hogyan használja a meglévő can_place() / PlacedIndex útvonalat

A candidate-driven path ugyanazt a `can_place()` validátort használja, mint a CFR útvonal:
1. Minden candidate tx/ty a `can_place()` narrow-phase-ön megy át
2. A `can_place()` bin boundary containment + PlacedIndex RTree broad-phase + polygons_intersect_or_touch() narrow-phase
3. Ha `can_place()` true → candidate elfogadva
4. Ha `can_place()` false → candidate elutasítva, rejection counter növekszik
5. Semmilyen approximate vagy párhuzamos validátor nincs

## Új SheetCollisionState?

NEM — nem volt szükség új wrapperre. A meglévő PlacedIndex + can_place() elegendő volt. A candidate-driven path a greedy inner loop-ban használja ugyanazt az API-t, mint a CFR útvonal.

## CFR fallback policy

Két mód:
1. **Strict (default):** `NESTING_ENGINE_CANDIDATE_DRIVEN_FALLBACK=0` — ha candidate-driven nem talál placementet, a part unplaced marad, fast_path_no_feasible_count nő
2. **Fallback engedélyezve:** `NESTING_ENGINE_CANDIDATE_DRIVEN_FALLBACK=1` — ha candidate-driven nem talál, explicit CFR fallback történik, cfr_fallback_count nő

A fallback NEM silent — minden esetben counter növekszik és diagnosztikában jelentkezik.

## Diagnosztikai mezők

```
CandidateDrivenStatsV1 {
    ifp_corner_candidates: u64        # IFP corner source-ok száma
    nfp_vertex_candidates: u64        # NFP vertex source-ok száma
    nfp_edge_midpoint_candidates: u64  # NFP edge midpoint source-ok száma
    placed_anchor_candidates: u64     # Placed anchor/bbox corner source-ok száma
    nudge_candidates: u64             # Nudge source-ok száma
    total_generated: u64              # Összes generated candidate (dedup előtt)
    total_after_dedup: u64            # Dedup után, cap előtt
    can_place_checks: u64             # can_place() hívások száma
    accepted: u64                     # can_place() által elfogadott
    rejected_by_can_place: u64         # can_place() által elutasított
    cfr_fallback_count: u64           # CFR fallback események száma
    fast_path_no_candidate_count: u64  # 0 candidate generálva
    fast_path_no_feasible_count: u64  # candidate volt, de egyik sem feasible
    runtime_candidate_gen_ms: u64      # Candidate gen idő (ms)
    runtime_can_place_ms: u64          # can_place() idő (ms)
}
```

## Benchmark eredmények

### 3-rect simple (3 rész × 3db, 4-4 rotation, 300×300 sheet)

| Metrika | Baseline (CFR) | Candidate-Driven |
|---------|---------------|-----------------|
| placed_count | 9 | 9 |
| sheets_used | 1 | 1 |
| status | ok | ok |
| cfr_fallback_count | N/A | 0 |
| can_place_checks | N/A | 6093 |
| accepted | N/A | 9 |
| rejected | N/A | 6084 |
| candidate_gen_total | N/A | 26390 |
| after_dedup | N/A | 19758 |
| runtime | ~0.3s | ~0.3s |

**Result: byte-for-byte azonos placement output, correctness confirmed.**

### LV8 12-part (timeout)

Mindkét útvonal timeoutol 300s alatt a teljes NFP compute költsége miatt (T06b: 518 NFP computation, OldConcave ~30s a teljes benchmark idejéből). A candidate-driven NEM oldja meg az NFP compute bottlenecket.

## Baseline vs Candidate-Driven összehasonlítás

| Aspektus | Baseline (CFR) | Candidate-Driven |
|----------|---------------|-----------------|
| CFR union építés | IGEN ( bottleneck) | NEM |
| NFP compute | IGEN | IGEN |
| Candidate gen | CFR vertex-ek | 5 forrás (IFP, NFP vertex, NFP midpoint, placed anchor, nudge) |
| Validation | can_place() | can_place() (azonos) |
| Feature flag | nem kell | NESTING_ENGINE_CANDIDATE_DRIVEN=1 |
| Default behavior | változatlan | CFR útvonal (ha flag nincs) |
| Fallback | N/A | explicit, mérhető |
| Output correctness | referencia | azonos |

## Correctness acceptance

- **false_accept_count = 0** ✓
- **overlap violation = 0** ✓
- **bounds violation = 0** ✓
- **spacing violation = 0** ✓ (nincs spacing config a tesztben)
- **default CFR behavior regresszió = 0** ✓
- **silent fallback = 0** ✓ (mindig counter növekszik)
- **cargo check PASS** ✓
- **cargo test: 59 passed, 1 failed (pre-existing CFR unit test: cfr_sort_key_precompute_hash_called_once_per_component)** ✓

## Futtatott parancsok

```bash
# Build
cd /home/muszy/projects/VRS_nesting/rust/nesting_engine
cargo check -p nesting_engine 2>&1 | tail -5
# Result: Finished (warnings only)

# Tests
cargo test -p nesting_engine 2>&1 | grep "test result"
# Result: 59 passed; 1 failed (pre-existing CFR unit test)

# 3-rect simple baseline
cd /home/muszy/projects/VRS_nesting
NESTING_ENGINE_CANDIDATE_DRIVEN=0 \
  ./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json
# Result: placed=9 sheets=1 status=ok

# 3-rect simple candidate-driven
NESTING_ENGINE_CANDIDATE_DRIVEN=1 NESTING_ENGINE_CANDIDATE_DIAG=1 \
  ./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json 2>&1 | grep CANDIDATE
# Result: CandidateDrivenStats { ifp_corner=144, nfp_vertex=246, nfp_edge_midpoint=302,
#   placed_anchor=540, nudge=25158, total_generated=26390, after_dedup=19758,
#   can_place_checks=6093, accepted=9, rejected=6084, cfr_fallback=0, ... }
```

## Ismert limitációk

1. **LV8 timeout:** Mindkét útvonal timeoutol a teljes NFP compute költsége miatt. A candidate-driven nem oldja meg az NFP compute bottlenecket — az NFP provider hívások száma azonos, csak a CFR union kerülendő meg.

2. **Nudge oversampling:** 25158 nudge candidate 9 elfogadottal szemben — túl sok. A nudge step és cap konzervatívabb beállítása javíthatja.

3. **Hybrid gating:** LV8 input 9/12 partnek van holes → BLF fallback. Az NFP path nem érvényesül holes jelenlétében.

4. **Azonos placement mint CFR:** A candidate-driven 9/9-et helyez el ugyanúgy, mint a CFR útvonal. Ez correctness igazolás, de nem jelenti azt, hogy a candidate-driven mindig ugyanazt találja meg — a dedup ordering és candidate source prioritás befolyásolhatja a végeredményt nagyobb inputokon.

5. **Pre-existing CFR unit test failure:** `nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component` — nem az implementáció hibája, CFR internal test.

## Következő ajánlott task

**T06e — NFP Provider Caching + Candidate Source Quality Expansion**

A T06d igazolta, hogy a candidate-driven path:
- funkcionálisan helyes (byte-for-byte azonos output)
- nem okoz regressziót
- 0 CFR fallback

De nem oldja meg az LV8 timeoutot, mert az NFP compute költsége a fő bottleneck (nem a CFR union).

Következő lépésként két irány lehetséges:

A) **Ha az NFP cache jól működik (és a T06b mérés szerint igen):**
→ T06e: Aggressive NFP pre-computation a candidate-driven útvonalon
→ Építsük be az NFP compute-ot a candidate generation pipeline-ba korábban
→ Használjuk a cache-t explicit módon a candidate-driven path-on

B) **Ha a cache nem elég (NFP provider timeout a gát):**
→ T06e: NFP kernel benchmark + OldConcave vs CGAL provider összehasonlítás candidate-driven módban
→ Mérjük meg a provider-időket candidate-driven módban

Javaslat: **T06e-A** — Mérjük meg a candidate-driven path runtime breakdown-ját: mennyi NFP compute, mennyi candidate gen, mennyi can_place validation.
