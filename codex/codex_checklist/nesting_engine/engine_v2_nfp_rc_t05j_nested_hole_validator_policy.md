# T05j — Nested Hole Validator Policy Checklist

## Státusz: ✅ COMPLETE

---

## Beadandó Items

- [x] LV8 GEO_TOPOLOGY_INVALID reprodukálva
  - LV8_11612_6db REV3.dxf: `GEO_TOPOLOGY_INVALID: Holes are nested`
  - Shapely `is_valid=False` "Holes are nested" okozza

- [x] nested topology/source entity audit elkészült
  - JSON: `tmp/reports/nfp_cgal_probe/t05j_lv8_11612_nested_hole_audit.json`
  - MD: `tmp/reports/nfp_cgal_probe/t05j_lv8_11612_nested_hole_audit.md`
  - 2 depth-2 kontúr azonosítva (hole[3]⊂hole[9], hole[4]⊂hole[10])

- [x] root cause dokumentálva
  - Root cause: shapely Polygon is_valid elutasítja hole-within-hole topológiát
  - Nem a DXF geometria tényleges invaliditása
  - 3 szintű topology: depth=0 (outer), depth=1 (9 holes), depth=2 (2 nested holes)

- [x] policy kiválasztva
  - **Policy A — UNSUPPORTED_REVIEW**
  - Nem accepted_for_import (geometria jelentése nem tiszta)
  - Nem preflight_rejected (generic GEO_TOPOLOGY_INVALID nem segít)
  - HANEM: preflight_review_required + `DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW`

- [x] generic preflight_rejected megszűnt vagy indokoltan megmaradt
  - LV8_11612: `preflight_rejected` → `preflight_review_required`
  - Generic `GEO_TOPOLOGY_INVALID` helyett specifikus nested island reason
  - Guard: csak demót, ha MINDEN validator hiba "Holes are nested"

- [x] Lv8_11612 explicit regression eredmény dokumentálva
  - Új fixture: `tests/fixtures/dxf_preflight/real_world/Lv8_11612_6db REV3.dxf`
  - Új teszt: `test_real_world_lv8_nested_hole_demoted_to_review_required()`
  - Teszt ellenőrzi: outcome, review reason family, importer is_pass, hole_count

- [x] LV6 regression nem romlott
  - LV6: 11/11 accepted_for_import (nincs változás)
  - LV6-on nincs nested hole topológia

- [x] normál hole-os DXF regression nem romlott
  - LV8_07919, LV8_07920, LV8_07921, LV8_15348, LV8_15435: mind accepted_for_import marad

- [x] tests PASS
  - `tests/test_dxf_preflight_role_resolver.py`: 25/25
  - `tests/test_dxf_preflight_real_world_regressions.py`: 7/7
  - Összesen: 32/32 PASSED

- [x] nincs CGAL production integráció
  - CGAL probe csak fejlesztői/eszköz, nincs módosítva

- [x] nincs T08 indítás
  - T08 nem indítva, nincs engine_v2 integráció

---

## Módosított fájlok

1. `api/services/dxf_preflight_acceptance_gate.py`
   - `_resolve_outcome`: Policy A demotion logika
   - `_collect_blocking_reasons`: `validator_probe_rejected` block eltávolítva

2. `api/services/dxf_preflight_diagnostics_renderer.py`
   - `_build_issue_summary`: `review_required_reasons` propagálás a unified issue listára

3. `tests/test_dxf_preflight_real_world_regressions.py`
   - Új teszt: `test_real_world_lv8_nested_hole_demoted_to_review_required()`

4. `tests/fixtures/dxf_preflight/real_world/Lv8_11612_6db REV3.dxf`
   - Új fixture (791 KB)

---

## Before / After Summary

| Mérés | Előtte | Utána |
|---|---|---|
| LV6 accepted | 11/11 | 11/11 |
| LV8 accepted | 10/12 | 10/12 |
| LV8 review_required | 0/12 | 1/12 |
| LV8 rejected | 1/12 | 0/12 |
| LV8_11612 státusz | `preflight_rejected` | `preflight_review_required` |
| LV8_11612 ok | GEO_TOPOLOGY_INVALID | NESTED_ISLAND_REQUIRES_MANUAL_REVIEW |

---

## Blockerek / Limitációk

- **Nincs új blocker** — a megoldás kész
- LV8_11612 jelenleg `preflight_review_required` — emberi review szükséges a végleges döntéshez
- Shapely `is_valid` korlátozás továbbra is fennáll (design, nem bug)

---

## Következő lépés

**T05k — LV8 Gravír Layer Geometry Review**

A LV8_11612 Gravír layer-én lévő 2 nested island kontúr gyártási jelentésének kézi ellenőrzése.
