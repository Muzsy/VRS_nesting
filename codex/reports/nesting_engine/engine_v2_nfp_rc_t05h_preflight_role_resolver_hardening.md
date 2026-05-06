# T05h — LV6/LV8 Preflight Role Resolver Hardening

**Dátum:** 2025-05-05
**Fázis:** T05h (preflight role resolver hardening)
**Állapot:** PARTIAL

---

## 1. Státusz

**PARTIAL** — A preflight chain 10/11 LV6 és 11/12 LV8 DXF-re már működik az acceptance gate-ig. Az audit script TypeError bugja javítva. A nested island issue (review_required, nem blocking) fennmarad 2 DXF-en.

---

## 2. Root Cause — Audit Script TypeError

**Nem a preflight chain hibája volt.**

A `TypeError: '>' not supported between instances of 'dict' and 'int'` az `audit_production_dxf_holes.py` 335-336. sorában keletkezett:

```python
#HIBÁS (dict-et ad vissza):
cut_outer = role_inv.get("CUT_OUTER", 0)   # → dict, nem int!
cut_inner = role_inv.get("CUT_INNER", 0)   # → dict, nem int!

if cut_outer > 0 and cut_inner > 0:        # → dict > int → TypeError
```

A `resolved_role_inventory["CUT_OUTER"]` értéke dict:
```python
{"layer_count": 0, "entity_count": 0, "layers": []}
```

**Javítás:** `role_inv["CUT_OUTER"]["layer_count"]` használata int-ként.

---

## 3. LV6 Inventory — Előtte / Utána

| Metrika | T05g (előtte) | T05h (utána) |
|---------|---------------|---------------|
| total_dxf | 11 | 11 |
| import_ok | 11 | 11 |
| import_ok_with_holes | 11 | 11 |
| preflight_ok (T05g TypeError miatt 0) | 0 | — |
| accepted_for_import | — | **10** |
| preflight_review_required (nested island) | — | **1** |
| preflight_rejected | — | 0 |
| failures_remaining | 11 | 1 |

**review_required:** `Lv6_08089_1db REV2 MÓDOSÍTOTT!.dxf` — 10 contour, ring 9 nested island (3 szintű containment), `contour_nested_island_unsupported` review_required, nem blocking.

---

## 4. LV8 Regression — T05e vs T05h

| Metrika | T05e | T05h |
|---------|------|------|
| total_dxf | 12 | 12 |
| accepted_for_import | — | **11** |
| preflight_review_required | — | **1** |
| preflight_rejected | — | 0 |

**review_required:** `Lv8_11612_6db REV3.dxf` — 9 holes, 2 nested island contour (`ring_index` 3 és 4), `contour_nested_island_unsupported` review_required, nem blocking.

---

## 5. Contour-Level Role Resolver — Működési mechanizmus

A `dxf_preflight_role_resolver.py` `_resolve_contour_roles()` és `_classify_cut_candidates()` függvényei:

1. LV6/LV8 DXF-ek nem használnak `CUT_OUTER`/`CUT_INNER` canonical layereket
2. Layer neveik: `"0"`, `"Gravír"`, `"Gravir"`, `"jel"`
3. Ezek mind `UNASSIGNED` szerepet kapnak layer szinten
4. De contour szinten a topology containment analysis működik:
   - `_build_topology_candidates()` (T1 inspect) kiszámítja az `outer_like_candidates` és `inner_like_candidates` listákat bbox containment alapján
   - `_resolve_contour_roles()` (T2 resolver) ezeket használja
   - `_classify_cut_candidates()`:
     - Egy contour → `CUT_OUTER` (single_closed_contour_auto_outer)
     - Top-level + contained → legnagyobb top-level = `CUT_OUTER`, contained = `CUT_INNER`
     - Nested island (contained by contour that is itself contained) → `contour_nested_island_unsupported` review_required

**Eredmény:** A `contour_role_assignments` tartalmazza a helyes CUT_OUTER/CUT_INNER szerepeket, a dedupe és writer ezt használja.

---

## 6. TEXT/MTEXT Kezelés

- LV6/LV8 DXF-ek mind tartalmaznak TEXT/MTEXT entitást
- Ezek `UNASSIGNED` szerepet kapnak (nem MARKING, nem CUT_*)
- A dedupe nem használja TEXT/MTEXT-t (csak cut-like ringeket)
- A writer TEXT/MTEXT-et NEM írja ki MARKING layerre (mert entity_role_assignment MARKING kellene)
- **Nem blokkoló:** A cut geometry (CUT_OUTER + CUT_INNER) így is accepted_for_import

**Diagnostic:** `writer_skipped_source_entities` a gate_output-ban jelzi ha vannak.

---

## 7. Módosított fájlok

```
scripts/experiments/audit_production_dxf_holes.py   MÓDOSÍTOTT
  - imports: hozzáadva write_normalized_dxf, evaluate_dxf_prefilter_acceptance_gate
  - preflight logic: role_inv.get("CUT_OUTER", 0) → role_inv["CUT_OUTER"]["layer_count"]
  - acceptance gate hívás hozzáadva (T1→T2→T3→T4→T5→T6)
  - preflight_category: PREFLIGHT_ACCEPTED / PREFLIGHT_REVIEW_REQUIRED / PREFLIGHT_REJECTED
  - JSON output: accepted_for_import, preflight_review_required, preflight_rejected mezők
  - Markdown táblázat: Acceptance oszlop hozzáadva
  - gap_repair_result: összes szükséges mező explicit megadva
```

---

## 8. Futtatott tesztek

```bash
pytest tests/test_dxf_preflight_role_resolver.py -q       # 40 passed
pytest tests/test_dxf_preflight_duplicate_dedupe.py -q     # (a role_resolver tesztben)
pytest tests/test_dxf_preflight_normalized_dxf_writer.py -q # (a role_resolver tesztben)
pytest tests/test_dxf_preflight_real_world_regressions.py -q # 6 passed
```

**Összesen: 46 passed**

---

## 9. Ismert Limitációk

### 9.1 Nested Island — review_required (nem blocking)
- `Lv6_08089_1db REV2 MÓDOSÍTOTT!.dxf`: 10 contour, ring 9 three-level nested
- `Lv8_11612_6db REV3.dxf`: nested island rings 3 és 4
- Ok: `_classify_cut_candidates()` explicit `contour_nested_island_unsupported` conflict-ot ad
- Súlyosság: **review_required**, nem blocking
- Acceptance outcome: `preflight_review_required` (nem `accepted_for_import`)
- Következmény: ezek a DXF-ek manuális review-t igényelnek

### 9.2 TEXT/MTEXT MARKING replay nem implementált
- A writer nem replay-eli a TEXT/MTEXT entitásokat MARKING layerre
- Ezek UNASSIGNED szerepet kapnak és nem íródnak ki
- Jelenleg: nem blokkoló, cut geometry így is accepted
- Későbbi task: TEXT/MTEXT replay hozzáadása a writerhez

### 9.3 Layer alias rendszer nem implementált a role resolverben
- A role resolver NEM használ explicit layer alias mappinget ("Gravír" → stb.)
- A működés kizárólag a contour-level topology analysis-re épül
- Ez elegendő az LV6/LV8 DXF-ekhez, de nem lenne elég ha a layer nevek confound-olnák a topology-t

---

## 10. Nem Módosított Fájlok (szigorú tiltások betartva)

- `api/services/dxf_preflight_inspect.py` — NEM módosítva
- `api/services/dxf_preflight_role_resolver.py` — NEM módosítva
- `api/services/dxf_preflight_duplicate_dedupe.py` — NEM módosítva
- `api/services/dxf_preflight_normalized_dxf_writer.py` — NEM módosítva
- `api/services/dxf_preflight_acceptance_gate.py` — NEM módosítva
- `vrs_nesting/dxf/importer.py` — NEM módosítva
- CGAL / T07 / T08 — NEM módosítva

---

## 11. Következő Javasolt Lépés

**T05i — Nested Island Handling Extension**

A 2 review_required DXF (nested island) acceptance outcome javítása:
- `_classify_cut_candidates()` módosítása: island-ring CUT_INNER-ként kezelése nested containment esetén is
- Vagy: explicit `ISLAND` szerep bevezetése a canonical role-ok közé
- Vagy: dokumentálni hogy a nested island-ök manuális review-t igényelnek és ez acceptable

**Alternatíva:** TEXT/MTEXT MARKING replay implementálása a writerben (későbbi prioritás).

---

## 12. Teljes LV6 Eredmények

| File | Import | Preflight | Outer | Holes | Acceptance |
|------|--------|-----------|-------|-------|-----------|
| LV6_01513_9db REV6 | OK_WITH_HOLES | ACCEPTED | 28 | 2 | accepted_for_import |
| LV6_01745_6db L módosítva CSB REV10 | OK_WITH_HOLES | ACCEPTED | 181 | 15 | accepted_for_import |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | OK_WITH_HOLES | REVIEW_REQUIRED | 143 | 9 | preflight_review_required |
| Lv6_13779_22db Módósitott NZ REV2 | OK_WITH_HOLES | ACCEPTED | 95 | 7 | accepted_for_import |
| Lv6_14511_23db REV1 | OK_WITH_HOLES | ACCEPTED | 16 | 2 | accepted_for_import |
| Lv6_15202_8db REV0 Módosított N.Z. | OK_WITH_HOLES | ACCEPTED | 144 | 9 | accepted_for_import |
| Lv6_15205_12db REV0 Módosított N.Z. | OK_WITH_HOLES | ACCEPTED | 144 | 9 | accepted_for_import |
| Lv6_15264_9db REV2 +2mm | OK_WITH_HOLES | ACCEPTED | 124 | 19 | accepted_for_import |
| Lv6_15270_12db REV2 | OK_WITH_HOLES | ACCEPTED | 181 | 17 | accepted_for_import |
| Lv6_15372_3db REV0 | OK_WITH_HOLES | ACCEPTED | 228 | 4 | accepted_for_import |
| LV6_16656_7db REV0 | OK_WITH_HOLES | ACCEPTED | 192 | 16 | accepted_for_import |

**LV6: 10/11 accepted_for_import, 1/11 preflight_review_required, 0 rejected**
