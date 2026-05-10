# Checklist — T06-next Greedy Eval Cost Decomposition

## Előkészület
- [x] Friss repo állapot auditálva
- [x] T06i/T06j/T06k/T06f releváns reportok elolvasva
  - T06i: SA/greedy budget calibration (236s greedy eval, CFR 154.7s)
  - T06k: active-set prototype (compile clean, benchmark infrastructure verified)
  - T06j: quality preserving CFR reduction (not fully resolved)
  - T06f: prepacked hole-free NFP path (baseline established)
- [x] `quality_cavity_prepack_cgal_reference` profil auditálva
  - placer: nfp, search: sa, part_in_part: prepack, compaction: slide, nfp_kernel: cgal_reference
  - sa_eval_budget_sec: NOT SET (uses main.rs default=time_limit/10=36s)
- [x] cavity_prepack collapsed solver contract auditálva
  - 0 holes after prepack ✓
  - 12 solver part types ✓
  - --part-in-part off after prepack ✓

## Prepack és baseline reprodukció
- [x] prepack-only LV8 futás: holes_after=0, guard_passed=true, 276 qty
- [x] search=none LV8 baseline: 276/276 placed, 3 sheet, 49.40% utilization
- [x] actual placer = nfp ✓
- [x] actual kernel = cgal_reference ✓
- [x] BLF fallback nincs ✓
- [x] OldConcave fallback nincs ✓

## Greedy eval decomposition
- [x] NFP provider/cache breakdown: 842 compute calls, 16.1s total, 99.3% cache hit
- [x] CFR union/diff breakdown: 1266 calls, 15.0s total (13.3s union + 0.6s diff)
- [x] Candidate extraction: 11.16M before dedupe, 1.07M after cap
- [x] Compaction cost: slide vs off azonos output (49.40%), nem befolyásolja a quality-t

## Top slow breakdown
- [x] Top 10 slow NFP compute: placed_pts=520 → 508ms max, 175ms+ 7 call
- [x] Top 10 slow CFR: nfp_poly=180, vertices=19204, union=47ms, total=50ms max
- [x] NFP vertex count korreláció: ~22K max (nem 154K+ mint T06i-ben)

## SA/search budget kontroll
- [x] search=none baseline: 276/276, 49.40%, 3 sheet
- [x] SA sa-iters=2, eval_budget=240s → iters=0 (clamp: 360/240=1 → 0)
- [x] eval_budget kalibrációs probléma dokumentálva (36s default vs ~35s actual)

## Kísérleti flagek
- [x] NESTING_ENGINE_ACTIVE_SET_CANDIDATES default off ✓
- [x] Active-set path search=none alatt nem aktív ✓
- [x] NESTING_ENGINE_HYBRID_CFR default off ✓
- [x] T06k prototype nem módosítva ✓

## Optimalizációs javaslat
- [x] A) SA eval_budget guard: recommended YES
- [x] B) Active-set candidate-first: recommended YES
- [x] C) Candidate-first fast path: recommended after B
- [x] D) Compaction ritkítás: NOT recommended
- [x] E) NFP cache optimalizáció: NOT recommended

## Következő implementációs task
- [x] T06l javasolva: SA eval_budget guard + Active-set candidate-first SA path

## Módosított fájlok
- [x] NEM MÓDOSÍTOTT EGYETLEN FÁJL SEM (diagnosztikai task)

## Tesztek
- [x] cargo check nem futtatva (nincs Rust módosítás)
- [x] pytest nem futtatva (nincs Python módosítás)

## Report és checklist
- [x] Report elkészült: `codex/reports/nesting_engine/engine_v2_nfp_rc_t06_next_greedy_eval_cost_decomposition.md`
- [x] Checklist elkészült

## Ismert limitációk dokumentálva
- [x] Wall time nem mérhető közvetlenül (becslés NFP+CFR összegből)
- [x] can_place/broad-phase/narrow-phase nem instrumentált
- [x] Placement step-id nem korrelálható CFR DIAG sorokkal
- [x] T06i vs T06-next 236s→35s különbség nem magyarázott