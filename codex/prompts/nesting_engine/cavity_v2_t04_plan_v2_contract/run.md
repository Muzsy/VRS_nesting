# Cavity v2 T04 — Cavity plan v2 contract bevezetése
TASK_SLUG: cavity_v2_t04_plan_v2_contract

## Szerep
Senior Python + dokumentáció coding agent vagy. Bevezeted a v2 schema konstansokat és a normalizer version check bővítést, valamint elkészíted a v2 contract dokumentumot.

## Cél
`_PLAN_VERSION_V2`, `_PlacementTreeNode` dataclass, `_empty_plan_v2()` helper a `worker/cavity_prepack.py`-ban. `_load_enabled_cavity_plan()` elfogad `"cavity_plan_v2"` version stringet. `docs/nesting_engine/cavity_prepack_contract_v2.md` dokumentum.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t04_plan_v2_contract.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t04_plan_v2_contract.yaml`
- `worker/cavity_prepack.py` (TELJES fájl)
- `worker/result_normalizer.py` (_load_enabled_cavity_plan sor ~233-248)
- `docs/nesting_engine/cavity_prepack_contract_v1.md`

## Engedélyezett módosítás
- `worker/cavity_prepack.py`
- `worker/result_normalizer.py`
- `docs/nesting_engine/cavity_prepack_contract_v2.md` (ÚJ)
- `tests/worker/test_cavity_prepack.py`
- `tests/worker/test_result_normalizer_cavity_plan.py`

## Szigorú tiltások
- Tilos a meglévő v1 `build_cavity_prepacked_engine_input()` logikát módosítani.
- Tilos a normalizer v1 branch-et módosítani.
- Tilos v2 rekurzív algoritmust implementálni (az T06).
- A `_PlacementTreeNode` és `_empty_plan_v2` belső szimbólumok — ne add `__all__`-ba.
- Tilos nem létező mezőre hivatkozni a v2 sémában.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Azonosítsd a `_PLAN_VERSION` konstans, `_empty_plan()` és `_CavityPlacement` helyét a cavity_prepack.py-ban.

### Step 2: worker/cavity_prepack.py bővítése
Adj hozzá:
```python
_PLAN_VERSION_V2 = "cavity_plan_v2"

@dataclass(frozen=True)
class _PlacementTreeNode:
    node_id: str
    part_revision_id: str
    instance: int
    kind: str
    parent_node_id: str | None
    parent_cavity_index: int | None
    x_local_mm: float
    y_local_mm: float
    rotation_deg: int
    placement_origin_ref: str
    children: tuple  # tuple[_PlacementTreeNode, ...]

def _empty_plan_v2(*, enabled: bool, max_cavity_depth: int = 3) -> dict[str, Any]:
    ...
```
A canvas specifikációja alapján.

### Step 3: worker/result_normalizer.py version check
Egyetlen sor módosítás a `_load_enabled_cavity_plan()`-ban:
```python
if version not in ("cavity_plan_v1", "cavity_plan_v2"):
```

### Step 4: cavity_prepack_contract_v2.md dokumentum
Hozd létre a docs/nesting_engine/cavity_prepack_contract_v2.md fájlt a canvas spec alapján.

### Step 5: Unit tesztek
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```

### Step 6: Checklist és report
### Step 7: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t04_plan_v2_contract.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```

## Ellenőrzési pontok
- [ ] _PLAN_VERSION_V2 = "cavity_plan_v2" megvan a cavity_prepack.py-ban
- [ ] _PlacementTreeNode dataclass megvan
- [ ] _empty_plan_v2() helper megvan, helyes sémát ad
- [ ] _load_enabled_cavity_plan() elfogad "cavity_plan_v2"-t
- [ ] docs/nesting_engine/cavity_prepack_contract_v2.md létezik, placement_trees példával
- [ ] V1 tesztek zöldek

## Elvárt végső jelentés
Magyar nyelvű report. DoD→Evidence: minden alfogadási feltételhez fájl:sor.

## Hiba esetén
Ha a `_load_enabled_cavity_plan()` verziója máshol van mint sor 233-248, grep-pel keresd: `grep -n "_load_enabled_cavity_plan" worker/result_normalizer.py`. Csak a valós sorokat módosítsd.
