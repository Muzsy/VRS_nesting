# T05j — LV8 Geometry Validator: Nested Hole Policy

**Státusz:** PASS

**Dátum:** 2026-05-05

**Task referencia:** T05i PARTIAL → T05j

---

## Választott Policy

**Policy A — UNSUPPORTED_REVIEW**

A nested hole / island-within-hole topológia esetén a DXF **preflight_review_required** státuszt kap (nem `preflight_rejected`, és nem `accepted_for_import`).

**Policy indoklása:**
- A shapely `is_valid` validáció elutasítja a hole-within-hole (nested island) topológiát, noha ez érvényes GIS geometria.
- A geometria az importeren sikeresen átmegy (az importer nem használ `is_valid` checket).
- A nested island topológia gyártási jelentése nem egyértelmű: lehet valódi material island, gravírozási minta, vagy import artifact.
- Az **accepted_for_import** csak akkor lenne helyes, ha a geometria jelentése egyértelműen tisztázott — ezt emberi review-nak kell eldöntenie.
- A **preflight_rejected** generic `GEO_TOPOLOGY_INVALID` üzenettel nem segít az operátornak, és nem tükrözi a valódi problémát.

---

## Root Cause

A `dxf_geometry_import.py` shapely-based validációja a `build_canonical_geometry_probe_from_part_raw` függvényben meghívja a `Polygon(outer, holes)` konstruktort, ami **elfogadja** a nested holes paramétert, de az eredmény `is_valid` property-je `False`-t ad vissza `"Holes are nested"` üzenettel.

Ez nem a DXF geometria tényleges invaliditása — a shapely belső korlátozása, ami a hole-within-hole struktúrát nem támogatja.

A korábbi T05i megoldás (safe flatten LV6-on) nem oldja meg az LV8-at, mert:
- LV6: nincs nested hole topológia
- LV8: LV8_11612_6db REV3.dxf 2 szintű nested topology-vel rendelkezik (depth=2)

---

## Topológia részletek (LV8_11612_6db REV3.dxf)

```
outer kontúr:        layer=0,        depth=0, ring=0, area=173600 mm²
hole[0..8]:          layer=0,        depth=1, ring=1..9
  hole[3] ⊂ hole[9]: layer=0,        depth=2  ← NESTED ISLAND
  hole[4] ⊂ hole[10]: layer=0,       depth=2  ← NESTED ISLAND
hole[9]:             layer=Gravír,   depth=1
hole[10]:            layer=Gravír,   depth=1
```

- 12 kontúr összesen
- 11 lyuk (ebből 2 közvetlenül another hole-on belül)
- importer_probe: `is_pass=true`, outer=1, hole_count=11
- validator_probe: `is_pass=false`, error: `Holes are nested`

---

## Módosított fájlok

### 1. `api/services/dxf_preflight_acceptance_gate.py`

**Módosítás 1 — `_resolve_outcome` (Policy A implementáció):**
Ahol a `validator_probe` errors mind `GEO_TOPOLOGY_INVALID` + `"Holes are nested"` üzenetek, ott az outcome nem `preflight_rejected`, hanem `preflight_review_required` + sentinel reason.

Guard feltétel: **csak akkor** demót, ha minden validator hiba ilyen.
Más geometry hibák (pl. self-intersection) továbbra is blokkolnak.

**Módosítás 2 — `_collect_blocking_reasons` (korábban T05i):**
`validator_probe_rejected` block eltávolítva (lines 334–344), mert a validator probe status kizárólag `_resolve_outcome`-ban kezelve.

### 2. `api/services/dxf_preflight_diagnostics_renderer.py`

**Módosítás — `_build_issue_summary` (391–403 után):**
A renderer most propagálja a `acceptance_gate_result["review_required_reasons"]`-ból a `validator_probe` és `importer_probe` source-ú bejegyzéseket a unified issue listára. Ez előfeltétele annak, hogy a nested island issue megjelenjen a diagnosztika outputban.

### 3. `tests/test_dxf_preflight_real_world_regressions.py`

Új teszt: `test_real_world_lv8_nested_hole_demoted_to_review_required()`
- Ellenőrzi: outcome=`preflight_review_required`
- Ellenőrzi: review reason family=`DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW`
- Ellenőrzi: importer_probe `is_pass=true`
- Ellenőrzi: hole_count=11

### 4. `tests/fixtures/dxf_preflight/real_world/Lv8_11612_6db REV3.dxf`

Új fixture (791 KB) — a problémás LV8 fájl másolata regression teszthez.

---

## Before / After

### LV6 (kontroll)
| | Előtte | Utána |
|---|---|---|
| accepted_for_import | 11 | 11 |
| preflight_review_required | 0 | 0 |
| preflight_rejected | 0 | 0 |

**Nincs változás** — LV6-on nincs nested hole topológia.

### LV8 (12 fájl)
| | Előtte | Utána |
|---|---|---|
| accepted_for_import | 10 | 10 |
| preflight_review_required | 0 | 1 (+1) |
| preflight_rejected | 1 | 0 (-1) |

### Lv8_11612_6db REV3.dxf
| | Előtte | Utána |
|---|---|---|
| Státusz | `preflight_rejected` | `preflight_review_required` |
| Blokkoló ok | `GEO_TOPOLOGY_INVALID: Holes are nested` | (nincs) |
| Review reason | (nincs) | `DXF_PREFLIGHT_NESTED_ISLAND_REQUIRES_MANUAL_REVIEW` |
| Importer | IMPORT_OK_WITH_HOLES | IMPORT_OK_WITH_HOLES |
| Geometry | érvényes, 1 outer + 11 hole | érvényes, 1 outer + 11 hole |

---

## Futtatott tesztek

```
tests/test_dxf_preflight_role_resolver.py         25/25 PASSED
tests/test_dxf_preflight_real_world_regressions.py  7/7 PASSED
---------------------------------------------------------------
Total                                           32/32 PASSED
```

Tesztek:
- LV8 nested hole demotion regression (új)
- LV6 hole safety (T05i-ból)
- Normál hole + outer regression
- Multiple outer candidates safety
- TEXT/MTEXT exclusion
- Duplikált kontúrok
- Minden T05i-beli teszt átmegy

---

## Audit fájlok

- `tmp/reports/nfp_cgal_probe/t05j_lv8_11612_nested_hole_audit.json` — gépi audit
- `tmp/reports/nfp_cgal_probe/t05j_lv8_11612_nested_hole_audit.md` — emberi audit

---

## Ismert limitációk

1. **Shapely is_valid nem módosul** — a javítás nem javítja a shapely viselkedését. A nested holes továbbra is `is_valid=False`-t adnak. Ez design decision, nem bug.

2. **Nem accepted_for_import** — a nested island fájl nem lesz automatikusan accepted. Ha a jövőben kiderül, hogy ezek a kontúrok biztonságosan flatten-elhetők vagy multipolygonként kezelhetők, Policy B vagy C implementálható. Jelenleg Policy A a konzervatív választás.

3. **A Gravír layer kontúrjai is nestedek** — a 2 depth-2 kontúr egyike a Gravír layer-en van. Ez további kézi review-t igényelhet gyártási szempontból.

4. **Audit script output path** — a `Saved:` sorok a `tmp/reports/nfp_cgal_probe/` path-ot használják, ami kozmetikai inkonzisztencia (LV6 run felülírja az LV8-at ugyanabban a mappában).

---

## Szigorú tiltások betartása

- ✅ T08 nem indítva
- ✅ CGAL production integráció nincs
- ✅ Production Dockerfile nincs módosítva
- ✅ Worker runtime nincs módosítva
- ✅ Acceptance gate nem lazított vakon
- ✅ DXF nem minősítve accepted_for_import-nak, ha a geometria jelentése nem tiszta
- ✅ Nested island kontúrok nem törölve csendben
- ✅ Gyártási cut geometria nem módosítva destruktívan
- ✅ Nincs silent fallback
- ✅ TEXT/MTEXT nem vesz részt cut contour döntésben

---

## Következő javasolt lépés

**T05k — LV8 Gravír Layer Geometry Review**

A LV8_11612 Gravír layer-én lévő 2 nested island kontúr gyártási jelentésének kézi ellenőrzése. Ha kiderül, hogy:
- valódi gravír/minta → TEXT/MARKING role, nem cut
- import artifact → törölhető
- valódi material island → `accepted_for_import` lehet

Ehhez meg kell vizsgálni a Gravír kontúrok entity type-jait és kontextusát.
