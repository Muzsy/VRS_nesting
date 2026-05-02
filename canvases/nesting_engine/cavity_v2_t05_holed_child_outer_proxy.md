# Cavity v2 T05 — Lyukas child támogatása outer-only proxyval

## Cél

A `worker/cavity_prepack.py` `_candidate_children()` függvénye jelenleg kemény kizárással elveti a lyukas child alkatrészeket (`child_has_holes_unsupported_v1`). A v2-ben a lyukas child is részt vehet cavity elhelyezésben: a **cavity fit** ellenőrzéséhez az outer kontúrt (lyukak nélkül) használjuk proxyként, de az alkatrész geometriája az exportban teljes marad. A child saját lyukai rekurzívan vizsgálhatók majd (T06).

---

## Miért szükséges

Ha egy child alkatrész maga is lyukas, éppen ő az, aki saját belső cavityt nyújthat egy harmadik (kisebb) alkatrész számára. A v1 kizárás megakadályozta a matrjoska-szerű elhelyezést. A v2 outer proxy megközelítés lehetővé teszi a lyukas child elhelyezését egy cavitybe úgy, hogy:
- A fit check az outer kontúrral működik (lyukak nem akadályozzák)
- Az export pontos geometriát ad (lyukak megmaradnak)
- A child lyukai rekurzívan feldolgozhatók (T06 logikája)

---

## Érintett valós fájlok

### Módosítandó:
- `worker/cavity_prepack.py` — `_candidate_children()`, `_rotation_shapes()`, diagnostic kódok

### Tesztek:
- `tests/worker/test_cavity_prepack.py` — új tesztesetek lyukas child proxy viselkedésre

---

## Nem célok / scope határok

- **Nem** implementálja a rekurzív cavity fill algoritmust (az T06).
- **Nem** módosítja a normalizer-t.
- A lyukas child outer proxyjának létrehozása: csak `holes_points_mm=[]` az `_rotation_shapes()` hívásban — ez már meglévő viselkedés, a v1-ben a `_rotation_shapes()` már ignoral minden lyukat.
- **Nem** törli a gyártási geometriából a child lyukait — azok megmaradnak a part record-ban.

---

## Részletes implementációs lépések

### 1. `_candidate_children()` módosítása

**Jelenlegi állapot (sor ~248-256):**
```python
if part.holes_points_mm:
    diagnostics.append(
        {
            "code": "child_has_holes_unsupported_v1",
            "child_part_revision_id": part.part_id,
        }
    )
    continue
```

**Várt állapot (v2):**
```python
if part.holes_points_mm:
    diagnostics.append(
        {
            "code": "child_has_holes_outer_proxy_used",
            "child_part_revision_id": part.part_id,
            "hole_count": len(part.holes_points_mm),
        }
    )
    # lyukas child engedélyezett outer proxy fittel: NEM continue
```

A lyukas child **nem kap** `continue`-t — bekerül a candidate listába. A `_rotation_shapes()` már most is `holes=[]` proxyval dolgozik (sor ~225), tehát a fit check helyesen outer-only marad.

### 2. Diagnosztika szétválasztása

A `diagnostics` listában legyen különbség:
- `child_has_holes_outer_proxy_used` — lyukas child belép, outer proxy aktív (informális)
- `child_has_holes_unsupported_v1` — ha v1 módban fut (backward compat esetén)

A v2 build folyamatban a `child_has_holes_outer_proxy_used` kerül naplózásra. A `child_has_holes_unsupported_v1` kód megmarad, de csak akkor emittál, ha explicit v1 kompatibilitási mód aktív (nem a main flow-ban).

### 3. `_rotation_shapes()` megjegyzés frissítése

A jelenlegi megjegyzés (sor ~224):
```python
# v1 intentionally ignores child holes: unsupported and filtered before use.
```

Frissítsd:
```python
# outer-only proxy: holes excluded from fit geometry; exact holes preserved in part record for export.
```

### 4. Új tesztek

```python
def test_holed_child_enters_candidate_list():
    """v2: lyukas child outer proxyval részt vehet cavity elhelyezésben."""
    parts = [
        {
            "id": "parent-a",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0, 0, 100, 100),
            "holes_points_mm": [_rect(10, 10, 90, 90)],  # nagy cavity
        },
        {
            "id": "child-b",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0, 0, 20, 20),
            "holes_points_mm": [_rect(5, 5, 15, 15)],  # child maga is lyukas
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    base = _base_input(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot, base_engine_input=base, enabled=True
    )
    # child-b bekerül internal placement-be
    virtual_parts = plan["virtual_parts"]
    assert len(virtual_parts) == 1
    virtual = next(iter(virtual_parts.values()))
    assert len(virtual["internal_placements"]) == 1
    assert virtual["internal_placements"][0]["child_part_revision_id"] == "child-b"
    # quantity csökkent
    assert plan["quantity_delta"]["child-b"]["internal_qty"] == 1

def test_holed_child_diagnostic_is_outer_proxy_used():
    """v2: lyukas child esetén child_has_holes_outer_proxy_used diagnostic jelenik meg."""
    parts = [
        {
            "id": "parent-a",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0, 0, 100, 100),
            "holes_points_mm": [_rect(10, 10, 90, 90)],
        },
        {
            "id": "child-b",
            "quantity": 2,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0, 0, 20, 20),
            "holes_points_mm": [_rect(5, 5, 15, 15)],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    base = _base_input(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot, base_engine_input=base, enabled=True
    )
    diag_codes = [d["code"] for d in plan["diagnostics"]]
    assert "child_has_holes_outer_proxy_used" in diag_codes

def test_v1_solid_child_behavior_unchanged():
    """Meglévő solid child viselkedés változatlan."""
    # ... meglévő teszt futtatása ...
```

### 5. Regression check

A meglévő tesztek mind zöldek maradjanak. A `child_has_holes_unsupported_v1` kód **nem jelenik meg** a normál v2 futásban.

---

## Adatmodell / contract változások

- `diagnostics` listában `child_has_holes_outer_proxy_used` kód jelenik meg lyukas child esetén
- A `quantity_delta` és `instance_bases` struktúra változatlan
- Az `internal_placements` tartalmazza a lyukas child-ot is — a child `holes_points_mm` nincs a placement adatban, azt a normalizer a `part_index`-ből tölti be szükség esetén

---

## Backward compatibility szempontok

- A változtatás a v2 prepack flow-t érinti; a v1 `cavity_plan_v1` output struktúrája változatlan
- A solid child elhelyezés logikája érintetlen
- A `_rotation_shapes()` megjegyzés szövegváltozás nem funkcionális

---

## Hibakódok / diagnosztikák

| Kód | Leírás |
|-----|--------|
| `child_has_holes_outer_proxy_used` | Lyukas child outer proxy fittel jelent meg (v2 normál) |
| `child_has_holes_unsupported_v1` | Lyukas child kizárva (v1 compat mode) |

---

## Tesztelési terv

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "holed_child"
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md
```

---

## Elfogadási feltételek

- Lyukas child nem kap `continue`-t a `_candidate_children()`-ben
- `child_has_holes_outer_proxy_used` diagnostic emittálódik
- Lyukas child bekerülhet `internal_placements`-be, ha geometriailag fér
- A lyukas child `holes_points_mm` **megmarad** a `_PartRecord`-ban (nem módosítható)
- Meglévő solid child tesztek zöldek
- `_rotation_shapes()` megjegyzés frissítve

---

## Rollback / safety notes

- Ha a lyukas child befogadás nem kívánt, a `continue` visszahelyezésével v1 viselkedés visszaállítható
- A `_rotation_shapes()` outer-only logika már most is megvolt — nincs fit ellenőrzési regresszió

---

## Dependency

- T04 ajánlott (v2 schema és konstansok), de T05 önállóan is futtatható a `cavity_plan_v1` outputra.
- T06 (rekurzív fill) épít erre: a lyukas child saját lyukait T06 vizsgálja rekurzívan.
