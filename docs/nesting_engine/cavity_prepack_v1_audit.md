# Cavity Prepack v1 Audit Snapshot

## 1. Task scope es statusz

- Task slug: `cavity_v2_t01_audit_contract_snapshot`
- Datum: `2026-05-02`
- Scope: read-only audit a `cavity_plan_v1` worker + normalizer viselkedeserol.
- Kodmodositas: nincs.

## 2. Beolvasott forrasok

- `worker/cavity_prepack.py`
- `worker/result_normalizer.py`
- `tests/worker/test_cavity_prepack.py`
- `tests/worker/test_result_normalizer_cavity_plan.py`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `vrs_nesting/config/nesting_quality_profiles.py`

## 3. Public API es alap adatmodellek

### 3.1 Public API

`build_cavity_prepacked_engine_input(*, snapshot_row, base_engine_input, enabled) -> tuple[dict[str, Any], dict[str, Any]]`

- Input:
  - `snapshot_row`: manifest adatok (part metadata)
  - `base_engine_input`: solver input (`nesting_engine_v2`)
  - `enabled`: cavity prepack kapcsolo
- Output:
  - `out_input`: solverbe kuldendo modositott input
  - `plan`: `cavity_plan_v1` sidecar

Kivetel:
- `CavityPrepackError` dobodik invalid input, invalid polygon, vagy hianyzo snapshot metadata eseten.

### 3.2 Konstansok

- `_PLAN_VERSION = "cavity_plan_v1"`
- `_VIRTUAL_PART_PREFIX = "__cavity_composite__"`
- `_EPS_AREA = 1e-7`
- `_EPS_COORD = 1e-9`

### 3.3 Dataclassok

- `_PartRecord`
  - `part_id`, `part_code`, `quantity`, `allowed_rotations_deg`
  - `outer_points_mm`, `holes_points_mm`
  - `area_mm2`, `bbox_max_dim_mm`
  - `source_geometry_revision_id`, `selected_nesting_derivative_id`
- `_CavityPlacement`
  - `child_part_revision_id`, `child_instance`, `cavity_index`
  - `x_local_mm`, `y_local_mm`, `rotation_deg`
  - `placement_origin_ref`

Megjegyzes: `_CavityPlacement` dataclass definialva van, de a runtime tervben dict alaku internal placement rekordok epulnek.

## 4. build_cavity_prepacked_engine_input() teljes flow

### 4.1 Disabled ag (`enabled=False`)

- `out_input` a base input deep copy-ja.
- `plan = _empty_plan(enabled=False)`:
  - `version="cavity_plan_v1"`
  - `enabled=false`
  - `virtual_parts={}, instance_bases={}, quantity_delta={}, diagnostics=[]`

### 4.2 Enabled ag (`enabled=True`)

1. Input validacio es part rekord epites:
   - `base_engine_input.parts` beolvasas + tipus/ertek validacio.
   - Snapshot metadata lookup minden `part_id`-hoz.
2. Parent csoportositas:
   - `holed_parents`: lyukas parentek.
   - `non_holed`: nem lyukas top-level partok.
3. Minden lyukas parent minden instance-re virtual part keszul:
   - `virtual_id = "__cavity_composite__{parent_part_id}__{instance:06d}"`
   - top-level solver part:
     - `quantity = 1`
     - `holes_points_mm = []` (top-level hole-free)
4. Cavity fill ciklus parent hole-rol parent hole-ra:
   - cavity polygon validacio (`_to_polygon`).
   - child jeloltek (`_candidate_children`), deterministic sort.
   - rotacios alakok (`_rotation_shapes`) + anchor probing.
   - fit check:
     - bbox prefilter (`_bbox_prefilter`)
     - shapely exact cover + overlap ellenorzes (`_fits_exactly`)
5. Placement siker eseten:
   - `remaining_qty[child]` csokken.
   - `reserved_internal[child]` no.
   - `internal_placements[]` rekord hozzaadas:
     - `child_part_revision_id`, `child_instance`, `cavity_index`
     - `x_local_mm`, `y_local_mm`, `rotation_deg`
     - `placement_origin_ref = "bbox_min_corner"`
6. Cavity status:
   - `"used"` ha legalabb 1 placement.
   - `"not_used_no_child_fit"` ha 0 placement.
   - `"invalid_cavity_polygon"` ha cavity geometry invalid.
7. `instance_bases` + `quantity_delta` epites csak referencelt childokra.
8. `out_input["parts"]` rendezve (`id` szerint), plan kitoltve es visszaadva.

## 5. _candidate_children, _rotation_shapes, _fits_exactly audit

### 5.1 _candidate_children()

- Kizart:
  - onmaga (`part_id == parent_part_id`)
  - nulla maradek mennyiseg
  - lyukas child (`part.holes_points_mm` nem ures)
- Lyukas child eseten diagnostic:
  - `code="child_has_holes_unsupported_v1"`
  - `child_part_revision_id=<child>`
- Rendezes:
  - `-area_mm2`, `bbox_max_dim_mm`, `part_code`, `part_id`

### 5.2 _rotation_shapes()

- Szandekosan outer-only shape-et hasznal:
  - `base_poly = _to_polygon(part.outer_points_mm, [])`
- Minden engedelyezett rotaciora:
  - rotate origin `(0,0)` korul
  - bbox-min pontra normalizal

Kovetkezmeny:
- v1 nem kezeli a child hole-okat cavity placementben.

### 5.3 _fits_exactly()

- `cavity_polygon.covers(candidate_polygon)` kotelezo.
- Occupied candidate-tel metszesnel:
  - ha metszet area `> _EPS_AREA`, placement tiltva.

Ez shapely exact containment + overlap guard, nem bbox-only fit.

## 6. V1 diagnostics kodok es jelentese

### 6.1 Plan-level diagnostics (`plan["diagnostics"]`)

- `child_has_holes_unsupported_v1`
  - Jelentes: lyukas child elvagva a cavity candidate listabol.
  - Mezo: `child_part_revision_id`.

### 6.2 Cavity-level diagnostics (`virtual_parts[*].cavity_diagnostics[]`)

- `invalid_cavity_polygon`
  - Jelentes: cavity ringbol nem keszitheto valid polygon.
  - `usable_area_mm2=0.0`, `placements_count=0`.
- `not_used_no_child_fit`
  - Jelentes: cavity valid, de nincs befero child placement.
- `used`
  - Jelentes: cavity hasznalva, legalabb 1 child placement sikerult.

## 7. cavity_plan_v1 schema (snapshot)

### 7.1 Top-level mezok

- `version`: mindig `cavity_plan_v1`
- `enabled`: bool
- `policy`:
  - `mode`
  - `top_level_hole_policy`
  - `usable_cavity_source`
  - `quantity_allocation`
- `virtual_parts`: virtual parent map
- `instance_bases`: child-level instance offset map
- `quantity_delta`: child-level qty bontas
- `diagnostics`: plan-level diagnostics lista

### 7.2 Teljes JSON pelda

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
  "virtual_parts": {
    "__cavity_composite__parent-a__000000": {
      "kind": "parent_composite",
      "parent_part_revision_id": "parent-a",
      "parent_instance": 0,
      "source_geometry_revision_id": "geo-parent-a",
      "selected_nesting_derivative_id": "drv-parent-a",
      "internal_placements": [
        {
          "child_part_revision_id": "child-a",
          "child_instance": 0,
          "cavity_index": 0,
          "x_local_mm": 2.0,
          "y_local_mm": 4.0,
          "rotation_deg": 180,
          "placement_origin_ref": "bbox_min_corner"
        }
      ],
      "cavity_diagnostics": [
        {
          "cavity_index": 0,
          "status": "used",
          "usable_area_mm2": 64.0,
          "placements_count": 1
        }
      ]
    }
  },
  "instance_bases": {
    "child-a": {
      "internal_reserved_count": 1,
      "top_level_instance_base": 1
    }
  },
  "quantity_delta": {
    "child-a": {
      "original_required_qty": 4,
      "internal_qty": 1,
      "top_level_qty": 3
    }
  },
  "diagnostics": [
    {
      "code": "child_has_holes_unsupported_v1",
      "child_part_revision_id": "child-hole"
    }
  ]
}
```

## 8. quantity_delta es instance_bases viselkedes

- `quantity_delta[child]`:
  - `original_required_qty`: eredeti base input quantity
  - `internal_qty`: cavitybe foglalt mennyiseg
  - `top_level_qty`: solverbe marado top-level mennyiseg
- `instance_bases[child]`:
  - `internal_reserved_count = internal_qty`
  - `top_level_instance_base = internal_qty`

Normalizer mappingnek ez adja a top-level solver instance offsetet.

## 9. Normalizer v1 bridge (cavity_plan_v1)

### 9.1 _load_enabled_cavity_plan()

- `run_dir/cavity_plan.json` hiany -> `None`
- invalid json -> `ResultNormalizerError`
- `enabled=false` -> `None` (legacy viselkedes)
- version check szigoru:
  - csak `cavity_plan_v1` elfogadott
  - mas ertek -> `ResultNormalizerError`

### 9.2 _normalize_solver_output_projection_v2 cavity branch

- Virtual parent rekord parse:
  - `parent_part_revision_id`, `parent_instance`, `internal_placements[]`
- Virtual placement map:
  - solver `part_id` virtual id esetben parent row + internal child row expansion
- Internal child abszolut transzform:
  - `abs_xy = placement_transform_point(local, parent_transform)`
  - `abs_rotation = normalize(parent_rotation + local_rotation)`
- Top-level child instance mapping:
  - `mapped_instance = engine_instance + top_level_instance_base`

### 9.3 placement_transform_point() helper

Helper formula:

- `norm_x = local_x - base_x`
- `norm_y = local_y - base_y`
- `x_abs = norm_x*cos(theta) - norm_y*sin(theta) + tx`
- `y_abs = norm_x*sin(theta) + norm_y*cos(theta) + ty`

V1 cavity bridge minden internal child abszolut helyzetet erre epit.
Ez a helper a v2 tree flatten compose alapja is.

## 10. V1 lapos modell korlatai

- Nincs rekurziv parent-child tree.
- `internal_placements` egy lapos lista virtual parentenkent.
- Lyukas child v1-ben unsupported (candidate filter + diagnostic).
- Child sajat cavity-je nem kerul tovabb prepack futasra.
- Matrjoska (A->B->C nested chain) nem reprezentalhato v1 contracttal.

## 11. Teszt baseline allapot

T01 futasban lefutott:

- `python3 -m pytest -q tests/worker/test_cavity_prepack.py` -> `7 passed`
- `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py` -> `2 passed`

Kovetkeztetes:
- A v1 cavity prepack + normalizer cavity bridge baseline zold.

