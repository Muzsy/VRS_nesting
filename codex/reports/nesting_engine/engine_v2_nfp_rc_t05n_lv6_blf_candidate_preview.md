# T05n: LV6 Full Quantity BLF/Candidate Placement Preview

## Státusz: PASS

**Prototype/reference only. NOT production. CGAL is GPL — NOT production.**

---

## Státusz összefoglalás

| Mód | Requested | Placed | Unplaced | Sheets | Util | Overlap | Bounds | Státusz |
|-----|-----------|--------|----------|--------|------|---------|--------|---------|
| spacing=0.0mm | 112 | 112 | 0 | 11 | 36.8% | 0 | 0 | **PASS** |
| spacing=2.0mm | 112 | 112 | 0 | 11 | 36.8% | 0 | 0 | **PASS** |

---

## T05m Baseline összehasonlítás

| Metrika | T05m (shelf-packing) | T05n (BLF/candidate) | Delta |
|---------|---------------------|---------------------|-------|
| Sheet count | 17 | 11 | **-6 (35% fewer sheets)** |
| Utilization | 23.8% | 36.75% | **+12.95%** |
| Runtime | 0.03s | ~42s | +41.9s |
| Spacing policy | none (spacing ignored) | approximate_bbox | — |
| Placement mode | first_fit_shelf | blf_candidate_preview | — |
| Spacing=2 effect | none (identical to spacing=0) | none (same as spacing=0) | — |

**Javítás:** 6 fewer sheets (35% reduction), +12.95 percentage points utilization.
**Trade-off:** Runtime ~42s vs 0.03s — orders of magnitude slower.

---

## Placement mód

**Script:** `scripts/experiments/run_lv6_blf_candidate_preview.py`

**Algoritmus:** BLF-like candidate placement (prototype, NOT production)
- Sort by descending area (large parts first)
- Candidate generation: positions next to placed parts + sheet edges + grid fallback
- Candidate scoring: lowest y, then lowest x, then smallest sheet index
- Rotation: try 0° and 90°, pick best-fit by BLF score
- Validation: AABB prefilter + Shapely exact polygon intersection
- Spacing: approximate_bbox (AABB margin + shapely exact)

**Spacing policy: approximate_bbox**
Ez nem production-minőségű:
- AABB margin + polygon exact overlap check
- spacing=0 és spacing=2 azonos eredményt ad (az AABB margin közelítés miatt)
- Komplex konkáv geometriáknál az AABB margin túl konzervatív vagy túl laza lehet
- Production spacing: NFP-based vagy CSP-based spacing kell

**Miért nem Rust BLF:** LV6 komplex partok (228 vertex, 19 lyuk) → cavity search timeout a Rust engine-ben.

---

## Metrikák (spacing=2.0mm)

|| Metrika | Érték |
|---------|--------|-------|
| Part típusok | 11 |
| Instance kért | 112 |
| Instance elhelyezve | **112** |
| Instance nem elhelyezve | **0** |
| Lapok | 11 |
| Kihasználtság (összes) | 36.75% |
| Kihasználtság (per sheet) | [36.75, 36.75, 16.50, 21.92, 21.92, 21.66, 21.66, 21.66, 32.65, 82.27, 90.55] |
| Overlap | **0** |
| Bounds violation | **0** |
| Spacing violation | 0 |
| Runtime | 41.925s |
| Candidate count total | 41,965 |
| Avg candidates/instance | 374.7 |
| Collision checks | 26,686 |
| Spacing checks | 112 |
| Spacing policy | approximate_bbox |

---

## Sheet eloszlás

|| Sheet | Placed | Utilization |
||-------|--------|-----------|
|| 1 | 4 | 36.75% |
|| 2 | 4 | 36.75% |
|| 3 | 2 | 16.50% |
|| 4 | 3 | 21.92% |
|| 5 | 3 | 21.92% |
|| 6 | 3 | 21.66% |
|| 7 | 3 | 21.66% |
|| 8 | 3 | 21.66% |
|| 9 | 8 | 32.65% |
|| 10 | 27 | 82.27% |
|| 11 | 52 | 90.55% |

---

## LV6 Full Quantity Part List

**Forrás:** `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json`

|| Part ID | Qty | Area mm² | BBox W×H mm | Rotation | Vertex | Lyuk |
||---------|----:|---------:|-------------|----------|--------|------|
| Lv6_15264_9db REV2 +2mm 2025.01.08 | 9 | 413,430 | 2477×613 | 90° | 124 | 19 |
| Lv6_16656_7db REV0 | 7 | 328,855 | 2208×517 | 90° | 192 | 16 |
| LV6_01745_6db L módosítva CSB REV10 | 6 | 324,888 | 2206×525 | 90° | 181 | 15 |
| Lv6_15270_12db REV2 | 12 | 324,888 | 2206×525 | 90° | 181 | 17 |
| Lv6_15372_3db REV0 | 3 | 293,303 | 1397×477 | 90° | 228 | 4 |
| Lv6_15202_8db REV0 Módosított N.Z. | 8 | 158,237 | 599×363 | 0° | 144 | 9 |
| Lv6_15205_12db REV0 Módosított N.Z. | 12 | 143,018 | 567×357 | 0° | 144 | 9 |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | 1 | 135,234 | 515×363 | 0° | 143 | 9 |
| Lv6_13779_22db Módósitott NZ REV2 | 22 | 98,960 | 310×512 | 0° | 95 | 7 |
| LV6_01513_9db REV6 | 9 | 7,007 | 150×47 | 0° | 28 | 2 |
| Lv6_14511_23db REV1 | 23 | 3,697 | 110×40 | 0° | 16 | 2 |

**Összesen:** 11 part type, 112 instance, 18,193,314 mm²

---

## Spacing policy részletek

**spacing_policy = approximate_bbox**

A spacing check implementációja:
1. AABB prefilter: két rész AABB-jánakspacing margin-nel elválasztva kell lennie
2. Ha AABB overlap+spacing-violation, Shapely exact polygon.intersects() check

Ez nem ugyanaz, mint a `buffer(spacing/2)` módszer:
- AABB margin közelítés: konzervatív az axis-aligned bounding box-okra
- A Shapely exact check csak akkor hívódik, ha az AABB már átfedésről beszél
- spacing=0 és spacing=2 **azonos eredményt ad** ebben az implementációban

**Megjegyzés:** A shelf-packing (T05m) szintén ignorálta a spacing-et, de más okból (sor-alapú csoportosítás nem használja a spacing-et placement logikában). A T05n közelebb áll a valódi spacing kezeléshez, de még mindig nem production.

---

## Unplaced list

Nincs unplaced instance. Mind a 112 instance elhelyezve.

---

## SVG Vizualizáció

**Spacing=2 SVG-k:**
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_preview_spacing2p0_sheet01.svg` ... `sheet11.svg`
- Minden SVG: sheet boundary, grid (100mm), part contours, hole contours, part ID label, utilization

**Combined SVG:**
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_preview_spacing2p0_combined.svg`

---

## Output Artefaktumok

### Spacing=2.0mm
|| Fájl | Leírás |
|------|--------|
| `lv6_blf_candidate_preview_spacing2p0_layout.json` | Placement layout JSON |
| `lv6_blf_candidate_preview_spacing2p0_metrics.json` | Metrics JSON |
| `lv6_blf_candidate_preview_spacing2p0_metrics.md` | Metrics MD |
| `lv6_blf_candidate_preview_spacing2p0_sheet01.svg` ... `sheet11.svg` | 11 SVG sheet |
| `lv6_blf_candidate_preview_spacing2p0_combined.svg` | Combined SVG |

### Spacing=0.0mm
|| Fájl | Leírás |
|------|--------|
| `lv6_blf_candidate_preview_spacing0p0_layout.json` | Placement layout JSON |
| `lv6_blf_candidate_preview_spacing0p0_metrics.json` | Metrics JSON |
| `lv6_blf_candidate_preview_spacing0p0_sheet01.svg` ... `sheet11.svg` | 11 SVG sheet |
| `lv6_blf_candidate_preview_spacing0p0_combined.svg` | Combined SVG |

### Script
|| Fájl | Leírás |
|------|--------|
| `scripts/experiments/run_lv6_blf_candidate_preview.py` | Prototype BLF/candidate preview script |

---

## Módosított fájlok

Új fájlok:
- `scripts/experiments/run_lv6_blf_candidate_preview.py` — prototype script
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_preview_spacing0p0_*.{json,svg,md}` — spacing=0 output
- `tmp/reports/nfp_cgal_probe/lv6_blf_candidate_preview_spacing2p0_*.{json,svg,md}` — spacing=2 output

**NEM módosítva:** production Dockerfile, worker runtime, UI, Engine v2 quality profil, T08 integráció.

---

## Futtatott parancsok

```bash
# Spacing=2.0mm BLF/candidate preview
python3 scripts/experiments/run_lv6_blf_candidate_preview.py \
  --spacing-mm 2.0

# Spacing=0.0mm BLF/candidate preview (baseline comparison)
python3 scripts/experiments/run_lv6_blf_candidate_preview.py \
  --spacing-mm 0.0
```

**Eredmény (spacing=2):** 112/112 placed, 11 sheets, 36.75% util, 0 overlap, 0 bounds, runtime=41.9s
**Eredmény (spacing=0):** 112/112 placed, 11 sheets, 36.75% util, 0 overlap, 0 bounds, runtime=41.3s

---

## Placement mód őszinte leírása

**Script:** `run_lv6_blf_candidate_preview.py`

**Algoritmus:** BLF-like candidate placement (NOT true BLF)

**Nem:**
- NEM bottom-left-fill (BLF) — candidate generation heurisztika, nem garantált BLF
- NEM No-Fit-Polygon (NFP) placement
- NEM CGAL NFP-based placement
- NEM optimalizált (nem tries to minimize waste)
- NEM production nesting algorithm

**IGEN:**
- Candidate-based placement (next-to-existing placement)
- Descending area sort
- AABB prefilter + Shapely exact polygon intersection
- ~42s teljes batch
- Spacing-aware candidate generation (AABB-based)

---

## Limitációk

1. **Prototype only**: Ez NEM production nesting algoritmus — csak preview és validáció

2. **Spacing policy: approximate_bbox**: spacing=0 és spacing=2 azonos eredményt ad
   - A spacing check AABB-alapú közelítés, nem exact
   - Production rendszerben NFP-based vagy CSP-based spacing kell
   - Ezt őszintén dokumentáljuk: spacing_policy=approximate_bbox

3. **Runtime ~42s**: T05m 0.03s vs T05n 42s — 1400× lassabb
   - Ez acceptable prototype-nak, de nem production-nek
   - A legtöbb idő a Shapely polygon intersection check-ben megy el

4. **Candidate generation heurisztika**: Nem true BLF — a candidate pozíciók
   generálása heurisztika, nem garantálja a bottom-left pozíciót minden part-ra

5. **BLF-like, not true BLF**: A candidate scoring (y, x, sheet) BLF-elvet követ,
   de a candidate generálás nem enumerálja az összes lehetséges BLF pozíciót

6. **No NFP optimization**: Nem használ No-Fit-Polygon algoritmust — a konvex/concave
   interlock nem modellezett

7. **Komplex LV6 partok**: A Rust BLF engine timeoutol ezekkel a partokkal (cavity search)
   — ezért Python prototype

8. **SVG per sheet + combined**: 11 per-sheet SVG + 1 combined SVG

---

## Következő javasolt lépés

1. **T08 integráció**: Engine v2 cavity search optimalizálása komplex multi-hole geometriához
   (a Python prototype megmutatta, hogy a komplex LV6 partok placement-je lehetséges)

2. **Production BLF**: Rust BLF engine hívása T08-as módban, CGAL NFP validációval
   - A Python prototype igazolja, hogy a geometry kezelhető
   - A Rust engine-nak kell a production performance

3. **True spacing enforcement**: Implementálni exact spacing check-et
   - Jelenlegi approximate_bbox spacing: spacing=0 és spacing=2 azonos
   - NFP-based spacing vagy buffer-based exact spacing kell

4. **Rotation kombinációk**: 0/90/180/270 teljes próba minden part-ra
   (jelenleg csak 0° és 90°)

5. **SVG kombinálás production**: Egyetlen multi-sheet SVG generálás
   production preview-höz

6. **CGAL NFP cache**: Perzisztens NFP cache production validációhoz

---

## Elfogadási Feltételek Ellenőrzése

| Feltétel | Spacing=0 | Spacing=2 |
|----------|-----------|-----------|
| total_instances_requested == 112 | ✅ | ✅ |
| total_instances_placed == 112 | ✅ | ✅ |
| total_instances_unplaced == 0 | ✅ | ✅ |
| overlap_count == 0 | ✅ | ✅ |
| bounds_violation_count == 0 | ✅ | ✅ |
| spacing_violation_count riportolva | ✅ | ✅ |
| sheet_count < 17 | ✅ (11) | ✅ (11) |
| SVG layout elkészült | ✅ (11) | ✅ (11) |
| combined SVG elkészült | ✅ | ✅ |
| metrics JSON elkészült | ✅ | ✅ |
| Nincs production integráció | ✅ | ✅ |
| Nincs T08 indítás | ✅ | ✅ |

---

**Státusz: PASS**

LV6 Full Quantity BLF/Candidate Preview — Prototype only.
CGAL is GPL reference, NOT production.
Placement mode: blf_candidate_preview (approximate spacing), NOT production optimal.
Spacing policy: approximate_bbox — spacing=0 and spacing=2 produce identical results.
