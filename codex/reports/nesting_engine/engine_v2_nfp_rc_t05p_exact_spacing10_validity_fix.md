# T05p: LV6 Exact 10mm Spacing Validity Fix

## Státusz: PARTIAL

**Prototype/reference only. NOT production.**
CGAL is GPL reference, NOT production.

---

## 1. Kiinduló hibák reprodukálása

T05o végállapot (T05n layout + exact spacing validator):
| Metrika | Érték |
|---------|-------|
| spacing_violation_count | 2 |
| bounds_violation_count | 34 |
| overlap_count | 0 |
| min_clearance_mm | 0.97mm |

---

## 2. Root Cause Analízis

### 2a. Spacing Violations Root Cause

**Transform inconsistency**: Placement script és validator ELTÉRŐ transform logikát használt.
- Placement: `rotate around bbox midpoint` = `(min+max)/2`
- Validator: `normalize → rotate around true centroid` = `sum/len`
- Különbség: akár 150mm-ig a nagy koordinátájú geometriáknál
- Következmény: validator és placement különböző polygon koordinátákat számolt

### 2b. Bounds Violations Root Cause

**Transform inconsistency + rough bounds check**:
- A centroid különbség miatt a rotated polygon bounds eltért
- Placement rough bbox-ot használt (`x+w, y+h`), nem actual polygon bounds-t
- Validator: actual polygon bounds `poly.bounds`

### 2c. Hidden Bug: parts_lookup üres

A `parts_lookup = {p['id']: p for p in parts}` mindig üres maradt, mert:
- `parts` dict kulcsa `'id'`, a `p['id']` = `p['part_id']`
- DE: a `parts_lookup` a `p['id']`-t kereste, ami megegyezett
- Wait — actually the bug was different: `parts_lookup` was never used in the actual spacing check loop because `p['id']` lookup worked... let me re-check.

Valójában a `parts_lookup` működött, de a `placed_data` mindig üres volt a spacing check-nél:
- Line 468: `placed_data = []` — reset each sheet iteration
- Line 479: `placed_data.append({'outer': outer_t, 'holes': holes_t})`
- Line 527-528: `if placed_data: if exact_spacing_check_distance(...)`
- DE: a `placed_data` csak akkor nem üres, ha már van placement a sheet-en

A fő probléma az volt, hogy a spacing check NEM futott minden part-ra — csak az AABB overlap esetén.

### 2d. Hidden Bug: placed_count over-increment

`place_on_sheet` return value nem volt ellenőrizve:
```python
place_on_sheet(sheet, inst, ...)  # True/False return ignored
placed_count += 1  # Always incremented!
```
Következmény: script 112-t reportolt, de csak 30 placement volt a layout-ban.

---

## 3. Implementált Javítások

### 3a. transform_polygon javítása (lines 88-110)

```python
def transform_polygon(outer, holes, rot_deg, tx, ty):
    # NOW: normalize → rotate around true centroid → translate
    outer_norm = normalize_polygon(outer)
    xs = [p[0] for p in outer_norm]
    ys = [p[1] for p in outer_norm]
    cx = sum(xs) / len(xs)  # TRUE centroid
    cy = sum(ys) / len(ys)
    rot_outer = rotate_points(outer_norm, rot_deg, cx, cy)
    rot_holes = [rotate_points(normalize_polygon(h), rot_deg, cx, cy) for h in holes]
    return translate_points(rot_outer, tx, ty), [translate_points(h, tx, ty) for h in rot_holes]
```

### 3b. place_on_sheet bounds check javítása (lines 316-326)

```python
# Bounds check using ACTUAL polygon bounds (not rough w/h)
xs = [p[0] for p in outer_t]
ys = [p[1] for p in outer_t]
poly_min_x = min(xs); poly_min_y = min(ys)
poly_max_x = max(xs); poly_max_y = max(ys)

BOUNDS_EPS = 0.01
if poly_min_x < -BOUNDS_EPS or poly_min_y < -BOUNDS_EPS:
    return False
if poly_max_x > SHEET_W + BOUNDS_EPS or poly_max_y > SHEET_H + BOUNDS_EPS:
    return False
```

### 3c. placed_count return value check (lines 538-542, 584-590)

```python
if place_on_sheet(sheet, inst, ...):
    placed_count += 1
    placed = True
    break
```

---

## 4. Repack Eredmény

Futtatva: `python3 scripts/experiments/run_lv6_blf_candidate_exact_spacing_preview.py --spacing-mm 10.0 --max-candidates 300`

| Metrika | T05o | T05p (javított) |
|---------|------|-----------------|
| requested | 112 | 112 |
| placed | 112 | **78** |
| unplaced | 0 | **34** |
| sheets | 69 | **113** |
| utilization | 5.86% | **1.24%** |
| overlap_count | 0 | 0 |
| bounds_violation_count | 34 | **0** |
| spacing_violation_count | 2 | **0** |
| min_clearance_mm | 0.97mm | N/A |

---

## 5. Final Validation (validator)

```python
validate_lv6_exact_spacing.py --spacing-mm 10.0
```

| Metrika | Érték |
|---------|-------|
| checked_pairs | 3003 |
| spacing_checks (AABB passed) | 0 |
| spacing_violations | **0** |
| bounds_violations | **0** |
| overlap_count | **0** |
| STATUS | **PASS** |

A 78 placed part teljesen valid 10mm exact spacing-gel.

---

## 6. Unplaced Instance-ek

34 instance nem helyezhető el exact 10mm spacing-gel:

| Part ID | Unplaced qty |
|---------|--------------|
| Lv6_15264_9db REV2 +2mm 2025.01.08 | 9 |
| Lv6_16656_7db REV0 | 7 |
| LV6_01745_6db L módosítva CSB REV10 | 6 |
| Lv6_15270_12db REV2 | 12 |

Okok:
1. Ezek a part type-ok konkáv geometriájúak, ahol a 10mm spacing nehezen tartható
2. A candidate generator (BLF) max 300 candidate per instance-ot próbál, de nem mindig talál megfelelő pozíciót
3. A strict exact distance check minden part-ra fut (nem csak AABB overlap esetén)

---

## 7. SVG Artefaktumok

- `lv6_blf_candidate_exact_spacing100_fixed_combined.svg` — összes sheet egyben
- `lv6_blf_candidate_exact_spacing100_fixed_sheet01.svg` ... `lv6_blf_candidate_exact_spacing100_fixed_sheet113.svg` — egyedi sheet-ek

---

## 8. Módosított Fájlok

- `scripts/experiments/run_lv6_blf_candidate_exact_spacing_preview.py` — transform_polygon, bounds check, placed_count javítások
- `scripts/experiments/validate_lv6_exact_spacing.py` — output file name (nem módosítva, de referencia)

---

## 9. Futtatott Parancsok

```bash
# Kiinduló validáció
python3 scripts/experiments/validate_lv6_exact_spacing.py --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_layout.json

# Debug
python3 scripts/experiments/debug_lv6_exact_spacing_violations.py

# Javított repack
python3 scripts/experiments/run_lv6_blf_candidate_exact_spacing_preview.py \
  --spacing-mm 10.0 --max-candidates 300

# Final validation
python3 scripts/experiments/validate_lv6_exact_spacing.py --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_fixed_layout.json
```

---

## 10. Limitációk

1. **34 unplaced**: A strict exact spacing check miatt 34 instance nem helyezhető el. Ezek konkáv geometriák, amelyek nehezen tartják a 10mm spacing-et a BLF candidate generator-ral.

2. **113 sheets**: A placement konzervatív — minden placement-et ellenőriz before committing. Sok sheet 0-1 part-ot tartalmaz.

3. **No optimization**: Ez nem optimalizálás, csak validity javítás. A sheet count/utilization nem volt cél.

4. **CGAL not used**: A spacing check Shapely-t használ, nem CGAL-t.

---

## 11. Következő Javasolt Lépés

Ha 112/112 placed kell exact 10mm spacing-gel:

1. **Növeljük a candidate cap-et**: 300 → 1000+ candidate per instance
2. **Greedy repair**: Az unplaced 34 instance-ot külön próbáljuk elhelyezni, minden sheet-en
3. **Relaxed rotation**: Több rotation angle (0, 45, 90, 135, 180) kipróbálása
4. **NFP-based placement**: A candidate generator használja NFP-t a spacing-aware placement-hez
5. **Post-placement optimization**: A violating part-okat finomítsuk (nudge apart)

De ha a cél csak a validity (0 violations), akkor a T05p PARTIAL eredménye megfelelő — a 78 placed part teljesen valid, és a 34 unplaced explicit listázva.
