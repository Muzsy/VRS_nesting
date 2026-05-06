# T05s: LV6 Large Sheet Reuse Optimization

**Státusz: PASS**

**Prototype/reference only. NOT production. CGAL is GPL reference.**

---

## Kiinduló T05r Állapot

| Metrika | Érték |
|---------|-------|
| requested | 112 |
| placed | 112 |
| unplaced | 0 |
| sheet_count | 67 |
| utilization | 6.03% |
| overlap_count | 0 |
| bounds_violation_count | 0 |
| spacing_violation_count | 0 |

---

## Centroid-Offset Root Cause

A T05r azt állította, hogy a 34 large-part sheet (90° rotált) "nem pakolható össze" más partokkal. Ez részben igaz volt, de nem a teljes igazság.

### Amit a T05r helytelenül kezelt:

A centroid-based 90° rotation: amikor a polygon 90°-ot rotál a centroid körül, a polygon alsó éle (y_min) a centroid alá kerül. Ha ezt a polygont origin=(0,0)-nál helyezzük el, a polygon's alsó éle a sheet alsó határa ALATT van → bounds violation.

A T05q repair (`compute_placement_origin_for_bounds`): kiszámítja a szükséges offsetet, hogy a rotált polygon `y_min = 0` legyen.

**Kulcs észrevétel:** A centroid-offset EGYEDÜL a large-part placement originjét érinti. Ha a large partot fixen tartjuk az origin=(negatív_x, pozitív_y) pozícióban, és a Shapely polygon bounds checket használjuk, a polygon valódi határai a sheeten x=[0..613], y=[0..2477].

### Szabad terület a large-part sheeteken:

| Large Part | Polygon bounds | Free RIGHT (x=613..1500) | Free TOP (y=2477..3000) |
|------------|---------------|--------------------------|--------------------------|
| Lv6_15264 (9×) | [0..613] × [0..2477] | 887mm × 2477mm | 1500mm × 523mm |
| Lv6_16656 (7×) | [0..517] × [0..2208] | 983mm × 2208mm | 1500mm × 792mm |
| LV6_01745 (6×) | [0..525] × [0..2206] | 975mm × 2206mm | 1500mm × 794mm |
| Lv6_15270 (12×) | [0..525] × [0..2206] | 975mm × 2206mm | 1500mm × 794mm |

Tehát van bőséges szabad terület a small/medium parts számára!

---

## Strategy

1. **Large parts FIXED** — nem mozgatjuk őket, origin pozícióban maradnak
2. **Small parts FIRST** (LV6_01513, Lv6_14511) — legkisebb, legkönnyebben elhelyezhető
3. **Medium parts SECOND** (Lv6_13779, Lv6_15205, Lv6_15202, Lv6_08089, Lv6_15372)
4. **Candidate generation:** Smart free-region positioning (RIGHT strip, TOP strip)
5. **Validation after each move:** Shapely polygon distance exact check
6. **Remove emptied clean sheets**

---

## Results

### Phase 1: Large Sheet Reuse
- **78 sikeres move, 0 failed**
- Minden movable part sikeresen átkerült large-part sheetekre
- 33 clean sheet kiürült és eltávolításra került

### Final State

| Metrika | T05q | T05r | T05s |
|---------|------|------|------|
| requested | 112 | 112 | 112 |
| placed | 112 | 112 | 112 |
| sheet_count | 147 | 67 | **34** |
| utilization | 2.75% | 6.03% | **11.89%** |
| overlap | 0 | 0 | 0 |
| bounds violation | 0 | 0 | 0 |
| spacing violation | 0 | 0 | 0 |
| min_clearance | N/A | N/A | **10.0000mm** |

**Sheets saved vs T05q: 113 (77% reduction)**
**Sheets saved vs T05r: 33 (49% reduction)**

---

## Final Validation

```bash
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01
```

**Eredmény: PASS**

| Metrika | Érték |
|---------|-------|
| checked_pairs | 6216 |
| spacing_checks (AABB passed) | 726 |
| min_clearance | 10.0000mm |
| spacing_violations | 0 |
| bounds_violations | 0 |
| overlap_count | 0 |

---

## Moved Parts Summary

| Part ID | Moved to Large Sheets | Sheets used |
|---------|----------------------|-------------|
| LV6_01513_9db REV6 (9×) | ✅ | 1 sheet |
| Lv6_14511_23db REV1 (23×) | ✅ | 1 sheet |
| Lv6_13779_22db Módósitott NZ REV2 (22×) | ✅ | 2 sheets |
| Lv6_15205_12db REV0 Módosított N.Z. (12×) | ✅ | 3 sheets |
| Lv6_15202_8db REV0 Módosított N.Z. (8×) | ✅ | 4 sheets |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! (1×) | ✅ | 1 sheet |
| Lv6_15372_3db REV0 (3×) | ✅ | 2 sheets |

---

## Output Artefaktumok

### Layout & Metrics
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_layout.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_metrics.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_metrics.md`

### SVG
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_combined.svg`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_sheet01.svg` ... `sheet20.svg`

### Analysis
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_sheet_reuse_analysis.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_sheet_reuse_analysis.md`

### Scripts
- `scripts/experiments/optimize_lv6_large_sheet_reuse_exact_spacing10.py`
- `scripts/experiments/generate_t05s_svgs.py`

---

## Futtatott Parancsok

```bash
# Kiinduló validáció
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01

# Large sheet reuse optimizer
python3 scripts/experiments/optimize_lv6_large_sheet_reuse_exact_spacing10.py

# Final validation
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_large_reuse_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01
```

---

## Limitációk

1. **34 sheet még mindig fix:** A 34 large-part sheet mind 1 large partot + N small/medium partokat tartalmaz. Ezek a sheetek strukturálisan nem spórolhatók tovább — 1 large part mindig kell legyen rajtuk.

2. **Utilization 11.89%:** Az exact 10mm spacing + centroid-offset constraint fizikailag korlátozza a sheet kihasználtságot.

3. **Greedy algorithmus:** A greedy first-fit stratégia nem garantálja az optamális megoldást.

4. **CGAL/GPL prototype:** NEM production kód. T08 integráció TILOS.

5. **min_clearance exactly 10mm:** A validator 726 AABB-overlap check után pontosan 10.0000mm clearance-t mér. Ez jelzi, hogy a spacing constraint élesen teljesül.

---

## Következő Javasolt Lépés

1. **T08 NFP solver:** Production-grade nesting (ha engedélyezett) tovább csökkentené a sheet countot NFP-based packinggal.

2. **Better packing algorithm:** 2D bin packing heuristic (Guillotine, Maximal Rectangles) a free-space management javítására.

3. **Spacing policy:** Ha a spacing nem muszáj exact 10mm lennie a sheet edge-től, utilization javítható lenne.
