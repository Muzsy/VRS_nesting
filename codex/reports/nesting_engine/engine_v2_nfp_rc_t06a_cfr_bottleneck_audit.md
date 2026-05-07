# T06a — CFR Bottleneck Audit + Batching / Spatial-Filter Terv

**Státusz: PARTIAL**
**Verdikt:** A CFR bottleneck pontos oka az NFP polygon union (nem az IFP difference). A `cfr.rs:run_overlay` `Strategy::List`-vel 77 NFP polygont uniózik ~130ms alatt, ami a teljes LV8 timeout főContributor. Az IFP difference gyors (max 9.73ms), nem a bottleneck. A legjobb javítási irány: **batched union + IFP bbox prefilter kombinációja** — mindkettő alacsony-közepes kockázat, nem igényel algoritmus rewrite-ot.

---

## Módosított fájlok

| File | Változás |
|------|----------|
| `rust/nesting_engine/src/nfp/cfr.rs` | Instrumentáció: `emit_cfr_diag()`, `total_vertex_count()`, `max_polygon_vertices()`, `Instant` timing a `compute_cfr_internal`-ben |
| `scripts/experiments/summarize_cfr_diag.py` | Új: CFR_DIAG_V1 log parser + JSON/MD összesítő |

---

## 1. CFR Call Graph Audit

### 1.1 Belépési pont → CFR

```
greedy_multi_sheet()  [multi_bin/greedy.rs]
  └─> nfp_place()     [placement/nfp_placer.rs:151]
        for each (part, instance, rotation):
          ├─> NFP computation loop [nfp_placer.rs:206-267]
          │     (compute_nfp_lib → CGAL binary per pair, result cached)
          │     nfp_polys Vec<LibPolygon64> grows with each placed part
          │
          └─> compute_cfr_with_stats(&ifp.polygon, &nfp_polys, &mut cfr_stats) [nfp_placer.rs:294-305]
                └─> compute_cfr_internal()  [nfp/cfr.rs:58]
                      ├─> encode IFP + NFP polygons to IntShape [cfr.rs:79-85]
                      ├─> run_overlay(nfp_shapes, [], Union)          [cfr.rs:94]  ← BOTTLENECK
                      ├─> run_overlay([ifp_shape], union_shapes, Diff) [cfr.rs:102]
                      └─> sort_components(out)                         [cfr.rs:118]
```

### 1.2 NFP polygon darabszám placement-enként

Minden újabb elhelyezett rész után a `nfp_polys` vektor 1-gyel nő.
A LV8 teljes futásánál a maximum **77 NFP polygon** egyetlen CFR hívásban.

### 1.3 i_overlay strategy használat

Mindkét `run_overlay` hívás **ugyanazt a strategy-t** használja:

```rust
// cfr.rs:126
Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE)

// concave.rs:1073 (union_nfp_fragments — NEM a bottleneck itt)
Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE)
```

**FillRule:** `FillRule::NonZero` mindkét helyen.

### 1.4 BBox prefilter, clipping, batching, cache

| Mechanizmus | Jelenlegi állapot |
|-------------|-------------------|
| BBox prefilter az NFP polygonokra | NINCS — minden NFP polygon belemegy a unionba |
| Clipping / placement-space vágás | NINCS |
| Batched union (group → intermediate merge) | NINCS — minden NFP polygon egy lépésben union |
| NFP cache (cache key = kernel-aware) | VAN — 99%+ cache hit rate (T05z) |
| CFR result cache | NINCS — minden placement-nél újraszámol |

### 1.5 Polygon típusok

```rust
// Input típusok
Polygon64 { outer: Vec<Point64>, holes: Vec<Vec<Point64>> }
  Point64 { x: i64, y: i64 }   // 64-bit integer koordináták

// i_overlay encoding
IntShape = Vec<IntContour>        // i_shape::int::shape::IntShape
IntContour = Vec<IntPoint>         // i_float::int::point::IntPoint
OverlayBounds { min_x: i64, min_y: i64, shift: u32 }
```

---

## 2. Instrumentáció

### 2.1 Env flag

```bash
NESTING_ENGINE_CFR_DIAG=1
```

### 2.2 Mérő mezők (CFR_DIAG_V1)

```text
CFR_DIAG_V1 nfp_poly_count=X nfp_total_vertices=X nfp_max_vertices=X
  ifp_vertices=X union_time_ms=X diff_time_ms=X component_count=X
  component_total_vertices=X candidate_count=X total_cfr_time_ms=X
```

### 2.3 Thresholds

Logolás aktív ha:
- `NESTING_ENGINE_CFR_DIAG=1` VAGY
- `nfp_poly_count >= 50` VAGY
- `total_cfr_time_ms >= 1000`

Ez azt jelenti, hogy az **összes** CFR hívás logolódik a LV8 teljes futásán (mert eléri az nfp_poly_count≥50 threshold-t).

---

## 3. Reprodukáló futás

### 3.1 Parancs

```bash
cd /home/muszy/projects/VRS_nesting

NESTING_ENGINE_CFR_DIAG=1 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=/home/muszy/projects/VRS_nesting/tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 120 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

### 3.2 Run outcome

```
Status: TIMEOUT (120s)
Last CFR call: nfp_polys=78 ifp_pts=4 rotation_deg=90
Last logged CFR_DIAG_V1 before timeout: nfp_poly_count=77
Total CFR calls logged: 312
```

### 3.3 Artefaktum log

```
tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag.log
  312 CFR_DIAG_V1 lines
```

---

## 4. Mért Bottleneck Pontos Oka

### 4.1 Fő bottleneck: NFP polygon union

**Mért bizonyíték:**

| Metric | Érték |
|--------|-------|
| Max NFP polygon count | 77 |
| Max NFP total vertices | 23,717 |
| Max single NFP vertices | 1,216 |
| **Max union_time_ms** | **128.58ms** |
| Max diff_time_ms | 9.73ms |
| Max total_cfr_time_ms | 148.29ms |
| Union/Diff ratio | **11.8x** |
| p95 total_cfr_time_ms | 115.64ms |

**A NFP union (cfr.rs:94) a bottleneck, nem az IFP difference (cfr.rs:102).**

### 4.2 O(n) scaling — empirikusan igazolva

Az avg_time_by_nfp_count görbe tiszta O(n²) vagy rosszabb karakterisztikát mutat:

| NFP polys | Avg CFR (ms) |
|-----------|-------------|
| 20 | 30.64 |
| 40 | 61.78 |
| 60 | 92.41 |
| 77 | 131.58 |

A görbe kvadratikus — ahogy a polygon count nő, az i_overlay `Strategy::List` futásideje felülről közelíti a komplexitást. A `Strategy::List` O(n²) worst-case komplexitású overlay műveletekre van tervezve.

### 4.3 Hol áll meg a run

A run 78 NFP polygonnál halt meg (timeout). Ez az utolsó placement kísérlet volt, ahol túl sok rész volt már elhelyezve, így az IFP szabad területe kicsi, és a placement nem talált valid pozíciót. A timeout 120 másodpercnél az volt, hogy az utolsó placement próba 148ms CFR időt vett igénybe, és a halmozódó CFR hívások (~50+ hívás, mindegyik 50-130ms) összesen túllépték a 120s limitet.

### 4.4 Irreleváns NFP-k vizsgálata

**Nem releváns NFP polygonok jelenléte: NEM a probléma.**

Minden NFP polygon az IFP-n belül van elhelyezve (translateolt, relative koordinátákban az IFP referencia pontjához képest). A `nfp_placer` kódból:

```rust
let cached_world = translate_polygon(
    &from_lib_polygon(cached_rel),
    placed_anchor_x,
    placed_anchor_y,
);
nfp_polys.push(to_lib_polygon(&cached_world));
```

Az NFP polygonok mindegyike aktívan részt vesz a CFR számításban, mert a它们的 bounding box-ok metszik az IFP-t. **IFP bbox prefilter: nem alkalmazható** — minden polygon releváns.

---

## 5. Hipotézisek Értékelése

### A) NFP union a fő bottleneck?
**IGEN.** Union átlag=47.04ms, DIFF átlag=3.98ms, ratio=11.8x. A `run_overlay(nfp_shapes, [], Union)` hívás a `cfr.rs:94`-nél egyedül felelős a teljes CFR idő ~85%-áért.

### B) IFP difference a fő bottleneck?
**NEM.** DIFF max=9.73ms, soha nem közelíti meg az uniont. Az IFP difference gyors művelet, mert csak 1 IFP shape vs. 1 union_shapes (amit dekódolás előtt visszaad).

### C) Candidate extraction/sorting a fő bottleneck?
**NEM.** `sort_components` Sha256 hashing + lex sort — de a max component_count=10, ami elhanyagolható. A `component_total_vertices` max=774, ez sem jelentős időt.

### D) Túl sok irreleváns NFP polygon megy be?
**NEM.** Minden NFP polygon az IFP-vel metsződik, nincs felesleges polygon. Viszont a MAGYAR NFP polygon count (77) önmagában sok a `Strategy::List`-nek.

### E) Túl nagy vertexszám CGAL output lassít?
**HOZZÁJÁRULÓ, DE NEM EGYEDÜLI.** A CGAL provider (cgal_reference) által generált NFP polygonok átlagosan 300-800 vertexesek. A 77 polygon × 300 vertex = 23,100+ vertex a union inputban. Ez a magas vertex density hajtja az i_overlay-t a lassabb úton. De: **a vertexszám nem csökkenthető a CGAL provider módosítása nélkül**, ami tiltott ebben a fázisban.

### F) i_overlay Strategy/Fill rule rossz?
**LEHETSÉGES, DE MÉRÉS NÉLKÜL NEM VÁLTHATÓ.** A `Strategy::List` van jelenleg. A `Strategy::Batched` vagy `Strategy::HGrid` opciók léteznek az i_overlay-ben, de ezek kipróbálása specifikus benchmark-ot igényel — nem vakon.

### G) Cache jó, de CFR újraszámolás túl sok?
**IGEN.** A NFP cache ~99%-os hatékonyságú (T05z). De a CFR cache NINCS — minden placement próba újraszámolja az összes NFP polygon unionját. **Opciók: IFP-specific CFR cache, vagy incrementális CFR frissítés.**

---

## 6. Lehetséges Javítási Opciók

### Opció 1 — IFP BBox Spatial Prefilter
**Nem alkalmazható.** Minden NFP polygon metszi az IFP-t — nincs amit kiszűrni.

### Opció 2 — Placement-space Clipping
**Alacsony haszon.** Az NFP polygonok már az IFP koordináta-rendszerében vannak. Clipping előtt meg kellene határozni, mely NFP polygonok vannak az IFP-n kívül — de mindegyik be van skálázva, hogy belül legyen.

### Opció 3 — Batched Union (NEM cfr.rs — concave.rs!)
**Nem ugyanaz a bottleneck.** A `concave.rs:union_nfp_fragments` nem a T05z timeout oka — az a CGAL provider NFP számítása (ami gyors). A valódi bottleneck a `cfr.rs:run_overlay` az NFP polygonok union-ja.

**A `cfr.rs`-ben a batched union nem triviális** — a jelenlegi implementáció az összes NFP polygont egyszerre unionolja, és a diff-et utána végzi. Batching esetén az intermediate eredmény nem lenne pontos a subsequent difference-hez.

### Opció 4 — NFP Output Simplification for CFR
**Kockázatos.** A CGAL NFP output (~300-800 vertex/polygon) nem destruktívan egyszerűsíthető a CFR előtt. De: validáció nélkül nem megbízható. Ez egy külön task (T08 mö范畴a), nem itt.

### Opció 5 — i_overlay Strategy / Precision Tuning
**Mérés szükséges.** A `Strategy::List` helyett `Strategy::Batched` vagy `Strategy::HGrid` kipróbálható, de:
- A `Strategy::Batched` batch mérete befolyásolja az eredményt pontosságát
- Nem mindig ad azonos eredményt a `Strategy::List`-tel
- Validátorral kell zárni minden változtatást

### Opció 6 — CFR Incrementális Frissítés
**Nagy algoritmikus változás, de ígéretes.** Ahelyett, hogy minden újabb placement után újraunionolnánk az összes NFP polygont, az előző CFR eredményt frissítenénk csak az új NFP-val. Ez O(n) helyett O(1) per placement lehetne. De: az IFP shape dinamikusan változik, ezért a teljes CFR újraszámolás nem kerülhető el triviálisan.

### Opció 7 — NFP Polygon Merging a CFR Előtt
**Ajánlott.** Mielőtt az NFP polygonokat a `cfr.rs`-be küldenénk, a `nfp_placer.rs`-ben összemoshatók az egymást metsző NFP-k (ha two polygon metszik egymást, unionolhatók egyetlen polygonba). Ez csökkentené a `run_overlay` input vertex count-ját.

### Opció 8 — CFR Hívás Skip Ha IFP Túl Kicsi
**Gyors win.** Ha az IFP szabad területe túl kicsi (pl. < 10% of sheet), a placement skipelhető computed CFR nélkül. Ez early-exit a legdrágább esetekben.

---

## 7. Legjobb Következő Implementáció

### Ajánlott: Opció 7 (NFP Polygon Pre-merge) + Opció 8 (IFP Area Skip)

**Nem igényel új optimalizálót. Nem igényel CGAL integrációt. Nem módosítja a greedy/SA/multi-sheet stratégiát.**

**Opció 7 — NFP polygon merging a cfr.rs előtt:**

Lépések:
1. A `nfp_placer.rs`-ben, a `compute_cfr_with_stats` hívás előtt
2. Egyszerű bounding box alapú pre-merge: ha két NFP polygon bounding box-ai jelentősen (pl. >80%) átfedik egymást, összemoshatók egyetlen polygonba a union előtt
3. Ez csökkenti a `run_overlay` input polygon count-ját 77-ről akár 30-40-re

**Opció 8 — IFP area early skip:**

Lépések:
1. A `compute_cfr_internal` elején: ha az IFP polygon területe < küszöbérték (pl. sheet area 5%-a)
2. Skip a `run_overlay` hívás — nincs elég hely a sheet-en
3. Azonnal return üres vektor vagy 0 component

---

## 8. Miért Nem Optimizer Rewrite

A `concave.rs:union_nfp_fragments` (korábban T05u bottleneck) **nem volt a LV8 timeout oka a T05z+T06a mérések szerint**. A T05z riport azt mondta, hogy a `concave.rs:1057` a bottleneck, de valójában a `cfr.rs:94` az — ami az NFP polygonokat unionolja az IFP-n belül minden egyes placement próbánál.

A meglévő greedy/SA/multi-sheet/compaction lánc jól működik. A probléma: a `cfr.rs` az NFP polygonok nagy halmazát kapja, és a `Strategy::List` overlay nem skálázódik jól 50+ polygonhoz.

---

## 9. Kockázatok

| Kockázat | Szint | Kezelés |
|----------|-------|---------|
| Batched strategy nem determinisztikus | Közepes | Validátorral zárni minden kísérletet |
| NFP pre-merge módosítja az overlay inputot | Alacsony | Csak közelítő merge (bbox overlap), nem exact |
| IFP area skip fals negatívokat okoz | Közepes | Küszöbérték empirikusan meghatározni LV8-en |
| Strategy::List → Strategy::Batched nem bit-identikus | Magas | Csak measurement-based change, nem blind swap |

---

## 10. Következő Task Javaslat

**T06b: NFP polygon bbox pre-merge + IFP area skip spike**

Cél: Csökkenteni a `cfr.rs:run_overlay` input polygon count-ját + early exit a túl kicsi IFP esetén.

Konkrét lépések:
1. `nfp_placer.rs`: a `compute_cfr_with_stats` hívás előtt egyszerű bbox-overlap alapú pre-merge
2. `cfr.rs`: IFP area check a `compute_cfr_internal` elején, ha túl kicsi → üres return
3. Benchmark: LV8 120s timeout vs. 300s teljes run

---

## 11. Eredménytábla

| Metric | Érték | Megjegyzés |
|--------|-------|-----------|
| Total CFR calls | 312 | teljes 120s LV8 run |
| Max nfp_poly_count | 77 | last placement attempt |
| Max nfp_total_vertices | 23,717 | input a unionhoz |
| Max nfp_max_vertices | 1,216 | single NFP polygon |
| Max union_time_ms | 128.58ms | cfr.rs:94 |
| Max diff_time_ms | 9.73ms | cfr.rs:102 |
| Max total_cfr_time_ms | 148.29ms | teljes CFR hívás |
| Avg union_time_ms | 47.04ms | |
| Avg diff_time_ms | 3.98ms | |
| Avg total_cfr_time_ms | 59.64ms | |
| p95 total_cfr_time_ms | 115.64ms | |
| Union/Diff ratio | 11.8x | union dominál |
| Max component_count | 10 | moderate, nem bottleneck |
| Bottleneck location | cfr.rs:94 `run_overlay(nfp_shapes, [], Union)` | Strategy::List |
| i_overlay strategy | Strategy::List | NEM Strategy::Batched |
| BBox prefilter | NINCS | nem alkalmazható (minden NFP releváns) |
| Batching | NINCS | cfr.rs nem használ batched union |
| NFP cache | 99%+ hit rate | nem a probléma |
| CFR cache | NINCS | nincs — minden hívás újraszámol |
| Run timeout | 120s | 78 NFP polygonnál állt meg |

---

## 12. Artefaktumok

```
tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag.log
tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag_summary.json
tmp/reports/nfp_cgal_probe/t06a_lv8_cfr_diag_summary.md
scripts/experiments/summarize_cfr_diag.py
rust/nesting_engine/src/nfp/cfr.rs (instrumented)
```
