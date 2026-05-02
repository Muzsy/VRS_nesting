# Cavity v2 T01 — Cavity-prepack v1 audit és contract snapshot

## Cél

Teljes auditot végezni a meglévő `cavity_plan_v1` implementáción, dokumentálni a jelenlegi viselkedést, korlátokat és a v1 contract minden részletét. Az audit alapján egy snapshot dokumentum készül, amely a v2 fejlesztés kiindulópontja.

**Nem kell kódot módosítani.** Ez egy read-only audit + dokumentáció task.

---

## Miért szükséges

A v2 fejlesztés csak akkor biztonságos, ha a v1 baseline pontosan dokumentált. Ha a v1 viselkedése nem ismert, a v2 módosítások regressziót okozhatnak a meglévő `cavity_plan_v1` folyamatokon.

---

## Érintett valós fájlok

### Olvasandó (read-only audit):
- `worker/cavity_prepack.py` — teljes v1 implementáció
- `worker/result_normalizer.py` — `_load_enabled_cavity_plan()` v1 logika, `_normalize_solver_output_projection_v2()` cavity branch
- `docs/nesting_engine/cavity_prepack_contract_v1.md` — meglévő contract doc
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `docs/nesting_quality/cavity_prepack_rollout_decision.md`
- `tests/worker/test_cavity_prepack.py`
- `tests/worker/test_result_normalizer_cavity_plan.py`
- `vrs_nesting/config/nesting_quality_profiles.py`

### Létrehozandó:
- `docs/nesting_engine/cavity_prepack_v1_audit.md` — az audit eredménye

---

## Nem célok / scope határok

- Nem módosítható a `worker/cavity_prepack.py`, `result_normalizer.py` vagy bármely más kódfájl.
- Nem kell v2 feature-t implementálni.
- Nem kell a frontend-et érinteni.
- Nem kell új tesztet írni (csak a meglévőket futtatni).

---

## Részletes implementációs lépések

### 1. Beolvasás és áttekintés

Olvasd el sorban:
1. `worker/cavity_prepack.py` — minden függvényt, a `_PLAN_VERSION`, `_VIRTUAL_PART_PREFIX` konstansokat, a `build_cavity_prepacked_engine_input()` teljes folyamatát.
2. `worker/result_normalizer.py` — `_load_enabled_cavity_plan()`, `_normalize_solver_output_projection_v2()` virtual part branch (sor ~577–807).
3. `tests/worker/test_cavity_prepack.py` — milyen eseteket fed le.
4. `tests/worker/test_result_normalizer_cavity_plan.py` — normalizer v1 tesztek.

### 2. Futtatás baseline-ként

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```

Minden tesztnek zöldnek kell lennie.

### 3. Audit dokumentum megírása

A `docs/nesting_engine/cavity_prepack_v1_audit.md` tartalmazza:

**a) Public API:**
- `build_cavity_prepacked_engine_input(snapshot_row, base_engine_input, enabled)` szignatúra, return type
- `CavityPrepackError` kivétel mikor dob

**b) Data flow:**
- snapshot → part_records → holed_parents / non_holed felosztás
- virtual part ID formula: `__cavity_composite__{parent_part_id}__{instance:06d}`
- cavity_plan.json séma (v1): `version`, `enabled`, `policy`, `virtual_parts`, `instance_bases`, `quantity_delta`, `diagnostics`
- `internal_placements` struktúra (lapos lista): `child_part_revision_id`, `child_instance`, `cavity_index`, `x_local_mm`, `y_local_mm`, `rotation_deg`, `placement_origin_ref`

**c) Ismert korlátok és diagnostic kódok:**
- `child_has_holes_unsupported_v1` — lyukas child nem kerülhet cavitybe (v1 kemény korlát)
- `invalid_cavity_polygon` — érvénytelen cavity polygon
- `not_used_no_child_fit` — nincs beférő child
- `used` — sikeres cavity kihasználás

**d) v1 quantity kezelés:**
- `original_required_qty`, `internal_qty`, `top_level_qty` mezők
- `instance_bases.top_level_instance_base` = internal_qty

**e) Normalizer v1 bridge:**
- `_load_enabled_cavity_plan()` — csak `cavity_plan_v1` fogadja el
- `_normalize_solver_output_projection_v2()` virtual parent branch (~sor 722)
- `placement_transform_point()` — local→absolute koordináta transform
- `_normalize_rotation_deg()` — rotáció normalizálás

**f) v1 lapos modell korlátja:**
- A `children` nincsenek rekurzívan kezelve
- `internal_placements` egydimenziós lista
- A child saját lyukait nem vizsgálja
- Matrjoska eset nem lehetséges v1-ben

---

## Adatmodell dokumentálás (v1 snapshot)

Az audit dokumentumban rögzíteni kell a teljes v1 cavity_plan.json sémát JSON példával:

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
    "__cavity_composite__<parent_id>__000000": {
      "kind": "parent_composite",
      "parent_part_revision_id": "<parent_id>",
      "parent_instance": 0,
      "source_geometry_revision_id": "<sgr_id>",
      "selected_nesting_derivative_id": "<snd_id>",
      "internal_placements": [
        {
          "child_part_revision_id": "<child_id>",
          "child_instance": 0,
          "cavity_index": 0,
          "x_local_mm": 10.0,
          "y_local_mm": 5.0,
          "rotation_deg": 0,
          "placement_origin_ref": "bbox_min_corner"
        }
      ],
      "cavity_diagnostics": [
        {
          "cavity_index": 0,
          "status": "used",
          "usable_area_mm2": 3600.0,
          "placements_count": 1
        }
      ]
    }
  },
  "instance_bases": {
    "<child_id>": {
      "internal_reserved_count": 1,
      "top_level_instance_base": 1
    }
  },
  "quantity_delta": {
    "<child_id>": {
      "original_required_qty": 5,
      "internal_qty": 1,
      "top_level_qty": 4
    }
  },
  "diagnostics": []
}
```

---

## Tesztelési terv

1. Futtatás: `python3 -m pytest -q tests/worker/test_cavity_prepack.py tests/worker/test_result_normalizer_cavity_plan.py`
2. Minden teszt zöld → baseline confirmed
3. Tesztlefedettség áttekintése: mely esetek nincsenek lefedve (ez a v2 számára tesztigényt jelez)

---

## Elfogadási feltételek

- `docs/nesting_engine/cavity_prepack_v1_audit.md` létezik és tartalmazza az összes fenti pontot
- Minden meglévő v1 teszt zöld
- Az audit dokumentum explicit megemlíti a `child_has_holes_unsupported_v1` korlátot
- Az audit dokumentum tartalmazza a `placement_transform_point()` helperről szóló megjegyzést (v2 erre épít)
- Nincs kódmódosítás egyetlen `.py` fájlban sem

---

## Rollback / safety notes

Ez a task kizárólag dokumentumot hoz létre. Nincs futtatható kódváltozás, nincs rollback kockázat.

---

## Dependency

- Nincs — ez az első task, önálló.
