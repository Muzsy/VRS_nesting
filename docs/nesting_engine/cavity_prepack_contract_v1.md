# Cavity Prepack Contract v1

## 1. Cel es scope

- Contract azonosito: `cavity_plan_v1`
- Cel: worker-side cavity-first/composite prepack output szerzodes rogzites.
- Ez a contract NEM uj Rust IO contract.
- A Rust solver input/output contract tovabbra is `nesting_engine_v2`.

## 2. Helye es artifact path

- Run temp mappa: `<run_dir>/cavity_plan.json`
- Canonical storage key: `runs/<run_id>/inputs/cavity_plan.json`
- Run artifact referenciaban a `cavity_plan` fajl visszakeresheto kell legyen.

## 3. Top-level schema

```json
{
  "version": "cavity_plan_v1",
  "enabled": true,
  "policy": {
    "mode": "auto_prepack",
    "top_level_hole_policy": "solidify_parent_outer",
    "usable_cavity_source": "inflated_or_deflated_hole_from_pipeline",
    "quantity_allocation": "internal_first_deterministic"
  },
  "virtual_parts": {},
  "instance_bases": {},
  "quantity_delta": {},
  "diagnostics": []
}
```

## 4. Mezojelentes

- `version`:
  - kotelezo string, erteke mindig `cavity_plan_v1`.
- `enabled`:
  - `false` eseten minden downstream komponensnek legacy viselkedest kell adnia.
- `policy`:
  - dokumentacios/audit blokk a hasznalt prepack policyrol.
- `virtual_parts`:
  - virtual parent part ID -> mapping adat.
- `instance_bases`:
  - child part revision szintu instance offset informacio.
- `quantity_delta`:
  - eredeti required qty, internal reserved qty, top-level qty adatok.
- `diagnostics`:
  - nem blokkolo vagy unsupported jelzesek.

## 5. `virtual_parts` szerkezet

Kulcs:
- virtual part ID, pl. `__cavity_composite__<parent_revision_id>__000000`

Ertek:
- `kind`: `parent_composite`
- `parent_part_revision_id`: eredeti parent revision ID
- `parent_instance`: 0-bazisu parent instance index
- `source_geometry_revision_id`
- `selected_nesting_derivative_id`
- `internal_placements`: child placement lista
- `cavity_diagnostics`: cavity-level status lista

`internal_placements[]` mezo minimum:
- `child_part_revision_id`
- `child_instance`
- `cavity_index`
- `x_local_mm`
- `y_local_mm`
- `rotation_deg`
- `placement_origin_ref` (v1: `bbox_min_corner`)

## 6. `instance_bases` es `quantity_delta`

`instance_bases[child_revision_id]`:
- `internal_reserved_count`: hany child instance ment cavitybe
- `top_level_instance_base`: top-level solver output instance offset

`quantity_delta[child_revision_id]`:
- `original_required_qty`
- `internal_qty`
- `top_level_qty`

Normativ invariansok:
- `top_level_qty = original_required_qty - internal_qty`
- `top_level_qty >= 0`
- ugyanaz a child instance nem szerepelhet ket helyen

## 7. Worker-side invariansok

- Minden virtual parent top-level solver input part:
  - `quantity = 1`
  - `holes_points_mm = []`
  - `outer_points_mm = parent outer`
- Prepack modban a legacy runtime BLF part-in-part nem lehet aktiv.
- Child holes v1-ben unsupported; diagnosticsban jelolni kell.
- Nincs filename vagy part_code hardcode.

## 8. Result normalizer elvarasok (v1)

- `cavity_plan` hianyaban vagy `enabled=false` eseten legacy normalizer viselkedes.
- Virtual parent output mapping vissza eredeti `parent_part_revision_id`-ra.
- Internal child rows abszolut transformmal expanziora kerulnek:
  - `child_abs_point = rotate(parent_rotation, child_local_point) + parent_translation`
  - `child_abs_rotation = normalize(parent_rotation + child_local_rotation)`
- Top-level child placement es unplaced instance ID offset:
  - `actual_instance = engine_instance + top_level_instance_base`

## 9. Backward compatibility

- `nesting_engine_v2` contract version NEM valtozik.
- `cavity_plan_v1` additive sidecar artifact.
- Cavity nelkuli runokra nincs viselkedesvaltozas.

## 10. Nem-celok ebben a contractban

- Full hole-aware NFP implementacio.
- Manufacturing cut-order scheduler.
- Rust CLI `--part-in-part prepack` ertek.

## 11. Kapcsolodo dokumentumok

- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `docs/nesting_engine/json_canonicalization.md`
