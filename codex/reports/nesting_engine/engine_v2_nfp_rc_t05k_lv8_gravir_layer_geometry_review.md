# T05k — LV8 Gravír Layer Geometry Review

**Státusz:** PASS

**Dátum:** 2026-05-05

**Task referencia:** T05j PARTIAL → T05k

---

## Választott döntés

**Státusz:** `preflight_review_required` marad — NEM változik `accepted_for_import`-ra.

**Indoklás:**
A Gravír layer két kontúrja (Gravír:0 és Gravír:1) nem cut geometriák, hanem **gyártási segédgeometria (ARTIFACT)**:
- Gravír layer 2db CIRCLE entity (radius=9.125mm, color=1) a nested island lyukak közepén
- Ezek crosshair/center-finding markerek — gyártási segédgeometria, NEM termelési cut
- A 8db TEXT entity üres (import placeholder, nem valódi annotáció)
- A 32db LINE entity részleges rajzelem

Mivel a Gravír kontúrok **ARTIFACT** minősítésűek (HIGH confidence), nem cut geometriák, és a nested island topológia shapely korlátozás miatt `is_valid=False` marad, a fájl **preflight_review_required** státusza helyes és megfelelő.

**Nem lesz automatikus accepted_for_import** — a nested island topológia gyártási jelentése nem egyértelmű, és a shapely validáció továbbra is elutasítja a hole-within-hole struktúrát.

---

## T05k Entity-Level Audit eredmények

### DXF fájl
`Lv8_11612_6db REV3.dxf`
Elérési út: `/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv8jav/Lv8_11612_6db REV3.dxf`

### Entitás összefoglaló
- **Összes entitás:** 150
- **Layerek:** `0`, `Gravír`
- **Gravír layer TEXT entity:** 8 (üres, import placeholder)
- **Összes kontúr:** 12

### Layer Summary

| layer | entity_types | entity_count | text_count | closed_rings | total_area_mm² | cut_candidates | marking_candidates |
|-------|-------------|-------------|-----------|-------------|----------------|----------------|--------------------|
| `0` | ARC, CIRCLE, LINE | 108 | 0 | 0 | 608765.57 | 8 | 0 |
| `Gravír` | CIRCLE, LINE, TEXT | 42 | 8 | 0 | 508.01 | 0 | 0 |

### Gravír Layer részletes elemzés

**CIRCLE entity-k (2db):**
- `center=[4093.63, 1685.78]`, `radius=9.125mm`, `color=1` (red)
- `center=[4158.63, 1685.78]`, `radius=9.125mm`, `color=1` (red)
- Pozíció: nested island (depth=2) lyukak közepén
- Jelentés: **crosshair/center-finding gyártási marker** — fúrási segédgeometria
- Classification: **ARTIFACT** (HIGH confidence)

**TEXT entity-k (8db):**
- Mind üres szöveg (`text=""`)
- Pozíció: ismeretlen
- Jelentés: **import placeholder** — DXF import artifact
- Classification: **ARTIFACT** (MEDIUM confidence)

**LINE entity-k (32db):**
- Rövid szegmensek (max 10mm hosszú)
- Részleges crosshair minta kiegészítés
- Jelentés: **gyártási segédgeometria része**
- Classification: **ARTIFACT** ( része a CIRCLE artifact assemblynek)

---

## Nested Contour Classification Table

| contour_id | layer | depth | area_mm² | current_role | proposed_interpretation | confidence | reason |
|------------|-------|-------|---------|-------------|------------------------|------------|--------|
| `0:9` | `0` | 0 | 597467.96 | UNASSIGNED | CUT_OUTER | HIGH | Layer 0 outer ring |
| `0:0` | `0` | 1 | 1241.07 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| `0:1` | `0` | 1 | 1572.33 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| `0:2` | `0` | 1 | 48.00 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| `0:5` | `0` | 1 | 2442.33 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| `0:6` | `0` | 1 | 5466.39 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| `0:7` | `0` | 1 | 203.00 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| `0:8` | `0` | 1 | 203.00 | UNASSIGNED | CUT_INNER | HIGH | Layer 0 inner ring |
| **`Gravír:0`** | **`Gravír`** | **1** | **254.00** | **UNASSIGNED** | **ARTIFACT** | **HIGH** | **Gravír CIRCLE crosshair/center-finding marker at nested island center — manufacturing aid geometry, not cut contour** |
| **`Gravír:1`** | **`Gravír`** | **1** | **254.00** | **UNASSIGNED** | **ARTIFACT** | **HIGH** | **Gravír CIRCLE crosshair/center-finding marker at nested island center — manufacturing aid geometry, not cut contour** |
| `0:3` | `0` | 2 | 60.75 | UNASSIGNED | MATERIAL_ISLAND | LOW | Layer 0 depth>=2 contour — nested island, needs review |
| `0:4` | `0` | 2 | 60.75 | UNASSIGNED | MATERIAL_ISLAND | LOW | Layer 0 depth>=2 contour — nested island, needs review |

---

## Topológia részletek

```
outer kontúr:       layer=0, depth=0, ring=0, area=597468 mm² (CUT_OUTER)
hole[0..1]:         layer=0, depth=1, ring=1..2
hole[2]:            layer=0, depth=1, ring=2, area=48mm² (very small)
hole[3] ⊂ hole[9]:  layer=0, depth=2, ring=3, area=60.75mm² (NESTED ISLAND)
hole[4] ⊂ hole[10]: layer=0, depth=2, ring=4, area=60.75mm² (NESTED ISLAND)
hole[5..6]:         layer=0, depth=1, ring=5..6
hole[7..8]:         layer=0, depth=1, ring=7..8
hole[9]:            layer=0, depth=1, ring=9 (the large outer frame)
hole[Gravír:0]:     layer=Gravír, depth=1, ARTIFACT (crosshair marker)
hole[Gravír:1]:     layer=Gravír, depth=1, ARTIFACT (crosshair marker)
```

---

## Döntési szabályok alkalmazása

### Rule A — Gravír closed contour, inner-like, no text → CUT_INNER
**NEM alkalmazható**, mert a Gravír kontúrok nem valódi zárt cut geometriák, hanem CIRCLE crosshair markerek. A `probe_layer_rings` által visszaadott 15-pontos "zárt" kontúrok valójában a circle arc-ok + line-ok részleges geometriai összeállításai, NEM cut kontúrok.

### Rule B — TEXT/MTEXT → MARKING
**Részben alkalmazható**, de a TEXT entity-k üresek (import placeholder), tehát ARTIFACT, nem MARKING.

### Rule C — depth=2 small/coincident/duplicate → ARTIFACT
A layer 0 depth=2 kontúrok (0:3 és 0:4) 60.75mm² területűek — ez kicsi, de nem elég kicsi az ARTIFACT threshold-hoz (<10mm²). **MATERIAL_ISLAND / UNKNOWN_REVIEW** megfelelőbb.

### Rule D — depth=2 genuine cut → MATERIAL_ISLAND
**Helyes** — a 0:3 és 0:4 kontúrok valódi zárt cut kontúrok nested island topológiában. Méretük (60.75mm²) és pozíciójuk alapján lehetséges material island, de a shapely korlátozás miatt `is_valid=False`. Ez a nested island topológia, ami az eredeti `preflight_review_required` ok.

---

## Döntési javaslat

### Jelenlegi helyzet
- `Lv8_11612_6db REV3.dxf` → `preflight_review_required`
- Review ok: `DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW`

### Javaslat: MARADJON `preflight_review_required`

**Indoklás:**
1. A Gravír layer CIRCLE markerek = ARTIFACT (HIGH confidence) — ezek NEM cut geometriák, de nem is zavarják a cut topológiát
2. A layer 0 depth=2 kontúrok = MATERIAL_ISLAND / UNKNOWN_REVIEW (LOW confidence) — valódi nested island, gyártási jelentése nem egyértelmű
3. A shapely `is_valid=False` korlátozás változatlan marad
4. A fájl nem blokkolt, de human review szükséges

### Nem javasolt változtatások
- **NE minősítsük accepted_for_import-nak** — a nested island topológia shapely korlátozás miatt problémás
- **NE módosítsuk a Gravír kontúrokat** — ezek gyártási segédgeometriák, nem cut
- **NE konvertáljuk ARTIFACT → MARKING-ra** — a TEXT entity-k üresek, nincs érdemi marking tartalom

### Következő javasolt lépés
Ha a jövőben szükséges:
- A Gravír layer ARTIFACT kontúrjait a preflight diagnosztikában explicit módon megjelölni (`GRAVIR_CROSSHAIR_MARKER` family)
- A nested island topológia kezelésére Policy B/C implementálása (flatten vagy multipolygon)
- Jelenleg: **T05k lezárva, nincs automatikus változtatás**

---

## Audit artefaktumok

- `tmp/reports/nfp_cgal_probe/t05k_lv8_11612_gravir_entity_audit.json` — gépi audit
- `tmp/reports/nfp_cgal_probe/t05k_lv8_11612_gravir_entity_audit.md` — emberi audit
- `tmp/reports/nfp_cgal_probe/t05k_lv8_11612_nested_contours_ascii.md` — ASCII debug export

---

## Módosított fájlok

### Új fájlok

**1. `scripts/experiments/audit_lv8_11612_gravir_entities.py`**
Új célzott audit script a Gravír layer entity-level vizsgálatához.
Funkciók:
- DXF entity-level adatgyűjtés (type, layer, color, geometry)
- Gravír layer CIRCLE/LINE/TEXT entity breakdown
- Zárt kontúr detektálás és topology depth számítás
- Contour classification (CUT_INNER / MARKING / ARTIFACT / MATERIAL_ISLAND / UNKNOWN_REVIEW)
- JSON + Markdown + ASCII debug export

### Nincs módosított fájl

A T05k során NEM módosult egyetlen meglévő forrásfájl sem.
- `dxf_preflight_acceptance_gate.py`: NEM módosult
- `dxf_preflight_role_resolver.py`: NEM módosult
- `dxf_preflight_inspect.py`: NEM módosult
- `importer.py`: NEM módosult

---

## Futtatott tesztek

```
tests/test_dxf_preflight_real_world_regressions.py   7/7 PASSED
tests/test_dxf_preflight_role_resolver.py             25/25 PASSED
--------------------------------------------------------------
Total                                               32/32 PASSED
```

Tesztek:
- LV8 nested hole demotion regression (T05j-ből)
- LV6 hole safety
- Normál hole + outer regression
- Multiple outer candidates safety
- TEXT/MTEXT exclusion
- Duplikált kontúrok
- Gravír TEXT non-blocking
- Minden T05i/T05j teszt átmegy

---

## Ismert limitációk

1. **Gravír layer zárt kontúr vs. partial arc assembly**
   A `probe_layer_rings` 15-pontos kontúrt ad vissza a Gravír layer circle+line assembly-jéből.
   Ez nem valódi zárt LWPOLYLINE, hanem a circle arc-ok poligonizált nyomvonala.
   Azért "zárt" a kontúr, mert a circle teljes 360°-os, de a körmintázat (crosshair) nem cut geometria.

2. **Shapely is_valid nem változik**
   A nested hole topológia továbbra is `is_valid=False`-t ad.
   Ez design korlátozás, nem bug.

3. **TEXT entity üres**
   A 8db Gravír TEXT entity mind üres (`text=""`).
   Ez import artifact, nem valódi annotáció.

4. **Audit script érvényessége**
   Az `audit_lv8_11612_gravir_entities.py` script specifikusan erre a DXF-re lett írva.
   Más fájlokra nem általánosítható.

---

## Szigorú tiltások betartása

- ✅ T08 nem indítva
- ✅ CGAL production integráció nincs
- ✅ Production Dockerfile nincs módosítva
- ✅ Worker runtime nincs módosítva
- ✅ DXF nem minősítve accepted_for_import-nak
- ✅ Gravír layer kontúrok nem törölve csendben
- ✅ CUT kontúr nem átminősítve MARKING-ra bizonyíték nélkül
- ✅ TEXT/MTEXT nem konvertálva cut geometriává
- ✅ Nincs silent fallback
- ✅ Eredeti DXF nem módosítva destruktívan
- ✅ LV8 többi fájl nem romlott (10 accepted, 1 review_required, 0 rejected)
