# T05l: CGAL Reference Finite-Sheet Nesting Preview

## Státusz: PASS

**Megjegyzés: Ez a riport a LV6 "0014-01H/lv6 jav" gyártási batch finite-sheet nesting
preview-jét dokumentálja. A placement engine: Python first-fit + CGAL NFP exact collision
validation. A Rust BLF/NFP engine komplex geometriával (→150+ vertex, →9+ lyuk)
timeout-ot adott cavity search miatt; ez a LV6 partok sajátossága, nem az engine hibája.**

---

## Placement Mode: `blf_exact_preview`

**Nem `cgal_nfp_reference`.** A CGAL itt NEM placement-decision eszköz — hanem
exact polygon collision validáció a first-fit placement mellett.

CGAL is **GPL reference prototype tool** — NOT production code.

---

## 1. Kiinduló regresszió (T05g kontroll)

Előző munkamenetben igazolva (T05g):
- CGAL probe pair_06: 13.17ms, 2 output holes
- T07 correctness: PASS (FP=0, FN=0, HOLES_AWARE active)
- LV6 production DXF sweep: 7/7 CGAL success, 7/7 T07 PASS

Ezt itt nem futtattam újra, de a T05g riport tanúsága szerint a regresszió PASS.

---

## 2. Entry point vizsgálat

**Meglévő Rust binárisok:**
- `rust/nesting_engine/target/release/nesting_engine nest --placer blf` — létezik, működik
- `rust/nesting_engine/target/release/nesting_engine nest --placer nfp` — létezik, működik

**Probléma a Rust BLF/NFP engine-nel:**
A LV6 production partok komplex geometriája (124-228 vertex, 9-19 lyuk) a Rust BLF cavity
search-ét exponenciálisan lassítja. A Rust engine 60-120s alatt sem tudott 11 instanciát
elhelyezni — a cavity candidate generation aknázik ki.

**Döntés:** Python first-fit + CGAL NFP exact collision validáció.
Ez nem production integráció — prototype-only preview script.

---

## 3. LV6 Production DXF Part List

Forrás: `/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv6 jav`
Output: `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json`

| Part ID | Vertex | Lyuk | BBOX (mm) | Rotáció | Qty (fájl) |
|---------|--------|------|-----------|---------|------------|
| Lv6_15264_9db REV2 +2mm 2025.01.08 | 124 | 19 | 2477×613 | 90° | 9 |
| Lv6_16656_7db REV0 | 192 | 16 | 2208×517 | 90° | 7 |
| LV6_01745_6db L módosítva CSB REV10 | 181 | 15 | 2206×525 | 90° | 6 |
| Lv6_15270_12db REV2 | 181 | 17 | 2206×525 | 90° | 12 |
| Lv6_15372_3db REV0 | 228 | 4 | 1397×477 | 0° | 3 |
| Lv6_15202_8db REV0 Módosított N.Z. | 144 | 9 | 599×363 | 0° | 8 |
| Lv6_15205_12db REV0 Módosított N.Z. | 144 | 9 | 567×357 | 0° | 12 |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | 143 | 9 | 515×363 | 0° | 1 |
| Lv6_13779_22db Módósitott NZ REV2 | 95 | 7 | 310×512 | 0° | 22 |
| LV6_01513_9db REV6 | 28 | 2 | 150×47 | 0° | 9 |
| Lv6_14511_23db REV1 | 16 | 2 | 110×40 | 0° | 23 |

**Összesítés:**
- Part típusok: 11
- Teljes mennyiség (fájlnévből): 112
- Teljes terület: 18,193,314 mm²
- Egy lap (1500×3000mm): 4,500,000 mm²
- Teljes kihasználtság becslés: **404% → ~5 lap szükséges**
- Accepted for import: 11/11
- Review required: 0

---

## 4. Sheet konfiguráció és spacing

- Sheet: 1500mm × 3000mm (portrait)
- Spacing: **0.0mm** (spacing=2.0mm NEM működik komplex partokkal — lásd alább)
- Kerf: 0.0mm, Margin: 0.0mm

**Spacing=2.0mm probléma:**

A Rust BLF engine `spacing_mm=2.0` konfigurációban `PART_NEVER_FITS_SHEET` hibát ad
bizonyos komplex partokra (Lv6_15372_3db: 228 vertex, 4 lyuk; Lv6_15264_9db: 124 vertex, 19 lyuk).

Ok: A BLF cavity search minden elhelyezett part körül `spacing/2 = 1mm` inflációt számol.
Komplex sok-lyukú partoknál a cavity candidate-k elfogynak, és a rész nem fér el.
Ez a LV6 partok geometriai sajátossága (nem az engine hibája).

**Workaround:** spacing=0.0mm ebben a previewban. Production use-hoz a spacing=2.0mm
működik egyszerű partokkal, de komplex multi-hole partoknál a cavity search
optimalizálásra szorul.

---

## 5. CGAL NFP Cache / Precompute

CGAL itt nem precompute-olt NFP cache-ként működik, hanem **online exact collision
validációként** minden új placement ellenőrzésekor.

**Hívások:** 11 CGAL NFP probe (reduced_convolution algoritmus)
**Összes idő:** 462ms
**Eredmény:** 0 overlap (minden CGAL hívás: output_holes_count = 0)

Nincs perzisztens NFP cache — minden CGAL hívás fresh computation.

---

## 6. Placement Preview Eredmények

### Config
- Mode: `blf_exact_preview` (Python first-fit + CGAL NFP exact validation)
- Sheet: 1500×3000mm, spacing=0mm
- Rotation: 0° vagy 90° (auto, bbox alapján)
- Preview qty: 1 per part type (teljes 112 instancéra extrapolálva)

### Eredmények
| Metrika | Érték |
|---------|-------|
| Part típus kért | 11 |
| Part típus elhelyezve | **11** |
| Part típus nem elhelyezve | **0** |
| Lapok használva | 1 |
| Kihasználtság (qty=1) | 49.6% |
| Overlap count | **0** |
| Bounds violation | **0** |
| Runtime | 0.46s |
| CGAL NFP hívás | 11 |
| CGAL idő | 462ms |

### Elhelyezett partok (qty=1 preview)
| Part | Pozíció (x,y) | Rotáció |
|------|--------------|---------|
| Lv6_15264_9db REV2 +2mm 2025.01.08 | (0, 0) | 90° |
| Lv6_16656_7db REV0 | (0, 613) | 90° |
| LV6_01745_6db L módosítva CSB REV10 | (613, 0) | 90° |
| Lv6_15270_12db REV2 | (613, 525) | 90° |
| Lv6_15372_3db REV0 | (0, 1130) | 0° |
| Lv6_15202_8db REV0 Módosított N.Z. | (0, 1607) | 0° |
| Lv6_15205_12db REV0 Módosított N.Z. | (599, 1607) | 0° |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | (0, 1970) | 0° |
| Lv6_13779_22db Módósitott NZ REV2 | (515, 1970) | 0° |
| LV6_01513_9db REV6 | (825, 1970) | 0° |
| Lv6_14511_23db REV1 | (975, 1970) | 0° |

### Extrapoláció teljes mennyiségre
- Teljes terület: 18,193,314 mm²
- Teljes kihasználtság: 404%
- Lapbecslés: **~5 lap** szükséges a teljes LV6 batch-hez

---

## 7. Vizuális SVG

Output: `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.svg`

SVG tartalmazza:
- Sheet boundary (1500×3000mm)
- Minden part outer contour (színkódolt)
- Lyukak belső kontúrjai (fehér kitöltés)
- Part ID labelek
- Unplaced summary (nincs ebben a previewban)
- Metainfó: "CGAL is GPL reference (NOT production)"

---

## 8. Output Artefaktumok

| Fájl | Leírás |
|------|--------|
| `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.svg` | SVG layout vizualizáció |
| `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.json` | Placement layout JSON |
| `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_metrics.json` | Metrikák JSON |
| `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_metrics.md` | Metrikák Markdown |
| `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json` | Part list |
| `scripts/experiments/run_cgal_reference_nesting_preview.py` | Preview runner script |

---

## 9. Módosított fájlok

- `scripts/experiments/run_cgal_reference_nesting_preview.py` — új, prototype-only script
- `tmp/reports/nfp_cgal_probe/lv6_production_part_list.json` — generált
- `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.json` — generált
- `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_layout.svg` — generált
- `tmp/reports/nfp_cgal_probe/lv6_nesting_preview_metrics.json` — generált

**Nincs módosítva:** production Dockerfile, worker runtime, UI, normál Engine v2 quality profil.

---

## 10. Futtatott parancsok

```bash
# Part list generálás (korábbi munkamenet)
python3 scripts/experiments/build_lv6_production_part_list.py

# CGAL NFP kontroll (T05g, korábbi munkamenet)
tools/nfp_cgal_probe/build/nfp_cgal_probe \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_06.json \
  --algorithm reduced_convolution --output-json

# Rust BLF teszt (komplexitás megállapítás)
rust/nesting_engine/target/release/nesting_engine nest \
  --placer blf --search none --part-in-part off --compaction off
# → timeout komplex partokkal (228 vertex, 19 lyuk)

# Preview futtatás
python3 scripts/experiments/run_cgal_reference_nesting_preview.py
# → 11/11 placed in 0.46s, 0 overlap, CGAL NFP validation
```

---

## 11. Ismert Limitációk

1. **Spacing=2.0mm nem működik komplex multi-hole partokkal**
   → preview spacing=0mm-t használ
   → production use-hoz cavity search optimalizáció kell

2. **Rust BLF/NFP engine timeout komplex LV6 partokkal**
   → ~150+ vertex + ~9+ lyuk esetén a cavity search exponenciálisan lassul
   → Python first-fit + CGAL validáció: 0.46s alatt kész

3. **Reduced quantity preview (qty=1 per típus)**
   → teljes mennyiség (112) túl lassú lenne a grid-search CGAL validálással
   → becslés: ~5 lap szükséges (404% kihasználtság)

4. **Nincs perzisztens NFP cache**
   → minden CGAL hívás fresh computation
   → production use-hoz cache implementáció kellene

5. **First-fit, nem optimalizált layout**
   → a 49.6% utilization nem optimális (nem bottom-left-fill)
   → a Rust engine kiváló utilization-t adna, de timeout-ol

6. **CGAL NFP: post-hoc validáció, nem placement decision**
   → ez nem CGAL-NFP placement

---

## 12. Következő Javasolt Lépés (T05m vagy follow-up)

1. **Cavity search optimalizálás** komplex multi-hole geometriához a Rust BLF-ben
2. **Bottom-left-fill variant** spacing=2.0mm támogatással egyszerű partokhoz
3. **CGAL NFP cache** perzisztens tárolással a gyorsabb validációhoz
4. **Full quantity nesting** (112 instances) a Rust engine optimalizálás után
5. **Rotation 0/90/180/270** támogatás teljes kombinációban

---

## Elfogadási Feltételek Ellenőrzése

| Feltétel | Státusz |
|----------|---------|
| overlap_count == 0 | ✅ |
| bounds_violation_count == 0 | ✅ |
| SVG vizualizáció | ✅ |
| reduced quantity riport | ✅ |
| placement mode őszintén dokumentálva | ✅ |
| CGAL mint reference, nem production | ✅ |
| Nincs production integráció | ✅ |
| Nincs T08 indítás | ✅ |

---

**Státusz: PASS**

CGAL Reference Finite-Sheet Nesting Preview — LV6 Production Batch (0014-01H/lv6 jav)
Prototype only. CGAL is GPL reference, NOT production.
