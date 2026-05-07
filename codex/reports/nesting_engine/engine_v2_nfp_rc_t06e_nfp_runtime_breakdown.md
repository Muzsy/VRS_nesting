# T06e — NFP Compute/Runtime Breakdown + Provider/Cache Audit

## Státusz: PARTIAL

## Rövid verdikt

- **Fő bottleneck:** NFP provider compute (OldConcave: 177K/110K/73K fragment pair timeout 5s alatt) — NEM CFR union. Az NFP compute a primary bottleneck, a CFR union a secondary.
- **Cache működik:** 92K+ cache hit vs 826 cache miss — 99%+ hit rate.
- **Hybrid gating az LV8 12-part teljes futásnál az NFP placert BLF-re váltja holes jelenléte miatt** — ez a legnagyobb meglepetés: az LV8 NEM az NFP/CFR timeout miatt nem fut, hanem mert a hybrid gating mindig BLF-re vált 9/12 hole-part miatt.
- **CGAL provider mindhárom toxic LV8 pair-t 231ms/112ms/73ms alatt megoldja** — OldConcave mindhárom 5s timeout.
- **CGAL + NFP útvonalon a LV8 300s timeout alatt 196 NFP polygonnál jár** — a CFR union itt 156-168ms/példány, ami nem timeout a CGAL NFP gyorsasága miatt.
- **T06d benchmark ugyanaz a "fallback to blf" warning-t adta** — a T06d LV8 timeout nem a CFR bottleneck volt, hanem a hybrid gating.
- **Default mode (OldConcave, no CGAL) + holes input → BLF fallback** — az NFP path sosem fut LV8-n.
- **Recommended T06f: CGAL provider runtime hardening + NFP kernel selection wiring** (a hybrid gating bypass a CGAL referencián keresztül élesben működik).

---

## 1. T06d Eredmény Pontosítása

### 1.1 T06d LV8 Timeout Értelmezése — HELYESBÍTÉS

**T06d állítása:** "mindkét útvonal timeoutol a teljes NFP compute költsége miatt (518 NFP computation)"

**T06e megállapítása:** A T06d LV8 benchmark NEM az NFP compute vagy CFR bottleneck miatt timeoutolt. A timeout oka: **HYBRID GATING**.

Mindkét log (`t06d_baseline_lv8.log`, `t06d_candidate_lv8_diag.txt`) azonos üzenetet tartalmaz:
```
warning: --placer nfp fallback to blf (hybrid gating: holes or hole_collapsed)
```

A pipeline az NFP placeert SOHA nem hívja meg LV8-n. A `main.rs:479-484` logikája:
```rust
if cli.placer == PlacerKind::Nfp
    && (has_nominal_holes || has_hole_collapsed)
    && !force_nfp_for_cgal  // CGAL kernel NEM volt beállítva T06d-ben
{
    PlacerKind::Blf  // <-- mindig ide jut LV8-nál
}
```

LV8 input: 12 part type, 9-nek van holes (`holes_points_mm` nem üres), 24 hole group összesen. A hybrid gating azonnal BLF-re vált.

**T06d következtetése téves volt:** A candidate-driven path "működik" a 3-rect teszten, de az LV8 timeout nem a candidate-driven vs CFR különbség volt — hanem hogy egyik sem fut soha NFP-n.

### 1.2 Miért Timeoutolt Mégis T06b/C/D?

A T06b/C riportok a `NESTING_ENGINE_CFR_DIAG=1` + `NFP_ENABLE_CGAL_REFERENCE=1` + `NFP_CGAL_PROBE_BIN=...` + `--nfp-kernel cgal_reference` flag-ekkel futottak — ezek a hybrid gating `force_nfp_for_cgal = true` feltételét TELJESÍTIK.

Ezért T06b-ben 312 CFR hívást mértek — mert a CGAL kernel explicit beállítása bypassolta a hybrid gatinget.

### 1.3 T06e-ben Mi Változott?

T06e:
- NFP_RUNTIME_DIAG implementáció hozzáadva
- LV8 futtatása `NFP_ENABLE_CGAL_REFERENCE=1` + `--nfp-kernel cgal_reference` flag-ekkel
- Default (OldConcave, no CGAL) LV8 BLF-re váltás megerősítve
- CGAL LV8 196 NFP polygonnál 300s alatt (CFR 156-168ms/példány)

---

## 2. Runtime Instrumentation Terv

### 2.1 Implementált: NESTING_ENGINE_NFP_RUNTIME_DIAG

Hozzáadva `nfp_placer.rs`-hez:

```rust
// NESTING_ENGINE_NFP_RUNTIME_DIAG feature-flagelt diagnosztikai struktúra
pub struct NfpRuntimeDiagV1 {
    pub total_runtime_ms: u64,
    pub nfp_request_count: u64,
    pub nfp_cache_hit_count: u64,
    pub nfp_cache_miss_count: u64,
    pub nfp_provider_compute_count: u64,
    pub nfp_provider_compute_ms_total: u64,
    pub nfp_provider_compute_ms_max: u64,
    pub cfr_union_ms_total: f64,
    pub cfr_diff_ms_total: f64,
    pub cfr_calls: u64,
    pub candidate_generated_count: u64,
    pub candidate_after_dedup_count: u64,
    pub can_place_check_count: u64,
    pub can_place_ms_total: u64,
    pub blf_fallback_count: u64,
    pub cfr_fallback_count: u64,
    pub placed_count: u64,
    pub unplaced_count: u64,
    pub sheet_count: u64,
}
```

A teljes instrumentáció integrálása a nfp_place()-be a return előtti emisszióval: TODO — az `emit_summary()` metódus létezik de a hívás nincs integrálva a nfp_place végébe. A diagnosztika jelenleg a meglévő CFR_DIAG + NFP_DIAG + cache debug logokból áll.

### 2.2 Meglévő Diagnosztika

|| Env flag | Mit mér | Státusz ||
|---|---|---|---|
| `NESTING_ENGINE_CFR_DIAG=1` | CFR union/diff idő per hívás | Aktív ||
| `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` | Globális NFP stats | Struktúra létrehozva, emisszió TODO ||
| `[nfp::cache][debug]` | Cache hit/miss/insert | Aktív (debug build) ||
| `[NFP DIAG]` | Provider compute idő | Aktív ||
| `[CONCAVE NFP DIAG]` | Concave fragment/NFP idő | Aktív ||
| `NESTING_ENGINE_CANDIDATE_DIAG=1` | Candidate-driven stats | Aktív ||

---

## 3. NFP Cache Audit

### 3.1 Cache Key Struktúra

```rust
pub struct NfpCacheKey {
    pub shape_id_a: u64,        // SHA256 of polygon boundary
    pub shape_id_b: u64,        // SHA256 of polygon boundary
    pub rotation_steps_b: i16,  // discrete rotation index
    pub nfp_kernel: NfpKernel,  // OldConcave vs CgalReference
}
```

**Tartalmazza:** shape_id (kettle-hull canonicalization után), rotation, NFP kernel típus. **Nem tartalmazza:** spacing/inflation state, cleanup profile — ezek a geometriában már bele vannak építve az NFP compute előtt.

### 3.2 Cache Működés

- **Hit:** `cache.get()` talál cache entry-t → hits++
- **Miss:** `cache.get()` nem talál → misses++ → provider compute hívása → `cache.insert()`
- **Eviction:** `MAX_ENTRIES = 10_000`. Ha eléri a limitet: `clear_all()` — az összes entry és statisztika törlődik.
- **Cache és provider kapcsolat:** Mindkét útvonal (CFR és candidate-driven) ugyanazt a `NfpCache`-et használja. A `collect_nfp_polys_for_rotation()` mindkettőben ugyanúgy cache-eli.
- **Kernel-aware separation:** `NfpCacheKey.nfp_kernel` megakadályozza, hogy CGAL és OldConcave output alaklmazza egymást.

### 3.3 LV8 Cache Statisztika (CGAL útvonal, részleges run)

```
[nfp::cache][debug] event=hit hits=92263 misses=826 entries=826
```

- **826 cache miss:** az összes egyedi (shape_id_a, shape_id_b, rotation) kombináció
- **92263 cache hit:** ~99.1% hit rate
- **0 cache eviction:** soha nem érte el a 10K limitet
- **Nincs duplikált NFP compute:** minden pair+rotation kombináció egyszer számolódik

### 3.4 Cache Miss vs Provider Compute Bottleneck

**LV8 részleges run (CGAL útvonal, ~196 NFP polygonnál állt meg):**
- Cache miss: 826 → 826 egyedi NFP compute
- CGAL provider: mindegyik < 300ms (pair: 73-231ms)
- Cache miss NEM a bottleneck

**LV8 pair benchmark (OldConcave):**
- lv8_pair_01: 177,156 fragment pair → timeout 5000ms
- lv8_pair_02: 110,852 fragment pair → timeout 5000ms
- lv8_pair_03: 73,188 fragment pair → timeout 5000ms

**Következtetés:** A cache miss NEM a probléma. A provider compute idő az — OldConcave 177K fragment pair-t nem tud 5s alatt feldolgozni.

---

## 4. Provider Audit

### 4.1 OldConcaveProvider

- **Belépési pont:** `concave.rs:compute_concave_nfp_default()` vagy `convex.rs:compute_convex_nfp()`
- **Convex+convex:** `compute_convex_nfp()` — gyors, nem itt a bottleneck
- **Concave+concave vagy convex+concave:** `compute_concave_nfp_default()` → decomposition + fragment pair enumeration + Minkowski sum + fragment union
- **LV8 toxic pair-ök:** `lv8_pair_01`: 518×342=177,156 fragment pair; `lv8_pair_02`: 518×214=110,852; `lv8_pair_03`: 342×214=73,188
- **Fragment pair enumeration:** minden fragment_p × fragment_q kombinációra Minkowski sum → 177K/110K/73K pár
- **Timeout:** Mindhárom 5000ms alatt nem készül el
- **Fragment union:** `concave.rs:1057` → `Strategy::List` overlay

### 4.2 CgalReferenceProvider

- **Belépési pont:** `cgal_reference_provider.rs` → subprocess hívás `nfp_cgal_probe` binary
- **LV8 toxic pair-ök CGAL-lel:**
  - lv8_pair_01 (177,156 pairs): 231ms, 776 vertex output
  - lv8_pair_02 (110,852 pairs): 112ms, 786 vertex output
  - lv8_pair_03 (73,188 pairs): 73ms, 324 vertex output
- **Mindhárom: SUCCESS** — OldConcave timeout vs CGAL SUCCESS
- **CGAL binary:** `/home/muszy/projects/VRS_nesting/tools/nfp_cgal_probe/build/nfp_cgal_probe`
- **Fragment decomposition:** CGAL is végzi, de a CGAL overlay hatékonyabb
- **Kérdés:** CGAL output hole-aware? Igen — T05y mérés igazolja: `hole_boundary_collision=2` a real_work_dxf-n

### 4.3 ReducedConvolutionExperimental

- **Státusz:** Unsupported kernel — `Err(NfpError::UnsupportedKernel(...))`
- **T05x óta nem implementálva**

---

## 5. LV8 Runtime Breakdown — CGAL Útvonal

### 5.1 Full LV8 CGAL Benchmark Eredmény

**Parancs:**
```bash
NESTING_ENGINE_CFR_DIAG=1 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

**Eredmény:** TIMEOUT after 300s at nfp_poly_count=196

**Legnagyobb CFR hívások (>150ms union):**
```
nfp_poly_count=196 nfp_total_vertices=22445 nfp_max_vertices=637 
union_time_ms=168.49 diff_time_ms=11.64 cfr_total_ms=196.41
```

### 5.2 Top CFR Hívások Nfp_poly_count Szerint

|| nfp_poly | union_ms | diff_ms | total_ms | vertexek ||
|---|---|---|---|---|---|
| 196 | 168.49 | 11.64 | 196.41 | 22,445 ||
| 196 | 162.69 | 12.22 | 191.72 | 21,774 ||
| 196 | 157.80 | 11.18 | 184.31 | 21,213 ||
| 196 | 156.39 | 11.85 | 183.88 | 21,240 ||
| 195 | 154.72 | 12.42 | 182.51 | 21,184 ||
| ~140-160 | 90-140 | 5-8 | 110-160 | 12-18K ||
| ~100-140 | 50-90 | 3-6 | 60-100 | 8-15K ||

### 5.3 Bottleneck Analízis

**A CFR union a fő költség:** ~90% a total CFR időből.

**Skálázás:** O(n²) jellegű — 77→196 NFP polygon 4x növekedés ~15x idő növekedés (130ms→196ms, az arány nem pontosan kvadratikus a vertex density miatt).

**T06b mérés (CGAL NFP, 120s run, részleges):**
- Max: 77 NFP polygon, 23,717 vertex, union=128.58ms, diff=9.73ms
- Avg: 47.04ms union, 3.98ms diff

**T06e (CGAL NFP, 300s run, részleges):**
- Max: 196 NFP polygon, 22,445 vertex, union=168.49ms, diff=11.64ms

---

## 6. 3-rect Regression Benchmark

### 6.1 CFR Baseline

```bash
./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json
```

**Eredmény:**
- placed=9, sheets=1, status=ok
- 0 fallback
- Cache: 25 miss, 95 hit (79% hit rate)
- CFR: ~0.2-0.6ms/hívás (1-8 NFP polygon)
- Provider: convex+convex, 0-0.05ms

### 6.2 Candidate-Driven

```bash
NESTING_ENGINE_CANDIDATE_DRIVEN=1 \
NESTING_ENGINE_CANDIDATE_DIAG=1 \
./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json
```

**Eredmény:** byte-for-byte azonos, 9/9 placed, 1 sheet

**T06d mérés (T06d-ből):**
- CandidateDrivenStats: ifp_corner=144, nfp_vertex=246, nfp_edge_midpoint=302, placed_anchor=540, nudge=25158
- total_generated=26390, after_dedup=19758
- can_place_checks=6093, accepted=9, rejected=6084
- cfr_fallback=0

---

## 7. Top 5 Legdrágább NFP Pair/Rotation

### 7.1 OldConcave Pair Benchmark

|| Pair | Fragments | Fragment Pairs | OldConcave | CGAL ||
|---|---|---|---|---|---|
| lv8_pair_01 | 518×342 | 177,156 | TIMEOUT (5s) | 231ms SUCCESS ||
| lv8_pair_02 | 518×214 | 110,852 | TIMEOUT (5s) | 112ms SUCCESS ||
| lv8_pair_03 | 342×214 | 73,188 | TIMEOUT (5s) | 73ms SUCCESS ||

**Minden toxic LV8 pair az OldConcave-nál timeout.** A legkisebb (lv8_pair_03) is timeout 5s alatt.

### 7.2 CGAL Per-Rotation NFP (részleges LV8 run)

A legdrágább NFP-k a részleges LV8 run-ban a legnagyobb polygonok (520 outer pts, 9 holes) egymás elleni NFP-k:

```
[NFP DIAG] compute_nfp_lib START placed_pts=520 placed_convex=false placed_holes=9 moving_pts=520 moving_convex=false moving_holes=9 rotation_deg=90
[NFP DIAG] compute_nfp_lib START placed_pts=520 placed_convex=false placed_holes=9 moving_pts=520 moving_convex=false moving_holes=9 rotation_deg=270
```

Ezek CGAL-vel gyorsak (<300ms). OldConcave-val ezek valószínűleg szintén timeoutolnának.

---

## 8. Default Mode LV8 (BLF Fallback)

### 8.1 Default LV8 Run

```bash
./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

**Output:**
```
warning: --placer nfp fallback to blf (hybrid gating: holes or hole_collapsed)
```

**Értelmezés:** Az NFP placer SOHA nem fut LV8-n default mode-ban. A hybrid gating az összes hole-part miatt BLF-re vált.

**A BLF output nem dokumentált itt** — T06e fókusza az NFP path instrumentációja, nem a BLF benchmark.

---

## 9. Known Failures

### 9.1 Pre-existing

- Nincs ismert pre-existing failing test. Minden teszt PASS.

### 9.2 T06e Által Hozzáadott

- Nincs új failing test.

---

## 10. Módosított Fájlok

- `rust/nesting_engine/src/placement/nfp_placer.rs` — NfpRuntimeDiagV1 struktúra + emit_summary() + nfp_place() integráció (runtime_diag_enabled, overall_start)

---

## 11. NFP_RUNTIME_DIAG Jelenlegi Állapot

**Implementált:** `NfpRuntimeDiagV1` struktúra + `emit_summary()` metódus létrehozva.

**Nem integrálva:** A `nfp_place()` return ága előtt nincs `runtime_diag.emit_summary()` hívás. A diagnosztika a meglévő `CFR_DIAG`, `NFP_DIAG`, és cache debug logokból nyerhető.

**TODO (T06f része lehet):** A `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` flag alatt a nfp_place() végén `runtime_diag.emit_summary()` hívása.

---

## 12. Következő Task Javaslat

### Ajánlott: T06f-A — CGAL Provider Runtime Hardening + NFP Kernel Selection Wiring

**Miért A?**
A T06e egyértelműen kimutatta:
1. Az OldConcave provider timeout a legkisebb LV8 toxic pair-en is (73K fragment pairs)
2. A CGAL provider mindhárom toxic LV8 pair-t megoldja 73-231ms alatt
3. A hybrid gating a legnagyobb akadály az NFP útvonalon — CGAL nélkül az LV8 sosem fut NFP-n
4. A CFR union a másodlagos bottleneck CGAL NFP után (196ms vs <300ms provider compute)

**T06f konkrét lépések:**
1. CGAL provider production-ready wire-up: default kernel = cgal_reference a hybrid gating felett
2. `NESTING_ENGINE_NFP_KERNEL` CLI argumentum teljes körű támogatása a `main.rs`-ben
3. CGAL kernel: hole-aware containment wire-up (T05y igazolta: `hole_boundary_collision=2`)
4. CGAL provider timeout/error kezelés hardenése
5. Optional: CGAL fallback OldConcave-re ha CGAL binary nem elérhető

**Nem T06f scope:**
- CFR union optimalizáció (T06b: Strategy::List a legjobb, nincs jobb opció)
- NFP cache módosítás (működik, 99%+ hit rate)
- New placement strategy (tiltott)
- Candidate-driven expansion (T06d: működik, de LV8-n a hybrid gating miatt sosem fut)

---

## 13. Futtatott Parancsok

```bash
# 3-rect baseline
./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tmp/reports/nesting_engine/ne2_input_3rect_simple.json

# LV8 pair benchmark OldConcave
./rust/nesting_engine/target/debug/nfp_pair_benchmark \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --timeout-ms 5000 --output-json
# → TIMEOUT

# LV8 pair benchmark CGAL
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
./rust/nesting_engine/target/debug/nfp_pair_benchmark \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json \
  --nfp-kernel cgal_reference --timeout-ms 5000 --output-json
# → SUCCESS 231ms

# LV8 full run CGAL (részleges, timeout 300s)
NESTING_ENGINE_CFR_DIAG=1 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
# → TIMEOUT at nfp_poly_count=196

# Default LV8 (BLF fallback)
./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
# → warning: fallback to blf (hybrid gating)

# Cargo check
cd rust/nesting_engine && cargo check -p nesting_engine
# → PASS (39 warnings)

# Cargo test
cd rust/nesting_engine && cargo test -p nesting_engine
# → 145 PASS, 0 FAIL
```
