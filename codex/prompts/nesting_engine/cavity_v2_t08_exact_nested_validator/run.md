# Cavity v2 T08 — Exact nested cavity validator
TASK_SLUG: cavity_v2_t08_exact_nested_validator

## Szerep
Senior Python/Shapely coding agent vagy. Független, exact geometriai validátort hozol létre a cavity placement tree-khez.

## Cél
`worker/cavity_validation.py` modul létrehozása. Shapely-alapú exact validáció minden szinten: child cavity containment, child-child overlap, quantity mismatch, transform helyes. Hard fail `CavityValidationError`.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t08_exact_nested_validator.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t08_exact_nested_validator.yaml`
- `worker/result_normalizer.py` (placement_transform_point ~sor 137-152, _normalize_rotation_deg ~sor 251)
- `worker/cavity_prepack.py` (_to_polygon, _fits_exactly, _EPS_AREA konstans)
- `requirements-dev.txt` (Shapely verzió ellenőrzés)
- `tests/worker/test_cavity_prepack.py` (_rect helper minta)

## Engedélyezett módosítás
- `worker/cavity_validation.py` (ÚJ fájl)
- `tests/worker/test_cavity_validation.py` (ÚJ fájl)

## Szigorú tiltások
- **Tilos a worker/cavity_prepack.py-t vagy worker/result_normalizer.py-t módosítani ebben a taskban.**
- Tilos DB-t írni, fájlt írni.
- Tilos a validátor `strict=True` esetén silent folytatást engedni — csak kivétel dobás.
- Tilos bbox-only fit alapján elfogadni — Shapely `covers()` kell.
- Tilos a gyártási geometriát módosítani.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Ellenőrizd a Shapely verzióját a requirements-dev.txt-ben (`shapely`). Ellenőrizd, hogy `from shapely.geometry import Polygon` és `from shapely import affinity` importok működnek.

### Step 2: worker/cavity_validation.py implementálása
A canvas spec alapján:
1. `CavityValidationError(RuntimeError)`
2. `ValidationIssue` dataclass
3. `validate_child_within_cavity()`
4. `validate_no_child_child_overlap()`
5. `validate_placement_tree_node()` (rekurzív)
6. `validate_cavity_plan_v2()` (teljes validátor)

`__all__` exportálva.

**Kritikus**: A `_build_placed_polygon()` helper helyes transformációt végez:
1. Shapely polygon felépítése az outer_points_mm-ből
2. Forgatás rotation_deg-gel az origó körül
3. bbox min-hez igazítás (normalizálás)
4. Eltolás abs_x, abs_y-ra

### Step 3: tests/worker/test_cavity_validation.py
6 teszt a canvas spec szerint. A `_rect()` helper importálható a test_cavity_prepack.py-ból, vagy újra definiálható.

```bash
python3 -m pytest -q tests/worker/test_cavity_validation.py
```

### Step 4: Checklist és report
### Step 5: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_cavity_validation.py
python3 -m pytest -q tests/worker/
```

## Ellenőrzési pontok
- [ ] worker/cavity_validation.py létezik
- [ ] CavityValidationError, ValidationIssue, validate_cavity_plan_v2 __all__-ban
- [ ] CAVITY_CHILD_OUTSIDE_PARENT_CAVITY, CAVITY_CHILD_CHILD_OVERLAP, CAVITY_QUANTITY_MISMATCH tesztelt
- [ ] strict=True → kivétel, strict=False → lista
- [ ] Shapely `covers()` alapú ellenőrzés (nem bbox-only)
- [ ] Modul nem ír fájlt, nem hív DB-t

## Elvárt végső jelentés
Magyar nyelvű report. DoD→Evidence. Minden hibakód tesztelési bizonyítéka. A `_build_placed_polygon()` transform logikájának magyarázata.

## Hiba esetén
Ha a Shapely transform nem ad helyes eredményt: ellenőrizd, hogy a polygon normalizálás (bbox min corner → origó) és az eltolás sorrend helyes-e. A `_fits_exactly()` logikáját a worker/cavity_prepack.py-ban referenciaként használhatod.
