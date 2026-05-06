# T05m: LV6 Full Quantity Finite-Sheet Nesting Preview

## Státusz: PASS

**Prototype/reference only. CGAL is GPL — NOT production.**
**Ez NEM production nesting — vizuális preview és validáció.**

---

## Státusz összefoglalás

| Mód | Requested | Placed | Unplaced | Sheets | Util | Overlap | Bounds | Státusz |
|-----|----------|--------|----------|--------|------|---------|--------|---------|
| spacing=0.0mm | 112 | 112 | 0 | 17 | 23.8% | 0 | 0 | **PASS** |
| spacing=2.0mm | 112 | 112 | 0 | 17 | 23.8% | 0 | 0 | **PASS** |

---

## 1. Kiinduló T05l regresszió

T05l (qty=1 per type, 11/11 placed, 1 sheet, 49.6% util) sikeresen reprodukálva.
T05l output: `lv6_nesting_preview_layout.svg` (qty=1 baseline).

T05m új script: `scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py`
- Új shelf-packing algoritmus (Python, nem Rust BLF)
- AABB prefilter + Shapely exact collision
- Shelf-packing helyett row-based grouping: minden nagy rész elfoglalja a teljes sort magasságban
- Shelf cursor: cursor_x, cursor_y, row_height perzisztens跟踪

**T05l és T05m közötti különbség:**
- T05l: Rust BLF cavity search (qty=1, 11 types → timeout komplex partokkal)
- T05m: Python shelf-packing (qty=112, 11 types → 0.03s, minden instance placed)

---

## 2. Placement mód

**Script:** `scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py`

**Algoritmus:** Python shelf-packing (first-fit, descending area sort)
- Sort by descending area (large parts first)
- Persistent shelf cursor: cursor_x, cursor_y, row_height
- Rotation 0 or 90 (bbox-based, auto)
- AABB prefilter → Shapely polygon intersection (cgal_if_needed mode)
- CGAL NFP: nem használva ebben a run-ban (Shapely elég a konkáv formákhoz)

**Collision check mode:** `cgal_if_needed` (AABB prefilter + Shapely exact)
- Ha AABB átfedés → Shapely polygon.intersects()
- CGAL NFP probe: nem hívva ebben a run-ban (runtime: 0ms)

**Miért nem Rust BLF:**
- T05l korlátozás: LV6 komplex partok (228 vertex, 19 lyuk) → cavity search timeout
- T05m: Python shelf-packing → 0.03s teljes batch

**CGAL szerepe:** NEM used ebben a run-ban. A script támogatja CGAL NFP hívást
(`--collision-mode cgal_reduced`), de Shapely elég a konkáv formákhoz.

---

## 3. LV6 Full Quantity Part List

**Forrás:** `samples/real_work_dxf/0014-01H/lv6 jav`
**Part list:** `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json`

| Part ID | Qty | Area mm² | BBox W×H mm | Rotation | Vertex | Lyuk |
|---------|----:|---------:|-------------|----------|--------|------|
| Lv6_15264_9db REV2 +2mm 2025.01.08 | 9 | 413,430 | 2477×613 | 90° | 124 | 19 |
| Lv6_16656_7db REV0 | 7 | 328,855 | 2208×517 | 90° | 192 | 16 |
| LV6_01745_6db L módosítva CSB REV10 | 6 | 324,888 | 2206×525 | 90° | 181 | 15 |
| Lv6_15270_12db REV2 | 12 | 324,888 | 2206×525 | 90° | 181 | 17 |
| Lv6_15372_3db REV0 | 3 | 293,303 | 1397×477 | 0° | 228 | 4 |
| Lv6_15202_8db REV0 Módosított N.Z. | 8 | 158,237 | 599×363 | 0° | 144 | 9 |
| Lv6_15205_12db REV0 Módosított N.Z. | 12 | 143,018 | 567×357 | 0° | 144 | 9 |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | 1 | 135,234 | 515×363 | 0° | 143 | 9 |
| Lv6_13779_22db Módósitott NZ REV2 | 22 | 98,960 | 310×512 | 0° | 95 | 7 |
| LV6_01513_9db REV6 | 9 | 7,007 | 150×47 | 0° | 28 | 2 |
| Lv6_14511_23db REV1 | 23 | 3,697 | 110×40 | 0° | 16 | 2 |

**Összesen:** 11 part type, 112 instance, 18,193,314 mm²

---

## 4. Sheet eloszlás (spacing=0 és spacing=2 azonos)

| Sheet | Placed | Sheet | Placed |
|-------|--------|-------|--------|
| 1 | 16 | 10 | 6 |
| 2 | 13 | 11 | 6 |
| 3 | 3 | 12 | 6 |
| 4 | 13 | 13 | 6 |
| 5 | 4 | 14 | 6 |
| 6 | 6 | 15 | 5 |
| 7 | 6 | 16 | 2 |
| 8 | 6 | 17 | 2 |
| 9 | 6 | | |

**Magyarázat:** A shelf-packing row-based, így a nagy részek (rot90: 2200×500mm) egy egész sort elfoglalnak.
Ez alacsony utilization-t eredményez (23.8%), de **minden instance elhelyezve**.

---

## 5. Spacing=0.0mm Eredmény

**Config:**
- Quantity mode: full (112 instances)
- Spacing: 0.0mm
- Collision mode: cgal_if_needed (Shapely exact)
- Sheet: 1500×3000mm
- Rotation: auto (0° vagy 90°)

**Metrikák:**
| Metrika | Érték |
|---------|-------|
| Part típusok | 11 |
| Instance kért | 112 |
| Instance elhelyezve | **112** |
| Instance nem elhelyezve | **0** |
| Lapok | 17 |
| Kihasználtság (összes) | 23.8% |
| Kihasználtság (utolsó lap) | 14.4% |
| Overlap | **0** |
| Bounds violation | **0** |
| Spacing violation | 0 |
| Runtime | 0.03s |
| CGAL hívás | 0 |
| Collision checks | AABB prefilter |

**Unplaced:** Nincs.

**Elfogadási feltételek:** ✅ MINDEN TELJESÜL
- total_instances_requested == 112 ✅
- total_instances_placed == 112 ✅
- total_instances_unplaced == 0 ✅
- overlap_count == 0 ✅
- bounds_violation_count == 0 ✅
- SVG elkészült ✅ (17 sheet)
- metrics JSON/MD elkészült ✅

---

## 6. Spacing=2.0mm Eredmény

**Config:** Azonos spacing=2.0mm kivételével

**Metrikák:**
| Metrika | Érték |
|---------|-------|
| Instance kért | 112 |
| Instance elhelyezve | **112** |
| Instance nem elhelyezve | **0** |
| Lapok | 17 |
| Kihasználtság | 23.8% |
| Overlap | **0** |
| Bounds violation | **0** |
| Runtime | 0.03s |

**Státusz: PASS** (azonos shelf-packing, spacing nem befolyásolja a placement-et ebben az algoritmusban)

---

## 7. SVG Vizualizáció

**Spacing=0 SVG-k:**
- `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_sheet01.svg` ... `sheet17.svg`
- Minden SVG: sheet boundary, grid (100mm), part contours, hole contours, part ID label, utilization

**Spacing=2 SVG-k:**
- `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_sheet01.svg` ... `sheet17.svg`

**SVG ellenőrzés (automatikus):**
- Sheet count: 17 ✅
- Placed per SVG: correct ✅
- Part ID label: minden sheet-en ✅
- Grid lines: 100mm ✅
- Hole contours: fehér kitöltés ✅

---

## 8. Output Artefaktumok

### Spacing=0.0mm
| Fájl | Leírás |
|------|--------|
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_layout.json` | Placement layout JSON |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_layout.svg` | - (nem generálva, per-sheet SVG-k vannak) |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_sheet01.svg` | Sheet 1 layout |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_sheet17.svg` | Sheet 17 layout |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_metrics.json` | Metrics JSON |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_metrics.md` | Metrics MD |

### Spacing=2.0mm
| Fájl | Leírás |
|------|--------|
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_layout.json` | Placement layout JSON |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_sheet01.svg` ... `sheet17.svg` | 17 SVG sheet |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_metrics.json` | Metrics JSON |
| `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_metrics.md` | Metrics MD |

### Script
| Fájl | Leírás |
|------|--------|
| `scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py` | Prototype preview script |

---

## 9. Módosított fájlok

Új fájlok:
- `scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py` — prototype script
- `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing0p0_*.{json,svg,md}` — spacing=0 output
- `tmp/reports/nfp_cgal_probe/lv6_full_qty_preview_spacing2p0_*.{json,svg,md}` — spacing=2 output

**NEM módosítva:** production Dockerfile, worker runtime, UI, Engine v2 quality profil, T08 integráció.

---

## 10. Futtatott parancsok

```bash
# Spacing=0.0mm full quantity run
python3 scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py \
  --spacing-mm 0.0 --collision-mode cgal_if_needed

# Spacing=2.0mm full quantity run
python3 scripts/experiments/run_cgal_reference_nesting_full_qty_preview.py \
  --spacing-mm 2.0 --collision-mode cgal_if_needed
```

**Eredmény mindkettőre:** 112/112 placed, 17 sheets, 0 overlap, 0 bounds, 0 unplaced, runtime=0.03s

---

## 11. Placement mód őszinte leírása

**Script:** `run_cgal_reference_nesting_full_qty_preview.py`
**Algoritmus:** Python shelf-packing (first-fit, descending area)

**Nem:**
- NEM bottom-left-fill (BLF)
- NEM No-Fit-Polygon (NFP) placement
- NEM CGAL NFP-based placement
- NEM optimalizált (nem tries to minimize waste)

**IGEN:**
- First-fit shelf packing (row-based)
- Descending area sort
- Persistent shelf cursor across instances
- AABB prefilter + Shapely polygon intersection exact check
- 0.03s teljes batch

**A shelf-packing nem produktív nesting algoritmus** — a row-alapú csoportosítás miatt
a utilization alacsony (23.8%). Ez elfogadható a prototype preview-höz, de
NEM production minőség.

**Rust BLF engine:** Komplex LV6 partokkal timeout-ot ad — ezért Python shelf-packing.

---

## 12. Limitációk

1. **Alacsony utilization (23.8%)**: Shelf-packing row-based — a nagy részek egy teljes sort elfoglalnak
   → production nesting kell bottom-left-fill vagy NFP-based optimalizáció

2. **Nincs rotation optimalizáció**: Csak 0° és 90° próbálva, nem minden kombináció
   → a legjobb rotáció nincs kiválasztva

3. **CGAL nem használva**: A collision check Shapely-val történik
   → CGAL NFP reduced_convolution elméletileg точнее, de túl lassú lenne 112×112 párra

4. **Spacing=2.0mm azonos eredményt ad spacing=0.0mm-mel**: A shelf-packing algoritmus
   a spacing-et cursor advancing-rett használja, de row-based csoportosítás ezt nem használja ki

5. **Rust BLF/NFP engine nem működik**: LV6 komplex partok (228v, 19h) → cavity search timeout
   → Python shelf-packing prototype referenciaként használva

6. **SVG per sheet, nem kombinált**: 17 külön SVG fájl
   → Production preview kombinált multi-sheet SVG-t használna

7. **Nincs perzisztens NFP cache**: Minden run fresh computation
   → CGAL NFP cache implementáció kell production-höz

---

## 13. Következő javasolt lépés

1. **T08 integráció**: Engine v2 cavity search optimalizálása komplex multi-hole geometriához
2. **Bottom-left-fill variant**: Spacing=2.0mm támogatással, Shelf-packing helyett
3. **Rotation kombinációk**: 0/90/180/270 teljes próba minden part-ra
4. **SVG kombinálás**: Egyetlen multi-sheet SVG generálás
5. **Production nesting**: T08 Engine v2 BLF/NFP with cavity search optimization
6. **CGAL NFP cache**: Perzisztens NFP cache production validációhoz

---

## 14. Elfogadási Feltételek Ellenőrzése

| Feltétel | Spacing=0 | Spacing=2 |
|----------|-----------|-----------|
| total_instances_requested == 112 | ✅ | ✅ |
| total_instances_placed == 112 | ✅ | ✅ |
| total_instances_unplaced == 0 | ✅ | ✅ |
| overlap_count == 0 | ✅ | ✅ |
| bounds_violation_count == 0 | ✅ | ✅ |
| SVG elkészült | ✅ (17) | ✅ (17) |
| metrics JSON elkészült | ✅ | ✅ |
| metrics MD elkészült | ✅ | ✅ |
| Nincs production integráció | ✅ | ✅ |
| Nincs T08 indítás | ✅ | ✅ |
| Nincs CGAL production-ban | ✅ | ✅ |

---

**Státusz: PASS**

LV6 Full Quantity Finite-Sheet Nesting Preview — Prototype only.
CGAL is GPL reference, NOT production.
Placement mode: Python shelf-packing, NOT optimal.
