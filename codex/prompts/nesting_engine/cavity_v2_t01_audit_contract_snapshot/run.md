# Cavity v2 T01 — Cavity-prepack v1 audit és contract snapshot
TASK_SLUG: cavity_v2_t01_audit_contract_snapshot

## Szerep
Senior audit agent vagy. Read-only vizsgálatot végzel a meglévő v1 cavity prepack implementáción, dokumentálod a teljes viselkedést, és baseline-t teremtesz a v2 fejlesztés számára.

## Cél
Hozd létre a `docs/nesting_engine/cavity_prepack_v1_audit.md` dokumentumot, amely teljes mértékben leírja a v1 implementációt. Semmi kódot nem módosítasz.

## Olvasd el először
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t01_audit_contract_snapshot.yaml`
- `worker/cavity_prepack.py` (TELJES fájl)
- `worker/result_normalizer.py` (főleg _load_enabled_cavity_plan, ~sor 233-248; _normalize_solver_output_projection_v2 cavity branch ~sor 577-807)
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `tests/worker/test_cavity_prepack.py`
- `tests/worker/test_result_normalizer_cavity_plan.py`

## Engedélyezett módosítás
Csak a YAML `outputs` listájában szereplő fájlok.

## Szigorú tiltások
- **Tilos bármely `.py` fájlt módosítani.** Ez read-only audit.
- Tilos v2 feature-t bevezető kódot írni.
- Tilos nem létező fájlokra hivatkozni.
- Tilos kommentből következtetni — csak valós kódot dokumentálni.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Felderítés és artefaktok
Olvasd el az összes kontextus fájlt. Rögzítsd:
- `build_cavity_prepacked_engine_input()` teljes flow
- `_PLAN_VERSION = "cavity_plan_v1"`, `_VIRTUAL_PART_PREFIX`
- `_CavityPlacement` dataclass mezők
- `_candidate_children()` — a `child_has_holes_unsupported_v1` continue
- `_rotation_shapes()` — outer-only proxy logika
- `_fits_exactly()` — Shapely exact containment
- `_load_enabled_cavity_plan()` — version check
- normalizer cavity branch: internal_placements lapos lista, placement_transform_point() hívás

### Step 2: Baseline tesztek futtatása
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```
Minden tesztnek zöldnek kell lennie. Ha nem, rögzítsd (ne javítsd).

### Step 3: docs/nesting_engine/cavity_prepack_v1_audit.md megírása
Tartalmazza a canvas specifikációja szerint:
- Public API, paraméterek, return type
- Data flow diagram szövegesen
- Összes diagnostic kód és jelentésük
- cavity_plan_v1 JSON séma teljes példával
- quantity_delta / instance_bases struktúra
- Normalizer v1 bridge: virtual part lookup, placement_transform_point hívás
- `placement_transform_point()` leírása (v2 erre épít)
- V1 lapos modell korlátai (nincs rekurzió, child holes unsupported)

### Step 4: Checklist és report
DoD→Evidence mátrix bizonyítékokkal.

### Step 5: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t01_audit_contract_snapshot.md
```

## Stop conditions
Állj meg, ha a kódfájlok nem olvashatók vagy a teszt runner nem elérhető. Rögzítsd a problémát a reportban.

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```

## Ellenőrzési pontok
- [ ] worker/cavity_prepack.py elolvasva
- [ ] worker/result_normalizer.py cavity branch elolvasva
- [ ] Baseline tesztek zöldek
- [ ] docs/nesting_engine/cavity_prepack_v1_audit.md létezik
- [ ] child_has_holes_unsupported_v1 dokumentálva
- [ ] placement_transform_point() dokumentálva
- [ ] Nincs kódmódosítás
- [ ] Report DoD→Evidence mátrixszal kitöltve
- [ ] Repo gate lefutott

## Elvárt végső jelentés formátuma
Magyar nyelvű report. Tartalmazza:
- Task meta (id, dátum)
- Olvasott fájlok listája
- Teszt eredmény (zöld/piros, count)
- Audit dokumentum útvonala
- DoD→Evidence mátrix
- AUTO_VERIFY blokk (verify.sh kimenet)

## Hiba esetén
Ha a teszt runner nem fut, rögzítsd és folytasd az audit dokumentum megírásával. Ne módosíts tesztet.

## Csak valós kód alapján
Minden állítás a repo valós forráskódján alapuljon. Nem extrapolálhatsz, nem találhatsz ki nem létező mezőket vagy függvényneveket.
