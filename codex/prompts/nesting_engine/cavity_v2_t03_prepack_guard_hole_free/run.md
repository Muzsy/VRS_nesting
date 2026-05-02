# Cavity v2 T03 — Prepack guard: solver input top-level hole-free legyen
TASK_SLUG: cavity_v2_t03_prepack_guard_hole_free

## Szerep
Senior Python coding agent vagy. Éles, minimális-invazív guard logikát implementálsz: egy validáló függvényt és annak bekötését.

## Cél
Ha `part_in_part=prepack` mód aktív, a Rust engine input ne tartalmazhasson `holes_points_mm != []` bejegyzést. Hard fail guard implementálása `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN` error kóddal.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t03_prepack_guard_hole_free.yaml`
- `worker/cavity_prepack.py` (TELJES fájl — CavityPrepackError, __all__, build_cavity_prepacked_engine_input)
- `worker/main.py` (TELJES fájl — hol hívják a prepacket és az engine CLI-t)
- `vrs_nesting/config/nesting_quality_profiles.py` (part_in_part értékek)
- `tests/worker/test_cavity_prepack.py`

## Engedélyezett módosítás
- `worker/cavity_prepack.py`
- `worker/main.py`
- `tests/worker/test_cavity_prepack.py`

## Szigorú tiltások
- Tilos silent warning-ot adni — csak hard fail.
- Tilos a meglévő prepack logikát módosítani (csak guard hozzáadva).
- Tilos a guard-ot part_in_part != "prepack" esetén futtatni.
- Tilos új fájlt létrehozni (csak meglévők módosíthatók).
- Tilos globálisan importálni a validátort — `from worker.cavity_prepack import ...` formában, a guard futtatásának helyén.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Azonosítsd a `build_cavity_prepacked_engine_input()` hívás helyét a `worker/main.py`-ban. Azonosítsd, hol dől el a `part_in_part` értéke.

### Step 2: cavity_prepack.py bővítése
Implementáld a canvas spec alapján:
```python
class CavityPrepackGuardError(CavityPrepackError): pass

def validate_prepack_solver_input_hole_free(engine_input: dict[str, Any]) -> None:
    """Raises CavityPrepackGuardError if any top-level part has non-empty holes_points_mm."""
    ...
```
A függvény üzenetében legyen: `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: {count} part(s)...`
Bővítsd `__all__`-t: `"CavityPrepackGuardError"`, `"validate_prepack_solver_input_hole_free"`.

### Step 3: worker/main.py bekötése
A `build_cavity_prepacked_engine_input()` visszatérése után, de az engine CLI hívás előtt:
```python
if runtime_policy.get("part_in_part") == "prepack":
    from worker.cavity_prepack import validate_prepack_solver_input_hole_free
    validate_prepack_solver_input_hole_free(prepackaged_engine_input)
```
Pontosan a canvas spec helyére.

### Step 4: Unit tesztek
Három teszt a canvas spec szerint:
1. `test_guard_passes_if_no_top_level_holes`
2. `test_guard_fails_if_holes_remain`
3. `test_guard_reports_all_violating_parts`
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
```

### Step 5: Checklist és report
### Step 6: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "guard"
```

## Ellenőrzési pontok
- [ ] CavityPrepackGuardError létezik és __all__-ban van
- [ ] validate_prepack_solver_input_hole_free létezik és __all__-ban van
- [ ] CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN az exception message-ben
- [ ] Violáló part ID-k az üzenetben
- [ ] main.py bekötés megvan (fájl + sor referencia a reportban)
- [ ] Guard csak part_in_part=="prepack" esetén fut
- [ ] Meglévő cavity tesztek zöldek

## Elvárt végső jelentés formátuma
Magyar nyelvű report. DoD→Evidence mátrix: minden elfogadási feltételhez fájl:sor bizonyíték.

## Hiba esetén
Ha a main.py struktúrája eltér a várttól (nem találod a prepack hívás helyét), olvasd el újra a teljes main.py-t és azonosítsd a pontos helyet. Ne találj ki nem létező változóneveket.
