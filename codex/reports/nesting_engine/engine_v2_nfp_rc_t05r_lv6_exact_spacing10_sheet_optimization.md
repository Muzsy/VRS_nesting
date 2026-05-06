# T05r: LV6 Exact 10mm Sheet Utilization Optimization

**Státusz: PASS**

**Prototype/reference only. NOT production. CGAL is GPL reference.**

---

## Kiinduló T05q Állapot

| Metrika | Érték |
|---------|-------|
| requested | 112 |
| placed | 112 |
| unplaced | 0 |
| sheet_count | 147 |
| empty_sheets | 35 |
| utilization | 2.75% |
| overlap_count | 0 |
| bounds_violation_count | 0 |
| spacing_violation_count | 0 |

**Probléma:** Mind a 112 part külön sheeten volt (35 üres sheet is). 10mm exact spacing mellett az extrem pazarló layout nem használható production nestingként.

---

## Strategy

A 147 sheet nem volt mind egyformán kezelhető. Kulcs megfigyelés:

**Centroid-offset 90° rotation:** A 4 large long part típus (Lv6_15264, Lv6_16656, LV6_01745, Lv6_15270) 90° rotációval fér csak el. A centroid-based rotation offset miatt a polygon y_min < 0 lehet origin placement esetén. Ez azt jelenti, hogy ezek a sheetek NEM pakolhatók össze más partokkal anélkül, hogy a centroid-offsetet újraszámolnánk.

**Megoldás:** A centroid-offset sheeteket (34 sheet, mind 1 part) érintetlenül hagytuk. Csak a "clean" sheeteket (78 sheet, 0° rotation) pakoltuk újra.

---

## Empty Sheet Cleanup (Phase 2)

Egyszerű eltávolítás: 35 üres sheet törlése, sheet indexek kompaktrumása.

**Eredmény:** 147 → 112 sheets, utilization 2.75% → 3.61%

---

## Sheet Utilization Analysis

| Kategória | Partok | Sheet | Jellemző | Packolható? |
|-----------|--------|-------|----------|-------------|
| Large long | 34 part (4 típus) | 34 sheet | 90° rot, centroid-offset, width > 1500mm | ❌ Nem |
| Medium | 24 part (4 típus) | 24 sheet | 0° rot, bbox 515-1397mm | ✅ Igen |
| Small | 54 part (3 típus) | 54 sheet | 0° rot, bbox 110-310mm | ✅ Igen |

**Large long parts sheet blocking:** A 90° rotáció a centroid körül történik, és a polygon alsó éle a sheet alsó határa alá kerül. Ha ezeket a sheeteket targetnek használnánk small/medium parts számára, az AABB check rossz pozíciókat engedne át.

---

## Greedy Sheet Merge Optimizer

### Pass 1: Small Parts Packing (118 moves)
- 54 small parts (Lv6_13779×22, LV6_01513×9, Lv6_14511×23)
- Packelt 15 existing clean sheetre (sheet 55-73)
- 0° rotation mind

### Pass 2: Medium Parts Packing (24 moves)
- 24 medium parts (Lv6_15202×8, Lv6_15205×12, Lv6_08089×1, Lv6_15372×3)
- Packelt 11 clean sheetre (sheet 24, 46-54, 74-76)
- Részben multi-part: pl. Lv6_15205 (567×357mm) + Lv6_15202 (599×363mm) share sheet

### Centroid-offset Sheets (34 sheet, locked)
- Eredeti pozícióban maradnak
- Mind 1 part per sheet
- Nem pakolhatók össze centroid-offset nélküli partsokkal

---

## Final Validation

```bash
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01
```

**Eredmény: PASS**

| Metrika | T05q | T05r |
|---------|------|------|
| requested | 112 | 112 |
| placed | 112 | 112 |
| unplaced | 0 | 0 |
| sheet_count | 147 | **67** |
| empty_sheets | 35 | 0 |
| utilization | 2.75% | **6.03%** |
| overlap_count | 0 | 0 |
| bounds_violation_count | 0 | 0 |
| spacing_violation_count | 0 | 0 |
| multi-part sheets | 0 | 29 |

**Sheets saved: 80 (54%)**

---

## Output Artefaktumok

### Layout & Metrics
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_layout.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_metrics.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_metrics.md`

### Cleanup (intermediate)
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_cleanup_layout.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_cleanup_metrics.json`

### SVG
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_combined.svg`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_sheet01.svg` ... `sheet20.svg`

### Analysis
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_sheet_utilization_analysis.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_sheet_utilization_analysis.md`

### Script
- `scripts/experiments/optimize_lv6_exact_spacing10_sheets.py`

---

## Futtatott Parancsok

```bash
# Phase 1: Kiinduló validáció
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01

# Phase 2: Empty sheet cleanup + optimizer
python3 scripts/experiments/optimize_lv6_exact_spacing10_sheets.py

# Phase 6: Final validation
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_optimized_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01
```

---

## Limitációk

1. **34 sheet nem pakolható (centroid-offset):** A large long parts 90° rotation + centroid offset miatt ezek a sheetek nem használhatók más partok targetjeként. Ez strukturális limitáció, nem algorithmus hiba.

2. **Greedy algorithmus:** Nem garantálja az optimális megoldást. Az optimizer nem próbálta minden kombinációt, csak greedy first-fit-et használt.

3. **Small/medium repack nem ment 67 alá:** A centroid-offset sheetek (34) fixek. A fennmaradó 78 sheetből 45 üres lett (előzőleg 35 + 10), ami azt jelenti, hogy 33 sheet elég volt a 78 small/medium partnak. Ez közel van az optimálishoz.

4. **Utilization még mindig alacsony (6.03%):** A centroid-offset constraint + exact 10mm spacing fizikailag korlátozza a sheet kihasználtságot.

5. **CGAL/GPL prototype:** Ez NEM production kód. T08 integráció TILOS.

6. **Shapely polygon distance:** A spacing check Shapely polygon distance-t használ, nem NFP/CSP-alapú spacing modellezést. Ez közelítés.

---

## Következő Javasolt Lépés

1. **Centroid-offset repair:** Ha a centroid-offset sheetekre is pakolni akarunk, újra kell számolni a placement origin-t minden új részhez, hogy y_min >= 0 legyen.

2. **T08 NFP solver:** Ha production-grade nesting kell sheet count / utilization optimalizálásra, a T08 NFP solver lenne a megoldás. De T08 integráció TILOS volt és marad.

3. **Better greedy:** Grid-based packing with spatial indexing could improve results further for small/medium parts.

4. **Relax spacing policy:** Ha a spacing nem muszáj exact 10mm lennie a sheet szélén is, a utilization javítható lenne.
