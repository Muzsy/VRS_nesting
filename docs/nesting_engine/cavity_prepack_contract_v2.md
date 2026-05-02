# Cavity Prepack Contract v2

## 1. Cel es scope

- Contract azonosito: `cavity_plan_v2`
- Cel: rekurziv cavity tree alapu prepack sidecar szerzodes definialasa.
- Ez a contract NEM uj rust IO contract.
- A solver input/output contract tovabbra is `nesting_engine_v2`.

## 2. Helye es artifact path

- Run temp mappa: `<run_dir>/cavity_plan.json`
- Canonical storage key: `runs/<run_id>/inputs/cavity_plan.json`
- Run artifact referenciaban a `cavity_plan` fajl visszakeresheto kell legyen.

## 3. Top-level schema

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
  "virtual_parts": {},
  "placement_trees": {},
  "instance_bases": {},
  "quantity_delta": {},
  "diagnostics": [],
  "summary": {}
}
```

## 4. placement_trees rekurziv node modell

- Kulcs: virtual parent id, pl. `__cavity_composite__A__000000`
- Ertek: gyoker node (`kind = "top_level_virtual_parent"`) rekurziv `children` tombbel.

### Pelda (A -> B -> C matrjoska)

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

## 5. virtual_parts / instance_bases / quantity_delta

- `virtual_parts` tovabbra is tartalmazza a top-level virtual parent mappinget.
- `instance_bases` child part szintu top-level instance offset informacio.
- `quantity_delta` quantity allokacio bontas:
  - `original_required_qty`
  - `internal_qty`
  - `top_level_qty`

## 6. V1 vs V2 osszehasonlitas

| Mezo | v1 | v2 |
|------|----|----|
| version | `cavity_plan_v1` | `cavity_plan_v2` |
| internal_placements | lapos lista | nincs (helyette `placement_trees`) |
| placement_trees | nincs | rekurziv node fa |
| child holes policy | unsupported | recursive outer proxy + exact export |
| max_cavity_depth | n/a | `policy.max_cavity_depth` |

## 7. Quantity invariansok

- `internal_reserved_qty + top_level_qty == original_required_qty`
- `top_level_qty >= 0`
- Egy child instance azonosito nem szerepelhet ket kulon foglalasban.
- Invarians sertes eseten hard-fail diagnosztika kotelezo:
  - `CAVITY_PREPACK_QUANTITY_MISMATCH`

## 8. Backward compatibility

- `cavity_plan_v1` run-ok tovabbra is ervenyesek es feldolgozhatok.
- Normalizer version switch alapon route-ol:
  - `cavity_plan_v1` -> legacy v1 bridge
  - `cavity_plan_v2` -> v2 flatten ag (T07)
- `nesting_engine_v2` contract nem valtozik.

## 9. Kapcsolodo dokumentumok

- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `docs/nesting_engine/io_contract_v2.md`
