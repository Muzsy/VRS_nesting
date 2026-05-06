# T05i — Nested Island Handling Extension

**Dátum:** 2025-05-05
**Fázis:** T05i (nested island safe flatten)
**Állapot:** PARTIAL

---

## 1. Státusz

**PARTIAL** — A nested island safe flatten stratégia működik LV6-on (11/11 accepted). LV8 esetében a role resolver szintén helyes (0 review_required), de a geometry validator T06 szinten `GEO_TOPOLOGY_INVALID` hiba miatt `preflight_rejected` állapotban marad. Ez nem a role resolver hibája, és a T05i hatókörén kívüli probléma.

---

## 2. Választott stratégia

**Safe flatten** — A nested island kontúrok (depth >= 2) `CUT_INNER` szerepet kapnak, nem `review_required`-t.

Indoklás:
- Mindkét problémás DXF (LV6 és LV8) single-outer topológiájú — nincs több separate outer candidate
- A containment chain tiszta: outer → hole → island (acyclic)
- A safe flatten a dedupe/writer/importer láncon keresztül érvényes (LV6 accepted_for_import)
- LV8: a role resolver correct, de a geometry validator T06 szinten utasítja el (`GEO_TOPOLOGY_INVALID: Holes are nested`)

---

## 3. Modifikáció: `_classify_cut_candidates` (T02)

**Fájl:** `api/services/dxf_preflight_role_resolver.py`

**Változás:** A `contour_nested_island_unsupported` conflict emisszió + `continue` helyett, minden contained contour (beleértve a depth >= 2 island-eket is) `CUT_INNER` assignment-et kap.

**Előtte:**
```python
if is_nested:
    _emit_conflict(
        review_required_candidates, blocking_conflicts,
        family="contour_nested_island_unsupported", ...
    )
    continue  # island kimarad az assignmentből → UNASSIGNED
assignments.append({..., "canonical_role": "CUT_INNER", ...})
```

**Utána:**
```python
# is_nested változó marad, de nem blokkol
assignments.append({
    "canonical_role": "CUT_INNER",
    "decision_source": "contour_topology_auto_nested_flattened",
    "nested_island_original_parent": str(direct_outer_in_candidates[0]) if is_nested else None,
    ...
})
```

**Döntési fa:**
- depth 0 (top-level, nincs parent) → `CUT_OUTER`
- depth >= 1 (hole vagy island) → `CUT_INNER`

---

## 4. LV6 / LV8 Before/After

### LV6

| Metrika | T05h (előtte) | T05i (utána) |
|---------|----------------|---------------|
| total_dxf | 11 | 11 |
| accepted_for_import | 10 | **11** |
| preflight_review_required | **1** | **0** |
| preflight_rejected | 0 | 0 |

**Módosult:** `Lv6_08089_1db REV2 MÓDOSÍTOTT!.dxf` — review_required → accepted_for_import

### LV8

| Metrika | T05h (előtte) | T05i (utána) |
|---------|----------------|---------------|
| total_dxf | 12 | 12 |
| accepted_for_import | 11 | **10** |
| preflight_review_required | **1** | **0** |
| preflight_rejected | 0 | **1** |

**Módosult:** `Lv8_11612_6db REV3.dxf` — review_required → preflight_rejected
- A role resolver most helyes: 0 review_required conflicts
- De T06 geometry validator: `GEO_TOPOLOGY_INVALID: Holes are nested[4089.13 1685.78]`
- Ez független a role resolver-től — a normalizált DXF geometriája önmagában invalid a validator szerint

---

## 5. Problémás fájlok részletes eredménye

### LV6 — Lv6_08089_1db REV2 MÓDOSÍTOTT!.dxf

| Mező | Érték |
|------|-------|
| topology | 1 outer (depth 0), 5 holes (depth 1), 4 islands (depth 2) |
| role_before | review_required (contour_nested_island_unsupported) |
| role_after | accepted_for_import |
| outer role | CUT_OUTER |
| inner roles | CUT_INNER (mind a 9 contour, beleértve 4 island-t is) |
| holes by importer | 9 |
| decision_source | contour_topology_auto_nested_flattened |

**4 islands mind ugyanabban a hole-ban (ring 9 és ring 6) — single-hole island cluster, nem több alkatrész.**

### LV8 — Lv8_11612_6db REV3.dxf

| Mező | Érték |
|------|-------|
| topology | 1 outer (depth 0), 9 holes (depth 1), 2 islands (depth 2) |
| role_before | review_required (contour_nested_island_unsupported) |
| role_after | preflight_rejected (geometry validator, NOT role resolver) |
| outer role | CUT_OUTER |
| inner roles | CUT_INNER (mind a 11 contour) |
| holes by importer | 11 |
| decision_source | contour_topology_auto_nested_flattened |
| validator error | GEO_TOPOLOGY_INVALID: Holes are nested |

**2 islands különböző hole-okban (ring 9 → Gravír:0 és Gravír:1). A validator T06 szinten utasítja el.**

---

## 6. Nested Topology Dump

Saved to:
- `tmp/reports/nfp_cgal_probe/nested_island_topology_lv6.json`
- `tmp/reports/nfp_cgal_probe/nested_island_topology_lv8.json`

**LV6 topology összefoglaló:**
- Ring 6: depth 0 (outer, area 135233.47 mm²)
- Rings 4,5,7,8,9: depth 1 (holes, area 58-10757 mm²)
- Rings 0,1,2,3: depth 2 (islands in hole 6 and 9, area 66 mm² each, center (0,0) — coincident)

**LV8 topology összefoglaló:**
- Ring 9: depth 0 (outer, area 597467.96 mm²)
- Rings 0,1,2,5,6,7,8 (layer 0) + Gravír:0, Gravír:1: depth 1 (holes)
- Rings 3,4: depth 2 (islands — island 3 in hole 9+Gravír:0, island 4 in hole 9+Gravír:1)

---

## 7. Módosított fájlok

```
api/services/dxf_preflight_role_resolver.py      MÓDOSÍTOTT
  - _classify_cut_candidates(): is_nested ágban continue+conflict helyett CUT_INNER assignment
  - decision_source: "contour_topology_auto_nested_flattened"
  - új mező: nested_island_original_parent

tests/test_dxf_preflight_role_resolver.py        MÓDOSÍTOTT
  - +test_contour_resolver_nested_island_flattened_to_cut_inner()

scripts/experiments/debug_nested_island_contours.py  ÚJ
  - Nested island topology dump script
  - Output: tmp/reports/nfp_cgal_probe/nested_island_topology_lv6/lv8.json

scripts/experiments/verify_nested_flatten.py       ÚJ
  - End-to-end verify script (T1→T6 chain)
```

---

## 8. Futtatott tesztek

```bash
PYTHONPATH=. pytest tests/test_dxf_preflight_role_resolver.py -q       # 25 passed (was 24)
PYTHONPATH=. pytest tests/test_dxf_preflight_real_world_regressions.py -q # 6 passed
```

**Összesen: 31 passed**

---

## 9. Nem módosított fájlok (szigorú tiltások betartva)

```
api/services/dxf_preflight_inspect.py         NEM módosítva
api/services/dxf_preflight_duplicate_dedupe.py NEM módosítva
api/services/dxf_preflight_normalized_dxf_writer.py  NEM módosítva
api/services/dxf_preflight_acceptance_gate.py  NEM módosítva
vrs_nesting/dxf/importer.py                   NEM módosítva
CGAL / T07 / T08                              NEM módosítva
Production Dockerfile / worker runtime          NEM módosítva
```

---

## 10. Ismert limitációk

### 10.1 LV8 geometry validator rejection (nem role resolver probléma)

`Lv8_11612_6db REV3.dxf` továbbra is `preflight_rejected`:
- Role resolver: helyes, 0 review_required
- Geometry validator (T06): `GEO_TOPOLOGY_INVALID: Holes are nested`
- A validator a normalizált DXF-t közvetlenül vizsgálja és nested hole-topológiát talál
- Root cause: a shapely-based validator nem támogatja a nested hole-okat (hole-on-belthin island = cut path, de a validator ezt nem fogadja el)
- Következmény: ez a DXF T05i hatókörén kívüli javítást igényel

### 10.2 TEXT/MTEXT MARKING replay nem implementált
- A writer nem replay-eli a TEXT/MTEXT entitásokat MARKING layerre
- Nem blokkoló: cut geometry accepted_for_import

### 10.3 Island reprezentáció korlát
- A jelenlegi PartRaw/importer modell nem tud valódi island-within-hole gyártási geometriát külön reprezentálni
- A safe flatten "megnyomja" az island-t a hole-ba (CUT_INNER-ként kezeli), ami a legtöbb gyártási esetben megfelelő

---

## 11. Következő javasolt lépés

**T05j — LV8 geometry validator nested hole policy**

A `GEO_TOPOLOGY_INVALID: Holes are nested` hiba LV8-on való kezelése a geometry validator szintjén — nem a role resolverben. Ha a nesting engine képes valódi island reprezentációra, a validator policy módosítása szükséges (de ez T08-as integráció, és a feladat explicit tiltja a T08 indítását).
