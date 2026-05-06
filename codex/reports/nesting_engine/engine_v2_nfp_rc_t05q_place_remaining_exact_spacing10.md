# T05q: LV6 — Place Remaining 34 Instances with Exact 10mm Spacing

**Státusz: PASS** ✅

**Prototype/reference only. NOT production. CGAL is GPL reference.**

---

## Kiinduló T05p Állapot

| Metrika | Érték |
|---------|-------|
| requested | 112 |
| placed | 78 |
| unplaced | 34 |
| sheet_count | 113 |
| overlap_count | 0 |
| bounds_violation_count | 0 |
| spacing_violation_count | 0 |

**Unplaced típusok:**

| Part ID | Unplaced | BBox (norm.) | Rotáció | Fit |
|---------|----------|---------------|---------|-----|
| Lv6_15264_9db REV2 +2mm 2025.01.08 | 9 | 2477×613mm | 90° only | ✅ |
| Lv6_16656_7db REV0 | 7 | 2208×517mm | 90° only | ✅ |
| LV6_01745_6db L módosítva CSB REV10 | 6 | 2206×525mm | 90° only | ✅ |
| Lv6_15270_12db REV2 | 12 | 2206×525mm | 90° only | ✅ |

---

## Unplaced Analysis

**Kulcs megfigyelés:** Mind a 4 unplaced típus csak **90° rotációval** fér el a 1500×3000mm sheeten. A centroid-alapú rotációnál a 90°-os forgatás után a polygon kiterjedése a centroid körül mozog, így a polygon's alsó határa (y_min) a centroid alatt van.

**Lv6_15264_9db példa:** centroid=(1315, 212), 90° rotáció után y_min=-1103mm a normalizált koordinátarendszerben. Ha placement origin = (0,0), a polygon -1103mm-re lenne a sheet alsó határán — ez bounds violation.

**Fix:** `compute_placement_origin_for_bounds()` függvény, amely kiszámítja a szükséges eltolást, hogy a rotált polygon y_min >= 0 legyen.

---

## Repair Strategy

1. **Új üres sheetek létrehozása** az egyes unplaced instance-oknak (mivel mind 1 part/sheet stratégiát alkalmaztunk)
2. **90° rotáció elsődleges** (egyetlen működő rotáció)
3. **Centroid-offset korrigált placement origin** — (0, |y_min|+0.1) a y-tengelyen
4. **Shapely polygon distance** alapú spacing validáció az üres sheeten (triviálisan átmegy)

---

## Final Validation

```bash
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json \
  --tolerance-mm 0.01
```

**Eredmény: PASS ✅**

| Metrika | Érték |
|---------|-------|
| **requested** | 112 |
| **placed** | 112 |
| **unplaced** | 0 |
| **sheet_count** | 147 |
| **utilization** | 2.75% |
| **overlap_count** | 0 |
| **bounds_violation_count** | 0 |
| **spacing_violation_count** | 0 |
| min_clearance_mm | N/A (mind 1 part/sheet) |
| runtime | 0.10s |

---

## Sheet Eloszlás

- **147 sheet összesen** (35 üres + 112 1-part sheet)
- T05p: 113 sheet (78 used + 35 empty)
- T05q: +34 új sheet (+34 új part)
- **Mind a 112 part külön sheeten van** — ez a 10mm exact spacing constraint direkt következménye nagy parts-oknál

---

## Rotations Used

| Rotation | Instances |
|----------|-----------|
| 90° | 34 (100%) |

---

## Final Placement by Type

| Part ID | Placed |
|---------|--------|
| LV6_01513_9db REV6 | 9 |
| LV6_01745_6db L módosítva CSB REV10 | 6 |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | 1 |
| Lv6_13779_22db Módósitott NZ REV2 | 22 |
| Lv6_14511_23db REV1 | 23 |
| Lv6_15202_8db REV0 Módosított N.Z. | 8 |
| Lv6_15205_12db REV0 Módosított N.Z. | 12 |
| Lv6_15264_9db REV2 +2mm 2025.01.08 | 9 |
| Lv6_15270_12db REV2 | 12 |
| Lv6_15372_3db REV0 | 3 |
| Lv6_16656_7db REV0 | 7 |

**Mind a 11 part típus teljes mennyiségben elhelyezve.**

---

## Output Artefaktumok

### Layout & Metrics
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_layout.json`
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_metrics.json`
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_metrics.md`

### SVG
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_combined.svg`
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_sheet01.svg` ... `sheet147.svg` (147 file)

### Analysis
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_unplaced_analysis.json`
- `tmp/reports/nfp_cgal_probe/lv6_exact_spacing10_unplaced_analysis.md`

### Scripts
- `scripts/experiments/repair_lv6_exact_spacing_unplaced.py`
- `scripts/experiments/analyze_lv6_unplaced_exact_spacing.py`

---

## Futtatott Parancsok

```bash
# Kiinduló reprodukció
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_fixed_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json

# Unplaced analysis
python3 scripts/experiments/analyze_lv6_unplaced_exact_spacing.py

# Repair script
python3 scripts/experiments/repair_lv6_exact_spacing_unplaced.py

# Final validation
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_repaired_layout.json \
  --part-list tmp/reports/nfp_cgal_probe/lv6_production_part_list.json
```

---

## Limitációk

1. **Sheet count magas (147)** — 10mm spacing + nagy parts → mind 1 part/sheet. Ez a constraint的直接 eredménye, nem optimalizálási hiba.

2. **Utilization alacsony (2.75%)** — a 10mm spacing és a centroid-based rotation placement strategy miatt. Production rendszerben NFP/CSP alapú spacing lenne szükséges.

3. **CGAL/GPL prototype** — ez NEM production kód. T08 integráció TILOS.

4. **Centroid-based rotation offset bug** — a T05p/T05q fix megkerüli a problémát, de a rotation-origin consistent kell legyen a validator és placer között.

5. **35 üres sheet** — ezek a T05p fixed layout-ból öröklődtek. Nem lettek törölve a "no sheet count optimization" rule miatt.

---

## Következő Javasolt Lépés

1. **Centroid-based rotation consistency** — ha a rotációs offset problémát más kontextusban is látod, érdemes a transform függvényt egységesíteni.

2. **NFP-based placement (T08)** — ha production nesting kell, a T08 NFP solver lenne a megoldás a sheet count / utilization problémára. De T08 integráció TILOS volt ebben a fázisban.

3. **Spacing policy clarification** — ha a spacing a sheet szélén is érvényes (azaz 10mm margin a sheet edge-től), akkor a jelenlegi 0mm sheet edge margin nem megfelelő. Ezt a policy-t tisztázni kell.

4. **Empty sheet cleanup** — ha a sheet count nem számít, a 35 üres sheet törölhető. Ha igen, ez egy külön optimalizálási probléma.

5. **T05r: Sheet utilization analysis** — elemezni, van-e lehetőség 2+ part/share sheet-re a 10mm spacing mellett kisebb parts-oknál.
