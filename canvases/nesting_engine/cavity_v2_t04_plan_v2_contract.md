# Cavity v2 T04 — Cavity plan v2 contract bevezetése

## Cél

Bevezeti a `cavity_plan_v2` schema-t: új konstansok, adatstruktúrák és dokumentáció. A `result_normalizer.py` `_load_enabled_cavity_plan()` függvénye elfogadja a `"cavity_plan_v2"` version stringet (de a tényleges rekurzív flatten logika T07-ben jön). Elkészül a `docs/nesting_engine/cavity_prepack_contract_v2.md` dokumentum.

---

## Miért szükséges

A v2 rekurzív cavity tree csak akkor implementálható biztonságosan, ha a contract sémája előre definiált és a normalizer már ismeri a v2 version stringet. T04 nélkül T06 (rekurzív algoritmus) és T07 (normalizer flatten) nem tudja, milyen struktúrát kell gyártania illetve elfogadnia.

---

## Érintett valós fájlok

### Módosítandó:
- `worker/cavity_prepack.py` — új `_PLAN_VERSION_V2` konstans, `_empty_plan_v2()`, `_PlacementTreeNode` dataclass
- `worker/result_normalizer.py` — `_load_enabled_cavity_plan()` v2 version string elfogadása (részleges)

### Létrehozandó:
- `docs/nesting_engine/cavity_prepack_contract_v2.md` — teljes v2 contract dokumentum

### Olvasandó (kontextus):
- `docs/nesting_engine/cavity_prepack_contract_v1.md` — a v1 referencia
- `worker/cavity_prepack.py` — meglévő `_PLAN_VERSION`, `_empty_plan()`

---

## Nem célok / scope határok

- **Nem** implementálja a rekurzív cavity fill algoritmust (az T06).
- **Nem** implementálja a v2 flatten logikát a normalizerben (az T07).
- **Nem** módosítja a `build_cavity_prepacked_engine_input()` main flow-ját (az T06).
- A v1 contract és a v1-et használó kódok változatlanok maradnak.

---

## Részletes implementációs lépések

### 1. `worker/cavity_prepack.py`: v2 konstansok és dataclass

```python
_PLAN_VERSION_V2 = "cavity_plan_v2"

@dataclass(frozen=True)
class _PlacementTreeNode:
    node_id: str
    part_revision_id: str
    instance: int
    kind: str  # "top_level_virtual_parent" | "internal_cavity_child"
    parent_node_id: str | None
    parent_cavity_index: int | None
    x_local_mm: float
    y_local_mm: float
    rotation_deg: int
    placement_origin_ref: str
    children: tuple  # tuple[_PlacementTreeNode, ...] — rekurzív

def _empty_plan_v2(*, enabled: bool, max_cavity_depth: int = 3) -> dict[str, Any]:
    return {
        "version": _PLAN_VERSION_V2,
        "enabled": bool(enabled),
        "policy": {
            "mode": "recursive_cavity_prepack" if enabled else "disabled",
            "top_level_hole_policy": "solidify_parent_outer",
            "child_hole_policy": "recursive_outer_proxy_with_exact_export",
            "quantity_allocation": "internal_first_scored",
            "max_cavity_depth": int(max_cavity_depth),
        },
        "virtual_parts": {},
        "placement_trees": {},
        "instance_bases": {},
        "quantity_delta": {},
        "diagnostics": [],
        "summary": {},
    }
```

Exportáld: `__all__` bővítése `_PLAN_VERSION_V2` és `_PlacementTreeNode` nélkül (belső), de a funkció `_empty_plan_v2` belső maradjon.

### 2. `worker/result_normalizer.py`: `_load_enabled_cavity_plan()` frissítése

**Jelenlegi állapot (sor ~244-248):**
```python
version = str(plan.get("version") or "").strip()
if version != "cavity_plan_v1":
    raise ResultNormalizerError(f"invalid cavity_plan version: {version or '<empty>'}")
return plan
```

**Várt állapot:**
```python
version = str(plan.get("version") or "").strip()
if version not in ("cavity_plan_v1", "cavity_plan_v2"):
    raise ResultNormalizerError(f"invalid cavity_plan version: {version or '<empty>'}")
return plan
```

Megjegyzés: A v2 plan visszatér, de a `_normalize_solver_output_projection_v2()` a `version` mező alapján dönti el a feldolgozási módot (T07 implementálja a v2 ágat).

### 3. `docs/nesting_engine/cavity_prepack_contract_v2.md` megírása

A dokumentum tartalmazza:

**a) Schema top-level:**
```json
{
  "version": "cavity_plan_v2",
  "enabled": true,
  "policy": {
    "mode": "recursive_cavity_prepack",
    "top_level_hole_policy": "solidify_parent_outer",
    "child_hole_policy": "recursive_outer_proxy_with_exact_export",
    "quantity_allocation": "internal_first_scored",
    "max_cavity_depth": 3
  },
  "virtual_parts": { ... },
  "placement_trees": { ... },
  "instance_bases": { ... },
  "quantity_delta": { ... },
  "diagnostics": [ ... ],
  "summary": { ... }
}
```

**b) `placement_trees` rekurzív node struktúra:**

```json
{
  "__cavity_composite__A__000000": {
    "node_id": "node:A:000000",
    "part_revision_id": "A",
    "instance": 0,
    "kind": "top_level_virtual_parent",
    "parent_node_id": null,
    "parent_cavity_index": null,
    "x_local_mm": 0.0,
    "y_local_mm": 0.0,
    "rotation_deg": 0,
    "placement_origin_ref": "bbox_min_corner",
    "children": [
      {
        "node_id": "node:B:000000",
        "part_revision_id": "B",
        "instance": 0,
        "kind": "internal_cavity_child",
        "parent_node_id": "node:A:000000",
        "parent_cavity_index": 2,
        "x_local_mm": 120.0,
        "y_local_mm": 45.0,
        "rotation_deg": 90,
        "placement_origin_ref": "bbox_min_corner",
        "children": [
          {
            "node_id": "node:C:000000",
            "part_revision_id": "C",
            "instance": 0,
            "kind": "internal_cavity_child",
            "parent_node_id": "node:B:000000",
            "parent_cavity_index": 0,
            "x_local_mm": 20.0,
            "y_local_mm": 10.0,
            "rotation_deg": 0,
            "placement_origin_ref": "bbox_min_corner",
            "children": []
          }
        ]
      }
    ]
  }
}
```

**c) v1 vs v2 összehasonlítás táblázat:**

| Mező | v1 | v2 |
|------|----|----|
| version | "cavity_plan_v1" | "cavity_plan_v2" |
| internal_placements | lapos lista | nincs (→ placement_trees) |
| placement_trees | nincs | rekurzív node fa |
| child holes | unsupported | outer proxy + rekurzív |
| max_cavity_depth | n/a | policy.max_cavity_depth |

**d) Quantity kezelési szabályok:**
- `internal_reserved_qty + top_level_qty == original_required_qty` invariáns
- Minden szinten: child instance nem lehet kétszer lefoglalva
- `CAVITY_PREPACK_QUANTITY_MISMATCH` ha eltérés van

**e) Backward compatibility garancia:**
- `cavity_plan_v1` run-ok változatlanul feldolgozhatók
- A normalizer version switch alapú routing

---

## Adatmodell / contract változások

- `_PLAN_VERSION_V2 = "cavity_plan_v2"` konstans (belső)
- `_PlacementTreeNode` dataclass (belső, T06 használja)
- `_empty_plan_v2()` helper (belső, T06 használja)
- `_load_enabled_cavity_plan()` elfogadja a `"cavity_plan_v2"` version stringet

---

## Backward compatibility szempontok

- A `_load_enabled_cavity_plan()` módosítás nem törhet v1 run-t: `"cavity_plan_v1"` továbbra is érvényes
- A `_normalize_solver_output_projection_v2()` v2 ágat T07 implementálja; T04-ben a v2 plan betöltött, de a normalizer a `version` mező alapján leállhat (version check) — **T07 előtt a v2 plan futtatása nem javasolt production-ban**

---

## Hibakódok / diagnosztikák

- `ResultNormalizerError("invalid cavity_plan version: ...")` — ha sem v1, sem v2 nem egyezik
- A v2 plan policy.max_cavity_depth mező hiánya: T06 alapértelmezést használ (3)

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t04_plan_v2_contract.md
```

Unit tesztek:
- `_empty_plan_v2(enabled=True)` visszaad helyes sémát
- `_load_enabled_cavity_plan()` elfogad v2 version stringet tesztfájlból
- `_load_enabled_cavity_plan()` továbbra is elutasít ismeretlen version stringet

---

## Elfogadási feltételek

- `_PLAN_VERSION_V2 = "cavity_plan_v2"` létezik a `worker/cavity_prepack.py`-ban
- `_PlacementTreeNode` dataclass létezik a `worker/cavity_prepack.py`-ban
- `_empty_plan_v2()` helper létezik és helyes schema-t ad
- `_load_enabled_cavity_plan()` elfogad `"cavity_plan_v2"` version stringet
- `docs/nesting_engine/cavity_prepack_contract_v2.md` létezik és tartalmazza a placement_trees struktúrát
- Meglévő v1 tesztek zöldek

---

## Rollback / safety notes

- `_load_enabled_cavity_plan()` változtatás 2 soros — könnyen visszafordítható
- Ha T06/T07 nem készül el, a v2 plan betöltése önmagában nem káros (a normalizer t07 előtt a v2 ágban meghiúsulna, de ezt a guard meg tudja fogni)
- A `worker/cavity_prepack.py` dataclass hozzáadás nem módosít meglévő logikát

---

## Dependency

- T01 ajánlott (v1 contract megismerése).
- T03 (guard) előtt vagy után futtatható.
