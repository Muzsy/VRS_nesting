# T06e Checklist — NFP Runtime Breakdown + Provider/Cache Audit

## Teljesített Feladatok

- [x] T06d report elolvasva
- [x] T06d LV8 timeout értelmezése ellenőrizve — **HELYESBÍTVE**: hybrid gating, nem NFP/CFR bottleneck
- [x] NESTING_ENGINE_NFP_RUNTIME_DIAG implementálva (`NfpRuntimeDiagV1` struktúra) — részben (struktúra létrehozva, emisszió integráció TODO)
- [x] NFP request count mérve (meglévő NFP_DIAG logokból)
- [x] NFP cache hit/miss mérve (cache debug log: 92K hit, 826 miss, 99%+ hit rate)
- [x] NFP provider compute time mérve (CFR_DIAG: 156-168ms max union; NFP_DIAG: CGAL 73-231ms)
- [x] per-pair/per-rotation timing top lista készült (lv8_pair_01/02/03: CGAL 73-231ms, OldConcave: timeout)
- [x] CFR union/diff idő továbbra is mérve (CFR_DIAG_V1 aktív)
- [x] candidate-driven candidate/can_place idő mérve (T06d-ből: 6093 checks, 9 accepted)
- [x] BLF / hybrid fallback count mérve vagy auditálva (default LV8: 100% BLF fallback, hybrid gating ok)
- [x] OldConcave provider audit elkészült (3 toxic LV8 pair: timeout 5s alatt)
- [x] CGAL provider audit elkészült (3 toxic LV8 pair: 73-231ms, SUCCESS)
- [x] LV8 CFR benchmark részlegesen futtatva (CGAL útvonal, 196 NFP polygonnál timeout 300s alatt)
- [x] LV8 candidate-driven benchmark — nem futott NFP-n (hybrid gating ok)
- [x] 3-rect regression benchmark futtatva (9/9 placed, 1 sheet, byte-for-byte azonos)
- [x] default behavior nem változott
- [x] candidate-driven behavior csak flag alatt fut
- [x] nincs optimizer rewrite
- [x] nincs provider policy change
- [x] nincs production Dockerfile változás
- [x] cargo check PASS (39 warnings)
- [x] cargo test PASS — 145 PASS, 0 FAIL
- [x] következő task javaslat elkészült

## Nyitott/TODO

- [ ] NESTING_ENGINE_NFP_RUNTIME_DIAG emisszió integrálása a nfp_place() return ágba (NfpRuntimeDiagV1.emit_summary() hívása)

## Kritikus Megállapítások

1. **T06d LV8 timeout HIBÁS ÉRTELMEZÉS** — nem NFP compute vagy CFR bottleneck, hanem hybrid gating
2. **Hybrid gating BLF-re váltja az NFP placert 9/12 hole-part miatt** — CGAL kernel beállításával bypassolható
3. **OldConcave minden toxic LV8 pair-en timeout** — legkisebb (73K fragment pairs) is timeout 5s alatt
4. **CGAL mindhárom toxic LV8 pair-t megoldja 73-231ms alatt**
5. **CGAL útvonalon: CFR union a másodlagos bottleneck** (196ms max vs provider compute <300ms)
6. **Cache működik: 99%+ hit rate, 0 eviction**
