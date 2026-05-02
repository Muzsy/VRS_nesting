# Cavity v2 T03 — Prepack guard: solver input top-level hole-free legyen

## Cél

Ha a `part_in_part=prepack` mód aktív, a Rust nesting engine CLI-nek adott input **egyetlen top-level alkatrésznél sem tartalmazhat `holes_points_mm != []` bejegyzést**. Ez a task egy hard-fail guard-ot vezet be, amely a `build_cavity_prepacked_engine_input()` visszatérése után, de az engine hívás előtt ellenőriz.

Hiba esetén az error code: `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN`

---

## Miért szükséges

A v1 prepack meglévő logikája biztosítja, hogy a lyukas parentekből virtual composite partok lesznek (`holes_points_mm=[]`). Azonban ha valamilyen okból lyukas alkatrész mégis a top-level solver inputban maradna (pl. bugos prepack logika, új part típus, edge case), a Rust engine hallgatólagosan kezelné azt, esetleg silent fallbackkel, ami production run-ban elfogadhatatlan.

A guard explicitre teszi ezt a garanciát: ha a prepack aktív és holes maradnak, a run azonnal és érthetően hibázik — nem csinálja meg a nesting-et egy érvénytelen inputból.

---

## Érintett valós fájlok

### Módosítandó:
- `worker/cavity_prepack.py` — új `validate_prepack_solver_input_hole_free()` funkció
- `worker/main.py` — a guard meghívása a prepack utáni lépésben

### Olvasandó (kontextus):
- `worker/cavity_prepack.py` — meglévő `build_cavity_prepacked_engine_input()` (sor ~345)
- `vrs_nesting/config/nesting_quality_profiles.py` — `part_in_part == "prepack"` feltétel
- `worker/main.py` — hol hívják a prepacket és az engine CLI-t

---

## Nem célok / scope határok

- Nem módosítja magát a prepack logikát — csak guard.
- Nem hív DB-t, nem ír fájlt.
- Nem módosítja a Rust engine-t vagy annak CLI arg-jait.
- Nem a result normalizert érinti.
- Nem ad silent warning-ot — csak hard fail.

---

## Részletes implementációs lépések

### 1. `worker/cavity_prepack.py`: guard függvény hozzáadása

```python
class CavityPrepackGuardError(CavityPrepackError):
    pass

def validate_prepack_solver_input_hole_free(engine_input: dict[str, Any]) -> None:
    """Raises CavityPrepackGuardError if any top-level part has non-empty holes_points_mm."""
    parts = engine_input.get("parts")
    if not isinstance(parts, list):
        raise CavityPrepackGuardError("CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: invalid parts field")
    violations: list[str] = []
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        holes = part.get("holes_points_mm")
        if isinstance(holes, list) and len(holes) > 0:
            part_id = str(part.get("id") or f"idx:{idx}")
            violations.append(part_id)
    if violations:
        raise CavityPrepackGuardError(
            f"CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: {len(violations)} part(s) still have holes "
            f"after prepack: {', '.join(sorted(violations))}"
        )
```

Exportáld: `__all__` listába add hozzá a `CavityPrepackGuardError`-t és `validate_prepack_solver_input_hole_free`-t.

### 2. `worker/main.py`: guard meghívása

Keresd meg a `build_cavity_prepacked_engine_input()` hívásának helyét. Utána (ha `part_in_part == "prepack"` és `enabled=True`), add hozzá:

```python
if runtime_policy.get("part_in_part") == "prepack":
    from worker.cavity_prepack import validate_prepack_solver_input_hole_free
    validate_prepack_solver_input_hole_free(prepackaged_engine_input)
```

Pontosan a `build_cavity_prepacked_engine_input()` visszatérése után, de az engine CLI hívás előtt helyezd el.

### 3. Tesztek írása

`tests/worker/test_cavity_prepack.py`-ban (vagy külön `tests/worker/test_cavity_prepack_guard.py`-ban):

```python
def test_guard_passes_if_no_top_level_holes():
    # prepackelt input: virtual part holes=[]
    engine_input = {"parts": [{"id": "vp-1", "holes_points_mm": [], "quantity": 1}]}
    validate_prepack_solver_input_hole_free(engine_input)  # nem dob

def test_guard_fails_if_holes_remain():
    engine_input = {"parts": [{"id": "p-1", "holes_points_mm": [[[1,1],[2,1],[2,2],[1,2]]], "quantity": 1}]}
    with pytest.raises(CavityPrepackGuardError) as exc_info:
        validate_prepack_solver_input_hole_free(engine_input)
    assert "CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN" in str(exc_info.value)
    assert "p-1" in str(exc_info.value)

def test_guard_reports_all_violating_parts():
    engine_input = {"parts": [
        {"id": "p-1", "holes_points_mm": [[[1,1],[2,1],[2,2],[1,2]]], "quantity": 1},
        {"id": "p-2", "holes_points_mm": [], "quantity": 1},
        {"id": "p-3", "holes_points_mm": [[[5,5],[6,5],[6,6],[5,6]]], "quantity": 1},
    ]}
    with pytest.raises(CavityPrepackGuardError) as exc_info:
        validate_prepack_solver_input_hole_free(engine_input)
    msg = str(exc_info.value)
    assert "p-1" in msg
    assert "p-3" in msg
    assert "p-2" not in msg
```

---

## Adatmodell / contract változások

- Új `CavityPrepackGuardError` kivétel osztály a `worker/cavity_prepack.py`-ban.
- Új `validate_prepack_solver_input_hole_free()` publikus függvény.
- Nincs JSON schema változás.

---

## Backward compatibility szempontok

- Ha `part_in_part != "prepack"`, a guard nem fut — nincs hatás a meglévő profilokra.
- A `CavityPrepackGuardError` a `CavityPrepackError` alosztálya — meglévő except clauses elkapják.
- A `CavityPrepackError` kivétel kezelése a `worker/main.py`-ban már megvan; a `CavityPrepackGuardError` automatikusan beleesik.

---

## Hibakódok / diagnosztikák

- `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN` — error message prefix, az üzenet tartalmazza a violáló part ID-kat
- Ez **nem warning**, hanem hard fail — a nesting run nem indul el

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/ -k "guard"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md
```

---

## Elfogadási feltételek

- `validate_prepack_solver_input_hole_free()` létezik a `worker/cavity_prepack.py`-ban
- `CavityPrepackGuardError` exportálva van
- Guard futtatva van a `worker/main.py`-ban prepack módban
- Guard tesztek zöldek (min: pass, fail, multi-violator esetek)
- A meglévő cavity tesztek nem törnek el
- `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN` kód megjelenik az exception message-ben

---

## Rollback / safety notes

- A guard csak új kódot ad hozzá, nem módosít meglévő logikát.
- Ha a main.py integráció hibát okoz, a guard import eltávolítható — a prepack maga működik tovább.
- A `CavityPrepackGuardError` catch nélküli terjedés run-fail — ez szándékos.

---

## Dependency

- T01 ajánlott (megismeri a v1-et), de nem kötelező.
- T02 nem szükséges ehhez.
