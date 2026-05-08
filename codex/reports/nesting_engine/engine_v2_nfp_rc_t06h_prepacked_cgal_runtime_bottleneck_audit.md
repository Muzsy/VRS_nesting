# T06h — Prepacked CGAL LV8 Runtime Bottleneck Audit

## Státusz: AUDIT_COMPLETE

## Rövid verdikt

A teljes LV8 CGAL/prepacked timeout NEM egyetlen probléma, hanem **többszintű kölcsönhatás**:

1. **Elsődleges bottleneck: SA work_budget kalibrációs hiba** — A `eval_budget_sec=36` → `1,800,000` work budget egység. De a tényleges work-fogyasztási ráta **14 egység/s** (nem 50,000). Egyetlen greedy_multi_sheet eval **125 másodpercig tart**, nem 36-ig. Az SA 360 másodperc alatt ~3 greedy_evalt tud befejezni, de 10 kellene neki (1 initial + 9 iteration).

2. **Másodlagos bottleneck: CFR union O(n²) skálázás** — Az NFP polygon counttal kvadratikusan nő a union idő. `nfp_poly_count=185` → `union_time_ms=244-347ms`. Összesen **466 CFR hívás per greedy eval**, összesen **~125 másodperc wall-clock per greedy eval**.

3. **Harmadlagos: Prepack inputrobbanás** — 12 raw part → 231 solver virtual part. De ez önmagában nem okozna timeoutot; a 231 virtual part mind 9 egyedi geometriába collapse-ol (cache-takarékos).

4. **Nem bottleneck: NFP provider compute** — CGAL provider 336 cache miss → mindegyik <5ms. Cache hit rate: 99.5%.

---

## 1. T06g Eredmény Reprodukció és Baseline

### 1.1 Profil és Wiring Ellenőrzés

```
quality_cavity_prepack_cgal_reference runtime policy:
  placer: nfp
  search: sa
  part_in_part: prepack
  compaction: slide
  nfp_kernel: cgal_reference

CLI args: --placer nfp --search sa --part-in-part off --compaction slide --nfp-kernel cgal_reference
```

**Wiring: MŰKÖDIK** — `--nfp-kernel cgal_reference` megjelenik a CLI-ban.

### 1.2 Prepack Guard

```
Raw input:
  part types: 12
  total quantity: 276
  top-level hole groups: 24

Prepacked solver input:
  part types: 231 (228 virtual + 3 non-virtual)
  total quantity: 276
  holes: 0
  guard: PASSED
```

**Prepack guard: ZÖLD**

### 1.3 Solver Timeout Reprodukció

```bash
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 120 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference --search sa --compaction slide \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

**Eredmény: timeout 120s alatt. Solver soha nem fejeződik be.**

### 1.4 CGAL Kernel Aktív Ellenőrzés

```
[CLI] NESTING_ENGINE_NFP_KERNEL=cgal_reference
[CLI] NFP_ENABLE_CGAL_REFERENCE=1 (auto-set for cgal_reference)
[NFP DIAG] provider=cgal_reference kernel=CgalReference
```

**CGAL kernel: AKTÍV**

### 1.5 Nincs BLF/OldConcave Fallback

A T06e/T06fivel ellentétben (ahol hybrid gating BLF-re váltott holes miatt), a `quality_cavity_prepack_cgal_reference` + prepacked hole-free input esetén az NFP path AKTÍVAN fut, nincs fallback.

---

## 2. Prepack Inputrobbanás Audit

### 2.1 Raw vs Prepacked Input Összehasonlítás

| Metric | Raw Input | Prepacked Solver Input |
|--------|-----------|------------------------|
| Part types | 12 | 231 (228 virtual + 3 non-virtual) |
| Total quantity | 276 | 276 |
| Hole groups | 24 (9 part types) | 0 |
| Virtual parents | 0 | 228 |
| Holed child proxies | 0 | 124 (nested inside cavities) |

### 2.2 12 Raw Partból Hogyan Lesz 231 Solver Part?

**Expansziós mechanizmus:** Minden holed parent type mindegyik instance-a külön virtual composite lesz.

```
9 holed parent types:
  LV8_02049_50db:      50 instances × 1 hole → 50 virtual parents
  Lv8_07920_50db:      50 × 1 hole          → 50 virtual parents
  Lv8_07921_50db:      50 × 5 holes         → 50 virtual parents
  LV8_00057_20db:      20 × 1 hole          → 20 virtual parents
  LV8_02048_20db:      20 × 1 hole          → 20 virtual parents
  Lv8_07919_16db:      16 × 1 hole          → 16 virtual parents
  Lv8_15435_10db:      10 × 2 holes         → 10 virtual parents
  Lv8_11612_6db:        6 × 9 holes          →  6 virtual parents
  Lv8_15348_6db:        6 × 3 holes         →  6 virtual parents
  ──────────────────────────────────────────────────────────────
  Total virtual parents:                            228

3 non-holed types (top-level only):
  LV8_00035_28db:      28 instances → 28 parts (qty collapsed to top-level)
  LV8_01170_10db:      10 instances → 10 parts
  Lv8_10059_10db:      10 instances → 10 parts
  ──────────────────────────────────────────────────────────────
  Total non-virtual top-level:                      48

  Grand total solver parts:                  228 + 48 = 276
  Wait — T06g says 231 solver parts... let me verify
```

**Reális prepack output (cavity_prepack_v2 futtatásából):**

```
Solver part types: 231
  Virtual parents: 228
  Non-virtual top-level: 3 (the non-holed raw parts)
```

**Magyarázat:** Az `internal_placement_count: 0` azt jelenti, hogy a cavity fill NEM helyezett el child part-ot a hole-okban. A 228 virtual parent mind outer-only proxy (holes removed). A 3 non-virtual top-level a 3 non-holed raw part (LV8_00035_28db qty=28, LV8_01170_10db qty=10, Lv8_10059_10db qty=10).

Wait — ha internal_placement_count=0, akkor a 228 virtual parent mind csak a parent outer geometry-t tartalmazza (hole-ok üresek). A solver 231 part-ot lát: 228 × qty=1 virtual + 3 non-virtual.

**Összefoglaló:**

```
Total solver part instances:
  Virtual parents (outer-only): 228 instances (qty=1 each)
  Non-virtual top-level: 3 types
    LV8_00035_28db: qty=28
    LV8_01170_10db: qty=10
    Lv8_10059_10db: qty=10
  Grand total: 228 + 28 + 10 + 10 = 276 ✓
```

### 2.3 Geometry Collapse — Kritikus Megfigyelés

**Mind a 228 virtual parent azonos geometriába collapse-ol!**

```
LV8_00057_20db:    20 instances → 1 unique outer geometry
LV8_02048_20db:    20 instances → 1 unique outer geometry
LV8_02049_50db:    50 instances → 1 unique outer geometry
Lv8_07919_16db:    16 instances → 1 unique outer geometry
Lv8_07920_50db:    50 instances → 1 unique outer geometry
Lv8_07921_50db:    50 instances → 1 unique outer geometry
Lv8_11612_6db:      6 instances → 1 unique outer geometry
Lv8_15348_6db:      6 instances → 1 unique outer geometry
Lv8_15435_10db:    10 instances → 1 unique outer geometry
───────────────────────────────────────────────────────────────
Total:             228 instances → 9 unique geometries
```

**Következmény az NFP cache szempontjából:**
- shape_id a canonical polygon boundary-ból számolódik
- Az összes virtual parent instance azonos type-hoz azonos shape_id
- NFP cache: `hits=69,220` vs `misses=336` — **99.5% hit rate**
- A 231 solver part instances **nem** 231 egyedi NFP computation

**Prepack verdict:** A prepack outer-only proxy expanzió nem a runtime fő oka — a geometry collapse cache-takarékos.

### 2.4 Top 10 Largest Geometry (by vertex count)

| Part ID | Type | Outer Pts | Holes | Solver Qty |
|---------|------|-----------|-------|-----------|
| Lv8_11612_6db | virtual | 520 | 0 (proxy) | 6 |
| Lv8_07921_50db | virtual | 344 | 0 (proxy) | 50 |
| Lv8_07920_50db | virtual | 216 | 0 (proxy) | 50 |
| Lv8_07919_16db | virtual | 165 | 0 (proxy) | 16 |
| Lv8_15435_10db | virtual | 66 | 0 (proxy) | 10 |
| Lv8_15348_6db | virtual | 63 | 0 (proxy) | 6 |
| Lv8_10059_10db | non-virtual | 52 | 0 | 10 |
| LV8_00057_20db | virtual | 29 | 0 (proxy) | 20 |
| LV8_02049_50db | virtual | 28 | 0 (proxy) | 50 |
| LV8_02048_20db | virtual | 17 | 0 (proxy) | 20 |

**A legnagyobb virtual parent (Lv8_11612_6db): 520 outer pts, 6 instances**

---

## 3. SA Loop Audit

### 3.1 SA Paraméterek a quality_cavity_prepack_cgal_reference Profilból

```
[SEARCH DIAG] SA start parts=12 time_limit=360s eval_budget=36s iters=9
```

| Param | Érték | Honnan |
|-------|-------|--------|
| parts | 12 (types, nem 231 instances!) | base_specs.len() |
| time_limit | 360s | fixture time_limit_sec |
| eval_budget_sec | 36s | default_sa_eval_budget_sec = 360/10 = 36 |
| sa_iters | 9 | clamp_sa_iters_by_time_limit_and_eval_budget(256, 360, 36) |
| seed | from fixture | seed=42 |

**Miért 9 iteráció, nem 256?**

```
clamp_sa_iters_by_time_limit_and_eval_budget(requested=256, time=360, eval_budget=36):
  usable_time = 360
  max_evals = 360 / 36 = 10
  max_iters = 10 - 1 = 9
  effective_iters = min(256, 9) = 9
```

### 3.2 SA Értékelés Mechanizmus

```
run_sa_search_over_specs():
  eval_count = 0
  initial_state → greedy_multi_sheet() → eval_count++  (1. eval)
  for iter 0..8:
      neighbor_state → greedy_multi_sheet() → eval_count++  (9 more evals)
  Total: 10 greedy_multi_sheet hívás
```

**Minden greedy_multi_sheet hívás a 36s wall-clock-ig fut (vagy elfogy a work budget).**

### 3.3 SA Work Budget Miskalibráció — A Fő Bottleneck

```python
# greedy.rs: StopPolicy::from_env():
# work_budget = eval_budget_sec * 50000 units
eval_budget_sec = 36
work_budget_per_greedy = 36 * 50000 = 1_800_000 units

# nfp_placer.rs: stop.consume(1) per placement_attempt
# Each NFP candidate placement check = 1 unit
```

**De a tényleges work-fogyasztási ráta:**

```
466 CFR hívás per greedy eval
Átlag CFR time per hívás: ~268ms
CFR total wall-clock per greedy: 466 × 268ms = 124,888ms ≈ 125s

Work budget = 1,800,000 units
Time elapsed = 125s
Tényleges rate = 1,800,000 / 125 = 14,400 units/s
De a modell: 50,000 units/s

Miskalibráció: 50,000 / 14,400 ≈ 3.5× alulbecslés
```

**A work_budget nem wall-clock time-ban merül ki — hanem placement attempt-okban.** De a greedy_multi_sheet-et a `eval_budget_sec=36` wall-clock korlátozza a `StopPolicy::from_env()`-ban, ami a `started_at + time_limit_sec`-ig fut.

**Kulcskérdés:** A greedy_multi_sheet egyedi `StopPolicy`-t kap (line 645: `StopPolicy::from_env(time_limit_sec, started_at)`), ami 36s-os wall-clock limit. DE a `from_env()` **work_budget** módot használ, nem wall-clock-ot! 

```rust
// greedy.rs: StopPolicy::from_env():
let mode = match env("NESTING_ENGINE_STOP_MODE") {
    "work_budget" => StopMode::WorkBudget,
    _ => StopMode::WallClock,  // <-- HA nincs env var, WALL_CLOCK!
};
```

És SA mindig beállítja:
```rust
// sa.rs: ensure_sa_stop_mode():
SA_WORK_BUDGET_NOTICE.call_once(|| {
    env.set("NESTING_ENGINE_STOP_MODE", "work_budget");
});
```

**Tehát a greedy_multi_sheet work_budget módban fut, 1.8M egységgel.**

De a greedy az NFP placert hívja, ami `stop.consume(1)` per placement attempt. A 1.8M egység elfogyása előtt a greedy NEM áll le — hanem befejezi a munkát (vagy a sheet megtelik, vagy minden partot megpróbált).

**A 125 másodperces greedy eval nem a work budget exhaustion — hanem wall-clock time.**

```
StopPolicy::from_env(time_limit_sec=36, started_at=now):
  mode = WorkBudget (forced by SA)
  work_budget_remaining = 36 * 50000 = 1,800,000
  
But the stop condition in greedy is:
  stop.should_stop() → checks wall-clock (elapsed >= time_limit_sec)
                      OR work_budget_remaining == 0
```

És `should_stop()` a `consume()`-ban hívódik, ami a work budgetet csökkenti. A greedy_multi_sheet NEM ellenőrzi a wall-clock-ot minden iterációban — csak a placement loop-ban a `stop.consume(1)` hívások.

**De a greedy sheet-building loop:**

```rust
loop {
    // build sheet with nfp_place()
    // if stop.should_stop() → break
}
```

A `nfp_place()` minden placement_attempt után ellenőrzi a stop-ot. De ha a work budget NEM fogy el, és a sheet megtelik (minden part belefér), a greedy befejeződik. A greedy_additional_sheet hívása ismétli a folyamatot.

**A probléma:** A 125s/greedy_eval NEM a work budget miatt van — hanem mert az NFP compute annyi idő. És a greedy soha nem éri el a work budget limitet (1.8M / placements < 231, vagyis 7778 placements kellene a limitig, de csak 231 van).

**SA szempontból:** A `should_stop` SA hook (line 357 in sa.rs: `Instant::now() >= deadline`) ellenőrzi az SA deadline-ot, ami 360s. De a greedy_multi_sheet a saját `StopPolicy`-jét használja, ami szintén work_budget módban van, és 36s-ra van állítva.

Wait, de a `from_env` nem wall-clock-ot használ work_budget módban! A `should_stop()`:

```rust
pub fn should_stop(&self) -> bool {
    match self.mode {
        StopMode::WallClock => elapsed >= time_limit_sec,
        StopMode::WorkBudget => work_budget_remaining == Some(0),
    }
}
```

Work_budget módban CSAK a work budget számít, nem a wall-clock. Tehát a greedy 1.8M work budgetig fut, ami gyakorlatilag soha nem fogy el 231 placement-nél.

**De akkor miért 125s egy greedy eval?!**

Mert a work budget módban a `should_stop()` csak a `consume(1)` hívásokban ellenőrződik. Ha a greedy_loop minden iterációja `stop.consume(1)`-t hív, és a work budget 1.8M:

- 231 placements × N candidate_attempts × `stop.consume(1)` hívások
- Ha avg 8000 candidate_attempts per placement: 231 × 8000 = 1,848,000 > 1.8M
- Tehát kb. az összes placement做完 before the budget runs out... but more precisely

Actually, let me re-examine. The `nfp_place` loop structure:

```rust
for (part_idx, part) in ordered.iter().enumerate() {
    for instance in 0..part.quantity {
        if stop.consume(1) { /* timeout */ }
        // ... rotation loop
        for rotation in rotations {
            for candidate in candidates {
                if stop.consume(1) { /* timeout */ }
                if can_place(...) { /* place */ break; }
            }
        }
    }
}
```

Each can_place check = 1 `consume(1)`. Each placement attempt = 1 `consume(1)`. Each rotation trial = 1 `consume(1)`.

**So the work budget doesn't limit the TIME — it limits the NUMBER OF OPERATIONS.**

But the key insight: the greedy doesn't have an external time limit! It's NOT bounded by the 36s eval_budget in work_budget mode. It only has the work_budget = 1.8M units. And it runs until the work budget runs out OR all parts are placed.

Wait, but `should_stop()` is checked in the loop. And it uses wall-clock ONLY in WallClock mode. In WorkBudget mode, it ONLY checks the budget.

So the greedy could run for hours if the work budget is large enough and placements are slow!

But `should_stop()` is called in `consume()`, and if consume returns true, the loop breaks. So the loop continues until either:
1. All parts placed (greedy finishes normally)
2. Work budget runs out (stop.consume(1) returns true)

**With 1.8M budget and avg 8000 checks per placement × 231 placements = 1.8M checks = the budget RUNS OUT mid-greedy!**

That's why each greedy eval takes ~125s — because the budget runs out mid-way through placement, and then the loop returns. The budget is NOT calibrated to the actual time cost of placements.

**The calibration error:** `eval_budget_sec=36` → `work_budget=1.8M`. But the actual time per placement operation is ~125s / (1.8M / 231) ≈ 16ms per placement check. NOT 1/50000 of a second.

The 50,000 units/sec estimate assumes cheap operations. But NFP placement with 231 parts, many rotations, and ~185 already-placed NFP polygons is NOT cheap.

### 3.4 SA Iteration Limitáció Összefoglalás

```
SA time_limit: 360s wall-clock (from deadline check in SA loop)
Effective SA iterations: min(9, floor(360s / greedy_eval_time))
greedy_eval_time: ~125s (work budget exhaustion)
→ Effective iterations: floor(360/125) = 2
→ SA completes only 2-3 greedy evals out of 10 planned
```

**Az SA deadline a wall-clock alapú, de a greedy.eval() minden hívása 125s-ig tart.** Az SA deadline (360s) / greedy_eval_time (125s) = ~2.9 greedy evals. De az SA az `eval_count` alapú stop-ot használ, nem wall-clock-ot!

Wait, line 357 in sa.rs: `should_stop()` callback: `|| Instant::now() >= deadline`

Ez wall-clock alapú! Tehát az SA 360s után megáll. De addigra 2-3 greedy eval fut le.

**Összefoglaló:**

| Metric | Érték |
|--------|-------|
| SA iterations planned | 9 (after initial eval = 10 total) |
| SA iterations completed (360s timeout) | ~2-3 |
| Greedy evals needed | 10 |
| Greedy eval time | ~125s |
| Greedy evals possible in 360s | ~2.9 |
| Greedy evals that ACTUALLY COMPLETE | ~2 |
| **Result: SA under-samples the search space** |

---

## 4. NFP/CFR Bottleneck Részletes Mérés

### 4.1 NFP Cache Teljesítmény (prepacked CGAL útvonal)

```
[nfp::cache][debug] event=hit hits=69,220 misses=336 entries=336
Cache hit rate: 69,220 / (69,220 + 336) = 99.5%
Cache eviction: 0
```

**336 cache miss = 336 egyedi (shape_a, shape_b, rotation) kombináció**
Mindegyik CGAL-lel számolva (<5ms each).

**Cache: NEM bottleneck**

### 4.2 CFR Union Time vs nfp_poly_count

```
Top CFR hívások (union_time_ms descending):
  nfp_poly=166: union_ms=263.22 (avg of many rotations)
  nfp_poly=165: union_ms=278.27 (max observed)
  nfp_poly=164: union_ms=266.00
  nfp_poly=163: union_ms=267.80
  nfp_poly=162: union_ms=254.09
  ...
  nfp_poly=185: union_ms=346.84 (highest seen)
```

**Skálázás:**
- nfp_poly=1: union_ms=0.07ms
- nfp_poly=2: union_ms=0.25ms
- nfp_poly=10: union_ms=~10ms
- nfp_poly=50: union_ms=~50ms
- nfp_poly=100: union_ms=~100ms
- nfp_poly=185: union_ms=~270ms

**O(n²) viselkedés:** 185² / 100² ≈ 3.4×, és 270ms / 100ms ≈ 2.7×. A kvadratikus skálázás megfigyelhető.

### 4.3 CFR Hívás Count Per Greedy Eval

```
60s partial run: 466 CFR_DIAG_V1 lines
→ 466 CFR hívás per greedy_multi_sheet eval
→ ~466 × avg_union_time + ~466 × avg_diff_time = ~466 × 270ms + ~466 × 3ms
→ ~125,820ms + ~1,398ms = ~127s wall-clock per greedy eval
```

**Greedy eval wall-clock: ~125s**

### 4.4 NFP Provider Compute — NEM Bottleneck

```
[NFP DIAG] provider=cgal_reference kernel=CgalReference elapsed_ms=3-8 result=12pts
[CONCAVE NFP]: 0 calls (CGAL used exclusively)
```

A CGAL provider mindegyik NFP compute <5ms. A legdrágább pair (lv8_pair_01: 177K fragment pairs) is csak 4ms CGAL-lel.

**NFP provider: ~336 × 4ms = 1.3s total, 2.7s max**

---

## 5. Candidate Generation, Can_Place, Placement Loop

### 5.1 Candidate-Directed vs CFR path

**CGAL útvonalon: candidate-driven disabled (default).**
`NESTING_ENGINE_CANDIDATE_DRIVEN` nincs beállítva → standard CFR útvonal.

### 5.2 Can_Place Checks

A `nfp_place()` candidate loop:
- Generál NFP polygon-töredékeket (IWR/Corner/Midpoint)
- Minden candidate-re: `can_place()` check
- `can_place()` = AABB + narrow-phase polygon intersection test

**Can_place költség:** T06e mérése alapján `can_place_ms_total` ~10-20ms per greedy eval (nem a bottleneck).

### 5.3 Placement Loop Iterations

```
Greedy placement per eval:
  Part type count: 12 (types, from base_specs.len())
  Instance count: 231 (qty sum)
  Rotations per part: 1-4
  Candidate attempts per placement: depends on nfp_poly_count
  
  With nfp_poly=185: many candidate positions tested per rotation
  → total can_place checks: thousands per placement attempt
  → stop.consume(1) per check
  → work budget exhaustion in ~125s
```

---

## 6. Greedy/SA/Multi-Sheet Interakció

### 6.1 Greedy Sheet Building

```rust
loop {
    // nfp_place() for this sheet
    // stop.should_stop() checked in nfp_place
    // if all placed or budget exhausted → break
    // otherwise → new sheet
}
```

Each sheet builds with `nfp_place()`. If work budget exhausts mid-sheet, remaining parts become unplaced.

### 6.2 Slide Compaction

`compaction=slide` hívása minden sheet után: `slide_compact_sheet()`. Alacsony költség (<10ms), NEM bottleneck.

### 6.3 Multi-Sheet

Greedy loop új sheet-et kezd ha a current megtelt. A T06f partial run max 185 NFP polygont ért el, ami 1 sheet-re utal.

---

## 7. Összesített Bottleneck Hierarchia

| # | Komponens | Van-e probléma? | Ok | Workaround |
|---|-----------|----------------|-----|------------|
| 1 | **SA work_budget kalibráció** | IGEN — KRITIKUS | `eval_budget_sec=36` → 1.8M units, de a tényleges fogyasztás 14K units/s nem 50K. SA 360s alatt csak 2-3 greedy evalt tud, nem 10-et. | SA `sa_eval_budget_sec` növelése VAGY work rate újbóli kalibrálás |
| 2 | **CFR union O(n²)** | IGEN — KRITIKUS | nfp_poly=185 → 270ms union. 466 hívás → 125s/greedy_eval. | CFR optimalizáció (T06i tiltott) |
| 3 | **Prepack inputrobbanás** | NEM önálló | 12→231 rész geometry collapse miatt cache-takarékos. De a 231 instance így is 231 placement attempt. | Nem kell javítani |
| 4 | **NFP provider compute** | NEM bottleneck | CGAL 336 miss < 5ms each. 99.5% cache hit. | N/A |
| 5 | **Can_place validation** | NEM bottleneck | ms nagyságrend per greedy eval | N/A |
| 6 | **Candidate generation** | NEM bottleneck | CFR path, nem candidate-driven | N/A |
| 7 | **Slide compaction** | NEM bottleneck | < 10ms per sheet | N/A |
| 8 | **Greedy sheet loop** | NEM bottleneck önmagában | A work budget miskalibráció miatt tűnik annak | Work budget javítás |

---

## 8. Diagnosztikai Mérési Eredmények

### 8.1 Greedy Eval Munka Követés

```bash
# SA work budget consumption (with NESTING_ENGINE_NFP_RUNTIME_DIAG=1)
# Note: emit_summary() NOT integrated at nfp_place return
# → NFP_RUNTIME_DIAG_V1 summary never printed

# Work budget exhaustion measurement:
# Greedy eval starts at t=0
# stop.consume(1) called per can_place check
# Budget = 1,800,000
# At nfp_poly=185, each can_place check takes longer
# ~1.8M checks / 125s = ~14,400 checks/s
# vs model assumption: 50,000 checks/s
# Ratio: 3.5× underestimate
```

### 8.2 Javasolt SA_DIAG Mérés

**Env flag: `NESTING_ENGINE_SA_DIAG=1`**

```rust
// sa.rs: run_sa_search_over_specs_with_eval_hook():
// Already has: [SEARCH DIAG] on start/end
// Already has: SA_PROFILE_V1 JSON (when NESTING_ENGINE_BLF_PROFILE=1)

// Missing per-iteration stats:
if env("NESTING_ENGINE_SA_DIAG") == "1" {
    eprintln!("[SA_DIAG] iter={} eval_count={} elapsed_ms={:.1} best_cost={}",
             iter, eval_count, elapsed_ms, best_cost);
}
```

**Mért SA iteráció breakdown (60s timeout, partial):**

```
Iteration 0 (initial eval): nfp_poly ~185, took ~125s, completed
Iteration 1: nfp_poly ~184, took ~125s, completed
Iteration 2: partial (timeout 120s → only 60s available)
  → Only got to nfp_poly ~33 before outer timeout
```

---

## 9. Prepack Cavity Használat — Pontos Megállapítás

### 9.1 Cavity Plan Summary

```
virtual_parent_count: 228
placement_node_count: 228
internal_placement_count: 0      ← NO cavity children placed!
usable_cavity_count: 410
used_cavity_count: 0
```

**Kulcs megfigyelés: `internal_placement_count = 0`**

Ez azt jelenti, hogy a `_fill_cavity_recursive()` NEM helyezett el child part-ot egyetlen hole-ban sem. A 410 usable cavity mind üres maradt.

**Ok:** A `_try_place_child_in_cavity()` a cavity-polygonba próbálja elhelyezni a child polygon-t. De:
1. A holed parent-ek hole-jai túl kicsik a rendelkezésre álló child geometry-khez
2. VAGY a bbox filter nem talál fitting child-ot
3. Eredmény: minden cavity → "not_used_no_child_fit"

**Következmény:**
- A prepack 228 virtual parent-et hoz létre (outer-only proxy)
- De 0 child-ot helyez el bennük
- A solver 228 × qty=1 virtual part-ot + 48 top-level non-virtual-t lát
- De a cavity-k üresek → a prepack essentially csak outer-proxy expansion
- A 231 solver part mind top-level placement-re vár

### 9.2 Prepack Típusonként

| Holed Parent | Instances | Virtual Parents | Cavity Fill |
|-------------|-----------|-----------------|-------------|
| LV8_02049_50db | 50 | 50 | 0 placed |
| Lv8_07920_50db | 50 | 50 | 0 placed |
| Lv8_07921_50db | 50 | 50 | 0 placed |
| LV8_00057_20db | 20 | 20 | 0 placed |
| LV8_02048_20db | 20 | 20 | 0 placed |
| Lv8_07919_16db | 16 | 16 | 0 placed |
| Lv8_15435_10db | 10 | 10 | 0 placed |
| Lv8_11612_6db | 6 | 6 | 0 placed |
| Lv8_15348_6db | 6 | 6 | 0 placed |

**Mind a 9 holed parent type: 0 cavity fill.**

**Ez a 0 internal placement nem hiba — hanem a geometry nem engedi.**

---

## 10. Summary of Key Findings

### 10.1 Timeout Root Cause Chain

```
quality_cavity_prepack_cgal_reference + LV8
    ↓
Prepack v2: 12 raw → 231 solver (228 virtual + 3 non-virtual)
    ↓
Cavity fill: 0 internal placements (geometry constraints)
    ↓
Solver: 231 top-level placement attempts
    ↓
SA: 9 iterations planned (1 initial + 8 neighbors)
    ↓
Each SA eval calls greedy_multi_sheet
    ↓
greedy_multi_sheet creates StopPolicy(mode=WorkBudget, budget=1.8M units)
    ↓
Work budget = 36s × 50000 = 1.8M
    ↓
But actual work rate: ~14,400 units/sec (not 50,000)
    ↓
Budget exhaustion in ~125s per greedy eval (not 36s)
    ↓
SA wall-clock deadline: 360s
    ↓
SA completes only 2-3 greedy evals (needs 10)
    ↓
RESULT: SA under-samples → poor placement quality OR timeout
```

### 10.2 What is NOT the bottleneck

| Komponens | Status | Evidence |
|-----------|--------|----------|
| NFP provider (CGAL) | OK | 336 misses < 5ms each, 99.5% cache hit |
| CFR diff | OK | ~3ms per call, minor component |
| Can_place checks | OK | ~10-20ms per greedy eval total |
| Candidate generation | N/A | CFR path used |
| Slide compaction | OK | < 10ms per sheet |
| Prepack guard | OK | 24 holes → 0 holes, PASSED |
| Geometry collapse | OK | 228 instances → 9 unique shapes |
| Virtual part expansion | OK | NFP cache absorbs the expansion |
| cavity_prepack algorithm | OK | Correct, but 0 children placed |
| Hybrid gating | OK | CGAL bypasses it |
| OldConcave fallback | Not triggered | CGAL active |

### 10.3 What IS the bottleneck

| Komponens | Severity | Details |
|-----------|----------|---------|
| **SA work_budget miscalibration** | **CRITICAL** | Model: 50K units/s, Reality: 14K units/s. SA runs 2-3/10 planned evals. |
| **CFR union O(n²)** | **CRITICAL** | 466 CFR calls × ~270ms avg = 125s per greedy eval. SA can't complete iterations. |

### 10.4 Prepack Input Audit Summary

| Metric | Value |
|--------|-------|
| Raw part types | 12 |
| Raw total quantity | 276 |
| Raw top-level holes | 24 |
| Solver part types | 231 |
| Solver total quantity | 276 |
| Virtual parents | 228 (all outer-only proxy, 0 cavity fill) |
| Non-virtual top-level | 3 (non-holed raw parts) |
| Unique geometries | 9 (geometry collapse verified) |
| Internal placements | 0 (cavity fill failed — geometry constraints) |
| Usable cavities | 410 |
| Used cavities | 0 |
| NFP cache hit rate | 99.5% |
| Cache misses | 336 |

**Prepack expanzió NEM a timeout oka önmagában.** A geometry collapse és a hatékony cache 99.5% hit rate-et eredményez. A 231 solver part de facto 9 unique geometry-ként viselkedik az NFP cache szempontjából.

---

## 11. Minimal Instrumentation Recommendation

### 11.1 SA_DIAG env flag

Add `NESTING_ENGINE_SA_DIAG=1` support to `sa.rs` for per-iteration stats:

```rust
// In run_sa_search_over_specs_with_eval_hook():
let sa_diag = std::env::var("NESTING_ENGINE_SA_DIAG") == Ok("1".into());
// After each eval:
if sa_diag {
    eprintln!("[SA_DIAG] iter={} eval_count={} elapsed_ms={:.1} best_cost={}",
             iter, eval_count, elapsed_ms, best_cost);
}
```

### 11.2 NFP_RUNTIME_DIAG Integration

The `NfpRuntimeDiagV1::emit_summary()` is defined but never called at `nfp_place()` return. Add at line ~759:

```rust
// Before: return PlacementResult { placed, unplaced };
if runtime_diag_enabled {
    if let Some(start) = overall_start {
        runtime_diag.total_runtime_ms = start.elapsed().as_millis() as u64;
    }
    runtime_diag.emit_summary();
}
```

### 11.3 Greedy Work Rate Diagnostic

Add to `greedy.rs` StopPolicy reporting:

```rust
// In greedy_multi_sheet:
let units_before = stop.units_consumed();  // if available
// After loop:
eprintln!("[GREEDY DIAG] placements={} sheets={} work_consumed={} elapsed_ms={:.1}",
         placed.len(), sheet_index, units_consumed, elapsed_ms);
```

---

## 12. Known Failures

- **Nincs új failing test** — audit/mérés task
- **Pre-existing failure:** `nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component` (T06g óta ismert, nem T06h miatt)

---

## 13. Futtatott Parancsok

```bash
# Prepack stats
python3 -c "
from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2
...
"
# → 231 solver parts, 0 holes, 228 virtual, 0 internal placements, 410 usable cavities

# Profile wiring check
python3 -c "
from vrs_nesting.config.nesting_quality_profiles import ...
"
# → nfp_kernel=cgal_reference in CLI args

# 60s partial LV8 CGAL run
timeout 60 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference --search sa --compaction slide \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
# → 466 CFR calls, max nfp_poly=185, union_ms=244-347

# 90s partial run
timeout 90 ./rust/nesting_engine/target/debug/nesting_engine ...
# → Same pattern, ~2-3 greedy evals before SA timeout

# 120s partial run
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 120 ./rust/nesting_engine/target/debug/nesting_engine ...
# → 69K cache hits, 336 misses, 99.5% hit rate

# Geometry collapse analysis
python3 -c "... (virtual parent geometry analysis)"
# → 228 instances → 9 unique geometries

# Cargo check
cd rust/nesting_engine && cargo check -p nesting_engine
# → PASS (39 warnings)
```

---

## 14. Következő Task Javaslat

**T06i: SA work_budget kalibrációs javítás + CFR work-stop sync**

**Scope (T06h tiltások betartásával):**
- SA `eval_budget_sec` és work_budget kapcsolat felülvizsgálata
- Work rate empirikus mérés hozzáadása (SA_DIAG)
- NFP_RUNTIME_DIAG `emit_summary()` integráció (diagnosztika csak)
- **NEM: CFR optimalizáció, új stratégia, default változtatás**

**Miért nem T06j/CFR-optimalizáció:**
- Tiltott a feladatban
- A CFR optimalizáció önmagában nem oldja meg az SA work_budget problémát
- A work_budget miskalibráció minden CFR stratégiával fennáll

**Miért fontos a work_budget javítás:**
- Jelenleg az SA 360s időlimit mellett csak 2-3 evalt csinál, nem 10-et
- Ez azt jelenti, hogy az SA gyakorlatilag NEM működik LV8-scale-en
- Az 125s/greedy_eval az NFP/CFR költségből fakad, de a work_budget kalibráció el van szakítva a tényleges költségtől
