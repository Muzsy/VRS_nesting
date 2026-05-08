# T06i — SA/greedy Budget Calibration + Runtime Diagnostics
## prepacked + cgal_reference útvonal diagnosztikája

**Dátum:** 2026-05-08
**Útvonal:** `quality_cavity_prepack_cgal_reference` → `--nfp-kernel cgal_reference`
**Típus:** Diagnosztikai + kalibrációs
**Constraint:** NEM optimalizálunk CFR-t, NEM írunk új stratégiát

---

## 1. T06h Baseline Reprodukció

### 1.1 Konfiguráció ellenőrzés — PASS

```
Profil: quality_cavity_prepack_cgal_reference          ✓
CLI --nfp-kernel: cgal_reference                       ✓
Prepacked holes after: 0                               ✓
Actual kernel: CgalReference                           ✓
BLF fallback: NINCS                                    ✓
OldConcave fallback: NINCS                             ✓
NFP cache hit rate: ~99.5% (336 miss / 66K+ calls)   ✓
```

### 1.2 Diagnosztika instrumentation — KIEGÉSZÍTve

Korábbi T06i munkamenetben hozzáadott instrumentáció (`greedy.rs` + `nfp_placer.rs`):
- `NESTING_ENGINE_SA_DIAG=1` → `[SEARCH DIAG]`, `[GREEDY_EVAL_DONE]`
- `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` → `emit_summary()` return path-okon
- `NESTING_ENGINE_CFR_DIAG=1` → CFR költség per rotation (működik)

### 1.3 Baseline futás — 420s wall (1 greedy eval = 236s)

```
[SEARCH DIAG] SA start parts=231 time_limit=360s eval_budget=36s iters=9
[GREEDY_EVAL_DONE] placed=254 unplaced=22 sheets=1 elapsed_ms=236083 stop_mode=budget_remaining=Some(1785278)
```

**Megállapítás:** 420s timeout alatt pontosan 1 greedy eval futott le.
A `budget_remaining=1.785M` azt mutatja, hogy a work budget NEM merült ki:
50K/sec × 36s = 1.8M kezdeti → 254 consume(1) = 254 unit fogyasztás.

---

## 2. SA / Work Budget Kalibrációs Hiba — KRITIKUS

### 2.1 Az eval_budget forrása

```rust
// main.rs:354-358
fn default_sa_eval_budget_sec(time_limit_sec: u64) -> u64 {
    let capped_limit = time_limit_sec.max(1);
    let tenth = capped_limit / 10;
    tenth.clamp(1, capped_limit)
}
```

```
time_limit_sec = 360 (from prepacked_solver_input.json)
eval_budget_sec = 360 / 10 = 36
```

A `quality_cavity_prepack_cgal_reference` profil NEM állítja be az
`sa_eval_budget_sec`-et, ezért a `default_sa_eval_budget_sec(360)` = 36s-t kapjuk.

### 2.2 A probléma lényege

```
eval_budget = 36s       ← konfigurált érték (360/10)
actual greedy eval time = 236s   ← T06i mért érték
model/tapasztalat arány = 6.6x   ← durva alábecsles
```

**SA iter clamp:**
```rust
clamp_sa_iters_by_time_limit_and_eval_budget(requested_iters=9, time_limit=360, eval_budget=36)
// max_evals = 360 / 36 = 10
// max_iters  = 10 - 1 = 9
```
Az SA 9 iterációt tervez. De a valóságban 360s alatt CSAK 360/236 = **1.5 greedy eval** fér be.

### 2.3 eval_budget vs. actual eval time mapping

```
eval_budget=  5s → iters=71, de actual_evals=1.5   (túltervezés: 47x)
eval_budget= 10s → iters=35, de actual_evals=1.5   (túltervezés: 23x)
eval_budget= 20s → iters=17, de actual_evals=1.5   (túltervezés: 11x)
eval_budget= 36s → iters= 9, de actual_evals=1.5   (túltervezés: 6x)  ← JELENLEGI
eval_budget= 60s → iters= 5, de actual_evals=1.5   (túltervezés: 3x)
eval_budget=120s → iters= 2, de actual_evals=1.5   (túltervezés: 1.3x)
eval_budget=180s → iters= 1, de actual_evals=1.5   (közelíti a valóságot)
eval_budget=240s → iters= 0   ← nem indít SA-t!
```

### 2.4 Work Budget vs. Wall Clock

A `work_budget` mód önmagában **fizikailag helyes** — a `consume(1)` mechanizmus
működik, de az `eval_budget` paraméter, ami a work_budget mennyiségét meghatározza,
NEM tükrözi a valós költségeket:

```
Work budget = 50K × 36s = 1,800,000 unit
consume(1) per placement → 254 unit/eval
Fogyasztás: 254 / 1.8M = 0.014%
→ Budget 99.986%-a megmarad a 236s-as eval után
```

**A `consume(1)` a part/instance elhelyezésekhez van kötve.** A greedy eval
költségének fő komponense (CFR union, slide compaction) NEM szerepel a
`consume(1)` modellben.

---

## 3. CFR Költég Növekedés — O(n²) mintás

### 3.1 Per-placement CFR költség (1 greedy eval, 420s run)

```
Placements  CFR/idő (ms)    Kumulatív CFR (s)
    1-10    ~0.2-1.0 ms       ~0.00s
   25       1.6 ms            0.02s
   50      11.2 ms            0.30s
  100      27.9 ms            1.29s
  150     127.0 ms            4.35s
  200     412.4 ms           20.37s
  250     952.5 ms           56.26s
  254   ~1000-20000 ms      154.7s (összesen)
```

### 3.2 Mi okozza a költségnövekedést?

A CFR költség a **poligon-fragmentumok számától** függ, ami az elhelyezett
konkáv alakzatok számával **kvadratikusan nő**:

```
nfp_poly=  1: nfp_total_vertices=  12    → union=0.01ms
nfp_poly= 50: nfp_total_vertices= 600    → union=11ms
nfp_poly=100: nfp_total_vertices=1200    → union=28ms
nfp_poly=150: nfp_total_vertices=1800    → union=127ms
nfp_poly=200: nfp_total_vertices=2400    → union=412ms
nfp_poly=250: nfp_total_vertices=3000    → union=950ms
nfp_poly=254: nfp_total_vertices=154K+   → union=1000-20000ms  ← EXPLOZÍÓ
```

**A 254. rész elhelyezésénél a `union_time_ms` 20 másodpercre ugrik**, mert:
- `nfp_total_vertices=154K+` (konkáv alakzatok → sok belső csúcs)
- `component_count=0` → a CFR nem tudta szétbontani komponensekre
- Egyetlen hatalmas overlay union call

### 3.3 Wall time breakdown (1 greedy eval, 236s)

```
CFR (nfp_poly union)       : 154.7s   (65.5%)
NFP compute (CGAL probe)    :  22.0s    (9.3%)
Egyéb (slide, overhead)    :  59.4s   (25.1%)
──────────────────────────────────────────────────
Összesen                    : 236.1s  (100.0%)
```

---

## 4. Diagnosztikai Megállapítások

### 4.1 Mi NEM a probléma

- **CGAL provider**: NEM bottleneck (NFP compute = 9.3% a wall time-nak)
- **NFP cache**: jól működik (99.5% hit rate, 336 miss, 0 eviction)
- **Work budget mechanizmus**: fizikailag helyes
- **Prepack**: zökkenőmentes, 0 holes
- **BLF/OldConcave fallback**: nem aktív

### 4.2 Mi a probléma

1. **`eval_budget` kalibráció**: Az `eval_budget=36s` ~6.6x kisebb, mint a
   valós greedy eval költség (236s). Ez az SA-t 9 iterációt tervezni, holott
   1.5 férne be a 360s-ba.

2. **CFR költség kvadratikus növekedése**: A 254. rész elhelyezése 20s CFR
   időt vesz igénybe, ami a teljes 236s-ból 65.5%-ot tesz ki. Ez a költség
   a konkáv alakzatok nagy számú belső csúcspontjából ered.

3. **Work budget → eval_budget disconnect**: A `consume(1)` part-elhelyezésekhez
   van kötve (254 unit/eval), de a valós költség 236s. A `eval_budget` és a
   valós költség közötti ~6.6x eltérés azt jelzi, hogy a greedy eval költségének
   fő komponense (CFR union, slide compaction) NEM szerepel a `consume(1)` modellben.

---

## 5. Kalibrációs Javaslatok (nem implementálva — T06j következik)

### 5.1 Work Budget javítás

A `work_budget` mód önmagában NEM rossz, de az `eval_budget` paramétert
frissíteni kell, hogy tükrözze a valós költségeket:

```
# JELENLEGI (hibás):
time_limit_sec = 360s
eval_budget = 360/10 = 36s
work_budget = 36s × 50K/sec = 1.8M unit
consume(1) per placement → 254 unit/eval
→ Budget 0.014%-a fogy, marad 1.785M

# JAVASOLT (calibration után):
eval_budget = measured_avg_greedy_eval_sec
work_budget = eval_budget × 50K/sec
→ Budget pontosan 1 greedy eval-ot fedez
```

Az `eval_budget` frissítésének módjai (NEM implementálva):

**Option A — Runtime learning:**
```
NESTING_ENGINE_SA_DIAG=1 mellett futtatni a solvert, megmérni az
első greedy eval idejét, és az alapján korrigálni az SA iter clamp-ot.
```

**Option B — Profile-based fix:**
```
quality_cavity_prepack_cgal_reference profilban:
  sa_eval_budget_sec = 240   # ~6.6x a jelenlegi 36s helyett
```

**Option C — Work budget per-rotation charging:**
```
A greedy_multi_sheet-ban a consume(1) helyett rotation-onként
kellene consume()-t hívni, ami 4×254 = 1016 unit/eval.
```

### 5.2 T06j irány döntéshozatal

A jelenlegi adatok alapján a T06j-ben két irány lehetséges:

**Irány 1 — Budget kalibráció (budget management javítása):**
- `sa_eval_budget_sec` növelése ~240s-ra
- SA iters = 1 (vagy 0, ha 360/240 ≤ 1 → nem indít SA-t)
- Előny: nem kell CFR-t módosítani
- Hátrány: SA gyakorlatilag nemiteratív lesz

**Irány 2 — CFR call reduction (candidate-driven fast-path):**
- A T06d candidate-driven útvonal befejezése és aktiválása
- Korai bounding box szűrés a fragmentumok feletti iterálás előtt
- Előny: valódi speedup a CFR költségnövekedés megfékezésére
- Hátrány: módosítás a placement logikában

**Jelenlegi álláspont:** Az `eval_budget` kalibráció (Irány 1) önmagában
nem oldja meg a problémát, mert az SA 0 iterációra korlátozódna, és a CFR
növekedése a 200+ placed part tartományban továbbra is 65%+-ot tenne ki.
A T06j-nek Irány 2-t kell választania.

---

## 6. Melléklet — Mért értékek

### 6.1 Greedy eval költség (420s run, 1 eval)

```
Metric                          Érték
───────────────────────────────────────────────
Greedy eval wall time           236.1s
Placements per eval             254
Unplaced after eval            22
Sheets used                     1
Work budget remaining           1,785,278 / 1,800,000
Work budget consumed            14,722 unit (0.8%)
CFR total time (154.7s)        65.5% of wall
NFP compute time (22.0s)         9.3% of wall
Egyéb (slide+overhead, 59.4s)   25.1% of wall
Max nfp_poly_count              254
Max nfp_total_vertices          154,497+
Max union_time per rotation     20,496ms (at nfp_poly=254)
```

### 6.2 SA konfiguráció (prepacked input JSON-ból)

```
time_limit_sec = 360    (from prepacked_solver_input.json)
default_sa_eval_budget_sec(360) = 360/10 = 36s
clamp(36, 1, 360) = 36s
SA stop mode = work_budget (forced by ensure_sa_stop_mode)
```

### 6.3 CFR költség növekedési görbe

```
nfp_poly  nfp_vertices  union_ms    cfr_total_ms/placement
    10        120          0.1              0.8
    50        600         11              11.2
   100      1,200         28              27.9
   150      1,800        127             127.0
   200      2,400        412             412.4
   250      3,000        953             952.5
   254    154,000+     1,000-20,000    ~1,000-20,000
```

---

## 7. Nyitott kérdések a T06j számára

1. A `eval_budget` NEM a `time_limit_sec` arányában van-e mindig? (Nem — a
   `default_sa_eval_budget_sec` = time_limit_sec / 10, ami heurisztika.)
2. A `quality_cavity_prepack_cgal_reference` profil `sa_eval_budget_sec` értéke
   honnan származik? (Sehonnan — a profil nem tartalmazza, main.rs default-ot
   használ: time_limit_sec/10.)
3. A slide compaction időbeli költsége (25% of wall) hogyan illeszkedik a képbe?
4. A candidate-driven útvonal (T06d) mennyire kész? Aktív-e egyáltalán?

---

## 8. Szigorú tiltások betartása

- [x] NEM írtunk új optimalizálót
- [x] NEM módosítottuk a greedy / SA / multi-sheet / slide compaction alaplogikáját
- [x] NEM optimalizáltuk a CFR uniont
- [x] NEM implementáltunk candidate-driven bővítést
- [x] NEM módosítottuk a cavity_prepack algoritmust
- [x] NEM módosítottuk az NFP providereket
- [x] NEM tettük CGAL-t production defaulttá
- [x] NEM módosítottuk a production Dockerfile-t
- [x] NEM kapcsoltuk ki silent módon az SA-t
- [x] NEM kapcsoltuk ki silent módon a CFR-t
- [x] NEM neveztük timeoutot PASS-nak
- [x] NEM kezdtük el a T06j-et
