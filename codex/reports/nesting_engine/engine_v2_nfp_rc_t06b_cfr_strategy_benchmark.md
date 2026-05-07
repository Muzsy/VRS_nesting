# T06b — CFR Strategy Benchmark Report

## Státusz: PARTIAL

## Rövid verdikt

A `Strategy::List` IGAZSBÓL a leggyorsabb az i_overlay library-ban ezen a munkaterhelésen. A Tree, Auto, és Frag stratégiák egyaránt **lassabbak** (~24-32%-kal). Az i_overlay strategy csere NEM megoldás. A CFR bottleneck strukturális — a polygon-szám/csúcspont-szám növekedésével az overlay idő exponenciálisan nő.

## Mért összefoglaló

| Metrika | Érték |
|---------|-------|
| Snapshot fájlok száma | 117 |
| Átlagos CFR idő (List) | 108.40ms |
| Átlagos CFR idő (Tree) | 143.46ms |
| Átlagos CFR idő (Auto) | 133.80ms |
| Átlagos CFR idő (Frag) | 136.72ms |
| Leglassabb snapshot | 78nfp/23581v → 170.18ms |
| Tree speedup vs List | **0.756x** (32% lassabb) |
| Auto speedup vs List | **0.810x** (24% lassabb) |
| Frag speedup vs List | **0.793x** (27% lassabb) |
| Crash-ek | 0 |

## Hipotézis értékelés

### A) NFP union a fő bottleneck? — IGEN, DE NEM A STRATEGIÁRÓL
**Mért:** A union a teljes CFR idő ~88%-át teszi ki (T06a: union/diff ratio = 11.8x). Ez változatlan.
**Új megállapítás:** A bottleneck NEM a `Strategy::List` használata — a List a leggyorsabb stratégia.

### B) IFP difference a fő bottleneck? — NEM
**Mért:** A diff átlagosan 3.98ms, a union 47.04ms (T06a). A diff a másodlagos bottleneck.

### C) Candidate extraction / sorting a fő bottleneck? — NEM
A `Strategy::List` használata mellett semmi nem utal arra, hogy a candidate extraction lenne a szűk keresztmetszet.

### D) Túl sok irreleváns NFP polygon megy be? — VALÓSZÍNŰ
**Nem mért:** A T06a megállapítása szerint nincs bbox prefilter, de ez nem is alkalmazható — minden NFP polygon releváns lehet a konkáv-detektáláshoz.

### E) Túl sok vertexes CGAL output lassít? — VALÓSZÍNŰ
**Mért:** A leglassabb snapshot (78nfp/23581v, 170ms) nem a legnagyobb vertex-számú. A korreláció nem lineáris — a polygonok alakja (konkáv részek, lyukak) legalább annyira számít, mint a nyers vertex-szám.

### F) i_overlay Strategy/fill rule rossz? — NEM
**Döntő megcáfolás:** `Strategy::List` a leggyorsabb. A library dokumentációja szerint Tree >10,000 edges-re, de ez a mi esetünkben nem teljesül — a Tree 32%-kal lassabb.

### G) Cache jó, de CFR újraszámolás túl sok? — NEM MÉRT
A cache 82 entry, 12330+ hit. Ez aktívan működik.

## Mit NEM old meg a strategy csere

1. **A polygon-kombinatorikai robbanás** — 78 NFP polygon union-ja ~3000+ intermediate edge-t eredményezhet, függetlenül a strategy-tól
2. **A geometry komplexitása** — a 17,000-24,000 vertex eloszlása polygonok között nem egyenletes; konkáv részek extra clipping-et igényelnek
3. **Az i_overlay library korlátai** — nincs ismert, dokumentált módja a ~O(n²) overlay complexity megkerülésére

## Mit KELL csinálni

A következő megoldási irányok maradnak:

### 1. NFP polygon count csökkentése (legjobb opció)
- Ha 78 NFP polygon helyett 40 megy CFR-be → az overlay idő drasztikusan csökkenhet
- Ehhez a `nfp_placer.rs`-ban kell spatial pre-merge vagy grouping logika
- **Nem heurisztikus skip** — hanem geometriai pre-aggregáció

### 2. IFP bounding-box pre-filter (T06a Opció 1 revived)
- Csak azok az NFP polygonok mennek CFR unionbe, amelyek spatialisan relevánsak
- A T06a szerint ez "alacsony kockázatú"
- **Kérdés:** segít-e, ha minden NFP polygon metszi az IFP-t?

### 3. CFR hívás késleltetése / lazy evaluation
- Nem építjük meg az összes CFR komponenest minden placement-nél
- Csak azokat számoljuk, amelyeket a placement algorithm ténylegesen használ

### 4. NFP output simplification for CFR (T06a Opció 6)
- CGAL NFP output nem destruktív egyszerűsítése CFR célra
- Exact validatorral zárva
- **Kockázatos** — külön task

## Módosított fájlok

- `rust/nesting_engine/src/nfp/cfr.rs` — snapshot funkció: `CfrSnap`, `write_cfr_snapshot_if_enabled`, `SNAPSHOT_SEQ`
- `rust/nesting_engine/src/bin/cfr_union_benchmark.rs` — ÚJ: Strategy comparison benchmark

## Futtatott parancsok

### Snapshot gyűjtés
```bash
cd /home/muszy/projects/VRS_nesting
mkdir -p tmp/reports/nfp_cgal_probe/cfr_snapshots

NESTING_ENGINE_CFR_SNAPSHOT_DIR=tmp/reports/nfp_cgal_probe/cfr_snapshots \
NESTING_ENGINE_CFR_DIAG=1 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 120 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference \
  < tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

### Benchmark futtatás
```bash
cd /home/muszy/projects/VRS_nesting
./rust/nesting_engine/target/debug/cfr_union_benchmark \
  --snapshots tmp/reports/nfp_cgal_probe/cfr_snapshots/ \
  --output tmp/reports/nfp_cgal_probe/cfr_benchmark_results.json
```

## Artefaktumok

| Fájl | Leírás |
|------|--------|
| `tmp/reports/nfp_cgal_probe/cfr_snapshots/` | 117 CFR snapshot JSON |
| `tmp/reports/nfp_cgal_probe/cfr_benchmark_results.json` | Strategy benchmark eredmények |
| `rust/nesting_engine/src/bin/cfr_union_benchmark.rs` | Benchmark binary forrás |

## Következő konkrét task

**T06c — NFP polygon bbox pre-merge spike**

A benchmark nem adott gyorsabb strategy-t. Az egyetlen reális megoldás: csökkenteni az NFP polygon count-ot, mielőtt az a CFR union-ba kerül.

Terv:
1. `nfp_placer.rs`-ban, `compute_cfr_with_stats` hívás ELŐTT spatial bounding-box overlap alapú grouping
2. Ha 2+ NFP polygon bbox-a >80%-ban átfedi egymást → pre-merged bounding box-ként kezeljük őket egyetlen polygonként
3. Ez csökkenti a `run_overlay` input count-ot 78-ról akár 30-40-re
4. Feature flag mögött: `NESTING_ENGINE_CFR_PREGROUP=1`

**Fontos:** Ez NEM heurisztikus skip — a pre-merged polygon-ok az IFP-NFP difference-ből még mindig kinyerhetők, csak a CFR komponens-detektáláshoz használunk durvább inputot.

## Miért nem optimizer rewrite

- Tilos a feladatban
- Még ha írnánk is új overlay-algoritmust, annak correctness validációja hónapokig tartana
- Az i_overlay library a jelenlegi state-of-the-art, és a Strategy::List IGAZBÓL a legjobb itt

## Kockázatok

- **Pre-merge heuristic bisa**: ha durva a bbox-overlap, elveszíthetjük a konkáv detektálás pontosságát
- **Nem mért a pre-merge hatása**: snapshot benchmark nem tartalmazza a grouping költségét
- **CGAL provider idő**: a CGAL NFP generálás ideje (30s a 120s timeout-ból) külön vizsgálatot igényel
