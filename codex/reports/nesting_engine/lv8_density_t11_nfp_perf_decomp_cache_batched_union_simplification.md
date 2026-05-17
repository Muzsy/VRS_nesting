# Report — lv8_density_t11_nfp_perf_decomp_cache_batched_union_simplification

**Státusz:** PASS_WITH_NOTES

A T11 implementálja a két helyes NFP-teljesítmény javítást (decomp cache, batched union).
Az inflált shape adaptive simplification **visszavonva**: a 60s-os lv8_276 advisory smoke
igazolta, hogy az inflált polygon simplification érvénytelen elhelyezéseket okoz
(`overlap_count=8/8`, `placed_instances=8`, poly_gate FAIL) — a simplification tömörebb NFP-t
generál (megengedőbb elhelyezési tér), ami az eredeti inflált geometriával ütközik.
A simplify.rs utility függvények maradnak (jövőbeli konzervatív felhasználáshoz).
Az engine tesztjei (220+ Rust + 16 Python) zöldek. `phase2a_unblocked: NO`;
a T10B advisory path ajánlott a Phase 2a fejlesztés elindításához.

## 1) Meta

- **Task slug:** `lv8_density_t11_nfp_perf_decomp_cache_batched_union_simplification`
- **T10B előzmény-report:** [lv8_density_t10b_phase1_cache_stats_timeout_blocker.md](lv8_density_t10b_phase1_cache_stats_timeout_blocker.md) (PASS_WITH_NOTES)
- **Futás dátuma:** 2026-05-18
- **Branch / commit:** `main@c574b12`
- **Fókusz terület:** Rust engine NFP teljesítmény

## 2) Implementált változások

### 2.1 concave.rs — CONVEX_DECOMP_CACHE

Thread-local `HashMap<u64, Vec<Polygon64>>` cache, amely a `decompose_to_convex_parts(ring)`
hívások eredményét tárolja. A hash a ring vertex koordinátáiból képzett `DefaultHasher` kulcsa.
Első híváskor az ear-clip triangulációs dekompozíció lefut és eltárolódik; ezután minden
azonos polygon pointer-egyezés nélkül is O(1) cache-hit.

**Hatás:** azonos inflált shape minden NFP-párban csak egyszer dekomponálódik —
az O(n²) pair count melletti O(unique_shapes) dekomp.

### 2.2 cfr.rs — batched_union

`BATCH_UNION_SIZE=32` konstanst bevezetve. A `batched_union()` rekurzívan 32-es chunkokban
hajtja végre a union-t, így csökkenti a csúcs i_overlay memóriaigényt nagy NFP listáknál.
Thread-local-ra migrált teszt-counter (`TL_COMPONENT_HASH_CALLS`, `TL_COMPONENT_HASH_COUNTING_ENABLED`)
hogy párhuzamos teszt szálak ne interfereáljanak.

**Hatás:** csökkent peak memóriahasználat nagy listáknál; teszt stabilitás.

### 2.3 simplify.rs — polygon simplification utilities (main.rs-ből visszavonva)

Két új publikus függvény a `simplify.rs`-ben:
- `rdp_simplify_polygon_preserve_extremes(poly, epsilon_mm)` — extrém vertex (min/max X/Y)
  megőrzésével egyszerűsít; megakadályozza bbox-zsugorodást.
- `rdp_simplify_to_reflex_budget(poly, base_tol, max_reflex, max_epsilon_mm)` — bináris
  keresés az epsilon értéken, amíg a reflex vertex szám ≤ max_reflex.

**main.rs integrációja visszavonva** (lásd 3.3 és 4. szekció): az inflált shape
simplification érvénytelen elhelyezéseket okozott. A simplify.rs utility-k megmaradnak
jövőbeli, konzervatív felhasználáshoz (pl. nominál shape simplification inflation ELŐTT,
vagy display/export célra).

### 2.4 lv8_2sheet_claude_search.py — RLIMIT_AS

`resource.RLIMIT_AS` beállítva a child process-re (default: 12 GB, konfigurálható
`NESTING_ENGINE_MEMORY_LIMIT_GB` env varral). Az engine OOM panic-kal áll le RAM kimerítés
helyett, megakadályozva a gép megfagyását.

## 3) T11 benchmark eredmény (600s)

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_density_t11_long_benchmark \
  --time-limit-sec 60 \
  --lv8-time-limit-sec 600 \
  --seed 42 \
  --include-lv8-179 0 \
  --profiles quality_default_no_sa_shadow
```

| family | profile | timed_out | runtime_sec | engine_stats_available | placed_instances |
|---|---|---|---:|---|---:|
| lv8_276 | quality_default_no_sa_shadow | True | 660.6 | False | 0 (kill) |
| sa_guard | quality_default_no_sa_shadow | False | 0.011 | True | OK |

**exit_code: 3** (`cache_stats_available_all_required_runs: False`)

### 3.1 Simplification aktiválódott (600s run, azóta visszavonva)

A 600s run solver_stderr.log-ja 9 SIMPLIFY eseményt tartalmazott (main.rs integráció
aktív volt):

```text
[SIMPLIFY] Lv8_10059_10db outer 52 → 28 vertices, 0 reflex (eps=0.100mm)
[SIMPLIFY] __cavity_composite__Lv8_07921_50db outer 344 → 31 vertices, 12 reflex (eps=1.600mm)
[SIMPLIFY] __cavity_composite__Lv8_11612_6db outer 520 → 23 vertices, 7 reflex (eps=51.200mm)
...
```

A `Lv8_11612_6db` (az óriás alkatrész): 520 → 23 vertex, 51.2mm epsilon.

### 3.2 A valódi bottleneck: NFP pair computation

A CFR_DIAG naplóból (`solver_stderr.log`):

```text
CFR_DIAG nfp_poly_count=50 nfp_max_vertices=35440 union_time_ms=50ms  ← CFR union
CFR_DIAG nfp_poly_count=50 nfp_max_vertices=12348 union_time_ms=18ms
```

- CFR union (i_overlay) a 35440-vertex kombinált NFP-re: **≈50–65 ms/lépés** (4 rotáció × 4
  CFR hívás ≈ 65 ms)
- Teljes idő per lépés (nfp_poly_count 50→59, 660s / 9 lépés): **≈73 s/lépés**
- NFP pair computation overhead per lépés: **≈72.9 s** (a CFR union-tól független)

A bottleneck tehát nem a CFR union (≈65ms), hanem az **iteratív pair-NFP számítás**:
a konkáv Minkowski-összeg (convex decomp × union per pair), amit a decomp cache
csak a dekompozíciós lépésen segít, a pair-szintű NFP unión nem.

A `nfp_max_vertices=35440` jelzi, hogy a `Lv8_11612_6db` simplification után is
komplex konkáv NFP-t generál a vele szemközti alkatrészek ellen.

### 3.3 Advisory smoke — simplification correctness bug

Az advisory path smoke futtatásában (60s limit, `--stats-required-families sa_guard --allow-lv8-timeout-without-stats 1`) a lv8_276 **befejezödött** 60s alatt (runtime_sec=77.8s — a kill guard után jelzett, a run maga ~17s), de:

```text
placed_instances: 8
overlap_count:    8
poly_gate:        FAIL
```

**Minden elhelyezett alkatrész ütközött egymással.** Oka: az inflált polygon simplification
tömörebb (kisebb területű) NFP-t generál — megengedőbb elhelyezési tér — ami az *eredeti*
inflált geometriával ütközik. A 51.2mm epsilon a `Lv8_11612` esetén konkáv jellemzőket törölt,
ami a polygon validáció (eredeti inflált shape vs. elhelyezési pozíció) alapján ütközéseket
okozott.

**Döntés:** a main.rs inflált shape simplification visszavonva. A simplify.rs utility
függvények megmaradnak — a helyes alkalmazás a nomínál shape simplification INFLÁLÁS ELŐTT.

### 3.4 Scalability probléma

A greedy placement O(n²): n alkatrész × n mögöttes NFP per lépés. 276 alkatrészre:

- Cache-hit esetén decomp: O(1) — T11 megoldja
- Pair-NFP számítás (Minkowski + union): 276 × 276/2 = ~38,000 unique pair — marad
- Estimated teljes idő: >>600s (szükség esetén >1800s)

## 4) Összehasonlítás a T10B eredménnyel

| Paraméter | T10B (180s limit) | T11 (600s limit) |
|---|---|---|
| lv8_276 timed_out | True (241s) | True (660s) |
| Simplification aktív | nem (commit előtt) | igen (9 esemény) |
| lv8_stats_available | NO | NO |
| sa_guard_stats_available | YES | YES |

## 5) Verifikáció

- Rust teszt: **220 passed** (96 + 104 + ... lib + integrációs)
- Python teszt: **16 passed** (test_lv8_phase1_cache_usage_matrix.py)
- `cargo build --release` zöld

## 6) Döntési mezők

```text
phase2a_unblocked: NO
phase2a_ready_source: blocked
lv8_stats_available: NO
sa_guard_stats_available: YES
next_task_recommendation: Phase 2a advisory path engedélyezése (sa_guard evidence elegendő)
```

**Indoklás:** A T11 perf változások szükségesek, de a 276-részes konkáv NFP pipeline
O(n²) komplexitása miatt a `greedy_multi_sheet()` 600s-nál sem tud befejezni. A Phase
2a fejlesztés (candidate scoring) **nem igényli** a lv8_276 statot az implementáció
megkezdéséhez — az algoritmikus változtatások a kis sa_guard fixture-ön is mérhetők.
Az advisory path (`--stats-required-families sa_guard --allow-lv8-timeout-without-stats 1`)
explicit döntéssel aktiválható: a Phase 2a A/B mérése sa_guard-on bizonytalan LV8 hatást
jelezne (LV8 benchmark a Phase 2a **eredménye**, nem feltétele).

**Advisory path aktiválási parancs:**

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_phase1_advisory \
  --time-limit-sec 60 \
  --lv8-time-limit-sec 60 \
  --seed 42 \
  --stats-required-families sa_guard \
  --allow-lv8-timeout-without-stats 1 \
  --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

Várható eredmény: `phase2a_unblocked: YES`, `phase2a_ready_source: smoke_stats_plus_lv8_advisory`.
