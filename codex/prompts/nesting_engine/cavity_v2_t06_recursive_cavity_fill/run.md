# Cavity v2 T06 — Rekurzív cavity fill algoritmus
TASK_SLUG: cavity_v2_t06_recursive_cavity_fill

## Szerep
Senior algoritmus-fejlesztő Python agent vagy. Rekurzív greedy cavity fill algoritmust implementálsz `cavity_plan_v2` kimenettel.

## Cél
`build_cavity_prepacked_engine_input_v2()` publikus függvény implementálása. A `placement_trees` rekurzív node struktúrát gyárt. Matrjoska (A→B→C) esetét is kezel. Ciklus-védelem megvan.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t06_recursive_cavity_fill.yaml`
- `worker/cavity_prepack.py` (TELJES fájl — meglévő helperek: _to_polygon, _ring_bbox, _rotation_shapes, _try_place_child_in_cavity, _fits_exactly, _dedupe_anchors, _bbox_prefilter)
- `worker/result_normalizer.py` (placement_transform_point ~sor 137-152)
- `tests/worker/test_cavity_prepack.py`
- T04 artefaktumok: `_PLAN_VERSION_V2`, `_PlacementTreeNode`, `_empty_plan_v2`
- T05 artefaktumok: `child_has_holes_outer_proxy_used` diagnostic

## Engedélyezett módosítás
- `worker/cavity_prepack.py`
- `tests/worker/test_cavity_prepack.py`

## Szigorú tiltások
- **Tilos a meglévő `build_cavity_prepacked_engine_input()` (v1) függvényt módosítani.**
- Tilos a meglévő v1 teszteket törni.
- Tilos globális state-et módosítani.
- Tilos filename/part_code hardcodeolás.
- Tilos random sorrend — az algoritmus determinisztikus kell legyen.
- **Tilos a lyukakat a final export geometriából elveszíteni** — a child `holes_points_mm` megmarad a `_PartRecord`-ban.
- Tilos ciklusos elhelyezés (A a saját cavityjébe).

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Ellenőrizd, hogy T04 és T05 implementálva van-e. Olvasd el a meglévő helper függvényeket.

### Step 2 + 3: Új helperek és build_cavity_prepacked_engine_input_v2()
A canvas spec pseudokódja alapján implementáld:
1. `_CavityRecord` frozen dataclass
2. `_build_usable_cavity_records()` — min area szűrés
3. `_rank_cavity_child_candidates()` — szűrés + rendezés
4. `_fill_cavity_recursive()` — rekurzív fill, mélységi + ciklus védelem
5. `build_cavity_prepacked_engine_input_v2()` — teljes v2 belépési pont

Kritikus invariáns: `internal_qty + top_level_qty == original_required_qty` minden partra.
Ugyanaz az instance kétszer nem foglalható le: `reserved_instance_ids` set véd.
Ancestor set védi a ciklust: `ancestor_part_ids = frozenset({parent.part_id})` indulásnál.

### Step 4: V2 rekurzív tesztek
A canvas spec 5 tesztje:
1. `test_v2_matrjoska_three_level`
2. `test_v2_cycle_protection`
3. `test_v2_quantity_invariant`
4. `test_v2_disabled_mode`
5. `test_v2_max_depth_respected`

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
```

### Step 5: Checklist és report
### Step 6: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "v2"
```

## Ellenőrzési pontok
- [ ] build_cavity_prepacked_engine_input_v2 létezik és __all__-ban van
- [ ] placement_trees mező a cavity_plan_v2-ben
- [ ] Matrjoska 3-szintes teszt zöld
- [ ] Ciklus védelem tesztelt
- [ ] Quantity invariáns tesztelt
- [ ] Minden top-level part holes_points_mm == []
- [ ] V1 build_cavity_prepacked_engine_input() és v1 tesztek változatlanok

## Elvárt végső jelentés
Magyar nyelvű report. DoD→Evidence mátrix. Bizonyítsd: matrjoska teszt zöld (kimenet is), ciklus védelem, quantity invariáns, v1 backward compat.

## Hiba esetén
Ha a `_try_place_child_in_cavity()` nem ad helyes eredményt a lyukas child outer proxyval, ellenőrizd, hogy T05 valóban implementálva van-e (a continue el van-e távolítva). Ha a rekurzió végtelen ciklusba kerül, a `ancestor_part_ids | {cavity.parent_part_id}` kiszámítása helyes-e.
