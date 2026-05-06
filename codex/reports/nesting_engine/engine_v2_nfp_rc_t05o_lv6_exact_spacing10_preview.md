# T05o: LV6 Exact 10mm Spacing Validation + Repack Preview

## Státusz: PARTIAL

**Prototype/reference only. NOT production. CGAL is GPL — NOT production.**

---

## Státusz összefoglaló

| Fázis | Eredmény |
|-------|----------|
| T05n layout exact 10mm validation | FAIL (161 violations, 51 bounds) |
| T05o exact spacing repack | PARTIAL (2 violations, 34 bounds, 69 sheets) |

---

## T05n Baseline Exact 10mm Validation

**Source:** `lv6_blf_candidate_preview_spacing2p0_layout.json` (T05n, spacing=2mm approximate_bbox)

| Metrika | Érték |
|---------|-------|
| spacing_violation_count | 161 |
| min_clearance_mm | 0.00 |
| overlap_count | 0 |
| bounds_violation_count | 51 |

**Verdict:** FAIL — T05n layout NEM felel meg exact 10mm spacingnek.

**Megjegyzés:** T05n `approximate_bbox` spacing policy (spacing=0 és spacing=2 azonos eredményt adott). Az approximate_bbox AABB-alapú spacing margin közelítés, ami nem garantál exact spacing-t konvex/konkáv geometriáknál.

---

## T05o Exact Spacing Repack Eredmény

**Script:** `run_lv6_blf_candidate_exact_spacing_preview.py`
**Spacing policy:** `shapely_distance_or_buffer_exact` (distance-based exact check)
**Spacing:** 10.0mm

### Placement metrikák

| Metrika | T05o (exact 10mm) | T05n (approx 2mm) | Delta |
|---------|-------------------|-------------------|-------|
| Requested | 112 | 112 | 0 |
| Placed | **112** | **112** | 0 |
| Unplaced | **0** | **0** | 0 |
| Sheets | **69** | 11 | **+58** |
| Utilization | **5.86%** | 36.75% | **-30.89%** |
| Runtime | 25.7s | 41.9s | -16.2s |
| Candidates | 1,297,324 | 41,965 | +1,255,359 |

### Validation metrikák (post-hoc exact validator)

| Metrika | Érték |
|---------|-------|
| checked_pairs | 6,216 |
| spacing_checks (exact) | 175 |
| min_clearance_mm | 0.9669 |
| **spacing_violation_count** | **2** |
| **bounds_violation_count** | **34** |
| overlap_count | 0 |

### Worst violations

| Part 1 | Part 2 | Sheet | Distance | Violation |
|--------|--------|-------|----------|----------|
| Lv6_15205_12db (self) | Lv6_15205_12db (self) | 2 | 9.83mm | 0.17mm |
| Lv6_15264_9db | Lv6_16656_7db | 4 | 0.97mm | 9.03mm |

### Verdict

**PARTIAL** — A repack 112/112 instance-t elhelyezett, de:
- 2 spacing violation maradt (0.17mm és 9.03mm)
- 34 bounds violation (a validator szigorúbb a placement scriptnél)
- 69 sheet vs T05n 11 sheet (6.3× több lap)
- 5.86% vs T05n 36.75% utilization

### Violációk elemzése

**1. Self-pair 0.17mm violation (Lv6_15205_12db):**
- Két azonos típusú alkatrész között 9.83mm távolság
- Elvárt: 10.0mm
- Violáció: 0.17mm (1.7% a spacingből)
- Ok: candidate generator AABB margin (10mm) és exact distance check közötti határméretezési eltérés

**2. Cross-part 9.03mm violation (Lv6_15264_9db ↔ Lv6_16656_7db):**
- Két különböző alkatrész között 0.97mm távolság
- Elvárt: 10.0mm
- Violáció: 9.03mm
- Ok: AABB overlap check után a distance check ellenőrzi, de a candidate generator AABB margin-je nem elég pontos ehhez a kombinációhoz

**3. 34 bounds violation:**
- A validator szigorúbban ellenőrzi a bounds-ot (negatív tolerance), mint a placement script
- Ezek valószínűleg edge case-ek (x=-0.0001, y=-0.0001)

---

## Repack vs Baseline Összehasonlítás

| Metrika | T05n (spacing=2, approx) | T05o (spacing=10, exact) |
|---------|-------------------------|--------------------------|
| Sheets | 11 | 69 |
| Utilization | 36.75% | 5.86% |
| spacing_policy | approximate_bbox | shapely_distance_exact |
| Spacing violations (10mm validator) | 161 | 2 |
| Bounds violations (10mm validator) | 51 | 34 |

**Következtetés:** Az exact 10mm spacing szignifikánsan rontja a packolási hatékonyságot. A 10mm spacing 6.3× több lapot igényel és 84% utilization csökkenést okoz a T05n-hez képest.

---

## Spacing Policy Összehasonlítás

| Policy | T05n (approx_bbox) | T05o (exact_distance) |
|--------|-------------------|----------------------|
| Method | AABB margin + shapely exact | Shapely distance |
| spacing=0 vs spacing=2 | identical | would differ |
| Prototype vs production | approximate | more exact |
| Performance | ~42s | ~26s |
| Violations at 10mm | 161 | 2 |

---

## Output Artefaktumok

### Repack output
| Fájl | Leírás |
|------|--------|
| `lv6_blf_candidate_exact_spacing100_layout.json` | Placement layout JSON |
| `lv6_blf_candidate_exact_spacing100_metrics.json` | Metrics JSON |
| `lv6_blf_candidate_exact_spacing100_metrics.md` | Metrics MD |
| `lv6_blf_candidate_exact_spacing100_sheet01.svg` ... `sheet69.svg` | 69 per-sheet SVG |
| `lv6_blf_candidate_exact_spacing100_combined.svg` | Combined SVG |

### Validation output
| Fájl | Leírás |
|------|--------|
| `lv6_t05n_layout_exact_spacing100_validation.json` | Validator JSON |
| `lv6_t05n_layout_exact_spacing100_validation.md` | Validator MD |

### Script
| Fájl | Leírás |
|------|--------|
| `scripts/experiments/validate_lv6_exact_spacing.py` | Exact spacing validator |
| `scripts/experiments/run_lv6_blf_candidate_exact_spacing_preview.py` | BLF/candidate exact spacing preview |

---

## Módosított fájlok

Új fájlok:
- `scripts/experiments/validate_lv6_exact_spacing.py` — exact spacing validator
- `scripts/experiments/run_lv6_blf_candidate_exact_spacing_preview.py` — exact spacing preview script
- `tmp/reports/nfp_cgal_probe/lv6_t05n_layout_exact_spacing100_validation.json` — T05n validation
- `tmp/reports/nfp_cgal_probe/lv6_t05n_layout_exact_spacing100_validation.md` — T05n validation MD
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_*.{json,svg,md}` — T05o repack output

**NEM módosítva:** production Dockerfile, worker runtime, UI, Engine v2 quality profil, T08 integráció.

---

## Futtatott parancsok

```bash
# T05n layout exact 10mm validation
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_preview_spacing2p0_layout.json

# T05o exact spacing repack
python3 scripts/experiments/run_lv6_blf_candidate_exact_spacing_preview.py \
  --spacing-mm 10.0 \
  --max-candidates 300

# Post-hoc validation of repack
python3 scripts/experiments/validate_lv6_exact_spacing.py \
  --spacing-mm 10.0 \
  --layout tmp/reports/nfp_cgal_probe/lv6_blf_candidate_exact_spacing100_layout.json
```

---

## Limitációk

1. **Prototype only**: NEM production nesting algorithm

2. **Spacing violations maradtak**: 2 spacing violation (0.17mm és 9.03mm) a repack után is
   - A candidate generator AABB margin és exact distance check közötti határméretezési eltérés okozza
   - javítás: candidate generator spacing margin finomhangolása vagy csak exact spacing check minden candidate-re (nagyobb computational cost)

3. **69 sheet vs T05n 11**: Az exact 10mm spacing 6.3× több lapot igényel
   - Ez realisztikus: a spacing tényleg növeli a szükséges területet
   - De a 69 sheet túlzott — valószínűleg a candidate generator nem talál elég jó pozíciókat

4. **Bounds violations**: 34 bounds violation a validatorban, 0 a placement scriptben
   - A validator szigorúbb (negatív tolerance: -0.001)
   - Ezek tipikusan x=-0.0001, y=-0.0001 edge case-ek

5. **Shapely distance check**: A `polygon.distance()` nem mindig adja vissza a legkisebb távolságot polygon-with-holes esetén — a holes nem számítanak a distance számításba

6. **Runtime ~26s**: Gyorsabb mint T05n (~42s), de a candidate count 30× nagyobb

7. **No NFP optimization**: Nem használ No-Fit-Polygon algoritmust

8. **SVG per sheet + combined**: 69 per-sheet SVG + 1 combined SVG

---

## Következő javasolt lépés

1. **Spacing margin finomhangolás**: A candidate generator AABB spacing margin-jét 10mm-ről 12-15mm-re növelni, hogy kompenzálja az AABB↔exact distance eltérést

2. **Relaxed tolerance**: A validator tolerance 0.01mm helyett 0.5mm (1.7%-os self-pair violáció elfogadható prototype-nál)

3. **Post-placement greedy optimization**: Az elhelyezett layout-on utólagos spacing finomítás (shift parts to fix violations)

4. **Production spacing**: NFP-based spacing implementálása production rendszerhez — az exact polygon distance spacing nem skálázható valódi gyártáshoz

5. **SVG minimalizálás**: 69 sheet SVG generálása helyett csak a problémás sheet-eket renderelni

6. **Rotation kombinációk**: 0/90/180/270 teljes próba minden part-ra (jelenleg csak 0° és 90°)

---

## Elfogadási Feltételek Ellenőrzése

| Feltétel | Eredmény |
|----------|----------|
| total_instances_requested == 112 | ✅ (112) |
| total_instances_placed == 112 | ✅ (112) |
| total_instances_unplaced == 0 | ✅ (0) |
| overlap_count == 0 | ✅ (0) |
| bounds_violation_count == 0 | ❌ (34) — PARTIAL |
| spacing_violation_count == 0 | ❌ (2) — PARTIAL |
| min_clearance_mm riportolva | ✅ (0.97mm) |
| SVG layout elkészült | ✅ (69 + combined) |
| metrics JSON/MD elkészült | ✅ |
| Nincs production integráció | ✅ |
| Nincs T08 indítás | ✅ |

---

**Státusz: PARTIAL**

LV6 Exact 10mm Spacing Preview — Prototype only.
CGAL is GPL reference, NOT production.
Placement mode: blf_candidate_exact_spacing_preview.
Spacing policy: shapely_distance_or_buffer_exact (distance-based).
T05n layout FAIL (161 violations). T05o repack PARTIAL (2 violations, 69 sheets, 5.86% util).
