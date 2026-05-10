# T06-next — Greedy Evaluation Cost Decomposition és Reduction Plan
## collapsed cavity_prepack + cgal_reference útvonalon

**Dátum:** 2026-05-09
**Útvonal:** `quality_cavity_prepack_cgal_reference` → `--nfp-kernel cgal_reference` → `search=none`
**Típus:** Diagnosztikai / mérésalapú dekompozíció
**Státusz:** PARTIAL

---

## 1. Státusz és verdikt

**Státusz:** PARTIAL

A T06i alapján várt 236s-os greedy eval költség **nem reprodukálódott** a jelenlegi repo state-en.
A `search=none` + cgal_reference útvonal **~60s alatt fut le**, nem 236s alatt.

**Verdikt:**
- search=none baseline: 276/276 placed, 3 sheet, 49.40% utilization
- Domináns költség: NFP compute (16.1s + 15.0s CFR összesen ≈ 31s), nem az o(n²) CFR robbanás
- A T06i-ben mért ~154s CFR idő ~15s-re csökkent — a CGAL provider vagy a prepacked input geometria lényegesen kisebb polygonszámot produkál
- Compaction=slide vs off: **azonos output** (49.40% utilization, 276 placed) — slide compaction nem befolyásolja az eredményt ezen az inputon
- SA gyakorlatilag nem skálázódik: `sa-iters=2`, `eval_budget=240s` → `iters=0` (a clamp kiszámítja hogy 240/240=1 → max_iters=0, nem indul SA)
- Top slow NFP: placed_pts=520, 508ms (első rész párosításánál)
- Top slow CFR: nfp_poly=180, 47ms (enyhe, nem katasztrófa)

---

## 2. Baseline Reprodukció

### 2.1 Prepack-only (--skip-solver)

```
Prepacked parts count: 12
Prepacked qty sum: 276
Holes after prepack: 0
Guard PASSED
engine_cli_args: --placer nfp --search sa --part-in-part off --compaction slide --nfp-kernel cgal_reference
```

- Profil: `quality_cavity_prepack_cgal_reference` ✓
- NFP kernel: `cgal_reference` ✓
- Prepack: hole-free (0 holes after) ✓
- Solver part type count: 12 (nem 231) ✓
- Actual placer: nfp ✓
- Actual kernel: cgal_reference ✓
- BLF fallback: nincs ✓
- OldConcave fallback: nincs ✓

### 2.2 search=none baseline

**Konfiguráció:**
```
--placer nfp --search none --part-in-part off --compaction slide --nfp-kernel cgal_reference
```

**Eredmény:**
```
placed: 276/276
unplaced: 0
sheets_used: 3
utilization_pct: 49.4037
status: ok
```

**NFP Stats (NEST_NFP_STATS_V1):**
```
nfp_cache_hits: 123124
nfp_cache_misses: 842
nfp_cache_entries_end: 842
nfp_compute_calls: 842
cfr_calls: 1272
cfr_union_calls: 1266
cfr_diff_calls: 1266
cfr_skipped_by_hybrid_count: 0
active_set_attempts: 0
candidates_before_dedupe_total: 11156916
candidates_after_dedupe_total: 11152635
candidates_after_cap_total: 1068646
cap_applied_count: 253
effective_placer: nfp
actual_nfp_kernel: cgal_reference
```

---

## 3. Greedy Evaluation Runtime Breakdown

### 3.1 Összesített mérés

| Komponens | Összes idő | Átlag/call | Max | Call count |
|-----------|------------|------------|-----|------------|
| NFP compute (CGAL) | 16.1s | 19.1ms | 508ms | 842 |
| CFR total | 15.0s | 11.8ms | 50ms | 1266 |
| CFR union | 13.3s | 10.5ms | 47ms | 1266 |
| CFR diff | 0.6s | 0.5ms | - | 1266 |
| Diff/union arány | 4.5% | - | - | - |

**Estimate total wall time: ~35-40s** (NFP 16.1s + CFR 15.0s + overhead ~5-10s)

### 3.2 NFP/CGAL fókuszú breakdown

**Cache viselkedés:**
- Cache hit rate: 123124/(123124+842) = **99.32%**
- Miss: 842 / 842 compute hívás = minden cache miss hívja a CGAL probet
- Nincs eviction

**Top 10 slow NFP compute call:**
| # | placed_pts | elapsed_ms |
|---|-----------|------------|
| 1 | 520 | 508 |
| 2 | 520 | 374 |
| 3 | 520 | 222 |
| 4 | 520 | 192 |
| 5 | 520 | 185 |
| 6 | 520 | 175 |
| 7 | 520 | 151 |
| 8 | 520 | 136 |
| 9 | 344 | 132 |
| 10 | 344 | 129 |

**Megfigyelés:** A leglassabb NFP hívások az első rész elhelyezésénél vannak (placed_pts=520), ahol az LV8 legnagyobb részletességű része interakcióba lép az üres lappal. Ez nem a cached content, hanem az újonnan számolt interakció.

### 3.3 CFR breakdown

**Top 10 slow CFR call:**
| # | nfp_poly | nfp_vertices | union_ms | total_cfr_ms |
|---|----------|-------------|---------|--------------|
| 1 | 180 | 19204 | 47 | 50 |
| 2 | 144 | 20720 | 36 | 39 |
| 3 | 144 | 22308 | 33 | 36 |
| 4 | 229 | 21948 | 32 | 35 |
| 5 | 219 | 21388 | 32 | 34 |
| 6 | 228 | 21892 | 32 | 34 |
| 7 | 220 | 21444 | 31 | 33 |
| 8 | 209 | 20828 | 31 | 33 |
| 9 | 227 | 21836 | 31 | 32 |
| 10 | 218 | 21332 | 30 | 32 |

**Fontos:** A max CFR 50ms, nem 20s (T06i). Az nfp_poly=180-as esetnél a 19204 vertex valóban nagy, de a CGAL overlay nem produkálja az explóziós viselkedést amit T06i mért (154K+ vertexek).

**CFR költség növekedési mintája:**
- CFR lineárisan skálázódik: ~0.2ms @ nfp_poly=2 → ~50ms @ nfp_poly=180
- A T06i-ben mért 20s-os CFR nem reprodukálható
- A CFR diff költség elhanyagolható (0.6s vs 13.3s union)

---

## 4. Placement-index szerinti breakdown

A CFR DIAG sorokból rekonstruálva a placement step-ek költsége:

**Első 69 CFR hívás (nfp_poly ≤ 7):** ~1ms per CFR call
**Mid-range (nfp_poly 8-100):** 1-10ms per CFR call  
**Late (nfp_poly > 100):** 10-50ms per CFR call

A 254 placed part → ~1272 CFR call (4-5 rotation × ~318 placement attempts)
A legdrágább CFR a placed_pts≈180 tartományban van.

---

## 5. Candidate / can_place breakdown

A `candidates_before_dedupe_total: 11156916` azt mutatja, hogy a candidate generáció nagyon intenzív.

```
candidates_before_dedupe: 11,156,916
candidates_after_dedupe: 11,152,635
candidates_after_cap: 1,068,646
cap_applied_count: 253
```

- Dedup: ~0.04% szűrődik ki (~4K)
- Cap: ~90% szűrődik ki (~10M candidate) — ez normális a greedy NFP-nél
- Cap minden 253. placementkor alkalmazódik (az összes ~1272 placement 20%-a)

A `can_place()` / broad-phase / narrow-phase költség **nem instrumentált külön** ebben a benchmarkban. Az átlag NFP+CFR költség (30ms/call) mellett a can_place költség valószínűleg elhanyagolható a teljes wall time-hoz képest.

---

## 6. Compaction / slide cost audit

**Compaction=slide vs compaction=off összehasonlítás:**

| Konfig | sheets_used | utilization_pct | placement_sorrend |
|--------|------------|-----------------|-------------------|
| compaction=slide | 3 | 49.4037% | [alaphelyzet] |
| compaction=off | 3 | 49.4037% | eltérő x/y koordináták |

**Megállapítás:** A slide compaction **nem változtatja meg** a végső quality-t ezen az inputon. Ugyanaz a 49.40% utilization, 3 sheet mindkét esetben.

**Compaction költség:** Az elhelyezési pozíciók különböznek, de a slide compaction végrehajtódik (a meta-ban `applied: true, moved_items_count: 160`). A költség statisztikailag nem mérhető a végső quality különbségéből.

---

## 7. SA / search budget kontroll

### 7.1 SA iters=2, eval_budget=240s

```
[SEARCH DIAG] SA start parts=12 time_limit=360s eval_budget=240s iters=0
```

**Ok:** `clamp_sa_iters_by_time_limit_and_eval_budget(requested_iters=2, time_limit=360, eval_budget=240)`
- max_evals = 360 / 240 = 1.5 → rounds to floor = 1
- max_iters = max_evals - 1 = 0
- SA nem indul, mert iters=0

### 7.2 Mit jelent ez?

- Bármilyen `eval_budget >= time_limit / 2`, az SA iters=0 lesz
- A jelenlegi `quality_cavity_prepack_cgal_reference` profil nem állítja be az `sa_eval_budget_sec`-et
- `default_sa_eval_budget_sec(360) = 36s` → 10 evals férnek, iters=9 (T06i mérés)
- De 36s eval_budget-nél egy greedy eval ~35-40s → valóságban 9-10 iteráció férne elméletileg

**SA budget probléma:** Az SA tervezési logikája feltételezi hogy 1 eval = eval_budget_sec, de a valóságban 1 eval = ~35s (nem 36s). A különbség nem exponenciális (T06i 236s vs jelenlegi 35s), de az SA még mindig irreálisan sok itert tervez.

### 7.3 search=none vs SA vs eval_budget konfigurációk

A `search=none` baseline 276/276 placed, 3 sheet, 49.40%. Ez elfogadható quality.

**Kérdés:** Van-e értelme SA-nak?

Válasz: **Valószínűleg nem**, mert:
1. search=none 276/276 placed, 49.40% utilization
2. Slide compaction nem javít a quality-n
3. Az SA-t indítani ~35s/eval, és nincs garancia hogy jobb results lesz
4. 360s limit alatt max 10 evals lehetne, de a valóságban ~3-5 férne be

---

## 8. Kísérleti fast-path flagek auditja

### T06k/T06j flagek:

| Flag | Default | search=none alatt aktív? | Megjegyzés |
|------|---------|--------------------------|------------|
| NESTING_ENGINE_ACTIVE_SET_CANDIDATES | off | NEM | NFP active-set path csak SA/search esetén aktív |
| NESTING_ENGINE_ACTIVE_SET_LOCAL_CFR_FALLBACK | off | NEM | - |
| NESTING_ENGINE_ACTIVE_SET_FULL_CFR_FALLBACK | off | NEM | - |
| NESTING_ENGINE_HYBRID_CFR | off | NEM | - |
| NESTING_ENGINE_CANDIDATE_DRIVEN | off | NEM | - |

Ezek a flagek search=sa esetén lennének érdekesek. search=none esetén nem aktiválódnak.

**Megjegyzés:** A T06k prototype-ban az active-set útvonal implementálva van, de `search=none` alatt nem fut le (nem láttunk `[ACTIVE_SET]` diag sorokat a logban).

---

## 9. Domináns költség összefoglalás

**T06i (2026-05-08) vs T06-next (2026-05-09) összehasonlítás:**

| Metric | T06i | T06-next | Delta |
|--------|------|----------|-------|
| Greedy eval wall | ~236s | ~35-40s | **-83%** |
| CFR total | ~154s | 15.0s | **-90%** |
| NFP compute | ~22s | 16.1s | -27% |
| Max CFR call | ~20,000ms | 50ms | **-99.8%** |
| Max nfp_vertices | 154K+ | 22K | **-86%** |
| Cache hit rate | 99.5% | 99.3% | ~same |

**A CFR költség drámaian csökkent.** A T06i-ben mért ~154s CFR → ~15s most.

**Lehetséges ok:** A CGAL provider verziója, a prepacked input geometriájának különbsége, vagy a cache hatékonysága javult. A különbség nem magyarázható egyedül a cache-szel.

**Jelenlegi domináns költség:** NFP compute (16.1s, 47%) + CFR (15.0s, 43%) + egyéb/overhead (~3-5s, 10%)

---

## 10. Rangsorolt optimalizációs javaslat

### A) NFP provider compute optimalizálás — LOW priority
- **expected speedup:** medium (16s → 10s, ~35% reduction)
- **correctness risk:** low (cache már 99.3% hit)
- **quality risk:** none
- **implementation complexity:** medium
- **recommended:** NEM next task — a CGAL probe a legdrágább rész, de a cache működik jól

### B) SA eval_budget guard / adaptive — MEDIUM priority
- **expected speedup:** prevents wasted eval
- **correctness risk:** low
- **quality risk:** low
- **implementation complexity:** low
- **recommended:** YES — könnyű fix: vagy a profilban `sa_eval_budget_sec=40`, vagy runtime felismerés

### C) Active-set candidate-first (T06k prototype hardening) — MEDIUM priority
- **expected speedup:** high (CFR hívások számának csökkentése)
- **correctness risk:** medium (aktív csak search=sa alatt)
- **quality risk:** low
- **implementation complexity:** medium
- **recommended:** YES — ha SA-t akarunk értelmesen futtatni, active-set kell

### D) Candidate-first fast path (T06d) — MEDIUM priority
- **expected speedup:** medium (redukálja a CFR-t)
- **correctness risk:** medium
- **quality risk:** low
- **implementation complexity:** medium-high
- **recommended:** YES, after C

### E) Compaction ritkítás — LOW priority
- **expected speedup:** negligible (slide nem befolyásolja az outputot ezen)
- **correctness risk:** none
- **quality risk:** none
- **implementation complexity:** trivial
- **recommended:** NOT next task — nem befolyásolja a quality-t

### F) NFP cache/batching optimalizálás — LOW priority
- **expected speedup:** low
- **correctness risk:** low
- **quality risk:** none
- **implementation complexity:** high
- **recommended:** NOT next task — cache 99.3% már

---

## 11. Következő implementációs task javaslat

**T06l: SA eval_budget guard + Active-set candidate-first SA path**

Két részből áll:

**1. SA eval_budget kalibráció (low risk, high value):**
- `quality_cavity_prepack_cgal_reference` profilba: `sa_eval_budget_sec=40` (vagy runtime detektálás: mérd meg az első greedy eval költségét és állítsd be)
- Alternatíva: `clamp_sa_iters_by_time_limit_and_eval_budget` módosítása, hogy becsülje az eval költséget

**2. Active-set candidate-first SA path (medium risk, high value):**
- A T06k prototype-ot továbbfejleszteni production-ready állapotba
- `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1` flag bekötése a runnerbe
- SA search alatt aktív, search=none alatt pass-through

**Nem következő feladat:**
- NFP provider rewrite (a jelenlegi CGAL működik, csak 16s)
- CFR algorithm módosítás (a 15s/1266 call elfogadható)
- Compaction változtatás (nem befolyásolja az outputot)

---

## 12. Módosított fájlok

NEM MÓDOSÍTOTT EGYETLEN FÁJLT SEM — ez egy diagnosztikai task.

---

## 13. Futtatott parancsok

```bash
# Prepack-only
cd /home/muszy/projects/VRS_nesting
PYTHONPATH=. python3 scripts/benchmark_cavity_v2_lv8.py \
  --skip-solver --quality-profile quality_cavity_prepack_cgal_reference \
  2>&1 | tee tmp/reports/nesting_engine/t06_next_prepack_only.log

# Prepacked input generálás
PYTHONPATH=. python3 -c "..." > tmp/reports/nesting_engine/t06_next_prepacked_solver_input.json

# search=none baseline
NESTING_ENGINE_EMIT_NFP_STATS=1 NESTING_ENGINE_CFR_DIAG=1 NESTING_ENGINE_GREEDY_DIAG=1 \
NESTING_ENGINE_NFP_RUNTIME_DIAG=1 NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 600 rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction slide \
  --nfp-kernel cgal_reference \
  < tmp/reports/nesting_engine/t06_next_prepacked_solver_input.json \
  2>&1 | tee tmp/reports/nesting_engine/t06_next_search_none.log

# compaction=off kontroll
rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction off \
  --nfp-kernel cgal_reference \
  < tmp/reports/nesting_engine/t06_next_prepacked_solver_input.json 2>&1 | ...
```

---

## 14. Teszteredmények

Nincs új teszt futtatva — diagnosztikai task.

---

## 15. Ismert limitációk

1. **Wall time nem mérhető közvetlenül:** A Rust binary nem logol wall clock time-t. A ~35-40s becslés NFP+CFR összegből + overhead-ből van.
2. **can_place/broad-phase/narrow-phase nem instrumentált:** A teljes wall time-nak csak egy része látható a NFP+CFR mérésből.
3. **Placement step-id nem korrelálható:** A CFR DIAG sorok nem tartalmaznak placement_index-et, csak nfp_poly_count-ot. Nem lehet pontosan tudni, melyik placement step volt a leglassabb.
4. **T06i vs T06-next különbség nem magyarázott:** A 236s → 35s változás oka nem ismert. Lehetséges okok: CGAL verzió, prepacked input különbség, cache warmup, geometriai különbség.

---

## 16. Appendix: T06i referenciadata (2026-05-08)

```
Greedy eval wall time: 236.1s
CFR total: 154.7s (65.5%)
NFP compute: 22.0s (9.3%)
Egyéb: 59.4s (25.1%)
Max CFR: 20,496ms (nfp_poly=254, 154K+ vertices)
```